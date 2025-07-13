from typing import List, Tuple, Optional, Union, Callable, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
import os


class KatalystState(BaseModel):
    # ── immutable run-level inputs ─────────────────────────────────────────
    task: str = Field(
        ..., description="Top-level user request that kicks off the whole run."
    )
    auto_approve: bool = Field(
        False, description="If True, file-writing tools skip interactive confirmation."
    )
    project_root_cwd: str = Field(
        ..., description="The CWD from which Katalyst was launched."
    )
    user_input_fn: Optional[Callable[[str], str]] = Field(
        default=None,
        exclude=True,
        description="Function to use for user input (not persisted).",
    )

    # ── todo list management ──────────────────────────────────────────────
    todo_list: List[str] = Field(
        default_factory=list, description="Current todo list managed by agent."
    )
    completed_todos: List[str] = Field(
        default_factory=list, description="Completed todo items for tracking."
    )

    # ── ReAct dialogue (inner loop) ───────────────────────────────────────
    agent_executor: Optional[Any] = Field(
        None,
        exclude=True,  # Don't persist the agent instance
        description="The persistent create_react_agent instance"
    )
    checkpointer: Optional[Any] = Field(
        None,
        exclude=True,  # Don't persist the checkpointer instance
        description="The checkpointer to use for the agent"
    )
    messages: List[BaseMessage] = Field(
        default_factory=list,
        description="Accumulated messages for the persistent agent conversation"
    )
    agent_outcome: Optional[Union[AgentAction, AgentFinish]] = Field(
        None,
        description=(
            "Output of the latest LLM call: "
            "• AgentAction → invoke tool\n"
            "• AgentFinish → task completed"
        ),
    )

    # ── execution trace / audit ───────────────────────────────────────────
    tool_execution_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description=(
            "History of all tool executions. "
            "Each entry contains: tool_name, status (success/error), summary."
        ),
    )

    # ── error / completion flags ──────────────────────────────────────────
    error_message: Optional[str] = Field(
        None,
        description="Captured exception text with trace (fed back into LLM for self-repair).",
    )
    response: Optional[str] = Field(
        None, description="Final deliverable from the agent."
    )
    completion_status: Optional[str] = Field(
        None,
        description="Set to 'completed' when agent finishes via attempt_completion tool.",
    )

    # ── loop guardrails ───────────────────────────────────────────────────
    agent_cycles: int = Field(
        0, description="Count of agent reasoning cycles."
    )
    max_agent_cycles: int = Field(
        default=int(os.getenv("KATALYST_MAX_AGENT_CYCLES", 50)),
        description="Abort agent once this many cycles are hit.",
    )

    class Config:
        arbitrary_types_allowed = True  # Enables AgentAction / AgentFinish