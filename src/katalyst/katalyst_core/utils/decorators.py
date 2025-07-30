"""Decorators for Katalyst tools."""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Set

from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.file_utils import resolve_and_validate_path
from katalyst.katalyst_core.utils.exceptions import SandboxViolationError
from katalyst.katalyst_core.utils.error_handling import create_error_message, ErrorType


# Common parameter names that typically contain file paths
PATH_PARAM_NAMES = {
    "path", "file_path", "directory", "dir_path", "source_path", 
    "target_path", "dest_path", "destination", "filename", "file"
}


def sandbox_paths(*param_names: str) -> Callable:
    """
    Decorator that validates path parameters are within the project sandbox.
    
    Usage:
        @sandbox_paths()  # Auto-detects common path parameter names
        def my_tool(path: str, ...): ...
        
        @sandbox_paths("custom_path", "another_path")  # Specify custom param names
        def my_tool(custom_path: str, ...): ...
    
    The decorator extracts project_root_cwd from the function's arguments and
    validates all path parameters before calling the function.
    """
    logger = get_logger()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Extract project_root_cwd and allowed_external_paths from arguments
            project_root = None
            allowed_external_paths = None
            
            # Check if there's a 'state' parameter with project_root_cwd and allowed_external_paths
            if 'state' in bound_args.arguments:
                state = bound_args.arguments['state']
                if hasattr(state, 'project_root_cwd'):
                    project_root = state.project_root_cwd
                if hasattr(state, 'allowed_external_paths'):
                    allowed_external_paths = state.allowed_external_paths
            
            # Check if project_root_cwd is passed directly
            if 'project_root_cwd' in bound_args.arguments:
                project_root = bound_args.arguments['project_root_cwd']
            
            # If no project root found, we can't validate paths
            if not project_root:
                logger.warning(
                    f"[SANDBOX] No project_root_cwd found for {func.__name__}, "
                    "path validation skipped"
                )
                return func(*args, **kwargs)
            
            # Determine which parameters to validate
            if param_names:
                # Use explicitly specified parameter names
                params_to_check = set(param_names)
            else:
                # Auto-detect common path parameter names
                params_to_check = PATH_PARAM_NAMES.intersection(bound_args.arguments.keys())
            
            # Validate each path parameter
            for param_name in params_to_check:
                if param_name in bound_args.arguments:
                    path_value = bound_args.arguments[param_name]
                    
                    # Skip None or empty values
                    if not path_value:
                        continue
                    
                    # Handle both string paths and lists of paths
                    if isinstance(path_value, str):
                        paths_to_validate = [path_value]
                    elif isinstance(path_value, (list, tuple)):
                        paths_to_validate = [p for p in path_value if isinstance(p, str)]
                    else:
                        continue
                    
                    # Validate each path
                    for path in paths_to_validate:
                        try:
                            validated_path = resolve_and_validate_path(
                                path, project_root, allowed_external_paths
                            )
                            # Update the path to the validated absolute path
                            if isinstance(path_value, str):
                                bound_args.arguments[param_name] = validated_path
                            # Note: For lists, we keep original to avoid modifying behavior
                            
                            logger.debug(
                                f"[SANDBOX] Validated path for {func.__name__}.{param_name}: "
                                f"{path} -> {validated_path}"
                            )
                        except SandboxViolationError as e:
                            logger.error(
                                f"[SANDBOX] Sandbox violation in {func.__name__}: {e}"
                            )
                            # Return error message in tool format
                            return create_error_message(
                                ErrorType.SANDBOX_VIOLATION,
                                str(e),
                                func.__name__
                            )
            
            # Call the original function with potentially updated paths
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    
    return decorator