"""
Custom Supervisor implementation using handoff tools pattern.

This supervisor uses a react agent with handoff tools to route between
coding and data science agents, providing better control and visibility.
"""

import os
from typing import Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.graph import StateGraph, START
from langgraph.types import Command

from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.state import KatalystState
from katalyst.coding_agent.graph import build_coding_graph
from katalyst.data_science_agent.graph import build_data_science_graph
from katalyst.katalyst_core.utils.logger import get_logger


def create_agent_handoff_tool(*, agent_name: str, agent_graph_builder, description: str = None):
    """
    Create a handoff tool that executes a full agent graph.
    
    Args:
        agent_name: Name of the agent (e.g., "coding_agent")
        agent_graph_builder: Function that builds the agent graph
        description: Tool description for the supervisor
    """
    name = f"transfer_to_{agent_name}"
    description = description or f"Transfer task to {agent_name}."
    logger = get_logger()

    @tool(name, description=description)
    def handoff_tool(
        task_description: str,
        state: Annotated[KatalystState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Execute the agent graph with the given task."""
        logger.info(f"[SUPERVISOR] Transferring to {agent_name} with task: {task_description}")
        
        # Debug: Check what's in the state
        logger.debug(f"[SUPERVISOR] State type: {type(state)}")
        logger.debug(f"[SUPERVISOR] Checkpointer in state: {state.checkpointer is not None}")
        
        # Create sub-agent state from current state
        # Use the same checkpointer throughout the system
        sub_state = {
            "task": task_description,
            "messages": state.messages,
            "auto_approve": state.auto_approve,
            "project_root_cwd": state.project_root_cwd,
            "user_input_fn": state.user_input_fn,
            "checkpointer": state.checkpointer,  # Pass the same checkpointer
        }
        
        logger.debug(f"[SUPERVISOR] Sub-state checkpointer: {sub_state['checkpointer'] is not None}")
        
        try:
            # Build and configure the agent graph with checkpointer
            agent_graph = agent_graph_builder()
            if state.checkpointer:
                agent_graph = agent_graph.with_config(checkpointer=state.checkpointer)
            
            # Execute the agent graph with proper config
            # Use the same thread_id as the main conversation for shared context
            config = {
                "recursion_limit": 100,  # Reasonable limit for sub-agents
                "configurable": {"thread_id": "katalyst-main-thread"},
            }
            result = agent_graph.invoke(sub_state, config)
            
            # Extract key results
            completed_tasks = result.get("completed_tasks", [])
            response = result.get("response", "")
            
            logger.info(f"[SUPERVISOR] {agent_name} completed with response: {response[:100]}...")
            
            # Create tool message with results
            tool_message = ToolMessage(
                content=f"{agent_name} completed the task. Response: {response}",
                name=name,
                tool_call_id=tool_call_id,
            )
            
            # Update state with results
            updated_state = {
                "messages": state.messages + [tool_message],
                "completed_tasks": state.completed_tasks + completed_tasks,
                "response": response,
            }
            
            # Return control to supervisor
            return Command(
                goto="supervisor",
                update=updated_state,
                graph=Command.PARENT,
            )
            
        except Exception as e:
            logger.error(f"[SUPERVISOR] Error in {agent_name}: {e}")
            error_message = ToolMessage(
                content=f"Error executing {agent_name}: {str(e)}",
                name=name,
                tool_call_id=tool_call_id,
            )
            return Command(
                goto="supervisor",
                update={"messages": state.messages + [error_message]},
                graph=Command.PARENT,
            )
    
    return handoff_tool


def build_custom_supervisor_graph():
    """
    Build a custom supervisor graph using handoff tools.
    
    Returns:
        Compiled supervisor graph
    """
    logger = get_logger()
    logger.info("[SUPERVISOR] Building custom supervisor graph...")
    
    # Get LLM configuration
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    # Create supervisor model
    supervisor_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base
    )
    
    # Create handoff tools with graph builders
    transfer_to_coding = create_agent_handoff_tool(
        agent_name="coding_agent",
        agent_graph_builder=build_coding_graph,
        description=(
            "Transfer to coding agent for software development tasks like: "
            "creating/modifying code, debugging, implementing features, "
            "writing tests, refactoring, or working with git."
        )
    )
    
    transfer_to_data_science = create_agent_handoff_tool(
        agent_name="data_science_agent",
        agent_graph_builder=build_data_science_graph,
        description=(
            "Transfer to data science agent for data analysis tasks like: "
            "analyzing datasets, creating visualizations, building models, "
            "statistical analysis, or working with CSV files."
        )
    )
    
    # Create supervisor agent with handoff tools
    supervisor_agent = create_react_agent(
        model=supervisor_model,
        tools=[transfer_to_coding, transfer_to_data_science],
        prompt=(
            "You are a supervisor managing two specialized agents:\n"
            "- coding_agent: For software development tasks\n"
            "- data_science_agent: For data analysis and modeling tasks\n\n"
            "Analyze the user's request and transfer it to the appropriate agent.\n"
            "Only call one agent at a time. Do not do any work yourself.\n"
            "When an agent completes its task, you can either:\n"
            "1. Return the result to the user if the task is complete\n"
            "2. Transfer to another agent if more work is needed\n\n"
            "Be decisive and route immediately based on the primary nature of the task."
        ),
        name="supervisor"
    )
    
    # Create the multi-agent graph
    graph = StateGraph(KatalystState)
    
    # Add supervisor node (with destinations for visualization)
    graph.add_node("supervisor", supervisor_agent)
    
    # Add edges
    graph.add_edge(START, "supervisor")
    
    # Compile the graph
    compiled = graph.compile(name="custom_supervisor")
    logger.info("[SUPERVISOR] Custom supervisor graph compiled successfully")
    
    return compiled