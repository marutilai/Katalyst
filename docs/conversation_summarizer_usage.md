# Conversation Summarizer Usage Guide

The `ConversationSummarizer` class provides intelligent conversation and text compression using LLM to create detailed summaries that preserve all essential context.

## Basic Usage

### Initialize the Summarizer

```python
from katalyst.katalyst_core.utils.conversation_summarizer import ConversationSummarizer

# Use default execution LLM for speed
summarizer = ConversationSummarizer()

# Or use reasoning LLM for better quality
summarizer = ConversationSummarizer(component="reasoning")
```

## Conversation Summarization

The summarizer creates RESULT-FOCUSED summaries that capture:
- Original user request
- Completed tasks with concrete outcomes (what was CREATED)
- Current project state (what EXISTS NOW)
- What does NOT exist yet (explicitly stated)
- Technical setup and dependencies
- Next task context and requirements

### Example Usage

```python
# Long conversation that needs compression
messages = [
    {"role": "system", "content": "You are a coding assistant"},
    {"role": "user", "content": "Help me build a web scraper"},
    {"role": "assistant", "content": "I'll help you build a web scraper..."},
    # ... many more messages ...
]

# Summarize keeping last 5 messages
compressed = summarizer.summarize_conversation(messages, keep_last_n=5)

# Result structure:
# - All system messages preserved
# - Detailed summary as an assistant message with [CONVERSATION SUMMARY] markers
# - Last 5 messages kept as-is
```

## Text Summarization

Summarize long text outputs while preserving technical details:

```python
# Long command output or file content
long_output = "npm install output with hundreds of lines..."

# Basic summarization
summary = summarizer.summarize_text(long_output)

# With context for better results
summary = summarizer.summarize_text(
    long_output, 
    context="npm install output showing dependency tree"
)
```

## Integration Example

### In Agent React

```python
from katalyst.katalyst_core.utils.conversation_summarizer import ConversationSummarizer

def manage_conversation_context(state: KatalystState) -> None:
    """Compress conversation when it gets too long."""
    
    # Convert chat history to proper format if needed
    messages = []
    for msg in state.chat_history:
        messages.append({
            "role": msg.type,  # system, human, ai
            "content": msg.content
        })
    
    # Check if compression needed (e.g., > 50 messages)
    if len(messages) > 50:
        summarizer = ConversationSummarizer()
        
        # Compress keeping last 10 messages
        compressed = summarizer.summarize_conversation(messages, keep_last_n=10)
        
        # Update state with compressed history
        # (Implementation depends on your state structure)
        logger.info(f"Compressed conversation from {len(messages)} to {len(compressed)} messages")
```

### For Action Trace Compression

```python
def compress_action_trace(action_trace: List[Tuple]) -> str:
    """Create a summary of action trace for context."""
    
    # Convert to conversation format
    messages = []
    for action, observation in action_trace:
        messages.append({
            "role": "assistant",
            "content": f"Action: {action.tool} with {action.tool_input}"
        })
        messages.append({
            "role": "user",
            "content": f"Result: {observation}"
        })
    
    # Summarize the actions
    summarizer = ConversationSummarizer()
    compressed = summarizer.summarize_conversation(messages, keep_last_n=5)
    
    # Extract just the summary part
    for msg in compressed:
        if "[CONVERSATION SUMMARY]" in msg.get("content", ""):
            return msg["content"]
    
    return "No summary generated"
```

## Summary Structure

The generated summaries follow this OUTCOME-FOCUSED structure:

```
Context: The current state to continue from.
1. Original Request: What the user asked for (concise)
2. Completed Tasks: What was ACCOMPLISHED with concrete outcomes
3. Current Project State: What EXISTS NOW (files, features, configurations)
4. What Does NOT Exist Yet: Explicitly stated missing functionality
5. Technical Setup: Current technologies and dependencies
6. Next Task Context: The immediate next task and requirements
```

Key principles:
- Focus on RESULTS not process
- State what EXISTS vs what DOESN'T EXIST
- No mention of searches or explorations
- Concrete outcomes only
- Clear action items for next steps

## Error Handling

The summarizer handles errors gracefully:
- If LLM fails during conversation summary, returns original messages
- If LLM fails during text summary, returns truncated text with error marker
- System messages are always preserved regardless of errors

## Best Practices

1. **Choose appropriate keep_last_n**: Balance between context and token usage
2. **Use context parameter**: Provide context for better text summarization
3. **Monitor compression**: Log shows reduction percentage
4. **Component selection**: Use "execution" for speed, "reasoning" for quality
5. **Preserve system prompts**: System messages are never compressed

## Performance Notes

- Adds 1-3 seconds for LLM summarization call
- Typical compression: 40-70% reduction in size
- Preserves all critical technical information
- Structured format ensures continuity of work