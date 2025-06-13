from langgraph.graph import StateGraph, START, END
from langchain_core.agents import AgentAction

from src.katalyst_core.state import KatalystState
from src.katalyst_core.routing import (
    route_after_agent,
    route_after_pointer,
    route_after_replanner,
)
from src.coding_agent.nodes.planner import planner
from src.coding_agent.nodes.agent_react import agent_react
from src.coding_agent.nodes.tool_runner import tool_runner
from src.coding_agent.nodes.advance_pointer import advance_pointer
from src.coding_agent.nodes.replanner import replanner


# Node-callable functions (define/import elsewhere in your code‑base)
# ------------------------------------------------------------------
# • planner          – produces an ordered list of sub‑tasks in ``state.task_queue``
# • agent_react      – LLM step that yields AgentAction / AgentFinish in ``state.agent_outcome``
# • tool_runner      – executes Python tool extracted from AgentAction
# • advance_pointer  – increments ``state.task_idx`` and resets ``state.inner_cycles`` & ``state.action_trace``
# • replanner        – builds a fresh plan or final answer when current plan exhausted
# ------------------------------------------------------------------

# ─────────────────────────────────────────────────────────────────────────────
# TWO-LEVEL AGENT STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
# 1. OUTER LOOP  (Plan-and-Execute)
#    planner  →  ⟮ INNER LOOP ⟯  →  advance_pointer  →  replanner
#         ↘                               ↑                ↘
#          └─────────────── LOOP ─────────┘   new-plan / END └───► END
#
# 2. INNER LOOP  (ReAct over a single task)
#    agent_react  →  tool_runner  →  agent_react  (repeat until AgentFinish)
# ─────────────────────────────────────────────────────────────────────────────


def build_compiled_graph():
    g = StateGraph(KatalystState)

    # ── planner: generates the initial list of sub‑tasks ─────────────────────────
    g.add_node("planner", planner)

    # ── INNER LOOP nodes ─────────────────────────────────────────────────────────
    g.add_node("agent_react", agent_react)  # LLM emits AgentAction/Finish
    g.add_node("tool_runner", tool_runner)  # Executes the chosen tool
    g.add_node("advance_pointer", advance_pointer)  # Marks task complete

    # ── replanner: invoked when plan is exhausted or needs adjustment ────────────
    g.add_node("replanner", replanner)

    # ── edges for OUTER LOOP ─────────────────────────────────────────────────────
    g.add_edge(START, "planner")  # start → planner
    g.add_edge("planner", "agent_react")  # initial plan → INNER LOOP

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

    # ── replanner output: new plan → back to INNER LOOP, or final answer → END ──
    g.add_conditional_edges(
        "replanner",
        route_after_replanner,  # use the new router
        ["agent_react", END],
    )

    return g.compile()
