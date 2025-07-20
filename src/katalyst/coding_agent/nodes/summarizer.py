"""
Conversation Summarization Node - Manages context through intelligent summarization.

Uses LangMem's SummarizationNode to compress conversation history when token
counts exceed configured thresholds, preserving essential context.
"""

from langmem.short_term import SummarizationNode
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.utils import count_tokens_approximately
from katalyst.katalyst_core.services.llms import get_llm_client
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.app.config import (
    MAX_AGGREGATE_TOKENS,
    MAX_TOKENS_BEFORE_SUMMARY,
    MAX_SUMMARY_TOKENS
)

logger = get_logger()


# Concise summarization prompt adapted from PR #43
SUMMARIZATION_PROMPT = """Summarize the conversation to preserve essential context for task completion.

Create a structured summary including:

1. **User's Request**: Original task and all explicit requirements
2. **Completed Work**: Tasks finished with key decisions and outcomes
3. **Technical Context**: Important files, code patterns, and architectural choices
4. **Current Status**: What was being worked on in the most recent messages
5. **Next Steps**: Any pending tasks or unresolved issues

Focus on information needed to continue work effectively. Preserve:
- File paths and code snippets
- User preferences and decisions
- Error solutions and workarounds
- Task dependencies and order

Be concise but thorough. Omit redundant tool outputs while keeping results."""


def get_summarization_node():
    """
    Create and configure a LangMem summarization node for conversation compression.
    
    Returns:
        SummarizationNode: Configured node that automatically summarizes conversations
                          when token thresholds are exceeded.
    """
    # Create prompt template
    initial_summary_prompt = ChatPromptTemplate.from_messages([
        ("placeholder", "{messages}"),
        ("user", SUMMARIZATION_PROMPT),
    ])
    
    # Get LLM client for summarization
    client = get_llm_client("summarizer")
    
    # Create and configure summarization node
    summarization_node = SummarizationNode(
        token_counter=count_tokens_approximately,
        model=client,
        max_tokens=MAX_AGGREGATE_TOKENS,
        max_tokens_before_summary=MAX_TOKENS_BEFORE_SUMMARY,
        initial_summary_prompt=initial_summary_prompt,
        max_summary_tokens=MAX_SUMMARY_TOKENS,
        # Replace messages in place
        output_messages_key="messages",
    )
    
    logger.debug(f"[SUMMARIZER] Created node with thresholds: "
                f"trigger={MAX_TOKENS_BEFORE_SUMMARY}, "
                f"max={MAX_AGGREGATE_TOKENS}, "
                f"summary_budget={MAX_SUMMARY_TOKENS}")
    
    return summarization_node