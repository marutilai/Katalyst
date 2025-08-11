"""
Execute data science code in a persistent Jupyter kernel.

This tool maintains state across executions, allowing for incremental data analysis.
"""

import os
from katalyst.katalyst_core.utils.tools import katalyst_tool
# Temporarily use simple kernel manager to fix communication issues
from katalyst.data_science_agent.kernel_manager_simple import get_kernel_manager


@katalyst_tool(prompt_module="execute_data_code", prompt_var="EXECUTE_DATA_CODE_TOOL_PROMPT", categories=["planner", "executor"])
def execute_data_code(code: str, timeout: int = 120) -> str:
    """
    Execute Python code in a persistent Jupyter kernel.
    
    State is maintained across executions, so variables and imports persist.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (default: 120, suitable for data operations)
    
    Returns:
        String containing execution output or error information
    """
    kernel_manager = get_kernel_manager()
    
    # Allow timeout override via environment variable
    env_timeout = os.getenv('KATALYST_KERNEL_TIMEOUT')
    if env_timeout:
        try:
            timeout = int(env_timeout)
        except ValueError:
            pass  # Use default if env var is invalid
    
    try:
        # Execute code
        result = kernel_manager.execute_code(code, timeout)
        
        # Format output
        output_parts = []
        
        # Add stdout/expression results
        if result['outputs']:
            output_parts.extend(result['outputs'])
        
        # Add errors if any
        if result['errors']:
            for error in result['errors']:
                output_parts.append(f"\n{error['ename']}: {error['evalue']}")
                if error['traceback']:
                    output_parts.append('\n'.join(error['traceback']))
        
        # Handle rich outputs (like plots)
        if result['data']:
            for mime_type, data in result['data'].items():
                if mime_type == 'image/png':
                    output_parts.append("[Plot displayed]")
                elif mime_type == 'text/html':
                    output_parts.append("[HTML output]")
                elif mime_type != 'text/plain':  # text/plain already in outputs
                    output_parts.append(f"[{mime_type} output]")
        
        return '\n'.join(output_parts) if output_parts else "Code executed successfully (no output)"
        
    except Exception as e:
        error_msg = str(e)
        # For now, just return the error
        # The simple kernel manager should handle most issues
        return f"Error executing code: {error_msg}"