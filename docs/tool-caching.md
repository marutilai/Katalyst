# Tool Caching in Katalyst

## Overview

Katalyst implements sophisticated caching mechanisms for file operations to significantly improve performance and reduce redundant I/O operations. The caching system covers two primary tools:

1. **Read File Caching** - Caches file contents to serve subsequent reads from memory
2. **List Files Caching** - Caches directory structure to serve listings without filesystem access

## Benefits

- **Performance**: Eliminates redundant filesystem I/O operations
- **Efficiency**: Cached operations don't consume inner loop cycles
- **Consistency**: Automatic cache updates maintain accuracy
- **Transparency**: Caching is completely transparent to the agent

## Read File Caching

### How It Works

1. **First Read**: When a file is read for the first time, its content is stored in `state.content_store`
2. **Cache Key**: Uses the absolute file path as the cache key
3. **Subsequent Reads**: Future reads of the same file are served directly from cache
4. **Content References**: The observation includes a `content_ref` instead of full content to reduce context size

### Cache Updates

The read file cache is automatically updated when:
- **write_to_file**: New content is cached when writing to a file
- **apply_source_code_diff**: Modified content is re-read and cached after applying diffs

### Example Flow

```python
# First read - hits filesystem
read_file("config.json")  # Content cached at /project/config.json

# Second read - served from cache (instant)
read_file("config.json")  # Returns cached content with "cached": true

# Write updates cache
write_to_file("config.json", new_content)  # Cache updated with new_content

# Next read gets updated content from cache
read_file("config.json")  # Returns new_content from cache
```

## List Files Caching

### How It Works

1. **First Call**: On the first `list_files` call (regardless of path), performs a full recursive scan from project root
2. **Directory Tree**: Builds a complete in-memory directory tree structure
3. **Subsequent Calls**: All future `list_files` calls are served from the cached tree
4. **Smart Traversal**: Handles both recursive and non-recursive queries efficiently

### Cache Structure

```python
DirectoryCache:
  root_path: "/project"
  cache: {
    "/project": ["src/", "tests/", "README.md"],
    "/project/src": ["main.py", "utils/"],
    "/project/src/utils": ["helper.py", "config.py"],
    ...
  }
  full_scan_done: True
```

### Cache Updates

The directory cache is automatically updated when:
- **write_to_file**: 
  - File creation adds entry to parent directory
  - New directories are created if needed
- **apply_source_code_diff**: File modifications don't affect directory structure
- **execute_command**: Entire cache is invalidated (for safety across platforms)

### Cache Invalidation

The directory cache is completely invalidated when `execute_command` is run because:
- Commands can perform arbitrary filesystem operations (rm, mv, mkdir)
- Command syntax varies across platforms (Windows, macOS, Linux)
- Ensures correctness over optimization

### Example Flow

```python
# First list_files call - triggers full root scan
list_files("src", recursive=False)  
# Actually scans entire project, returns just src/ contents

# Subsequent calls - all served from cache
list_files("tests", recursive=True)   # Instant, from cache
list_files(".", recursive=False)      # Instant, from cache
list_files("src/utils", recursive=False)  # Instant, from cache

# File creation updates cache
write_to_file("src/new_module.py", content)  # Cache updated

# Next list shows new file
list_files("src", recursive=False)  # Shows new_module.py from cache

# Command execution invalidates cache
execute_command("echo test")  # Cache cleared

# Next list_files triggers new full scan
list_files("src", recursive=False)  # Performs new root scan
```

## Implementation Details

### State Storage

Both caches are stored in the `KatalystState`:

```python
class KatalystState(BaseModel):
    # Read file cache
    content_store: Dict[str, Tuple[str, str]] = Field(
        default_factory=dict,
        description="Maps file path to (path, content) tuple"
    )
    
    # Directory cache
    directory_cache: Optional[Dict] = Field(
        None,
        description="Cached directory structure after first scan"
    )
```

### Cache Hit Detection

Cache hits are indicated in the tool response:

```json
{
  "path": "/project/src/main.py",
  "content_ref": "/project/src/main.py",
  "cached": true,
  "message": "Content retrieved from cache"
}
```

### Performance Impact

1. **No Inner Cycle Cost**: Cached operations don't increment `inner_cycles`
2. **Instant Response**: Cache lookups are O(1) for files, O(n) for recursive directory listings
3. **Memory Efficient**: Content references reduce observation size by ~25-30%

## Best Practices

### For Agent Developers

1. **Trust the Cache**: The caching system maintains consistency automatically
2. **Avoid Redundant Reads**: The cache eliminates the need to "remember" file contents
3. **Leverage Free Operations**: Cached operations don't count against cycle limits

### For Tool Developers

1. **Cache Updates**: Ensure file-modifying tools update relevant caches
2. **Path Normalization**: Always use absolute paths as cache keys
3. **Invalidation Strategy**: Be conservative - invalidate when uncertain

## Technical Specifications

### Cache Persistence

- Caches are part of the agent state and persist across conversation turns
- Caches are cleared when starting a new conversation

### Memory Management

- Read file cache stores full file contents
- Directory cache stores only filenames and structure
- No automatic eviction - caches grow as needed

### Thread Safety

- Caches are not thread-safe (single-threaded agent execution)
- All cache operations happen synchronously in tool_runner

## Debugging

### Logging

Cache operations are logged for debugging:

```
[INFO] [TOOL_RUNNER][CACHE] Initialized directory cache
[INFO] [TOOL_RUNNER][CACHE_HIT] Returned cached content for main.py
[INFO] [TOOL_RUNNER][DIR_CACHE] Updated directory cache for created file: src/new.py
[INFO] [TOOL_RUNNER][DIR_CACHE] Invalidating directory cache due to execute_command
```

### Cache Statistics

Monitor cache effectiveness through:
- Cache hit rate (logged cache hits vs total operations)
- Memory usage (size of content_store and directory_cache)
- Performance improvement (time saved on cached operations)

## Future Enhancements

Potential improvements to the caching system:

1. **Selective Invalidation**: Parse execute_command to invalidate only affected paths
2. **TTL Support**: Optional time-to-live for cache entries
3. **Size Limits**: Configurable cache size with LRU eviction
4. **Persistent Cache**: Save cache across agent restarts
5. **File Watching**: Use filesystem events for real-time updates

## Conclusion

The tool caching system in Katalyst provides substantial performance improvements while maintaining correctness and transparency. By eliminating redundant I/O operations and reducing context size, it enables agents to work more efficiently within their operational constraints.