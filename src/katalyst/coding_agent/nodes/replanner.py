"""
Minimal Replanner using LangChain's approach with tool execution history.
"""

from langchain_core.prompts import ChatPromptTemplate
# MINIMAL: AIMessage import not needed when chat_history is commented out
# from langchain_core.messages import AIMessage
from typing import Dict

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.models import ReplannerOutput
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model


# Minimal replanner prompt inspired by LangChain but using our execution history
replanner_prompt = ChatPromptTemplate.from_template(
    """You are a replanner for a coding agent. Analyze what has been done and determine if the goal is complete.

OBJECTIVE: {objective}

ORIGINAL PLAN:
{original_plan}

COMPLETED TASKS:
{completed_tasks}

TOOL EXECUTION HISTORY (all tools used across all tasks):
{execution_history}

CURRENT STATUS:
- Tasks completed: {num_completed}/{num_total}
- Current task: {current_task}

DECISION REQUIRED:
1. If the objective is FULLY ACHIEVED based on the execution history, set is_complete=true
2. If more work is needed, set is_complete=false and provide ONLY the remaining tasks

IMPORTANT:
- Review the tool executions to verify work was actually done (files created, tests passed, etc.)
- Do NOT repeat tasks that have been successfully completed
- If you see errors in execution history, include tasks to fix them
- Each new task should be concrete and implementable"""
)


def replanner(state: KatalystState) -> KatalystState:
    """
    Minimal replanner that uses tool execution history for better decisions.
    """
    logger = get_logger()
    logger.debug("[REPLANNER] Starting minimal replanner node...")
    
    # Skip if response already set
    if state.response:
        logger.debug("[REPLANNER] Final response already set. Skipping replanning.")
        state.task_queue = []
        return state
    
    # Format execution history - this is the key improvement!
    execution_history_str = ""
    if hasattr(state, 'tool_execution_history') and state.tool_execution_history:
        current_task = None
        for record in state.tool_execution_history:
            # Add task header when it changes
            if record['task'] != current_task:
                current_task = record['task']
                execution_history_str += f"\n=== Task: {current_task} ===\n"
            execution_history_str += f"- {record['tool_name']}: {record['status']}\n"
            if record['status'] == 'error':
                execution_history_str += f"  Error: {record['summary']}\n"
    else:
        execution_history_str = "No tool executions recorded yet."
    
    # Format completed tasks
    completed_tasks_str = ""
    if state.completed_tasks:
        for task, summary in state.completed_tasks:
            completed_tasks_str += f"✓ {task}\n  Result: {summary}\n"
    else:
        completed_tasks_str = "No tasks marked as completed yet."
    
    # Format original plan
    original_plan_str = "\n".join(
        f"{i+1}. {task}" for i, task in enumerate(state.original_plan)
    ) if state.original_plan else "No original plan provided."
    
    # Current task info
    current_task_str = (
        state.task_queue[state.task_idx] 
        if state.task_idx < len(state.task_queue) 
        else "No current task"
    )
    
    # Get configured model from LLM config
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("replanner")
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[REPLANNER] Using model: {model_name} (provider: {llm_config.get_provider()})")
    
    # Get native LangChain model
    model = get_langchain_chat_model(
        model_name=model_name,
        provider=llm_config.get_provider(),
        temperature=0,
        timeout=timeout,
        api_base=api_base
    )
    replanner_chain = replanner_prompt | model.with_structured_output(ReplannerOutput)
    
    try:
        # Get structured decision
        result = replanner_chain.invoke({
            "objective": state.task,
            "original_plan": original_plan_str,
            "completed_tasks": completed_tasks_str,
            "execution_history": execution_history_str,
            "num_completed": len(state.completed_tasks),
            "num_total": len(state.original_plan) if state.original_plan else 0,
            "current_task": current_task_str
        })
        
        logger.debug(f"[REPLANNER] Decision: is_complete={result.is_complete}, "
                    f"new_subtasks={len(result.subtasks)}")
        
        if result.is_complete:
            # Goal achieved
            logger.info("[REPLANNER] Goal achieved - marking complete")
            state.task_queue = []
            state.task_idx = 0
            
            # Generate final summary based on completed work
            if state.completed_tasks:
                summary = "Successfully completed the following:\n"
                summary += "\n".join(f"- {task}: {result}" 
                                   for task, result in state.completed_tasks)
                state.response = summary
            else:
                state.response = "Task completed as requested."
            
            # MINIMAL: chat_history is commented out (LangGraph tracks messages internally)
            # state.chat_history.append(
            #     AIMessage(content=f"[REPLANNER] Goal achieved. {state.response}")
            # )
            
        else:
            # More work needed
            logger.info(f"[REPLANNER] Creating new plan with {len(result.subtasks)} tasks")
            
            # Reset for new plan
            state.task_queue = result.subtasks
            state.task_idx = 0
            # Reset for new plan
            state.error_message = None
            state.response = None
            
            # Log new plan
            plan_msg = "Continuing with updated plan:\n" + "\n".join(
                f"{i+1}. {task}" for i, task in enumerate(result.subtasks)
            )
            # MINIMAL: chat_history is commented out (LangGraph tracks messages internally)
            # state.chat_history.append(AIMessage(content=f"[REPLANNER] {plan_msg}"))
            logger.info(f"[REPLANNER] {plan_msg}")
            
    except Exception as e:
        logger.error(f"[REPLANNER] Failed to replan: {str(e)}")
        state.error_message = f"Replanning failed: {str(e)}"
        state.response = "Unable to determine next steps due to an error."
    
    logger.debug("[REPLANNER] End of replanner node.")
    return state