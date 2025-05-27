from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
import operator


class KatalystAgentState(BaseModel):
    # --- Inputs to the graph run ---
    task: str = Field(..., description="The current high-level task from the user.")
    current_mode: str = Field(..., description='"architect" or "code".')
    llm_provider: str = Field(
        ..., description='Specific provider name, e.g., "openai", "google"'
    )
    llm_model_name: str = Field(
        ..., description='Specific model name, e.g., "gpt-4-turbo", "gemini-pro"'
    )
    auto_approve: bool = Field(False, description="Whether to skip user confirmations.")
    # verbose_prompt: bool # For debugging prompts - can be added later if needed

    # --- Core graph state ---
    chat_history: List[BaseMessage] = Field(
        default_factory=list, description="The full conversation history with the LLM."
    )

    # --- State for the current LLM interaction cycle ---
    messages_for_next_llm_call: Optional[List[BaseMessage]] = Field(
        None, description="Messages specifically prepared for the next LLM call."
    )
    llm_response_content: Optional[str] = Field(
        None, description="The raw string content from the LLM's last response."
    )
    parsed_tool_call: Optional[Dict[str, Any]] = Field(
        None,
        description="Standardized tool call, e.g., {'tool_name': ..., 'args': {...}}.",
    )
    tool_output: Optional[str] = Field(
        None,
        description="Output from the last executed tool, to be fed into the next prompt.",
    )

    # --- Error and feedback handling for the next LLM prompt ---
    error_message: Optional[str] = Field(
        None,
        description="If a node (e.g., tool execution) encounters an error to report to LLM.",
    )
    user_feedback: Optional[str] = Field(
        None,
        description="If a tool is rejected by the user, this holds their instructions for LLM.",
    )

    # --- Iteration control ---
    current_iteration: int = Field(0, description="Current iteration count.")
    max_iterations: int = Field(10, description="To prevent infinite loops.")
