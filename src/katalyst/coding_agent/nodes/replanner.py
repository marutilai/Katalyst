"""
Replanner Node - Uses create_react_agent for verification and replanning.

This node:
1. Creates a replanner agent with verification tools
2. Uses the agent to verify completed work  
3. Decides if the objective is complete or if more work is needed
4. Creates new tasks if needed
"""

from typing import List
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, create_tools_with_context


# Replanner prompt focused on verification and decision-making
replanner_prompt = """You are a senior software architect verifying completed work and deciding next steps.

Your role is to:
1. Review what has been implemented so far
2. Verify the work meets the original objective
3. Decide if the task is complete or if more work is needed
4. Create new tasks if needed to complete the objective

Use your tools to:
- Check files that were created or modified (ls, read)
- Verify the implementation works (bash - run tests, check functionality)
- Get user confirmation if unsure (request_user_input)

VERIFICATION GUIDELINES:
- Actually check that files exist and contain expected code
- Run simple commands to verify functionality if applicable
- Don't assume work is complete - verify it
- Consider edge cases and error handling

When you have thoroughly verified the work, respond with one of:

1. If objective is FULLY COMPLETE:
"OBJECTIVE COMPLETE: [Brief summary of what was accomplished]"

2. If more work is needed:
"MORE WORK NEEDED:"
Followed by a numbered list of remaining tasks, like:
1. Add error handling to the authentication module
2. Create unit tests for the new endpoints
3. Update documentation with API examples
"""


def replanner(state: KatalystState) -> KatalystState:
    """
    Use a replanner agent to verify work and decide next steps.
    """
    logger = get_logger()
    logger.debug("[REPLANNER] Starting replanner node...")
    
    # Skip if response already set
    if state.response:
        logger.debug("[REPLANNER] Final response already set. Skipping replanning.")
        state.task_queue = []
        return state
    
    # Check if we have a checkpointer
    if not state.checkpointer:
        logger.error("[REPLANNER] No checkpointer found in state")
        state.error_message = "No checkpointer available for conversation"
        state.response = "Failed to initialize replanner. Please try again."
        return state
    
    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("replanner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[REPLANNER] Using model: {model_name} (provider: {provider})")
    
    # Get replanner model
    replanner_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base
    )
    
    # Get replanner tools with logging context (verification tools)
    tool_functions = get_tool_functions_map(category="replanner")
    tools = create_tools_with_context(tool_functions, "REPLANNER")
    
    # Create replanner agent
    replanner_agent = create_react_agent(
        model=replanner_model,
        tools=tools,
        checkpointer=state.checkpointer
    )
    
    # Format context about what has been done
    context = f"""
OBJECTIVE: {state.task}

ORIGINAL PLAN:
{chr(10).join(f"{i+1}. {task}" for i, task in enumerate(state.original_plan)) if state.original_plan else "No original plan provided."}

COMPLETED TASKS:
{chr(10).join(f"✓ {task}: {summary}" for task, summary in state.completed_tasks) if state.completed_tasks else "No tasks marked as completed yet."}

TOOL EXECUTION HISTORY:
"""
    
    # Add execution history
    if hasattr(state, 'tool_execution_history') and state.tool_execution_history:
        current_task = None
        for record in state.tool_execution_history:
            if record['task'] != current_task:
                current_task = record['task']
                context += f"\n=== Task: {current_task} ===\n"
            context += f"- {record['tool_name']}: {record['status']}"
            if record['status'] == 'error':
                context += f" (Error: {record['summary']})"
            context += "\n"
    else:
        context += "No tool executions recorded yet.\n"
    
    # Create verification message
    verification_message = HumanMessage(content=f"""{replanner_prompt}

{context}

Please verify what has been implemented and decide if the objective is complete or if more work is needed.""")
    
    # Add to messages
    state.messages.append(verification_message)
    
    try:
        # Use the replanner agent to verify and decide
        logger.info("[REPLANNER] Invoking replanner agent to verify work")
        result = replanner_agent.invoke({"messages": state.messages})
        
        # Update messages
        state.messages = result.get("messages", state.messages)
        
        # Extract decision from the last AI message
        ai_messages = [msg for msg in state.messages if isinstance(msg, AIMessage)]
        
        if ai_messages:
            last_message = ai_messages[-1]
            
            # Check if objective is complete
            if "OBJECTIVE COMPLETE:" in last_message.content:
                # Extract summary
                complete_parts = last_message.content.split("OBJECTIVE COMPLETE:", 1)
                summary = complete_parts[1].strip() if len(complete_parts) > 1 else "Task completed successfully."
                
                # Set final response
                logger.info("[REPLANNER] Objective complete")
                state.task_queue = []
                state.task_idx = 0
                state.response = summary
                
            elif "MORE WORK NEEDED:" in last_message.content:
                # Extract new tasks
                work_parts = last_message.content.split("MORE WORK NEEDED:", 1)
                if len(work_parts) > 1:
                    tasks_text = work_parts[1].strip()
                    
                    # Parse numbered tasks
                    new_tasks = []
                    lines = tasks_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        # Match patterns like "1.", "2.", etc.
                        if line and line[0].isdigit() and '.' in line:
                            # Extract task after the number
                            task_parts = line.split('.', 1)
                            if len(task_parts) > 1:
                                task = task_parts[1].strip()
                                if task:
                                    new_tasks.append(task)
                    
                    if new_tasks:
                        # Update state with new plan
                        logger.info(f"[REPLANNER] Creating new plan with {len(new_tasks)} tasks")
                        state.task_queue = new_tasks
                        state.task_idx = 0
                        state.error_message = None
                        state.response = None
                        
                        # Log new plan
                        plan_message = "Continuing with updated plan:\n" + "\n".join(
                            f"{i+1}. {task}" for i, task in enumerate(new_tasks)
                        )
                        logger.info(f"[REPLANNER] {plan_message}")
                    else:
                        logger.error("[REPLANNER] Could not parse new tasks")
                        state.error_message = "Failed to parse new tasks from replanner"
                        state.response = "Unable to determine next steps."
                else:
                    logger.error("[REPLANNER] No tasks provided after MORE WORK NEEDED")
                    state.error_message = "Replanner indicated more work needed but provided no tasks"
                    state.response = "Unable to determine next steps."
            else:
                # Unclear response
                logger.error("[REPLANNER] Agent response unclear - no decision marker found")
                state.error_message = "Replanner did not provide clear decision"
                state.response = "Unable to determine if task is complete. Please try again."
        else:
            logger.error("[REPLANNER] No AI response from replanner agent")
            state.error_message = "No response from replanner"
            state.response = "Failed to get response from replanner. Please try again."
            
    except Exception as e:
        logger.error(f"[REPLANNER] Failed to replan: {str(e)}")
        state.error_message = f"Replanning failed: {str(e)}"
        state.response = "Unable to determine next steps due to an error."
    
    logger.debug("[REPLANNER] End of replanner node.")
    return state