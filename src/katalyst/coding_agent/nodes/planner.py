"""
Minimal Planner Node - Uses LangChain's simple prompt approach.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.models import SubtaskList
from katalyst.katalyst_core.utils.logger import get_logger


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
    
    # Create planner chain
    model = ChatOpenAI(model="gpt-4.1", temperature=0)
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
        plan_message = f"Generated plan:\\n" + "\\n".join(
            f"{i+1}. {s}" for i, s in enumerate(subtasks)
        )
        state.chat_history.append(AIMessage(content=plan_message))
        logger.info(f"[PLANNER] {plan_message}")
        
    except Exception as e:
        logger.error(f"[PLANNER] Failed to generate plan: {str(e)}")
        state.error_message = f"Failed to generate plan: {str(e)}"
        state.response = "Failed to generate initial plan. Please try again."
    
    logger.debug("[PLANNER] End of planner node.")
    return state