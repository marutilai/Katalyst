import os
import json
import stat
from datetime import datetime
from typing import Dict, List, Optional
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.file_utils import should_ignore_path
from katalyst.katalyst_core.utils.decorators import sandbox_paths


@katalyst_tool(prompt_module="ls", prompt_var="LS_TOOL_PROMPT", categories=["planner", "executor", "replanner"])
@sandbox_paths()  # Automatically validates 'path' parameter
def ls(
    path: str = ".",
    all: bool = False,
    long: bool = False,
    recursive: bool = False,
    human_readable: bool = True,
    respect_gitignore: bool = True,
    auto_approve: bool = True,
    project_root_cwd: str = None  # Added to receive project root from context
) -> str:
    """
    List directory contents, similar to Unix ls command.
    
    Args:
        path: Directory to list (default: current directory)
        all: Show hidden files (like ls -a)
        long: Use long listing format (like ls -l)
        recursive: List subdirectories recursively (like ls -R)
        human_readable: Show sizes in human readable format (like ls -h)
        respect_gitignore: Whether to respect .gitignore patterns
        
    Returns:
        JSON with 'path' and 'entries' (list of file/dir info)
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Entering ls with path='{path}', all={all}, long={long}, recursive={recursive}")
    
    # Use current directory if not specified
    if not path:
        path = "."
        
    # Validate path
    if not os.path.exists(path):
        return json.dumps({"error": f"Path not found: {path}"})
    
    # If path is a file, just show that file
    if os.path.isfile(path):
        return _list_single_file(path, long, human_readable)
    
    entries = []
    
    if recursive:
        # Recursive listing
        for root, dirs, files in os.walk(path):
            rel_root = os.path.relpath(root, path)
            
            # Filter directories based on settings
            if not all:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            if respect_gitignore:
                dirs[:] = [
                    d for d in dirs
                    if not should_ignore_path(os.path.join(rel_root, d), path, respect_gitignore)
                ]
            
            # Add directory header for recursive listing
            if rel_root != ".":
                entries.append({
                    "type": "header",
                    "path": rel_root + "/"
                })
            
            # List all items in this directory
            all_items = [(d, True) for d in dirs] + [(f, False) for f in files]
            
            for name, is_dir in sorted(all_items):
                if not all and name.startswith('.'):
                    continue
                    
                full_path = os.path.join(root, name)
                rel_path = os.path.join(rel_root, name) if rel_root != "." else name
                
                if respect_gitignore and should_ignore_path(rel_path, path, respect_gitignore):
                    continue
                
                entry = _create_entry(full_path, rel_path, is_dir, long, human_readable)
                if entry:
                    entries.append(entry)
    else:
        # Non-recursive listing
        try:
            items = os.listdir(path)
            
            # Filter hidden files unless -a flag
            if not all:
                items = [item for item in items if not item.startswith('.')]
            
            # Sort items
            items.sort()
            
            for item in items:
                full_path = os.path.join(path, item)
                
                if respect_gitignore and should_ignore_path(item, path, respect_gitignore):
                    continue
                
                is_dir = os.path.isdir(full_path)
                entry = _create_entry(full_path, item, is_dir, long, human_readable)
                if entry:
                    entries.append(entry)
                    
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return json.dumps({"error": f"Could not list directory: {e}"})
    
    logger.debug(f"[TOOL] Exiting ls successfully, found {len(entries)} items")
    return json.dumps({
        "path": path,
        "entries": entries
    })


def _create_entry(full_path: str, display_name: str, is_dir: bool, long: bool, human_readable: bool) -> Optional[Dict]:
    """Create an entry dict for a file or directory"""
    try:
        if long:
            # Get file stats for long format
            stat_info = os.stat(full_path)
            
            entry = {
                "name": display_name + ("/" if is_dir else ""),
                "type": "dir" if is_dir else "file",
                "size": _format_size(stat_info.st_size, human_readable),
                "permissions": _format_permissions(stat_info.st_mode),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
        else:
            # Simple format
            entry = {
                "name": display_name + ("/" if is_dir else ""),
                "type": "dir" if is_dir else "file"
            }
        
        return entry
    except Exception as e:
        logger.warning(f"Could not stat {full_path}: {e}")
        return None


def _list_single_file(path: str, long: bool, human_readable: bool) -> str:
    """List a single file"""
    try:
        stat_info = os.stat(path)
        
        if long:
            entry = {
                "name": os.path.basename(path),
                "type": "file",
                "size": _format_size(stat_info.st_size, human_readable),
                "permissions": _format_permissions(stat_info.st_mode),
                "modified": datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
        else:
            entry = {
                "name": os.path.basename(path),
                "type": "file"
            }
        
        return json.dumps({
            "path": path,
            "entries": [entry]
        })
    except Exception as e:
        return json.dumps({"error": f"Could not stat file: {e}"})


def _format_size(size: int, human_readable: bool) -> str:
    """Format file size"""
    if not human_readable:
        return str(size)
    
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}P"


def _format_permissions(mode: int) -> str:
    """Format Unix permissions"""
    perms = [
        'r' if mode & stat.S_IRUSR else '-',
        'w' if mode & stat.S_IWUSR else '-',
        'x' if mode & stat.S_IXUSR else '-',
        'r' if mode & stat.S_IRGRP else '-',
        'w' if mode & stat.S_IWGRP else '-',
        'x' if mode & stat.S_IXGRP else '-',
        'r' if mode & stat.S_IROTH else '-',
        'w' if mode & stat.S_IWOTH else '-',
        'x' if mode & stat.S_IXOTH else '-',
    ]
    
    # Add file type prefix
    if stat.S_ISDIR(mode):
        prefix = 'd'
    elif stat.S_ISLNK(mode):
        prefix = 'l'
    else:
        prefix = '-'
    
    return prefix + ''.join(perms)