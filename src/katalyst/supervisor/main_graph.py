"""
Main graph implementation using subgraphs for agent routing.

This approach uses native LangGraph subgraphs instead of tool-based routing,
providing cleaner state management and control flow.
"""

from langgraph.graph import StateGraph, START, END

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.coding_agent.graph import build_coding_graph
from katalyst.data_science_agent.graph import build_data_science_graph


def router_node(state: KatalystState) -> KatalystState:
    """
    Router node that decides which agent to use based on the task.
    
    This is a simple LLM call that classifies the task and routes accordingly.
    """
    logger = get_logger()
    logger.info(f"[ROUTER] Analyzing task: {state.task}")
    
    # Get LLM for routing decision
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base
    )
    
    # Create routing prompt
    routing_prompt = f"""Analyze this task and determine which agent should handle it:

Task: {state.task}

Available agents:
1. coding_agent - For software development tasks like:
   - Writing, modifying, or debugging code
   - Implementing features or fixing bugs
   - Refactoring or optimizing code
   - Writing tests or documentation
   - Working with git, dependencies, or project setup

2. data_science_agent - For data analysis tasks like:
   - Analyzing datasets and finding patterns
   - Reading and analyzing CSV files or other data formats
   - Creating visualizations and reports
   - Building predictive models
   - Statistical analysis and hypothesis testing
   - Data cleaning and preprocessing

Respond with ONLY the agent name: either "coding_agent" or "data_science_agent"
Do not include any explanation, just the agent name."""
    
    try:
        # Get routing decision
        response = model.invoke(routing_prompt)
        agent_choice = response.content.strip().lower()
        
        # Validate and set routing decision
        if "data" in agent_choice or "science" in agent_choice:
            state.next_agent = "data_science_agent"
            logger.info("[ROUTER] Routing to data_science_agent")
        else:
            state.next_agent = "coding_agent"
            logger.info("[ROUTER] Routing to coding_agent")
            
    except Exception as e:
        logger.error(f"[ROUTER] Error during routing: {e}")
        # Default to coding agent on error
        state.next_agent = "coding_agent"
        logger.info("[ROUTER] Defaulting to coding_agent due to error")
    
    return state


def route_to_agent(state: KatalystState) -> str:
    """
    Conditional edge function that routes based on the router's decision.
    """
    return state.next_agent or "coding_agent"


def build_main_graph():
    """
    Build the main graph with coding and data science agents as subgraphs.
    
    This provides a clean architecture where:
    - The router decides which agent to use
    - Agents are full subgraphs with their own nodes
    - State and checkpointer flow naturally through the system
    """
    logger = get_logger()
    logger.info("[MAIN_GRAPH] Building main graph with subgraphs...")
    
    # Create the main graph
    main = StateGraph(KatalystState)
    
    # Add router node
    main.add_node("router", router_node)
    
    # Add agent subgraphs
    logger.info("[MAIN_GRAPH] Adding coding agent subgraph...")
    main.add_node("coding_agent", build_coding_graph())
    
    logger.info("[MAIN_GRAPH] Adding data science agent subgraph...")
    main.add_node("data_science_agent", build_data_science_graph())
    
    # Add edges
    main.add_edge(START, "router")
    
    # Conditional routing from router to agents
    main.add_conditional_edges(
        "router",
        route_to_agent,
        ["coding_agent", "data_science_agent"]
    )
    
    # Both agents lead to END
    main.add_edge("coding_agent", END)
    main.add_edge("data_science_agent", END)
    
    # Compile the graph
    compiled = main.compile(name="main_graph")
    logger.info("[MAIN_GRAPH] Main graph compiled successfully")
    
    return compiled