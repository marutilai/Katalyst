# Context Summarization in Katalyst

Katalyst implements intelligent summarization strategies to manage context size and prevent token bloat, ensuring the agent can operate efficiently even during long-running tasks.

## Overview

The context summarization system consists of two main components:

1. **Conversation History Summarization** - Compresses chat history to maintain context window
2. **Action Trace Summarization** - Manages scratchpad size within subtasks

Both systems use adaptive strategies to balance information preservation with context efficiency.

## Conversation History Summarization

### Purpose
Prevents chat history from exceeding token limits while preserving critical context for decision-making.

### How it Works
- Monitors message count in chat history
- Triggers when threshold is exceeded (default: 50 messages)
- Preserves system messages and recent conversation
- Creates detailed summaries of older messages
- Uses LLM to maintain context continuity

### Configuration
```bash
# Environment variables
KATALYST_CHAT_SUMMARY_TRIGGER=50      # Compress after this many messages
KATALYST_CHAT_SUMMARY_KEEP_LAST_N=10  # Keep this many recent messages unsummarized
```

### Implementation Details
- Located in `katalyst_core/utils/conversation_summarizer.py`
- Integrated via `@compress_chat_history()` decorator
- Separates system messages from conversation
- Creates outcome-focused summaries

### Example
```
Original: 52 messages (14,630 chars)
Compressed: 11 messages (5,605 chars) - 61.7% reduction

[CONVERSATION SUMMARY]
Context: The current state to continue from...
- Original Request: Create a todo app with FastAPI
- Project Structure: mytodo/ folder created with standard directories
- Completed Tasks: 
  - Set up FastAPI project structure
  - Configured main.py with CORS
  - Created Todo model with SQLAlchemy
- Current State: Working on CRUD endpoints
[END OF SUMMARY]

[Recent 10 messages preserved in full...]
```

## Action Trace (Scratchpad) Summarization

### Purpose
Prevents scratchpad bloat within single subtasks, which can cause:
- Performance degradation  
- Token limit issues
- Difficulty finding relevant information

### How it Works

#### Count-Based Trigger (Similar to Conversation History)
- Monitors number of actions in trace
- Triggers when count exceeds threshold (default: 10 actions)
- Preserves recent actions, summarizes older ones
- Individual observations truncated to 1000 chars

#### Adaptive Behavior
- Context > 30KB: Reduces trigger to 5 actions, keep_last_n to 3
- Force summarization when trigger exceeded (regardless of size)
- Summary ineffective (< 10% reduction): Falls back to truncation
- No LLM call for very small traces even if count exceeded

### Configuration
```bash
# Environment variables
KATALYST_ACTION_TRACE_TRIGGER=10       # Trigger after this many actions
KATALYST_ACTION_TRACE_KEEP_LAST_N=5    # Recent actions to keep unsummarized
```

### Key Features

1. **Efficiency First**
   - No wasted LLM calls on small traces
   - Grouped summarization by tool type
   - Smart fallback when summary isn't helpful

2. **Intelligent Compression**
   - Groups actions by tool for concise summaries
   - Preserves file paths and critical errors
   - Focuses on outcomes, not process

3. **Context-Aware Adaptation**
   - Adjusts aggressiveness based on total context size
   - Reduces recent action count for very large traces
   - Truncates individual observations to prevent bloat

### Example

#### Trigger Scenario:
- Action trace has 12 actions (exceeds trigger of 10)
- Older 7 actions get summarized
- Last 5 actions kept in full detail

#### Before (12 actions):
```
Previous Action: list_files
Previous Action Input: {'path': 'mytodo/app'}
Observation: {"files": ["__init__.py", "core/", "database.py", "main.py", "models/", "routers/", "schemas/"]}

Previous Action: read_file  
Previous Action Input: {'path': 'mytodo/app/database.py'}
Observation: [2000+ chars of file content - truncated to 1000]

[... 10 more actions ...]
```

#### After compression:
```
[PREVIOUS ACTIONS SUMMARY]
list_files (3 calls):
  {'path': 'mytodo/app'} → Found standard FastAPI structure
  {'path': 'mytodo/app/routers'} → __init__.py only
  {'path': 'mytodo/app/schemas'} → __init__.py only

write_to_file (2 calls):
  Created mytodo/app/schemas/todo.py with Pydantic models
  Created mytodo/app/routers/todo.py with CRUD endpoints

read_file: {'path': 'mytodo/app/database.py'} → SQLAlchemy setup with SessionLocal
[END OF SUMMARY]

Recent actions and observations:
Previous Action: apply_source_code_diff
Previous Action Input: {'path': 'mytodo/app/routers/todo.py', 'diff': '...'}
Observation: Successfully fixed import statements
[... last 5 actions in full detail ...]
```

## Integration Points

### For Nodes
Conversation summarization is applied automatically via decorator:
```python
@compress_chat_history()
def executor(state: KatalystState) -> KatalystState:
    # Chat history automatically compressed if needed
    ...
```

### For Action Traces
Integrated directly in executor.py:
```python
summarizer = ActionTraceSummarizer(component="execution")
scratchpad_content = summarizer.summarize_action_trace(
    state.action_trace,
    keep_last_n=keep_last_n,
    max_chars=max_chars
)
```

## Performance Impact

### Observed Improvements
- Prevents context from exceeding 80K+ chars
- Reduces negative compression (wasted LLM calls)
- Maintains 40-70% compression on large traces
- Minimal overhead on small contexts

### Trade-offs
- LLM calls for summarization add latency
- Some detail loss in summaries
- Requires careful tuning of thresholds

## Best Practices

1. **Monitor Context Size**
   - Watch for "Very large context detected" warnings
   - Adjust thresholds based on your use case

2. **Tune for Your Workload**
   - Longer tasks may need more aggressive settings
   - Simple tasks can use higher thresholds

3. **Test Summarization Quality**
   - Ensure summaries preserve critical information
   - Verify agent can still complete tasks with compressed context

4. **Use Environment Variables**
   - Adjust without code changes
   - Different settings for dev/prod

## Troubleshooting

### Common Issues

1. **"Negative compression" warnings**
   - Increase MIN_SIZE_FOR_SUMMARY threshold
   - Check if observations are already concise

2. **Agent loses context after summarization**
   - Increase KEEP_LAST_N settings
   - Review summary prompts for information loss

3. **Still hitting token limits**
   - Reduce MAX_CHARS thresholds
   - Enable more aggressive compression
   - Consider breaking tasks into smaller subtasks

### Debug Logging
Enable debug logs to monitor summarization:
```
[ACTION_TRACE_SUMMARIZER] Summarizing 15 actions, keeping 5 recent
[ACTION_TRACE_SUMMARIZER] Compressed 54085 chars to 11354 chars (79.0% reduction)
[CHAT_COMPRESSION] Compressed from 52 to 11 messages (78.8% reduction)
```

## Summary

Katalyst's context summarization ensures efficient agent operation by:
- Intelligently compressing both conversation and action traces
- Adapting compression based on context size
- Preserving critical information while reducing tokens
- Falling back gracefully when compression isn't effective

This enables the agent to handle complex, long-running tasks without context overflow or performance degradation.