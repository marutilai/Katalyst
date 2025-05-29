from langgraph.graph import StateGraph, END
from katalyst_agent.state import KatalystAgentState
from katalyst_agent.nodes.initialize_katalyst_run import initialize_katalyst_run
from katalyst_agent.nodes.generate_llm_prompt import generate_llm_prompt
from katalyst_agent.nodes.invoke_llm import invoke_llm
from katalyst_agent.nodes.parse_llm_response import parse_llm_response
from katalyst_agent.nodes.execute_tool import execute_tool
from katalyst_agent.nodes.prepare_reprompt_feedback import prepare_reprompt_feedback
from katalyst_agent.routing import (
    decide_next_action_router, 
    FINISH_MAX_ITERATIONS, 
    FINISH_SUCCESSFUL_COMPLETION, 
    EXECUTE_TOOL, 
    REPROMPT_LLM
)


def build_compiled_graph():
    agent_graph = StateGraph(KatalystAgentState)

    # Add nodes
    agent_graph.add_node("initialize_katalyst_run", initialize_katalyst_run)
    agent_graph.add_node("generate_llm_prompt", generate_llm_prompt)
    agent_graph.add_node("invoke_llm", invoke_llm)
    agent_graph.add_node("parse_llm_response", parse_llm_response)
    agent_graph.add_node("execute_tool", execute_tool)
    agent_graph.add_node("prepare_reprompt_feedback", prepare_reprompt_feedback)
    
    # Add edges
    agent_graph.add_edge("initialize_katalyst_run", "generate_llm_prompt")
    agent_graph.add_edge("generate_llm_prompt", "invoke_llm")
    agent_graph.add_edge("invoke_llm", "parse_llm_response")

    # Conditional edge after parse_llm_response using router
    agent_graph.add_conditional_edges(
        "parse_llm_response",
        decide_next_action_router,
        {
            EXECUTE_TOOL: "execute_tool",
            REPROMPT_LLM: "prepare_reprompt_feedback",
            FINISH_MAX_ITERATIONS: END,
            FINISH_SUCCESSFUL_COMPLETION: END,
        },
    )
    # After tool execution, go back to prompt generation
    agent_graph.add_edge("execute_tool", "generate_llm_prompt")
    agent_graph.add_edge("prepare_reprompt_feedback", "generate_llm_prompt")

    # Set entry point
    agent_graph.set_entry_point("initialize_katalyst_run")

    # Compile the graph
    return agent_graph.compile()
