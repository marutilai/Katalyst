"""
Data Science Agent Graph

Defines the LangGraph StateGraph for the data science agent.
Follows the same pattern as the coding agent with planner, executor, and replanner nodes,
but specialized for data science workflows.
"""

from langgraph.graph import StateGraph, START, END

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.routing import (
    route_after_agent,
    route_after_pointer,
    route_after_replanner,
    route_after_verification,
)

# Import DS-specific nodes
from .nodes.planner import planner
from .nodes.executor import executor
from .nodes.replanner import replanner

# Still use shared nodes for common functionality
from katalyst.coding_agent.nodes.advance_pointer import advance_pointer
from katalyst.coding_agent.nodes.human_plan_verification import human_plan_verification


def build_data_science_graph():
    """
    Build the data science agent graph.
    
    Uses DS-specific nodes for planner, executor, and replanner
    with prompts and logic optimized for data analysis workflows.
    """
    g = StateGraph(KatalystState)

    # ── planner: generates the initial list of analysis tasks ────────────────────
    g.add_node("planner", planner)
    
    # ── human verification: allows user to review/modify plans ────────────────────
    g.add_node("human_plan_verification", human_plan_verification)

    # ── INNER LOOP nodes ─────────────────────────────────────────────────────────
    g.add_node("executor", executor)  # Uses create_react_agent to complete the task
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
        ["executor", "planner", END],
    )

    # ── routing after agent completes the task ───────────────────────────────────
    g.add_conditional_edges(
        "executor",
        route_after_agent,  # returns "advance_pointer" or END
        ["advance_pointer", "replanner", END],
    )

    # ── decide whether to re‑plan or continue with next sub‑task ─────────────────
    g.add_conditional_edges(
        "advance_pointer",
        route_after_pointer,  # may return "executor", "replanner", or END
        ["executor", "replanner", END],
    )

    # ── replanner output: new plan → verification, or final answer → END ─────────
    g.add_conditional_edges(
        "replanner",
        route_after_replanner,  # routes to human_plan_verification or END
        ["human_plan_verification", END],
    )

    return g.compile(name="data_science_agent")