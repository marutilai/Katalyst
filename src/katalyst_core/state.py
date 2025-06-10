from typing import List, Tuple, Optional, Union
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

    # ── long-horizon planning ─────────────────────────────────────────────
    task_queue: List[str] = Field(
        default_factory=list, description="Remaining tasks produced by the planner."
    )
    task_idx: int = Field(
        0, description="Index of the task currently being executed (0-based)."
    )

    # ── ReAct dialogue (inner loop) ───────────────────────────────────────
    chat_history: List[BaseMessage] = Field(
        default_factory=list,
        description=(
            "Full conversation history as LangChain BaseMessage objects "
            "(e.g., HumanMessage, AIMessage, SystemMessage, ToolMessage). "
            "Used by planner, ReAct agent, and replanner for context."
        ),
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
    action_trace: List[Tuple[AgentAction, str]] = Field(
        default_factory=list,
        description=(
            "Sequence of (AgentAction, observation) tuples recorded during "
            "each agent↔tool cycle inside the current task. "
            "Useful for LangSmith deep-trace or step-by-step UI replay."
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

    # ── playbook / plan context ─────────────────────────────────────────────
    playbook_guidelines: Optional[str] = Field(
        None, description="Playbook or plan guidelines for the current run."
    )

    class Config:
        arbitrary_types_allowed = True  # Enables AgentAction / AgentFinish
