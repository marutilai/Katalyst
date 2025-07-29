# katalyst/katalyst_core/utils/tools.py
import os
import importlib
from typing import List, Dict
import inspect
from typing import Callable
import re
import asyncio
import functools
from langchain_core.tools import StructuredTool
from katalyst.katalyst_core.utils.logger import get_logger

# Directory containing all tool modules
TOOLS_IMPLEMENTATION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "coding_agent",
    "tools",
)


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
    if not os.path.exists(TOOLS_IMPLEMENTATION_DIR):
        print(
            f"Warning (get_tool_functions_map): Tools directory not found at {TOOLS_IMPLEMENTATION_DIR}"
        )
        return tool_functions

    for filename in os.listdir(TOOLS_IMPLEMENTATION_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"katalyst.coding_agent.tools.{filename[:-3]}"
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
        try:
            module_path = f"katalyst.coding_agent.prompts.tools.{prompt_module}"
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
        except Exception:
            continue
    return tool_descriptions




def create_tools_with_context(tool_functions_map: Dict[str, callable], agent_name: str) -> List[StructuredTool]:
    """
    Create StructuredTool instances with agent context logging.
    
    Args:
        tool_functions_map: Dictionary mapping tool names to their functions
        agent_name: Name of the agent (e.g., "PLANNER", "EXECUTOR", "REPLANNER")
    
    Returns:
        List of StructuredTool instances with logging wrappers
    """
    logger = get_logger()
    tools = []
    tool_descriptions_map = dict(extract_tool_descriptions())
    
    for tool_name, tool_func in tool_functions_map.items():
        description = tool_descriptions_map.get(tool_name, f"Tool: {tool_name}")
        
        # Create a wrapper that logs which agent is using the tool
        def make_logging_wrapper(func, t_name):
            @functools.wraps(func)
            def wrapper(**kwargs):
                # Format kwargs for logging, truncating long values
                log_kwargs = {}
                for k, v in kwargs.items():
                    # Skip internal parameters
                    if k in ['auto_approve', 'user_input_fn']:
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
                    # Format kwargs for logging, truncating long values
                    log_kwargs = {}
                    for k, v in kwargs.items():
                        # Skip internal parameters
                        if k in ['auto_approve', 'user_input_fn']:
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
                description=description
            )
        else:
            structured_tool = StructuredTool.from_function(
                func=make_logging_wrapper(tool_func, tool_name),
                name=tool_name,
                description=description
            )
        tools.append(structured_tool)
    
    return tools
