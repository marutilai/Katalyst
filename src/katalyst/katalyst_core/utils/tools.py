# katalyst/katalyst_core/utils/tools.py
import os
import importlib
from typing import List, Dict, Optional
import inspect
from typing import Callable, TYPE_CHECKING
import re
import asyncio
import functools
from langchain_core.tools import StructuredTool
from katalyst.katalyst_core.utils.logger import get_logger

if TYPE_CHECKING:
    from katalyst.katalyst_core.state import KatalystState

# Directories containing tool modules
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CODING_TOOLS_DIR = os.path.join(BASE_DIR, "coding_agent", "tools")
DATA_SCIENCE_TOOLS_DIR = os.path.join(BASE_DIR, "data_science_agent", "tools")


def katalyst_tool(func=None, *, prompt_module=None, prompt_var=None, categories=None):
    """
    Decorator to mark a function as a Katalyst tool, with optional prompt module/variable metadata.
    Usage:
        @katalyst_tool
        def foo(...): ...
    or
        @katalyst_tool(prompt_module="bar", prompt_var="BAR_PROMPT", categories=["planner", "executor"])
        def foo(...): ...
    """

    def wrapper(f):
        f._is_katalyst_tool = True
        if prompt_module:
            f._prompt_module = prompt_module
        if prompt_var:
            f._prompt_var = prompt_var
        # Default to ["executor"] for backward compatibility
        f._categories = categories if categories else ["executor"]
        return f

    if func is None:
        return wrapper
    return wrapper(func)




