"""
Conversation Agent Graph

Defines a simple LangGraph StateGraph for the conversation agent.
This agent handles greetings, clarifications, and off-topic requests.
"""

from langgraph.graph import StateGraph, START, END

from katalyst.katalyst_core.state import KatalystState

# Import conversation node
from .nodes.conversation import conversation


def build_conversation_graph():
    """
    Build the conversation agent graph.
    
    This is a simple single-node graph that:
    - Analyzes user input
    - Generates appropriate conversational responses
    - Helps users clarify their needs
    """
    g = StateGraph(KatalystState)

    # Add the conversation node
    g.add_node("conversation", conversation)

    # Simple flow: START -> conversation -> END
    g.add_edge(START, "conversation")
    g.add_edge("conversation", END)

    return g.compile(name="conversation_agent")