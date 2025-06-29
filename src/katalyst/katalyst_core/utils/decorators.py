"""
Decorators for Katalyst nodes

Provides reusable decorators for common node functionality like
chat history compression, error handling, etc.
"""

import os
import functools
from typing import Callable, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.conversation_summarizer import ConversationSummarizer
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()


def compress_chat_history(
    trigger: Optional[int] = None,
    keep_last_n: Optional[int] = None
) -> Callable:
    """
    Decorator to automatically compress chat history before node execution.
    
    Args:
        trigger: Number of messages that triggers compression (default from env)
        keep_last_n: Number of recent messages to keep (default from env)
        
    Usage:
        @compress_chat_history()  # Use env vars
        def my_node(state: KatalystState) -> KatalystState:
            ...
            
        @compress_chat_history(trigger=30, keep_last_n=8)  # Override
        def my_node(state: KatalystState) -> KatalystState:
            ...
    """
    # Read from environment if not provided
    if trigger is None:
        trigger = int(os.getenv("KATALYST_CHAT_SUMMARY_TRIGGER", 50))
    if keep_last_n is None:
        keep_last_n = int(os.getenv("KATALYST_CHAT_SUMMARY_KEEP_LAST_N", 10))
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: KatalystState) -> KatalystState:
            # Check if compression needed
            if len(state.chat_history) > trigger:
                logger.info(
                    f"[CHAT_COMPRESSION] Compressing chat history in {func.__name__}: "
                    f"{len(state.chat_history)} messages > {trigger} trigger"
                )
                
                # Convert BaseMessage objects to dict format
                messages = []
                for msg in state.chat_history:
                    if isinstance(msg, SystemMessage):
                        role = "system"
                    elif isinstance(msg, HumanMessage):
                        role = "user"
                    elif isinstance(msg, AIMessage):
                        role = "assistant"
                    elif isinstance(msg, ToolMessage):
                        # Tool messages are responses to assistant's tool calls
                        messages.append({
                            "role": "user",
                            "content": f"Tool Result ({getattr(msg, 'name', 'unknown')}): {msg.content}"
                        })
                        continue
                    else:
                        role = "unknown"
                    
                    messages.append({
                        "role": role,
                        "content": msg.content
                    })
                
                # Compress using summarizer
                summarizer = ConversationSummarizer(component="execution")
                compressed_messages = summarizer.summarize_conversation(
                    messages,
                    keep_last_n=keep_last_n
                )
                
                # Convert back to BaseMessage objects
                new_chat_history = []
                for msg in compressed_messages:
                    if msg["role"] == "system":
                        new_chat_history.append(SystemMessage(content=msg["content"]))
                    elif msg["role"] == "user":
                        new_chat_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        new_chat_history.append(AIMessage(content=msg["content"]))
                
                # Log compression stats
                original_count = len(state.chat_history)
                compressed_count = len(new_chat_history)
                logger.info(
                    f"[CHAT_COMPRESSION] Compressed from {original_count} to {compressed_count} messages "
                    f"({((original_count - compressed_count) / original_count * 100):.1f}% reduction)"
                )
                
                # Update state
                state.chat_history = new_chat_history
            
            # Call the original function
            return func(state)
        
        return wrapper
    
    return decorator