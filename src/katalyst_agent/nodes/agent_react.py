import os
from katalyst_agent.state import KatalystState
from katalyst_agent.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage, ToolMessage
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.models import AgentReactOutput
from langchain_core.agents import AgentAction, AgentFinish
from katalyst_agent.utils.tools import get_formatted_tool_prompts_for_llm, get_tool_functions_map

REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()

def agent_react(state: KatalystState) -> KatalystState:
    """
    Execute one ReAct (Reason-Act) cycle for the current sub-task.
    Uses Instructor to get a structured response from the LLM.

    * Primary Task: Execute one ReAct (Reason-Act) cycle for the current sub-task.
    * State Changes:
    * Increments state.inner_cycles.
    * Checks if state.inner_cycles > state.max_inner_cycles:
    * If true, sets state.response to an error message (e.g., "Inner loop limit exceeded...").
    * Sets state.agent_outcome = None (or an AgentFinish indicating error).
    * Returns the updated KatalystState (the route_after_agent router will then see state.response and route to END).
    * If within limits:
    * Formats a prompt for the LLM including the current sub-task, action_trace (as scratchpad), and any error_message.
    * Calls the LLM.
    * Parses the LLM's response to identify a "Thought" and either an "Action" (XML tool call) or a "Final Answer" for the current sub-task.
    * If "Action":
    * Parses the XML tool call into tool_name and args_dict.
    * Sets state.agent_outcome = AgentAction(tool=tool_name, tool_input=args_dict, log=thought_and_raw_action_string).
    * If "Final Answer":
    * Sets state.agent_outcome = AgentFinish(return_values={"output": final_answer_string}, log=thought_and_raw_final_answer_string).
    * If parsing fails or format is incorrect:
    * Sets state.error_message with details for the next agent_react call (to attempt self-correction for this sub-task).
    * Sets state.agent_outcome = None.
    * Logs the raw LLM interaction to state.chat_history (or a more detailed ReAct trace if preferred).
    * Returns: The updated KatalystState.    
    """
    logger = get_logger()
    logger.info(f"[AGENT_REACT] Starting agent_react node...")
    
    # 1) Inner-loop guard
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
    system_message_content = (
        "You are a ReAct agent. Your goal is to accomplish sub-tasks by thinking step by step "
        "and then either taking an action (tool call) or providing a final answer if the sub-task is complete. "
        "Respond in JSON with keys: thought (string, your reasoning), "
        "and EITHER (action (string, tool_name) AND action_input (object, tool_arguments)) "
        "OR (final_answer (string, your answer for the sub-task))."
    )

    # Get the detailed descriptions of all *discovered and registered* tools and add them to the system message
    all_detailed_tool_prompts = get_formatted_tool_prompts_for_llm(REGISTERED_TOOL_FUNCTIONS_MAP)
    system_message_content += f"\n\n{all_detailed_tool_prompts}"

    # 2) Build the user message (task, error, scratchpad)
    current_subtask = (
        state.task_queue[state.task_idx] 
        if state.task_idx < len(state.task_queue) 
        else ""
    )
    user_message_content_parts = [f"Subtask: {current_subtask}"]
    if state.error_message:
        user_message_content_parts.insert(
            0,
            f"An error occurred in the previous step: {state.error_message}\n"
            "Please analyze this error and try to correct your plan or action."
        )
        state.error_message = None  # Consume the error message

    if state.action_trace:
        scratchpad_content = "\n".join([
            f"Previous Action: {action.tool}\nPrevious Action Input: {action.tool_input}\nObservation: {obs}" 
            for action, obs in state.action_trace
        ])
        user_message_content_parts.append(
            f"\nPrevious actions and observations (scratchpad):\n{scratchpad_content}"
        )

    user_message_content = "\n".join(user_message_content_parts)

    llm_messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": user_message_content}
    ]

    # 3. Call the LLM
    llm = get_llm_instructor()
    response = llm.chat.completions.create(
        messages=llm_messages,
        response_model=AgentReactOutput,
        temperature=0.1,
    )
    logger.debug(f"[AGENT_REACT] Raw LLM response: {response}")
    logger.info(f"[AGENT_REACT] Parsed output: {response.dict()}")

    # 4) Log the LLM's thought to chat_history: full ReAct trace
    state.chat_history.append(AIMessage(content=f"Thought: {response.thought}"))
    if response.action:
        state.chat_history.append(AIMessage(content=f"Action: {response.action} with input {response.action_input}"))    

    # 5) If "action" key is present, wrap in AgentAction
    if response.action:
        args_dict = response.action_input or {}
        state.agent_outcome = AgentAction(
            tool=response.action,
            tool_input=args_dict,
            log=f"Thought: {response.thought}\nAction: {response.action}\nAction Input: {str(args_dict)}"
        )
        state.error_message = None
        logger.info(f"[AGENT_REACT] Action requested: {response.action} with input {args_dict}")

    # 6) If "final_answer" key is present, wrap in AgentFinish
    elif response.final_answer:
        state.agent_outcome = AgentFinish(
            return_values={"output": response.final_answer},
            log=f"Thought: {response.thought}\nFinal Answer: {response.final_answer}",
        )
        state.error_message = None
        logger.info(f"[AGENT_REACT] Final answer provided: {response.final_answer}")

    # 7) If neither "action" nor "final_answer", treat as parsing error
    else:
        # Example: If the LLM/tool signals a need to replan, set the marker
        # (In a real implementation, you might check for a specific LLM output or tool error)
        # For now, we just use the parsing error as a possible replan trigger example:
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