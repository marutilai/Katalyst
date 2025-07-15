"""
Utility functions for converting Katalyst tools to LangChain StructuredTools.
"""

import asyncio
import inspect
from typing import List, Dict, Callable
from langchain_core.tools import StructuredTool

from katalyst.katalyst_core.utils.logger import get_logger


def _make_sync_wrapper(async_func):
    """
    Create a synchronous wrapper for an async function.
    
    This is needed because LangGraph's create_react_agent expects synchronous tools,
    but some of our tools are async.
    
    Args:
        async_func: The async function to wrap
        
    Returns:
        A synchronous function that runs the async function in a new event loop
    """
    def sync_wrapper(**kwargs):
        # Run the async function in a new event loop
        return asyncio.run(async_func(**kwargs))
    return sync_wrapper


def convert_tools_to_structured(
    tool_functions: Dict[str, Callable],
    tool_descriptions: Dict[str, str]
) -> List[StructuredTool]:
    """
    Convert Katalyst tool functions to LangChain StructuredTool instances.
    
    This function handles both sync and async tools, creating sync wrappers
    for async functions since LangGraph's create_react_agent expects sync tools.
    
    Args:
        tool_functions: Dictionary mapping tool names to their implementation functions
        tool_descriptions: Dictionary mapping tool names to their descriptions
        
    Returns:
        List of StructuredTool instances ready for use with LangGraph
    """
    logger = get_logger()
    tools = []
    
    for tool_name, tool_func in tool_functions.items():
        description = tool_descriptions.get(tool_name, f"Tool: {tool_name}")
        
        # Handle async tools by creating sync wrappers
        # (LangGraph's create_react_agent expects sync tools)
        if inspect.iscoroutinefunction(tool_func):
            structured_tool = StructuredTool.from_function(
                func=_make_sync_wrapper(tool_func),
                coroutine=tool_func,  # Keep reference to original async function
                name=tool_name,
                description=description
            )
            logger.debug(f"Created sync wrapper for async tool: {tool_name}")
        else:
            # Sync tools can be used directly
            structured_tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_name,
                description=description
            )
            logger.debug(f"Created structured tool for: {tool_name}")
            
        tools.append(structured_tool)
    
    logger.debug(f"Converted {len(tools)} tools to StructuredTool format")
    return tools