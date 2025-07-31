from typing import List, Tuple, Optional, Union, Callable, Dict, Any, Set
from pydantic import BaseModel, Field
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from katalyst.app import config


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
    next_agent: Optional[str] = Field(
        None, description="Next agent to route to (used by router node)"
    )
    plan_feedback: Optional[str] = Field(
        None,
        description="User feedback about the generated plan to be incorporated in replanning.",
    )
    
    # ── security / sandbox ─────────────────────────────────────────────────
    allowed_external_paths: Set[str] = Field(
        default_factory=set,
        description="External file paths explicitly mentioned by user that can bypass sandbox.",
    )
    
    # ── user input handling ───────────────────────────────────────────────
    needs_user_input: bool = Field(
        False,
        description="Flag indicating the agent needs user input to continue.",
    )
    user_input_required: Optional[Dict[str, Any]] = Field(
        None,
        description="Details about the user input needed (question, suggested_responses, tool_name).",
    )
    user_input_response: Optional[str] = Field(
        None,
        description="User's response to the input request.",
    )

    # ── loop guardrails ───────────────────────────────────────────────────
    inner_cycles: int = Field(
        0, description="Count of agent↔tool cycles in the current task."
    )
    max_inner_cycles: int = Field(
        default=config.MAX_INNER_CYCLES,
        description="Abort inner loop once this many cycles are hit.",
    )
    outer_cycles: int = Field(
        0, description="Count of planner→replanner cycles for the whole run."
    )
    max_outer_cycles: int = Field(
        default=config.MAX_OUTER_CYCLES,
        description="Abort outer loop once this many cycles are hit.",
    )

    class Config:
        arbitrary_types_allowed = True  # Enables AgentAction / AgentFinish