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

    # ── long-horizon planning ─────────────────────────────────────────────
    task_queue: List[str] = Field(
        default_factory=list, description="Remaining tasks produced by the planner."
    )
    task_idx: int = Field(
        0, description="Index of the task currently being executed (0-based)."
    )
    original_plan: Optional[List[str]] = Field(
        default=None, description="The initial plan created by the planner."
    )

    # ── ReAct dialogue (inner loop) ───────────────────────────────────────
    agent_executor: Optional[Any] = Field(
        None,
        exclude=True,  # Don't persist the agent instance
        description="The persistent create_react_agent instance"
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
    completed_tasks: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="(task, summary) tuples appended after each task finishes.",
    )
    tool_execution_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Concise history of all tool executions across all tasks. "
            "Each entry contains: task, tool_name, status (success/error), summary. "
            "Used by replanner to understand full execution context."
        ),
    )

    # ── error / completion flags ──────────────────────────────────────────
    error_message: Optional[str] = Field(
        None,
        description="Captured exception text with trace (fed back into LLM for self-repair).",
    )
    response: Optional[str] = Field(
        None, description="Final deliverable once the outer loop terminates."
    )
    plan_feedback: Optional[str] = Field(
        None,
        description="User feedback about the generated plan to be incorporated in replanning.",
    )

    # ── loop guardrails ───────────────────────────────────────────────────
    inner_cycles: int = Field(
        0, description="Count of agent↔tool cycles in the current task."
    )
    max_inner_cycles: int = Field(
        default=int(os.getenv("KATALYST_MAX_INNER_CYCLES", 20)),
        description="Abort inner loop once this many cycles are hit.",
    )
    outer_cycles: int = Field(
        0, description="Count of planner→replanner cycles for the whole run."
    )
    max_outer_cycles: int = Field(
        default=int(os.getenv("KATALYST_MAX_OUTER_CYCLES", 5)),
        description="Abort outer loop once this many cycles are hit.",
    )

    class Config:
        arbitrary_types_allowed = True  # Enables AgentAction / AgentFinish