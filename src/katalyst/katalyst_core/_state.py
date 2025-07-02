from typing import List, Tuple, Optional, Union, Callable, Dict
from pydantic import BaseModel, Field
from langchain_core.agents import AgentAction, AgentFinish
# MINIMAL: Commented out unused imports
# from langchain_core.messages import BaseMessage
# from katalyst.katalyst_core.utils.tool_repetition_detector import ToolRepetitionDetector
# from katalyst.katalyst_core.utils.operation_context import OperationContext
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
    # MINIMAL: Not used in minimal implementation
    # created_subtasks: Dict[int, List[str]] = Field(
    #     default_factory=dict,
    #     description="Tracks subtasks created dynamically by the agent. Key is parent task index, value is list of created subtask descriptions."
    # )

    # ── ReAct dialogue (inner loop) ───────────────────────────────────────
    # MINIMAL: Written to but not read in minimal implementation (LangGraph uses its own message tracking)
    # chat_history: List[BaseMessage] = Field(
    #     default_factory=list,
    #     description=(
    #         "Full conversation history as LangChain BaseMessage objects "
    #         "(e.g., HumanMessage, AIMessage, SystemMessage, ToolMessage). "
    #         "Used by planner, ReAct agent, and replanner for context."
    #     ),
    # )
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
    # MINIMAL: Used by tool_runner and advance_pointer but redundant with LangGraph's message tracking
    # action_trace: List[Tuple[AgentAction, str]] = Field(
    #     default_factory=list,
    #     description=(
    #         "Sequence of (AgentAction, observation) tuples recorded during "
    #         "each agent↔tool cycle inside the current task. "
    #         "Useful for LangSmith deep-trace or step-by-step UI replay."
    #     ),
    # )
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
    # MINIMAL: Set but minimally used
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
    # MINIMAL: Only reset, not actively used
    # repetition_detector: ToolRepetitionDetector = Field(
    #     default_factory=ToolRepetitionDetector,
    #     description="Detects repetitive tool calls to prevent infinite loops.",
    # )
    
    # ── operation context tracking ─────────────────────────────────────────
    # MINIMAL: Only cleared, not actively used
    # operation_context: OperationContext = Field(
    #     default_factory=lambda: OperationContext(
    #         file_history_limit=int(os.getenv("KATALYST_FILE_CONTEXT_HISTORY", 10)),
    #         operations_history_limit=int(os.getenv("KATALYST_OPERATIONS_CONTEXT_HISTORY", 10))
    #     ),
    #     description="Tracks recent file and tool operations to prevent duplication.",
    # )

    # ── playbook / plan context ─────────────────────────────────────────────
    # MINIMAL: Not used in minimal implementation
    # playbook_guidelines: Optional[str] = Field(
    #     None, description="Playbook or plan guidelines for the current run."
    # )

    # ── content reference system ───────────────────────────────────────────
    # MINIMAL: Not used in minimal implementation
    # content_store: Dict[str, Union[str, Tuple[str, str]]] = Field(
    #     default_factory=dict,
    #     description="Temporary storage for file contents with reference IDs. "
    #                 "Maps ref_id to either content string or (file_path, content) tuple. "
    #                 "Used to prevent content hallucination when passing through LLM."
    # )
    
    # ── directory cache system ─────────────────────────────────────────────
    # MINIMAL: Not used in minimal implementation
    # directory_cache: Optional[Dict] = Field(
    #     None,
    #     description="Cache for list_files operations. Stores complete directory tree "
    #                    "after first scan to serve subsequent requests without file I/O."
    # )

    class Config:
        arbitrary_types_allowed = True  # Enables AgentAction / AgentFinish
