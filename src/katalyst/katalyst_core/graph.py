from langgraph.graph import StateGraph, START, END

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.routing import route_agent
from katalyst.coding_agent.nodes.agent_react import agent_react


# ─────────────────────────────────────────────────────────────────────────────
# SIMPLIFIED SINGLE-LOOP AGENT STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────
# The agent_react node now handles everything:
# - Planning (via create_todo_list tool)
# - Task management (via update_todo_list tool)
# - Execution (via all other tools)
# - Completion (via attempt_completion tool)
# ─────────────────────────────────────────────────────────────────────────────


def build_compiled_graph():
    g = StateGraph(KatalystState)

    # ── Single agent node that handles everything ─────────────────────────────────
    g.add_node("agent_react", agent_react)

    # ── Simple flow: start → agent → end ─────────────────────────────────────────
    g.add_edge(START, "agent_react")
    
    # ── Agent decides when to end (via attempt_completion tool) ──────────────────
    g.add_conditional_edges(
        "agent_react",
        route_agent,
        ["agent_react", END]
    )

    return g.compile()
