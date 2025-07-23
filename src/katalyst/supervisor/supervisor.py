"""
Supervisor implementation for routing between coding and data science agents.
"""

from langgraph_supervisor import create_supervisor
from langchain_core.runnables import RunnableConfig

from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.graph import build_compiled_graph as build_coding_graph
from katalyst.data_science_agent.graph import build_data_science_graph


# Supervisor prompt for routing decisions
SUPERVISOR_PROMPT = """You are a supervisor managing two specialized agents:

1. build_compiled_graph: For software development tasks (coding agent)
   - Creating, modifying, or debugging code
   - Implementing features or fixing bugs
   - Refactoring or optimizing code
   - Writing tests or documentation
   - Working with git, dependencies, or project setup

2. build_data_science_graph: For data analysis and modeling tasks (data science agent)
   - Analyzing datasets and finding patterns
   - Creating visualizations and reports
   - Building predictive models
   - Statistical analysis and hypothesis testing
   - Data cleaning and preprocessing

Analyze the user's request and route it to the appropriate agent.
Some requests may require both agents working together.

IMPORTANT RULES:
- Route to ONE agent at a time based on the current need
- Always explain your routing decision briefly
- Do not attempt to do any work yourself, only route to agents
"""


def build_supervisor_graph():
    """
    Build the supervisor graph that routes between coding and data science agents.
    
    Returns:
        Compiled supervisor graph
    """
    # Get LLM configuration
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")  # Use planner model config
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
    
    # Build the individual agents
    coding_agent = build_coding_graph()
    data_science_agent = build_data_science_graph()
    
    # Create supervisor with list of agents
    supervisor = create_supervisor(
        agents=[coding_agent, data_science_agent],
        model=supervisor_model,
        prompt=SUPERVISOR_PROMPT,
        add_handoff_back_messages=True,
        output_mode="full_history",
    )
    
    return supervisor.compile()