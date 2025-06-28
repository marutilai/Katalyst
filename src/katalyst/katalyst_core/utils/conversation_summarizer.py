"""
Conversation Summarizer Module

Provides utilities to compress conversation history while preserving critical information
for coding agents. Uses LLM to create detailed summaries that capture all essential context.
"""

from typing import List, Dict, Optional
from katalyst.katalyst_core.services.llms import get_llm_client, get_llm_params
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()


class ConversationSummarizer:
    """
    Summarizes conversations and text using LLM to preserve all critical context.
    """
    
    def __init__(self, component: str = "execution"):
        """
        Initialize the conversation summarizer.
        
        Args:
            component: LLM component to use (default: execution for speed)
        """
        self.component = component
        
    def summarize_conversation(
        self,
        messages: List[Dict[str, str]], 
        keep_last_n: int = 5
    ) -> List[Dict[str, str]]:
        """
        Summarize a conversation while preserving all essential context.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            keep_last_n: Number of recent messages to keep unchanged
            
        Returns:
            Compressed conversation with system messages, summary, and recent messages
        """
        if not messages or len(messages) <= keep_last_n:
            return messages
            
        # Separate system messages from conversation
        system_messages = [msg for msg in messages if msg.get('role') == 'system']
        conversation_messages = [msg for msg in messages if msg.get('role') != 'system']
        
        if len(conversation_messages) <= keep_last_n:
            return messages
        
        # Split into messages to summarize and messages to keep
        messages_to_summarize = conversation_messages[:-keep_last_n]
        messages_to_keep = conversation_messages[-keep_last_n:]
        
        logger.info(f"[CONVERSATION_SUMMARIZER] Summarizing {len(messages_to_summarize)} messages, keeping {len(messages_to_keep)} recent")
        
        # Create the summary
        summary = self._create_summary(messages_to_summarize)
        
        if not summary:
            logger.warning("[CONVERSATION_SUMMARIZER] Summary generation failed, returning original")
            return messages
        
        # Build the compressed conversation
        compressed = system_messages.copy()
        
        # Add summary as an assistant message
        compressed.append({
            "role": "assistant",
            "content": f"[CONVERSATION SUMMARY]\n{summary}\n[END OF SUMMARY]"
        })
        
        # Add recent messages
        compressed.extend(messages_to_keep)
        
        # Log compression stats
        original_size = sum(len(msg.get('content', '')) for msg in messages)
        compressed_size = sum(len(msg.get('content', '')) for msg in compressed)
        reduction = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(f"[CONVERSATION_SUMMARIZER] Compressed {original_size} chars to {compressed_size} chars ({reduction:.1f}% reduction)")
        
        return compressed
    
    def summarize_text(self, text: str, context: Optional[str] = None) -> str:
        """
        Summarize a text while preserving technical details.
        
        Args:
            text: Text to summarize  
            context: Optional context about what this text represents
            
        Returns:
            Summarized text
        """
        if not text or len(text.strip()) == 0:
            return text
            
        prompt = self._build_text_summary_prompt(text, context)
        
        try:
            llm = get_llm_client(self.component, async_mode=False, use_instructor=False)
            llm_params = get_llm_params(self.component)
            
            response = llm(
                messages=[{"role": "user", "content": prompt}],
                **llm_params
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"[CONVERSATION_SUMMARIZER] Summarized text from {len(text)} to {len(summary)} chars")
            return summary
            
        except Exception as e:
            logger.error(f"[CONVERSATION_SUMMARIZER] Text summarization failed: {str(e)}")
            return text[:1000] + "... [truncated due to error]"
    
    def _create_summary(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Create a detailed summary following the structured format."""
        
        # Format the conversation history
        formatted_history = []
        for msg in messages:
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')
            formatted_history.append(f"{role}: {content}")
        
        conversation_text = "\n\n".join(formatted_history)
        
        prompt = f"""Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and actions taken.

This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing the work.

Your summary should be structured as follows:

Context: The context to continue the conversation with. This should include:
  1. Previous Conversation: High level details about what was discussed, including the main objectives and any constraints
  2. Current Work: Describe in detail what was being worked on, including specific implementation details
  3. Key Technical Concepts: List all important technical concepts, technologies, coding conventions, and patterns discovered
  4. Relevant Files and Code: Enumerate specific files and code sections examined, modified, or created with their purposes
  5. Problem Solving: Document problems solved thus far and any ongoing troubleshooting efforts
  6. Pending Tasks and Next Steps: Outline all pending tasks and include direct quotes from the most recent conversation showing exactly what task was being worked on and where it was left off

For each section, be specific and include:
- Exact file paths mentioned
- Specific error messages encountered and their resolutions  
- Commands executed and their outcomes
- Code snippets or patterns that were important
- Decisions made and their rationale
- Any discoveries about the codebase structure or dependencies

CONVERSATION TO SUMMARIZE:
{conversation_text}

Output only the summary of the conversation so far, without any additional commentary or explanation."""

        try:
            llm = get_llm_client(self.component, async_mode=False, use_instructor=False)
            llm_params = get_llm_params(self.component)
            
            response = llm(
                messages=[{"role": "user", "content": prompt}],
                **llm_params
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"[CONVERSATION_SUMMARIZER] Failed to create summary: {str(e)}")
            return None
    
    def _build_text_summary_prompt(self, text: str, context: Optional[str]) -> str:
        """Build prompt for text summarization."""
        context_line = f"\nContext: {context}\n" if context else ""
        
        return f"""Summarize the following text while preserving all technical details, code patterns, and important information.{context_line}

Requirements:
- Preserve all file paths, commands, and identifiers exactly
- Keep error messages and their resolutions
- Maintain code snippets that demonstrate patterns or solutions
- Include outcomes of operations (success/failure)
- Note any patterns or insights discovered

TEXT TO SUMMARIZE:
{text}

SUMMARY:"""