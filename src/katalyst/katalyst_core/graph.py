from langgraph.graph import StateGraph, START, END
from langchain_core.agents import AgentAction

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.routing import (
    route_after_agent,
    route_after_pointer,
    route_after_replanner,
    route_after_verification,
)
from katalyst.coding_agent.nodes.planner import planner
from katalyst.coding_agent.nodes.agent_react import agent_react
from katalyst.coding_agent.nodes.tool_runner import tool_runner
from katalyst.coding_agent.nodes.advance_pointer import advance_pointer
from katalyst.coding_agent.nodes.replanner import replanner
from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification


# Node-callable functions (define/import elsewhere in your code‑base)
# ------------------------------------------------------------------
# • planner                    – produces an ordered list of sub‑tasks in ``state.task_queue``
# • human_plan_verification    – allows user to approve/reject plan with feedback
# • agent_react                – LLM step that yields AgentAction / AgentFinish in ``state.agent_outcome``
# • tool_runner                – executes Python tool extracted from AgentAction
# • advance_pointer            – increments ``state.task_idx`` and resets ``state.inner_cycles`` & ``state.action_trace``
# • replanner                  – builds a fresh plan or final answer when current plan exhausted
# ------------------------------------------------------------------

# ─────────────────────────────────────────────────────────────────────────────
# TWO-LEVEL AGENT STRUCTURE WITH HUMAN-IN-THE-LOOP
# ─────────────────────────────────────────────────────────────────────────────
# 1. OUTER LOOP  (Plan-and-Execute with Human Verification)
#    planner → human_verification → ⟮ INNER LOOP ⟯ → advance_pointer → replanner
#         ↑            ↓                                    ↑               ↓
#         └─ feedback ─┘                                    └─ new plan ───┘
#                                                                          ↓
#                                                         human_verification → END
#
# 2. INNER LOOP  (ReAct over a single task)
#    agent_react  →  tool_runner  →  agent_react  (repeat until AgentFinish)
# ─────────────────────────────────────────────────────────────────────────────


def build_compiled_graph():
    g = StateGraph(KatalystState)

    # ── planner: generates the initial list of sub‑tasks ─────────────────────────
    g.add_node("planner", planner)
    
    # ── human verification: allows user to review/modify plans ────────────────────
    g.add_node("human_plan_verification", human_plan_verification)

    # ── INNER LOOP nodes ─────────────────────────────────────────────────────────
    g.add_node("agent_react", agent_react)  # LLM emits AgentAction/Finish
    g.add_node("tool_runner", tool_runner)  # Executes the chosen tool
    g.add_node("advance_pointer", advance_pointer)  # Marks task complete

    # ── replanner: invoked when plan is exhausted or needs adjustment ────────────
    g.add_node("replanner", replanner)

    # ── edges for OUTER LOOP ─────────────────────────────────────────────────────
    g.add_edge(START, "planner")  # start → planner
    g.add_edge("planner", "human_plan_verification")  # planner → human verification
    
    # ── conditional routing after verification ────────────────────────────────────
    g.add_conditional_edges(
        "human_plan_verification",
        route_after_verification,
        ["agent_react", "planner", END],
    )

    # ── routing inside INNER LOOP (delegated to router.py) ───────────────────────
    g.add_conditional_edges(
        "agent_react",
        route_after_agent,  # may return "tool_runner", "advance_pointer", or END
        ["tool_runner", "advance_pointer", END],
    )

    # tool → agent (reflection)                          (INNER LOOP)
    g.add_edge("tool_runner", "agent_react")

    # ── decide whether to re‑plan or continue with next sub‑task ─────────────────
    g.add_conditional_edges(
        "advance_pointer",
        route_after_pointer,  # may return "agent_react", "replanner", or END
        ["agent_react", "replanner", END],
    )

    # ── replanner output: new plan → verification, or final answer → END ─────────
    g.add_conditional_edges(
        "replanner",
        route_after_replanner,  # routes to human_plan_verification or END
        ["human_plan_verification", END],
    )

    return g.compile()
