import os
from src.katalyst_core.state import KatalystState
from src.katalyst_core.services.llms import get_llm_instructor
from langchain_core.messages import AIMessage, ToolMessage
from src.katalyst_core.utils.logger import get_logger
from src.katalyst_core.utils.models import AgentReactOutput
from langchain_core.agents import AgentAction, AgentFinish
from src.katalyst_core.utils.tools import (
    get_formatted_tool_prompts_for_llm,
    get_tool_functions_map,
)
from src.katalyst_core.utils.error_handling import (
    ErrorType,
    create_error_message,
    classify_error,
    format_error_for_llm,
)

REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()


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
    logger.debug(f"[AGENT_REACT] Starting agent_react node...")

    # 1) Inner-loop guard: prevent infinite loops in the ReAct cycle
    state.inner_cycles += 1
    if state.inner_cycles > state.max_inner_cycles:
        error_msg = f"Inner loop exceeded {state.max_inner_cycles} cycles (task #{state.task_idx})."
        state.response = f"Stopped: {error_msg}"
        logger.warning(f"[AGENT_REACT][GUARDRAIL] {error_msg}")
        # Construct an AgentFinish to signal "done" to the router
        state.agent_outcome = AgentFinish(
            return_values={"output": "Inner loop limit exceeded"},
            log="Exceeded inner loop guardrail",
        )
        logger.warning(
            f"[AGENT_REACT] Inner loop limit exceeded. Returning AgentFinish."
        )
        return state

    # 2) Build the system message (persona, format, rules)
    # --------------------------------------------------------------------------
    # This message sets the agent's persona, output format, and tool usage rules.
    # It also appends detailed tool descriptions for LLM reference.
    system_message_content = """
        # AGENT PERSONA
        You are a ReAct agent. Your goal is to accomplish sub-tasks by thinking step-by-step and then either taking an action (tool call) or providing a final answer if the sub-task is complete.
        Based on your thought process, you will then EITHER take a single, precise 'action' (by calling one of the available tools) OR provide a 'final_answer' if, and ONLY if, the sub-task has been fully completed by your thought process alone or by a previous tool's observation.

        # OUTPUT FORMAT
        Respond in JSON with keys: thought (string, your reasoning), and EITHER (action (string, tool_name) AND action_input (object, tool_arguments)) OR (final_answer (string, your answer for the sub-task)).

        # TOOL USAGE RULES
        - You can ONLY use the tools explicitly defined in the 'You have access to the following tools:' section below.
        - Do NOT invent, hallucinate, or attempt to use any other tool names, variations, or structures (e.g., tools for parallel execution).
        - If you need to perform multiple actions that require tools, you MUST do them sequentially, one tool call per ReAct step (i.e., one 'action' in your JSON response).

        # FILE OPERATIONS & INFORMATION GATHERING
        - To list files in a directory, you MUST use the 'list_files' tool. Provide the full relevant path.
        - To read a file's content, you MUST use the 'read_file' tool.
        - To search within files, you MUST use the 'regex_search_files' tool.
        - Do NOT assume you can 'navigate' or 'list files' by just stating it in a 'final_answer'. You must use a tool if the subtask implies interacting with the file system.

        # SCRATCHPAD & REDUNDANCY RULES
        - Always use the scratchpad (previous actions and observations) to inform your reasoning and avoid repeating any tool calls or actions that have already been performed for the current sub-task.
        - Never ask the user for information that is already available in the scratchpad or previous tool outputs.
        - Do not repeat tool calls with the same arguments if the result is already present in the scratchpad.
        - If the required information is already available from previous steps, use it directly in your reasoning and proceed to the next logical step or provide a final answer.

        # FINAL ANSWER GUIDELINES
        When providing a final_answer after using tools:
        1. Be concise and clear about what was accomplished
        2. Mention which tool was used and what data is now available
        3. If multiple tools were used, summarize the key outcomes
        4. Do not repeat the full tool output in the final_answer

        # ERROR RECOVERY
        If you encounter an error:
        1. First, analyze the error and try to recover by using a different approach or tool.
        2. If recovery fails after multiple attempts, request replanning by setting replan_requested to true.
        3. If replanning is requested, provide a clear explanation of why the current approach isn't working.

        # TASK COMPLETION
        - Only provide a 'final_answer' when the *specific current sub-task* is fully and definitively completed.
        - If the overall original goal is complete after finishing all sub-tasks, the higher-level planner/replanner will handle the final wrap-up. Your role is to complete each sub-task given to you.
        - If you are unsure about the completion of a subtask, you MUST use the 'request_user_input' tool to ask the user for clarification or guidance. Do not guess or proceed without user input in such cases.
        """

    # Add detailed tool descriptions to the system message for LLM tool selection
    all_detailed_tool_prompts = get_formatted_tool_prompts_for_llm(
        REGISTERED_TOOL_FUNCTIONS_MAP
    )
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
            prev_task_name, prev_task_summary = state.completed_tasks[
                state.task_idx - 1
            ]
            user_message_content_parts.append(
                f"\nContext from previously completed sub-task ('{prev_task_name}'): {prev_task_summary}"
            )
        except IndexError:
            logger.warning(
                f"[AGENT_REACT] Could not get previous completed task context for task_idx {state.task_idx}"
            )

    # Add error message if it exists (for LLM self-correction)
    if state.error_message:
        # Classify and format the error for better LLM understanding
        error_type, error_details = classify_error(state.error_message)
        formatted_error = format_error_for_llm(error_type, error_details)
        user_message_content_parts.append(f"\nError Information:\n{formatted_error}")
        state.error_message = None  # Consume the error message

    # Add action trace if it exists (scratchpad for LLM reasoning)
    if state.action_trace:
        scratchpad_content = "\n".join(
            [
                f"Previous Action: {action.tool}\nPrevious Action Input: {action.tool_input}\nObservation: {obs}"
                for action, obs in state.action_trace
            ]
        )
        user_message_content_parts.append(
            f"\nPrevious actions and observations (scratchpad):\n{scratchpad_content}"
        )

    user_message_content = "\n".join(user_message_content_parts)

    # Compose the full LLM message list
    llm_messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": user_message_content},
    ]
    logger.debug(f"[AGENT_REACT] LLM messages: {llm_messages}")

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
        model=os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1"),
    )
    logger.debug(f"[AGENT_REACT] Raw LLM response: {response}")
    logger.debug(f"[AGENT_REACT] Parsed output: {response.dict()}")

    # 5) Log the LLM's thought and action to chat_history for traceability
    state.chat_history.append(AIMessage(content=f"Thought: {response.thought}"))
    if response.action:
        state.chat_history.append(
            AIMessage(
                content=f"Action: {response.action} with input {response.action_input}"
            )
        )

    # 6) If "action" key is present, wrap in AgentAction and update state
    if response.action:
        args_dict = response.action_input or {}
        state.agent_outcome = AgentAction(
            tool=response.action,
            tool_input=args_dict,
            log=f"Thought: {response.thought}\nAction: {response.action}\nAction Input: {str(args_dict)}",
        )
        state.error_message = None
        logger.debug(
            f"[AGENT_REACT] Action requested: {response.action} with input {args_dict}"
        )

    # 7) If "final_answer" key is present, wrap in AgentFinish and update state
    elif response.final_answer:
        state.agent_outcome = AgentFinish(
            return_values={"output": response.final_answer},
            log=f"Thought: {response.thought}\nFinal Answer: {response.final_answer}",
        )
        state.error_message = None
        logger.info(
            f"[AGENT_REACT] Completed subtask with answer: {response.final_answer}"
        )

    # 8) If neither "action" nor "final_answer", treat as parsing error or replan
    else:
        if getattr(response, "replan_requested", False):
            state.error_message = create_error_message(
                ErrorType.REPLAN_REQUESTED, "LLM requested replanning.", "AGENT_REACT"
            )
            logger.warning("[AGENT_REACT] [REPLAN_REQUESTED] LLM requested replanning.")
        else:
            state.agent_outcome = None
            state.error_message = create_error_message(
                ErrorType.PARSING_ERROR,
                "LLM did not provide a valid action or final answer. Retry.",
                "AGENT_REACT",
            )
            logger.warning(
                "[AGENT_REACT] No valid action or final answer in LLM output. Retry."
            )

    logger.debug(f"[AGENT_REACT] End of agent_react node.")
    return state
