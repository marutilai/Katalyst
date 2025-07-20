# Redundancy Protection in Katalyst

Katalyst implements a three-level protection system to prevent redundant and repetitive tool operations. This multi-layered approach ensures the agent works efficiently without getting stuck in loops or wasting resources on duplicate operations.

## Overview

The redundancy protection system consists of three complementary levels:

1. **Consecutive Duplicate Detection** - Blocks immediate back-to-back identical calls
2. **Repetition Threshold Detection** - Blocks after N identical calls (configurable threshold)
3. **Deterministic State Tracking** - Blocks redundant read operations when data already exists

Each level serves a specific purpose and together they create a comprehensive defense against different types of repetitive behavior.

## Three Levels of Protection

### Level 1: Consecutive Duplicate Detection

**Purpose**: Prevent the most obvious waste - calling the same tool with identical inputs twice in a row.

**How it works**:
- Tracks the last tool call made
- Immediately blocks if the current call is identical to the previous one
- No threshold - instant blocking

**When it triggers**:
```
Agent: read_file(path="config.py")
Result: Success
Agent: read_file(path="config.py")  # <-- BLOCKED immediately
Error: ⚠️ CRITICAL: Tool 'read_file' called with IDENTICAL inputs back-to-back!
```

**Implementation**: `ToolRepetitionDetector.is_consecutive_duplicate()`

### Level 2: Repetition Threshold Detection

**Purpose**: Prevent loops where the agent repeatedly tries the same operation with breaks in between.

**How it works**:
- Tracks recent tool calls in a sliding window
- Counts how many times identical calls appear
- Blocks when count exceeds threshold (default: 3)

**When it triggers**:
```
Agent: read_file(path="app.py")     # Call 1
Agent: list_files(path="./")        # Different operation
Agent: read_file(path="app.py")     # Call 2
Agent: write_to_file(...)           # Different operation
Agent: read_file(path="app.py")     # Call 3 (at threshold)
Agent: search_in_file(...)          # Different operation
Agent: read_file(path="app.py")     # Call 4 - BLOCKED
Error: Tool 'read_file' has been called 4 times with identical inputs
```

**Implementation**: `ToolRepetitionDetector.check()` with configurable `repetition_threshold`

### Level 3: Deterministic State Tracking

**Purpose**: Prevent redundant read operations when the agent already has the information.

**How it works**:
- Tracks successful read operations in `OperationContext`
- Only applies to read operations (read_file, list_files, search_*)
- Checks if the exact operation was already performed successfully
- Never blocks write operations

**When it triggers**:
```
Agent: read_file(path="models.py")   # Success - content in scratchpad
Agent: create_subtask(...)           # Other work...
Agent: write_to_file(...)            # Other work...
Agent: read_file(path="models.py")   # BLOCKED - already have this data
Error: ⚠️ REDUNDANT OPERATION BLOCKED: Tool 'read_file' was already successfully executed
```

**Implementation**: `OperationContext.has_recent_operation()` within individual tool implementations

## Comparison Table

| Feature | Consecutive Detection | Threshold Detection | Deterministic Tracking |
|---------|---------------------|-------------------|----------------------|
| **Blocks writes** | ✓ Yes | ✓ Yes | ✗ No |
| **Blocks failed retries** | ✓ Yes | ✓ Yes | ✗ No |
| **Immediate block** | ✓ Yes | ✗ No | ✗ No |
| **Requires success** | ✗ No | ✗ No | ✓ Yes |
| **Tool coverage** | All tools | All tools | Read operations only |
| **History window** | Last 1 call | Last N calls | Configurable |
| **Configurable** | ✗ No | ✓ Yes (threshold) | ✓ Yes (history size) |

## Example Scenarios

### Scenario 1: Reading Same File Multiple Times
```python
# First read - ALLOWED (no history)
read_file("config.py") ✓

# Immediate re-read - BLOCKED by consecutive detection
read_file("config.py") ✗ [Consecutive Duplicate]

# After other operations - BLOCKED by deterministic tracking
list_files("./")
read_file("config.py") ✗ [Redundant Operation]
```

### Scenario 2: Retrying Failed Operations
```python
# Failed read - ALLOWED
read_file("missing.py") ✓ (fails with "file not found")

# Immediate retry - BLOCKED by consecutive detection
read_file("missing.py") ✗ [Consecutive Duplicate]

# After other operations - ALLOWED (deterministic only tracks successful ops)
write_to_file("other.py", content)
read_file("missing.py") ✓ (may succeed if file now exists)
```

