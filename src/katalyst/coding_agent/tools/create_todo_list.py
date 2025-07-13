import json
from typing import List, Optional
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.todo_manager import todo_aware
from langchain_core.prompts import ChatPromptTemplate
from katalyst.katalyst_core.utils.models import SubtaskList
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model


# Planning prompt - adapted from the original planner
planning_prompt = ChatPromptTemplate.from_messages(
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


def format_todo_list_response(
    success: bool,
    message: str,
    todo_list: Optional[List[str]] = None,
    error: Optional[str] = None
) -> str:
    """Format the response for create_todo_list tool."""
    resp = {
        "success": success,
        "message": message,
    }
    if todo_list:
        resp["todo_list"] = todo_list
        resp["task_count"] = len(todo_list)
    if error:
        resp["error"] = error
    return json.dumps(resp, indent=2)


@katalyst_tool(prompt_module="create_todo_list", prompt_var="CREATE_TODO_LIST_TOOL_PROMPT")
@todo_aware(action="create")
def create_todo_list(
    task_description: str,
    include_verification: bool = True
) -> str:
    """
    Creates a comprehensive todo list for completing a complex task.
    This tool analyzes the task and breaks it down into manageable subtasks.
    
    Arguments:
        task_description: The main task or project to break down into subtasks
        include_verification: Whether to ask for user verification of the plan
    
    Returns:
        JSON string with the generated todo list and status
    """
    logger = get_logger()
    logger.debug(f"[TOOL] Creating todo list for task: '{task_description}'")
    
    # Validate input
    if not task_description or not isinstance(task_description, str):
        return format_todo_list_response(
            False,
            "Task description is required",
            error="Invalid task_description"
        )
    
    try:
        # Get configured model
        llm_config = get_llm_config()
        model_name = llm_config.get_model_for_component("planner")
        provider = llm_config.get_provider()
        timeout = llm_config.get_timeout()
        api_base = llm_config.get_api_base()
        
        logger.debug(f"[CREATE_TODO_LIST] Using model: {model_name} (provider: {provider})")
        
        # Get LangChain model
        model = get_langchain_chat_model(
            model_name=model_name,
            provider=provider,
            temperature=0,
            timeout=timeout,
            api_base=api_base
        )
        
        # Create planning chain
        planning_chain = planning_prompt | model.with_structured_output(SubtaskList)
        
        # Generate plan
        result = planning_chain.invoke({"task": task_description})
        subtasks = result.subtasks
        
        logger.debug(f"[CREATE_TODO_LIST] Generated {len(subtasks)} subtasks")
        
        # Format the plan for display
        plan_message = "Generated todo list:\n" + "\n".join(
            f"{i+1}. {task}" for i, task in enumerate(subtasks)
        )
        
        logger.info(f"[CREATE_TODO_LIST] {plan_message}")
        
        # If verification is requested, add a note about it
        if include_verification:
            verification_note = "\n\nPlease review this todo list. You can use the 'update_todo_list' tool to modify it if needed."
        else:
            verification_note = ""
        
        return format_todo_list_response(
            True,
            f"{plan_message}{verification_note}",
            todo_list=subtasks
        )
        
    except Exception as e:
        logger.error(f"[CREATE_TODO_LIST] Failed to generate todo list: {str(e)}")
        return format_todo_list_response(
            False,
            f"Failed to generate todo list: {str(e)}",
            error=str(e)
        )