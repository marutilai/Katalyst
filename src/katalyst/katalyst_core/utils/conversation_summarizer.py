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
        
        prompt = f"""Your task is to create a RESULT-FOCUSED summary that captures the CURRENT STATE after all actions taken, not the journey of exploration.

CRITICAL INSTRUCTION: Focus on OUTCOMES and CURRENT STATE, not the process or searches performed.

Your summary should be structured as follows:

Context: The current state to continue from. This should include:
  1. Original Request: What the user asked for (one line)
  2. CRITICAL Project Structure: WHERE files should be created
     - Project root directory if mentioned
     - Main project folder and its path relative to root
     - ALWAYS preserve the exact folder structure being used
  3. Completed Tasks: List what has been ACCOMPLISHED with concrete outcomes:
     - Task name: What was created/modified and its EXACT PATH
     - Include FULL PATHS for all files relative to project root
     - Focus on what EXISTS NOW, not how we searched or explored
  4. Current Project State: Describe WHAT EXISTS NOW:
     - List all files created with their FULL PATHS and purpose
     - Current features that are implemented and working
     - What is configured and ready to use
  5. What Does NOT Exist Yet: Explicitly state what hasn't been implemented:
     - Features or files that were searched for but don't exist
     - Functionality that needs to be created from scratch
  6. Technical Setup: Current technologies and dependencies in use
  7. Next Task Context: The immediate next task and what it needs

IMPORTANT RULES:
- ALWAYS include FULL PATHS for every file mentioned relative to project root
- PRESERVE the exact project folder structure in all file paths
- DO NOT mention searches, explorations, or "looked for" - only mention what was FOUND or CREATED
- DO NOT say "searched for X" - instead say "X does not exist yet" or "X was created in Y"
- DO NOT include the journey - only the destination
- BE EXPLICIT about what exists vs what doesn't exist
- Example: Instead of "Searched for CRUD endpoints in multiple locations", write "CRUD endpoints for Todo model do not exist yet and need to be created"

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