### Scenario 3: Write Operations
```python
# Multiple writes - Subject to consecutive/threshold but NOT deterministic
write_to_file("app.py", "content1") ✓
write_to_file("app.py", "content1") ✗ [Consecutive Duplicate]

# Different content - ALLOWED
write_to_file("app.py", "content2") ✓

# After many operations, same content again
# ... other operations ...
write_to_file("app.py", "content1") ✓ or ✗ [Depends on threshold]
```

### Scenario 4: Search Operations
```python
# Search for pattern - ALLOWED
search_in_file("TODO", "app.py") ✓

# Different pattern - ALLOWED  
search_in_file("FIXME", "app.py") ✓

# Same pattern again - BLOCKED by deterministic
search_in_file("TODO", "app.py") ✗ [Redundant Operation]

# Same pattern, different file - ALLOWED
search_in_file("TODO", "main.py") ✓
```

## Implementation Details

### Key Classes

1. **ToolRepetitionDetector** (`katalyst_core/utils/tool_repetition_detector.py`)
   - Manages consecutive and threshold detection
   - Configurable threshold (default: 3)
   - Sliding window of recent calls

2. **OperationContext** (`katalyst_core/utils/operation_context.py`)
   - Tracks file and tool operations
   - `has_recent_operation()` method for deterministic checks
   - Configurable history limits

3. **Tool Execution** (handled by create_react_agent)
   - Protection mechanisms are integrated into tool implementations
   - Validation happens within individual tools as needed

### Configuration

```python
# In KatalystState initialization
state = KatalystState(
    # Threshold for repetition detection
    repetition_detector=ToolRepetitionDetector(repetition_threshold=3),
    
    # History limits for operation context
    operation_context=OperationContext(
        file_history_limit=10,
        operations_history_limit=10
    ),
    ...
)
```

## Error Messages and Recovery

Each protection level provides specific error messages to guide the agent:

### Consecutive Duplicate Error
```
⚠️ CRITICAL: Tool 'read_file' called with IDENTICAL inputs back-to-back! 
This is wasteful and indicates you're stuck. The operation context shows 
you ALREADY have this information. STOP and use a DIFFERENT approach.
```
**Recovery**: Check scratchpad, try different tool or parameters

### Threshold Exceeded Error
```
Tool 'list_files' has been called 4 times with identical inputs. 
Please try a different approach or tool to avoid getting stuck in a loop.
```
**Recovery**: Reassess approach, consider if information exists elsewhere

### Redundant Operation Error
```
⚠️ REDUNDANT OPERATION BLOCKED: Tool 'read_file' was already successfully 
executed with these inputs. The information you need is in your scratchpad 
from the previous successful call. Check your Recent Tool Operations and 
use the existing information.
```
**Recovery**: Check scratchpad for existing data, proceed with available information

## Best Practices

1. **Configure thresholds based on use case**
   - Lower thresholds for production (stricter)
   - Higher thresholds for development/debugging

2. **Monitor operation context size**
   - Larger history = better redundancy detection
   - But also more memory usage

3. **Handle blocked operations gracefully**
   - Agent should check scratchpad when blocked
   - Use different approaches rather than retrying

4. **Understand the protection layers**
   - Consecutive: Immediate waste prevention
   - Threshold: Loop prevention
   - Deterministic: Efficiency optimization

## Integration Example

Here's how all three levels work together in practice:

```python
# State tracks all three protection mechanisms
state = KatalystState(...)

# In tool execution (handled by create_react_agent):
def validate_tool_call(tool_name, tool_input, state):
    # Level 1 & 2: Repetition detection
    if not state.repetition_detector.check(tool_name, tool_input):
        if state.repetition_detector.is_consecutive_duplicate(...):
            return "BLOCKED: Consecutive duplicate"
        else:
            return "BLOCKED: Repetition threshold exceeded"
    
    # Level 3: Deterministic state tracking  
    if state.operation_context.has_recent_operation(tool_name, tool_input):
        return "BLOCKED: Redundant operation"
    
    return "ALLOWED"
```

## Related Systems

### Context Management
In addition to redundancy protection, Katalyst implements intelligent context summarization to manage token usage and prevent context bloat. See [Context Summarization](context_summarization.md) for details on:
- Conversation history compression
- Action trace (scratchpad) summarization
- Adaptive compression strategies

## Summary

The three-level redundancy protection system in Katalyst provides:

- **Immediate protection** against obvious waste (consecutive duplicates)
- **Loop prevention** through repetition thresholds
- **Efficiency optimization** by tracking successful operations

Together with [context summarization](context_summarization.md), these systems ensure the agent operates efficiently without getting stuck, wasting resources, or running into context limitations. Each level complements the others, creating a robust defense against different patterns of repetitive behavior.