def get_tool_functions_map(category=None) -> Dict[str, callable]:
    """
    Returns a mapping of tool function names to their function objects.
    Only includes functions decorated with @katalyst_tool.
    
    Args:
        category: Optional category to filter tools by (e.g., "planner", "executor").
                 If None, returns all tools.
    """
    tool_functions = {}
    
    # Check both coding and data science tool directories
    tool_dirs = [
        (CODING_TOOLS_DIR, "katalyst.coding_agent.tools"),
        (DATA_SCIENCE_TOOLS_DIR, "katalyst.data_science_agent.tools")
    ]
    
    for tools_dir, module_prefix in tool_dirs:
        if not os.path.exists(tools_dir):
            continue
            
        for filename in os.listdir(tools_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"{module_prefix}.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    for attr_name in dir(module):
                        func_candidate = getattr(module, attr_name)
                        if callable(func_candidate) and getattr(
                            func_candidate, "_is_katalyst_tool", False
                        ):
                            # Check category filter if provided
                            if category:
                                tool_categories = getattr(func_candidate, "_categories", ["executor"])
                                if category not in tool_categories:
                                    continue
                            
                            # Use the stored LLM-facing tool name if available, else func name
                            tool_key = getattr(
                                func_candidate,
                                "_tool_name_for_llm_",
                                func_candidate.__name__,
                            )
                            tool_functions[tool_key] = func_candidate
                except ImportError as e:
                    print(
                        f"Warning (get_tool_functions_map): Could not import module {module_name}. Error: {e}"
                    )
    return tool_functions




def extract_tool_descriptions():
    """
    Returns a list of (tool_name, one_line_description) for all registered tools.
    The description is the first line after 'Description:' in the tool's prompt file.
    """
    tool_map = get_tool_functions_map()
    tool_descriptions = []
    for tool_name, func in tool_map.items():
        prompt_module = getattr(func, "_prompt_module", tool_name)
        prompt_var = getattr(func, "_prompt_var", f"{tool_name.upper()}_PROMPT")
        
        # Try both coding and data science prompt paths
        for prompt_prefix in ["katalyst.coding_agent.prompts.tools", "katalyst.data_science_agent.prompts.tools"]:
            try:
                module_path = f"{prompt_prefix}.{prompt_module}"
                module = importlib.import_module(module_path)
                prompt_str = getattr(module, prompt_var, None)
                if not prompt_str or not isinstance(prompt_str, str):
                    continue
                # Find the first line after 'Description:'
                match = re.search(r"Description:(.*)", prompt_str)
                if match:
                    desc = match.group(1).strip().split(". ")[0].strip()
                    if not desc.endswith("."):
                        desc += "."
                    tool_descriptions.append((tool_name, desc))
                    break  # Found it, don't try other prefix
            except Exception:
                continue
    return tool_descriptions




def _inject_context_from_state(func: Callable, kwargs: dict, state: Optional['KatalystState']) -> None:
    """
    Helper function to inject context from state into tool kwargs.
    
    Args:
        func: The function to inspect for parameters
        kwargs: The kwargs dict to update with context
        state: Optional KatalystState containing context
    """
    if state:
        sig = inspect.signature(func)
        if 'project_root_cwd' in sig.parameters and hasattr(state, 'project_root_cwd'):
            kwargs['project_root_cwd'] = state.project_root_cwd
        if 'user_input_fn' in sig.parameters and hasattr(state, 'user_input_fn'):
            kwargs['user_input_fn'] = state.user_input_fn
        if 'auto_approve' in sig.parameters and hasattr(state, 'auto_approve'):
            kwargs['auto_approve'] = state.auto_approve


def create_tools_with_context(tool_functions_map: Dict[str, callable], agent_name: str, state: Optional['KatalystState'] = None) -> List[StructuredTool]:
    """
    Create StructuredTool instances with agent context logging.
    
    Args:
        tool_functions_map: Dictionary mapping tool names to their functions
        agent_name: Name of the agent (e.g., "PLANNER", "EXECUTOR", "REPLANNER")
        state: Optional KatalystState to extract project_root_cwd from
    
    Returns:
        List of StructuredTool instances with logging wrappers
    """
    logger = get_logger()
    tools = []
    tool_descriptions_map = dict(extract_tool_descriptions())
    
    # Import args schema for tools that need it
    args_schema_map = {}
    try:
        from katalyst.katalyst_core.utils.models import RequestUserInputArgs
        args_schema_map['request_user_input'] = RequestUserInputArgs
    except ImportError:
        pass
    
    for tool_name, tool_func in tool_functions_map.items():
        description = tool_descriptions_map.get(tool_name, f"Tool: {tool_name}")
        
        # Create a wrapper that logs which agent is using the tool
        def make_logging_wrapper(func, t_name):
            @functools.wraps(func)
            def wrapper(**kwargs):
                # Inject context from state if available and tool needs it
                _inject_context_from_state(func, kwargs, state)
                
                # Format kwargs for logging, truncating long values
                log_kwargs = {}
                for k, v in kwargs.items():
                    # Skip internal parameters
                    if k in ['auto_approve', 'user_input_fn', 'project_root_cwd']:
                        continue
                    if isinstance(v, str) and len(v) > 100:
                        log_kwargs[k] = v[:100] + "..."
                    elif isinstance(v, list) and len(str(v)) > 100:
                        log_kwargs[k] = f"[list with {len(v)} items]"
                    else:
                        log_kwargs[k] = v
                logger.info(f"[{agent_name}] Calling tool: {t_name} with {log_kwargs}")
                return func(**kwargs)
            return wrapper
        
        if inspect.iscoroutinefunction(tool_func):
            # For async functions, create a sync wrapper with logging
            def make_sync_wrapper(async_func, t_name):
                def sync_wrapper(**kwargs):
                    # Inject context from state if available and tool needs it
                    _inject_context_from_state(async_func, kwargs, state)
                    
                    # Format kwargs for logging, truncating long values
                    log_kwargs = {}
                    for k, v in kwargs.items():
                        # Skip internal parameters
                        if k in ['auto_approve', 'user_input_fn', 'project_root_cwd']:
                            continue
                        if isinstance(v, str) and len(v) > 100:
                            log_kwargs[k] = v[:100] + "..."
                        elif isinstance(v, list) and len(str(v)) > 100:
                            log_kwargs[k] = f"[list with {len(v)} items]"
                        else:
                            log_kwargs[k] = v
                    logger.info(f"[{agent_name}] Calling tool: {t_name} with {log_kwargs}")
                    return asyncio.run(async_func(**kwargs))
                return sync_wrapper
            
            structured_tool = StructuredTool.from_function(
                func=make_sync_wrapper(tool_func, tool_name),  # Sync wrapper with logging
                coroutine=tool_func,  # Async version
                name=tool_name,
                description=description,
                args_schema=args_schema_map.get(tool_name)  # Add schema if available
            )
        else:
            structured_tool = StructuredTool.from_function(
                func=make_logging_wrapper(tool_func, tool_name),
                name=tool_name,
                description=description,
                args_schema=args_schema_map.get(tool_name)  # Add schema if available
            )
        tools.append(structured_tool)
    
    return tools
