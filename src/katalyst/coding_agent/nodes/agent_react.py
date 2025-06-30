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
from katalyst.katalyst_core.utils.decorators import compress_chat_history
from katalyst.katalyst_core.utils.task_display import get_task_context_for_agent

REGISTERED_TOOL_FUNCTIONS_MAP = get_tool_functions_map()


@compress_chat_history()
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
You are an adaptive ReAct agent. Your goal is to accomplish tasks through intelligent exploration, decision-making, and tool usage. 

# TASK CONTEXT
You'll see your current context like:
- Current Planner Task: The main task you're working on
- Subtasks: Any breakdown you've created (✓=done, →=current)
- Currently Working On: Your immediate focus

# OUTPUT FORMAT
Respond in JSON with:
- thought: (string) Your reasoning about what to do next
- EITHER:
  - action: (string) Tool name AND action_input: (object) Tool arguments
  - OR final_answer: (string) Your answer when task is complete

# CORE WORKFLOW: ANALYZE → EXECUTE → DECOMPOSE (only if needed)

## 1. ANALYZE THE TASK
For EVERY new task, determine the scope:
- Is this a focused, achievable goal? (e.g., "Add user authentication endpoint", "Create Todo model with validation")
- Or is this a broad objective needing breakdown? (e.g., "Build entire authentication system", "Create full CRUD API")

## 2. START EXECUTION
Begin working on the task:
- If you can see a clear path to completion, proceed with implementation
- File operations (creating directories, writing files) are NOT tasks - they're just tool operations
- A single task often involves multiple file operations

## 3. DECOMPOSE (only when you discover complexity)
Create subtasks ONLY when you discover during execution that:
- The current task has distinct, independent components
- You've identified multiple models/endpoints/features that need separate attention
- The work naturally splits into logical, testable units

## GOOD vs BAD TASK GRANULARITY
❌ BAD (too granular): "Create models directory", "Write __init__.py file", "Add import statement"
✅ GOOD (atomic but complete): "Implement User model with authentication fields", "Add validation to Todo endpoints", "Set up database connection"

Remember: Tasks should represent meaningful work units, not individual file operations!

# EXPLORATION LIMITS
- If you find yourself repeating similar operations without progress → reassess your approach
- After exploring 3-4 different files/directories without finding what you need → the content likely doesn't exist
- No repetitive operations - adapt your strategy or accept the current state

# FILE OPERATIONS
- Project root shown as "Project Root Directory" at message start
- ALWAYS use paths relative to project root (where 'katalyst' command was run)
- Include the full path from project root, not partial paths
- write_to_file auto-creates parent directories

# IMPORT STATEMENTS
- Use relative imports for files within the same project (e.g., from .models import User)
- Use absolute imports starting from project root for cross-module imports
- Do NOT use package-style imports (e.g., from myproject.app.models) unless project has setup.py
- For simple projects without setup.py, prefer relative imports or sys.path adjustments
- Example for a FastAPI project structure:
  - In routers/todo.py: from ..models import schemas, todo
  - In database.py: from .models.todo import Base
  - Or add to main.py: sys.path.append(os.path.dirname(__file__))

# TOOL USAGE
- Use ONLY tools from the available tools section
- Execute ONE tool per ReAct step (no parallel execution, no multi_tool_use.parallel)
- Check scratchpad before acting - don't repeat failed operations

# TASK GRANULARITY EXAMPLES

## Example 1: Setting up a FastAPI project structure
❌ WRONG APPROACH (too granular subtasks):
- "Create app directory"
- "Create models directory" 
- "Create routers directory"
- "Write __init__.py files"

✅ RIGHT APPROACH (single task with multiple operations):
Task: "Set up FastAPI project structure with standard directories"
Then use write_to_file multiple times to create all needed files/directories

## Example 2: Implementing a data model
❌ WRONG APPROACH (file-focused):
- "Create user.py file"
- "Add SQLAlchemy imports"
- "Define User class"

✅ RIGHT APPROACH (feature-focused):
Task: "Implement User model with authentication fields and validation"
This naturally includes creating the file, imports, model definition, and validation

## Example 3: Building CRUD endpoints
❌ WRONG APPROACH (too detailed):
- "Create GET endpoint"
- "Create POST endpoint"
- "Add error handling to endpoints"

✅ RIGHT APPROACH (cohesive unit):
Task: "Implement CRUD endpoints for Todo model"
All CRUD operations belong together as they share schemas, validation, and error handling

# TASK COMPLETION
- final_answer only when task FULLY complete
- Be specific about what was accomplished
- List the key components created/modified

# CONTEXT AWARENESS
- Check "Recent File Operations" section before creating/modifying files
- Review "Recent Tool Operations" to avoid redundant actions
- If a file appears as "created" in context, don't create it again
- If an operation failed recently, try a different approach

# SCRATCHPAD RULES
- Always check scratchpad (previous actions/observations) before acting
- Use EXACT information from scratchpad - do NOT hallucinate
- Avoid repeating tool calls already performed
- Build on previous discoveries to make informed decisions
- If searches yield no results after 2-3 attempts, accept that the content doesn't exist
- Don't keep searching for the same patterns - move on to creating what you need
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
    # Get full task context with hierarchy
    task_context = get_task_context_for_agent(state)
    
    # Get operation context
    operation_context = state.operation_context.get_context_for_agent()
    
    # Log contexts for debugging
    logger.debug(f"[AGENT_REACT] Task context:\n{task_context}")
    if operation_context:
        logger.debug(f"[AGENT_REACT] Operation context:\n{operation_context}")
    else:
        logger.debug("[AGENT_REACT] Operation context: None")
    
    user_message_content_parts = [
        f"Project Root Directory: {state.project_root_cwd}",
        "",
        "=== Task Context: Current Planner Task, Subtasks, and Currently Working On ===",
        task_context
    ]
    
    # Add operation context if available
    if operation_context:
        user_message_content_parts.extend([
            "",
            "=== Operation Context: Recent File Operations and Tool Operations DONE in the previous ReAct loop ===",
            operation_context
        ])

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
