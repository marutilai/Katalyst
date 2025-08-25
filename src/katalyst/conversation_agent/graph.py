"""
Conversation Agent Graph

Defines a simple LangGraph StateGraph for the conversation agent.
This is a ReAct agent that can:
- Handle greetings, clarifications, and off-topic requests
- Analyze code using read-only tools
- Answer technical questions about the codebase
- Provide recommendations without making changes
"""

from langgraph.graph import StateGraph, START, END

from katalyst.katalyst_core.state import KatalystState

# Import conversation node
from .nodes.conversation import conversation


def build_conversation_graph():
    """
    Build the conversation agent graph.
    
    This is a simple single-node ReAct agent that:
    - Handles conversational interactions (greetings, clarifications)
    - Analyzes code using read-only tools when needed
    - Answers technical questions with evidence from the codebase
    - Provides recommendations without making modifications
    """
    g = StateGraph(KatalystState)

    # Add the conversation node
    g.add_node("conversation", conversation)

    # Simple flow: START -> conversation -> END
    g.add_edge(START, "conversation")
    g.add_edge("conversation", END)

    return g.compile(name="conversation_agent")