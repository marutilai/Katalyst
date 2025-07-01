"""
Directory Cache Management

Provides caching for list_files operations to avoid repeated filesystem scans.
Stores complete directory tree after first scan and serves subsequent requests
from memory.
"""

import os
import json
from typing import Dict, List, Optional, Set
from datetime import datetime
from katalyst.katalyst_core.utils.logger import get_logger


class DirectoryCache:
    """
    Manages cached directory listings for the entire project tree.
    
    On first list_files call, performs a full recursive scan from project root
    and caches the complete tree structure. Subsequent calls are served from
    this cache without filesystem access.
    """
    
    def __init__(self, root_path: str):
        """
        Initialize directory cache.
        
        Args:
            root_path: The project root path to cache
        """
        self.root_path = os.path.abspath(root_path)
        self.cache: Dict[str, List[str]] = {}  # path -> list of entries
        self.full_scan_done = False
        self.last_scan_time: Optional[datetime] = None
        self.logger = get_logger()
    
    def perform_full_scan(self, respect_gitignore: bool = True) -> None:
        """
        Perform a complete recursive scan of the project tree.
        
        Args:
            respect_gitignore: Whether to respect .gitignore rules
        """
        self.logger.info(f"[DIRECTORY_CACHE] Starting full scan from root: {self.root_path}")
        start_time = datetime.now()
        
        # Import here to avoid circular dependencies
        from katalyst.katalyst_core.utils.file_utils import should_ignore_path
        
        # Clear existing cache
        self.cache.clear()
        
        # Perform recursive walk
        for root, dirs, files in os.walk(self.root_path):
            # Get relative path from project root
            if root == self.root_path:
                rel_root = "."
            else:
                rel_root = os.path.relpath(root, self.root_path)
            
            # Initialize entry list for this directory
            entries = []
            
            # Filter directories before walking into them
            if respect_gitignore:
                dirs[:] = [
                    d for d in dirs
                    if not should_ignore_path(
                        os.path.join(rel_root, d) if rel_root != "." else d,
                        self.root_path,
                        respect_gitignore
                    )
                ]
            
            # Add directories with trailing slash
            for dirname in sorted(dirs):
                entries.append(dirname + "/")
            
            # Add files
            for filename in sorted(files):
                if respect_gitignore:
                    file_path = os.path.join(rel_root, filename) if rel_root != "." else filename
                    if not should_ignore_path(file_path, self.root_path, respect_gitignore):
                        entries.append(filename)
                else:
                    entries.append(filename)
            
            # Store in cache with absolute path as key
            abs_path = os.path.abspath(root)
            self.cache[abs_path] = entries
        
        self.full_scan_done = True
        self.last_scan_time = datetime.now()
        
        duration = (datetime.now() - start_time).total_seconds()
        self.logger.info(
            f"[DIRECTORY_CACHE] Full scan completed in {duration:.2f}s. "
            f"Cached {len(self.cache)} directories."
        )
    
    def get_listing(self, path: str, recursive: bool) -> Optional[List[str]]:
        """
        Get directory listing from cache.
        
        Args:
            path: Directory path to list
            recursive: Whether to include subdirectory contents
            
        Returns:
            List of entries if found in cache, None otherwise
        """
        abs_path = os.path.abspath(path)
        
        # Non-recursive case: just return the entries for this directory
        if not recursive:
            if abs_path in self.cache:
                self.logger.debug(f"[DIRECTORY_CACHE] Cache hit for {path} (non-recursive)")
                return self.cache[abs_path].copy()
            else:
                self.logger.debug(f"[DIRECTORY_CACHE] Cache miss for {path}")
                return None
        
        # Recursive case: need to collect entries from this dir and all subdirs
        result = []
        
        # Check if the requested path is in cache
        if abs_path not in self.cache:
            self.logger.debug(f"[DIRECTORY_CACHE] Cache miss for {path}")
            return None
        
        # Collect all entries recursively
        for cached_path, entries in self.cache.items():
            # Check if this cached path is under the requested path
            if cached_path == abs_path or cached_path.startswith(abs_path + os.sep):
                # Calculate relative path from requested directory
                if cached_path == abs_path:
                    rel_path = ""
                else:
                    rel_path = os.path.relpath(cached_path, abs_path)
                
                # Add each entry with its relative path
                for entry in entries:
                    if rel_path:
                        # For subdirectories, join the paths
                        full_entry = os.path.normpath(os.path.join(rel_path, entry))
                        # Preserve directory indicators
                        if entry.endswith("/"):
                            full_entry += "/"
                        result.append(full_entry)
                    else:
                        # For the root directory, just add the entry
                        result.append(entry)
        
        self.logger.debug(f"[DIRECTORY_CACHE] Cache hit for {path} (recursive, {len(result)} entries)")
        return sorted(result)
    
    def invalidate(self) -> None:
        """Invalidate the entire cache."""
        self.logger.info("[DIRECTORY_CACHE] Invalidating entire cache")
        self.cache.clear()
        self.full_scan_done = False
        self.last_scan_time = None
    
    def update_for_file_operation(self, file_path: str, operation: str) -> None:
        """
        Update cache for a file operation (create/modify/delete).
        
        Args:
            file_path: Path to the file
            operation: Type of operation (created, modified, deleted)
        """
        if not self.full_scan_done:
            return  # No cache to update
        
        abs_file_path = os.path.abspath(file_path)
        dir_path = os.path.dirname(abs_file_path)
        filename = os.path.basename(abs_file_path)
        
        self.logger.debug(
            f"[DIRECTORY_CACHE] Updating cache for {operation} operation on {file_path}"
        )
        
        # Ensure parent directory exists in cache
        if dir_path not in self.cache:
            # Parent directory doesn't exist in cache, might be newly created
            self.cache[dir_path] = []
        
        entries = self.cache[dir_path]
        
        if operation == "created":
            if filename not in entries:
                entries.append(filename)
                entries.sort()
                self.logger.debug(f"[DIRECTORY_CACHE] Added {filename} to {dir_path}")
        
        elif operation == "deleted":
            if filename in entries:
                entries.remove(filename)
                self.logger.debug(f"[DIRECTORY_CACHE] Removed {filename} from {dir_path}")
        
        # For "modified" operation, no cache update needed (just content changed)
    
    def update_for_directory_creation(self, dir_path: str) -> None:
        """
        Update cache when a new directory is created.
        
        Args:
            dir_path: Path to the new directory
        """
        if not self.full_scan_done:
            return
        
        abs_dir_path = os.path.abspath(dir_path)
        parent_path = os.path.dirname(abs_dir_path)
        dir_name = os.path.basename(abs_dir_path)
        
        self.logger.debug(
            f"[DIRECTORY_CACHE] Updating cache for new directory: {dir_path}"
        )
        
        # Add to parent directory's entries
        if parent_path in self.cache:
            entries = self.cache[parent_path]
            dir_entry = dir_name + "/"
            if dir_entry not in entries:
                entries.append(dir_entry)
                entries.sort()
        
        # Create entry for the new directory itself
        if abs_dir_path not in self.cache:
            self.cache[abs_dir_path] = []
    
    def to_dict(self) -> Dict:
        """Convert cache to dictionary for serialization."""
        return {
            "root_path": self.root_path,
            "cache": self.cache,
            "full_scan_done": self.full_scan_done,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DirectoryCache":
        """Create DirectoryCache from dictionary."""
        cache = cls(data["root_path"])
        cache.cache = data.get("cache", {})
        cache.full_scan_done = data.get("full_scan_done", False)
        if data.get("last_scan_time"):
            cache.last_scan_time = datetime.fromisoformat(data["last_scan_time"])
        return cache