"""
Minimal Planner Node - Uses LangChain's simple prompt approach.
"""

from langchain_core.prompts import ChatPromptTemplate
# MINIMAL: AIMessage import not needed when chat_history is commented out
# from langchain_core.messages import AIMessage
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.models import SubtaskList
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, extract_tool_descriptions
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent


# Simple planner prompt - no complex guidelines
planner_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a senior staff software engineer planning implementation tasks for a junior software engineer.

ANALYSIS PHASE:
1. Read the user's request carefully and identify ALL requirements (explicit and implicit)
2. If user asks for an "app" - plan for a complete, usable application with UI
3. Note any specific: technologies mentioned, folder structures, quality requirements in the user's request
4. Consider what would make this a production-ready solution

PLANNING GUIDELINES:
- Come up with a simple step-by-step plan that delivers the COMPLETE solution
- Each task should be a significant feature or component (not setup steps)
- Make tasks roughly equal in scope and effort
- Do not add superfluous steps
- Ensure each step has all information needed

ASSUMPTIONS:
- Developer will handle basic project setup, package installation, folder creation
- Focus on implementing features, not configuring environments

The result of the final step should be a fully functional solution that meets ALL the user's requirements.""",
        ),
        ("human", "{task}"),
    ]
)


def planner(state: KatalystState) -> KatalystState:
    """
    Minimal planner - generates a simple task list using LangChain's approach.
    """
    logger = get_logger()
    logger.debug("[PLANNER] Starting minimal planner node...")
    
    # Get configured model from LLM config
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[PLANNER] Using model: {model_name} (provider: {provider})")
    
    # Get native LangChain model
    model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base
    )
    planner_chain = planner_prompt | model.with_structured_output(SubtaskList)
    
    try:
        # Generate plan
        result = planner_chain.invoke({"task": state.task})
        subtasks = result.subtasks
        
        logger.debug(f"[PLANNER] Generated subtasks: {subtasks}")
        
        # Update state
        state.task_queue = subtasks
        state.original_plan = subtasks
        state.task_idx = 0
        state.outer_cycles = 0
        state.completed_tasks = []
        state.response = None
        state.error_message = None
        state.plan_feedback = None
        
        # Log the plan
        plan_message = f"Generated plan:\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(subtasks)
        )
        logger.info(f"[PLANNER] {plan_message}")
        
        # Create the persistent agent executor that will handle all tasks
        logger.info("[PLANNER] Creating persistent agent executor")
        
        # Get tools
        tool_functions = get_tool_functions_map()
        tool_descriptions_map = dict(extract_tool_descriptions())
        tools = []
        
        for tool_name, tool_func in tool_functions.items():
            description = tool_descriptions_map.get(tool_name, f"Tool: {tool_name}")
            structured_tool = StructuredTool.from_function(
                func=tool_func,
                name=tool_name,
                description=description
            )
            tools.append(structured_tool)
        
        # Get model for agent
        agent_model = get_langchain_chat_model(
            model_name=llm_config.get_model_for_component("agent_react"),
            provider=provider,
            temperature=0,
            timeout=timeout,
            api_base=api_base
        )
        
        # Create the agent executor
        state.agent_executor = create_react_agent(
            model=agent_model,
            tools=tools,
            checkpointer=False
        )
        
        # Initialize conversation with the plan
        initial_message = HumanMessage(content=f"""I have the following plan to complete:

{plan_message}

I'll work through each task in order. Let's start with the first task.""")
        
        state.messages = [initial_message]
        
    except Exception as e:
        logger.error(f"[PLANNER] Failed to generate plan: {str(e)}")
        state.error_message = f"Failed to generate plan: {str(e)}"
        state.response = "Failed to generate initial plan. Please try again."
    
    logger.debug("[PLANNER] End of planner node.")
    return state