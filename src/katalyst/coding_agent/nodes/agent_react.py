import os
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.services.llms import (
    get_llm_client,
    get_llm_params,
)
from langchain_core.messages import AIMessage, ToolMessage
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.models import AgentReactOutput
from langchain_core.agents import AgentAction, AgentFinish
from katalyst.katalyst_core.utils.tools import (
    get_formatted_tool_prompts_for_llm,
    get_tool_functions_map,
)
from katalyst.katalyst_core.utils.error_handling import (
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
            "[AGENT_REACT] Inner loop limit exceeded. Returning AgentFinish."
        )
        return state

    # 2) Build the system message (persona, format, rules)
    # --------------------------------------------------------------------------
    # This message sets the agent's persona, output format, and tool usage rules.
    # It also appends detailed tool descriptions for LLM reference.
    system_message_content = """
# AGENT PERSONA
You are an adaptive ReAct agent. Your goal is to accomplish tasks through intelligent exploration, decision-making, and tool usage. Tasks may be goal-oriented rather than tool-specific.

# OUTPUT FORMAT
Respond in JSON with:
- thought: (string) Your step-by-step reasoning
- EITHER:
  - action: (string) Tool name AND action_input: (object) Tool arguments
  - OR final_answer: (string) Your answer when the task is complete

# HANDLING GOAL-ORIENTED TASKS
When given a high-level task (e.g., "Implement user authentication system"):
1. First understand the goal - what needs to be achieved?
2. Check dependencies - what must exist before this task can succeed?
3. Explore the existing codebase if relevant (list files, read examples)
4. Plan your approach mentally before starting implementation
5. Execute systematically, adapting based on discoveries
6. Use create_subtask if you discover the task has multiple independent parts

# DEPENDENCY CHECKING
Before starting implementation:
- Ask: "What needs to exist for this task to succeed?"
- Can't add validation to schemas that don't exist
- Can't test functions that aren't implemented
- Can't import from files that haven't been created
- If dependencies are missing, either:
  - Create them first within this task, OR
  - Use create_subtask to add prerequisite tasks

# DYNAMIC TASK DECOMPOSITION
You can create subtasks when:
- The current task has multiple independent components
- You discover complexity during exploration
- Better organization would help track progress
Example: If asked to "Create models", and you find User, Todo, and Category are needed,
create subtasks for each rather than trying to do all in one task.

# TOOL USAGE RULES
- Use ONLY the tools explicitly defined in the available tools section
- Do NOT invent or hallucinate tool names or structures
- Execute ONE tool per ReAct step (no parallel execution, no multi_tool_use.parallel)
- Remember: create_subtask is available for task decomposition

# FILE OPERATIONS
- ALWAYS use paths relative to project root (where 'katalyst' command was run)
- Include the full path from project root, not partial paths
- CRITICAL: When task says "create in folder X", ALL files go in that folder (e.g., "projectname/...")
- To find files: Use 'list_files' (can be recursive) to locate files by name
- To read: Use 'read_file' to examine file contents
- To search in content: Use 'regex_search_inside_files' to find patterns within files
- To create/modify: Use 'write_to_file' or 'apply_source_code_diff'
- For directories: 'write_to_file' auto-creates parent directories

# SCRATCHPAD RULES
- Always check scratchpad (previous actions/observations) before acting
- Use EXACT information from scratchpad - do NOT hallucinate
- Avoid repeating tool calls already performed
- Build on previous discoveries to make informed decisions
- If searches yield no results after 2-3 attempts, accept that the content doesn't exist
- Don't keep searching for the same patterns - move on to creating what you need

# TASK COMPLETION
- Only provide 'final_answer' when the current task goal is FULLY achieved
- Be specific about what was accomplished
- If task was too complex, mention any subtasks created for remaining work
- Focus on outcomes, not just tool executions

# ERROR RECOVERY
1. Analyze errors and adapt your approach
2. Use create_subtask if the task needs different strategy
3. Request replanning only if fundamentally stuck
4. Learn from failures to improve subsequent attempts"""

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
    if state.completed_tasks:
        try:
            # Get the summary of the most recently completed task
            prev_task_name, prev_task_summary = state.completed_tasks[-1]
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

    # 4) Call the LLM for a structured ReAct response
    # --------------------------------------------------------------------------
    # The LLM is expected to return a JSON object matching AgentReactOutput:
    #   - thought: reasoning string
    #   - action: tool name (optional)
    #   - action_input: dict of tool arguments (optional)
    #   - final_answer: string (optional)
    #   - replan_requested: bool (optional)
    # Use simplified API
    llm = get_llm_client("agent_react", async_mode=False, use_instructor=True)
    llm_params = get_llm_params("agent_react")
    response = llm.chat.completions.create(
        messages=llm_messages,
        response_model=AgentReactOutput,
        **llm_params,
    )

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
        logger.info(f"[AGENT_REACT] Agent selected action: {response.action} with input: {args_dict}")

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

    return state
