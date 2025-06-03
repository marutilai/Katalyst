import os
from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage, ToolMessage
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.models import AgentReactOutput
from langchain_core.agents import AgentAction, AgentFinish
from katalyst_agent.utils.tools import get_formatted_tool_prompts_for_llm, get_tool_functions_map

REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()

# agent_react.py
# ------------------------------------------------------------------------------
# This module defines the agent_react node for the Katalyst agent's ReAct loop.
# It handles a single Reason-Act cycle: builds a prompt, calls the LLM, parses
# structured output, and updates the agent state accordingly.
# ------------------------------------------------------------------------------

def agent_react(state: KatalystState) -> KatalystState:
    """
    Execute one ReAct (Reason-Act) cycle for the current sub-task.
    Uses Instructor to get a structured response from the LLM.

    * Primary Task: Execute one ReAct (Reason-Act) cycle for the current sub-task.
    * State Changes:
      - Increments state.inner_cycles (loop guard).
      - If max cycles exceeded, sets state.response and returns AgentFinish.
      - Otherwise, builds a prompt (system + user) with subtask, error, and scratchpad.
      - Calls the LLM for a structured response (thought, action, action_input, final_answer).
      - If action: wraps as AgentAction and updates state.
      - If final_answer: wraps as AgentFinish and updates state.
      - If neither: sets error_message for retry/self-correction.
      - Logs LLM thoughts and actions to chat_history for traceability.
    * Returns: The updated KatalystState.
    """
    logger = get_logger()
    logger.info(f"[AGENT_REACT] Starting agent_react node...")
    
    # 1) Inner-loop guard: prevent infinite loops in the ReAct cycle
    state.inner_cycles += 1
    if state.inner_cycles > state.max_inner_cycles:
        state.response = (
            f"Stopped: inner loop exceeded {state.max_inner_cycles} cycles "
            f"(task #{state.task_idx})."
        )
        # Construct an AgentFinish to signal "done" to the router
        state.agent_outcome = AgentFinish(
            return_values={"output": "Inner loop limit exceeded"}, 
            log="Exceeded inner loop guardrail"
        )
        logger.warning(f"[AGENT_REACT] Inner loop limit exceeded. Returning AgentFinish.")
        return state

    # 2) Build the system message (persona, format, rules)
    # --------------------------------------------------------------------------
    # This message sets the agent's persona, output format, and tool usage rules.
    # It also appends detailed tool descriptions for LLM reference.
    system_message_content = (
        "You are a ReAct agent. Your goal is to accomplish sub-tasks by thinking step by step "
        "and then either taking an action (tool call) or providing a final answer if the sub-task is complete. "
        "Respond in JSON with keys: thought (string, your reasoning), "
        "and EITHER (action (string, tool_name) AND action_input (object, tool_arguments)) "
        "OR (final_answer (string, your answer for the sub-task))."
    )

    # Add detailed tool descriptions to the system message for LLM tool selection
    all_detailed_tool_prompts = get_formatted_tool_prompts_for_llm(REGISTERED_TOOL_FUNCTIONS_MAP)
    system_message_content += f"\n\n{all_detailed_tool_prompts}"

    # 3) Build the user message (task, context, error, scratchpad)
    # --------------------------------------------------------------------------
    # This message provides the current subtask, context from the previous sub-task (if any),
    # any error feedback, and a scratchpad of previous actions/observations to help the LLM reason step by step.
    current_subtask = (
        state.task_queue[state.task_idx] 
        if state.task_idx < len(state.task_queue) 
        else ""
    )
    user_message_content_parts = [f"Current Subtask: {current_subtask}"]

    # Provide context from the most recently completed sub-task if available and relevant
    if state.task_idx > 0 and state.completed_tasks:
        try:
            # Get the summary of the immediately preceding task
            prev_task_name, prev_task_summary = state.completed_tasks[state.task_idx - 1]
            user_message_content_parts.append(
                f"\nContext from previously completed sub-task ('{prev_task_name}'): {prev_task_summary}"
            )
        except IndexError:
            logger.warning(f"[AGENT_REACT] Could not get previous completed task context for task_idx {state.task_idx}")

    # Add error message if it exists (for LLM self-correction)
    if state.error_message:
        user_message_content_parts.append(
            f"An error occurred in the previous step: {state.error_message}\n"
            "Please analyze this error and try to correct your plan or action."
        )
        state.error_message = None  # Consume the error message

    # Add action trace if it exists (scratchpad for LLM reasoning)
    if state.action_trace:
        scratchpad_content = "\n".join([
            f"Previous Action: {action.tool}\nPrevious Action Input: {action.tool_input}\nObservation: {obs}" 
            for action, obs in state.action_trace
        ])
        user_message_content_parts.append(
            f"\nPrevious actions and observations (scratchpad):\n{scratchpad_content}"
        )

    user_message_content = "\n".join(user_message_content_parts)

    # Compose the full LLM message list
    llm_messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": user_message_content}
    ]
    logger.info(f"[AGENT_REACT] LLM messages: {llm_messages}")

    # 4) Call the LLM for a structured ReAct response
    # --------------------------------------------------------------------------
    # The LLM is expected to return a JSON object matching AgentReactOutput:
    #   - thought: reasoning string
    #   - action: tool name (optional)
    #   - action_input: dict of tool arguments (optional)
    #   - final_answer: string (optional)
    #   - replan_requested: bool (optional)
    llm = get_llm_instructor()
    response = llm.chat.completions.create(
        messages=llm_messages,
        response_model=AgentReactOutput,
        temperature=0.1,
    )
    logger.debug(f"[AGENT_REACT] Raw LLM response: {response}")
    logger.info(f"[AGENT_REACT] Parsed output: {response.dict()}")

    # 5) Log the LLM's thought and action to chat_history for traceability
    state.chat_history.append(AIMessage(content=f"Thought: {response.thought}"))
    if response.action:
        state.chat_history.append(AIMessage(content=f"Action: {response.action} with input {response.action_input}"))    

    # 6) If "action" key is present, wrap in AgentAction and update state
    if response.action:
        args_dict = response.action_input or {}
        state.agent_outcome = AgentAction(
            tool=response.action,
            tool_input=args_dict,
            log=f"Thought: {response.thought}\nAction: {response.action}\nAction Input: {str(args_dict)}"
        )
        state.error_message = None
        logger.info(f"[AGENT_REACT] Action requested: {response.action} with input {args_dict}")

    # 7) If "final_answer" key is present, wrap in AgentFinish and update state
    elif response.final_answer:
        state.agent_outcome = AgentFinish(
            return_values={"output": response.final_answer},
            log=f"Thought: {response.thought}\nFinal Answer: {response.final_answer}",
        )
        state.error_message = None
        logger.info(f"[AGENT_REACT] Final answer provided: {response.final_answer}")

    # 8) If neither "action" nor "final_answer", treat as parsing error or replan
    else:
        if getattr(response, 'replan_requested', False):
            state.error_message = "[REPLAN_REQUESTED] LLM requested replanning."
            logger.warning("[AGENT_REACT] [REPLAN_REQUESTED] LLM requested replanning.")
        else:
            state.agent_outcome = None
            state.error_message = (
                "[AGENT_REACT] [Error] LLM did not provide a valid action or final answer. Retry. "
            )
            logger.warning("[AGENT_REACT] No valid action or final answer in LLM output. Retry.")

    logger.info(f"[AGENT_REACT] End of agent_react node.")
    return state