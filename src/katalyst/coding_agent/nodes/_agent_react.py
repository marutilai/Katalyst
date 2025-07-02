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
from katalyst.katalyst_core.utils.action_trace_summarizer import ActionTraceSummarizer

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

# CORE WORKFLOW
- Analyze if task is focused (single feature) or broad (needs breakdown)
- Execute directly if clear path exists - file operations are just tools, not tasks
- Decompose ONLY when discovering complexity during execution

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
- Use relative imports within same package: from .models import User
- For cross-module: from app.models import User (if app is root)
- Avoid package-style imports unless setup.py exists

# TOOL USAGE
- Use ONLY tools from the available tools section
- Execute ONE tool per ReAct step (no parallel execution, no multi_tool_use.parallel)
- Check scratchpad before acting - don't repeat failed operations


# TASK COMPLETION
- final_answer only when task FULLY complete
- Be specific about what was accomplished
- List the key components created/modified

# CONTEXT AWARENESS - CHECK BEFORE EVERY ACTION
- ALWAYS check "Recent File Operations" BEFORE any file operation
- ALWAYS check "Recent Tool Operations" BEFORE repeating any tool
- If you see the same file read 2+ times in context → STOP, you already have that information
- If you see failed operations → do NOT retry the same approach
- Use the operation context as your memory - trust what it tells you

## STRICT OPERATION CONTEXT RULES - VIOLATIONS WILL BE BLOCKED:

### 1. **BEFORE read_file - MANDATORY CHECK**:
   - If a file appears in "Recent Tool Operations" with "✓ read_file", you MUST NOT read it again
   - The content is already in your scratchpad from the previous read
   - Reading the same file again is WASTEFUL and will be BLOCKED
   - Example: If you see "✓ read_file: backend/app.py" → DO NOT call read_file on backend/app.py again

### 2. **BEFORE write_to_file - MANDATORY CHECK**:
   - Check "Recent File Operations" for the file path
   - If file shows as "created" → MUST use apply_source_code_diff to modify
   - Creating a file that already exists will FAIL
   - Trust the context - it never lies about file existence

### 3. **CONSECUTIVE DUPLICATES = IMMEDIATE BLOCK**:
   - Calling the same tool with same inputs back-to-back is FORBIDDEN
   - This will trigger a CRITICAL error and waste cycles
   - The system will forcibly block such calls

### 4. **OPERATION CONTEXT IS YOUR MEMORY**:
   - Recent Tool Operations shows EVERY tool call and its result (✓ = success, ✗ = failed)
   - Recent File Operations shows EVERY file created/modified/read
   - This is GROUND TRUTH - more reliable than your reasoning
   - If operation context says you did something, YOU DID IT
   - Do not "double-check" or "verify" - that's what causes loops

# HANDLING BLOCKED OPERATIONS
When blocked: STOP immediately, check scratchpad for existing info, try DIFFERENT approach
Blocked = information already exists - use it instead of retrying

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
        ""
    ]
    
    # Add operation context if available - MAKE IT PROMINENT
    if operation_context:
        user_message_content_parts.extend([
            "🔍 === CRITICAL: CHECK THIS FIRST - Recent Operations (YOUR MEMORY) ===",
            "⚠️  MANDATORY: Review this before any action to avoid redundant/blocked operations!",
            operation_context,
            "🚫 Do NOT repeat operations shown above - use existing information instead!",
            ""
        ])
    
    # Add task context after operation context
    user_message_content_parts.extend([
        "=== Task Context: Current Planner Task, Subtasks, and Currently Working On ===",
        task_context
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
        
        # Check if this is an escalated error message that should be preserved
        # These contain critical feedback patterns that help the agent adapt
        escalation_markers = ["💡 HINT:", "⚠️ WARNING:", "🚨 CRITICAL:", "THINK HARDER", "consecutive blocks"]
        should_preserve = any(marker in error_details for marker in escalation_markers)
        
        if should_preserve:
            # Preserve the full custom message for escalated feedback
            formatted_error = format_error_for_llm(error_type, error_details, custom_message=error_details)
        else:
            # Use default formatting for regular errors
            formatted_error = format_error_for_llm(error_type, error_details)
            
        user_message_content_parts.append(f"\nError Information:\n{formatted_error}")
        state.error_message = None  # Consume the error message

    # Add action trace if it exists (scratchpad for LLM reasoning)
    if state.action_trace:
        # Get configuration
        action_trace_trigger = int(os.getenv("KATALYST_ACTION_TRACE_TRIGGER", 10))
        keep_last_n = int(os.getenv("KATALYST_ACTION_TRACE_KEEP_LAST_N", 5))
        
        # Be more aggressive if context is already large
        current_context_size = len(system_message_content) + len("\n".join(user_message_content_parts))
        if current_context_size > 30000:
            # Very aggressive settings for large contexts
            action_trace_trigger = min(action_trace_trigger, 5)
            keep_last_n = min(keep_last_n, 3)
        
        # Check if we need to compress based on count (similar to conversation summarizer)
        if len(state.action_trace) > action_trace_trigger:
            # Calculate size before compression
            full_scratchpad = "\n".join([
                f"Previous Action: {action.tool}\nPrevious Action Input: {action.tool_input}\nObservation: {obs}"
                for action, obs in state.action_trace
            ])
            before_size = len(full_scratchpad)
            
            logger.info(
                f"[ACTION_TRACE_COMPRESSION] Compressing action trace in {agent_react.__name__}: "
                f"{len(state.action_trace)} actions > {action_trace_trigger} trigger, "
                f"size before: {before_size} chars"
            )
            
            # Split the trace
            actions_to_summarize = state.action_trace[:-keep_last_n]
            actions_to_keep = state.action_trace[-keep_last_n:]
            
            # Use summarizer to create a summary
            summarizer = ActionTraceSummarizer(component="execution")
            # Get just the summary text
            summary_text = summarizer._create_summary(actions_to_summarize, target_reduction=0.8)
            
            if summary_text:
                # Create a synthetic action/observation pair for the summary
                summary_action = AgentAction(
                    tool="[SUMMARY]",
                    tool_input={"count": len(actions_to_summarize)},
                    log=f"Summary of {len(actions_to_summarize)} previous actions"
                )
                summary_observation = f"[PREVIOUS ACTIONS SUMMARY]\n{summary_text}\n[END OF SUMMARY]"
                
                # Replace the action trace with summary + recent actions
                state.action_trace = [(summary_action, summary_observation)] + actions_to_keep
                
                logger.info(
                    f"[ACTION_TRACE_COMPRESSION] Replaced {len(actions_to_summarize)} actions with summary. "
                    f"New trace has {len(state.action_trace)} entries."
                )
            
            # Format the scratchpad content
            scratchpad_content = summarizer.summarize_action_trace(
                state.action_trace,
                keep_last_n=len(state.action_trace),  # Keep all since we already compressed
                max_chars=100000  # Don't force additional summarization
            )
            
            # Log compression results
            after_size = len(scratchpad_content)
            reduction = (1 - after_size / before_size) * 100 if before_size > 0 else 0
            logger.info(
                f"[ACTION_TRACE_COMPRESSION] Compressed from {before_size} to {after_size} chars "
                f"({reduction:.1f}% reduction)"
            )
        else:
            # Just format normally if under threshold
            formatted_actions = []
            for action, obs in state.action_trace:
                # Truncate very long observations even in normal formatting
                if len(obs) > 1000:
                    obs = obs[:997] + "..."
                formatted_actions.append(
                    f"Previous Action: {action.tool}\nPrevious Action Input: {action.tool_input}\nObservation: {obs}"
                )
            scratchpad_content = "\n".join(formatted_actions)
        
        user_message_content_parts.append(
            f"\nPrevious actions and observations (scratchpad):\n{scratchpad_content}"
        )
        
        # Log scratchpad size for debugging (max 10 actions now)
        logger.debug(f"[AGENT_REACT] Scratchpad size: {len(scratchpad_content)} chars, {len(state.action_trace)} actions (max 10)")

    user_message_content = "\n".join(user_message_content_parts)
    
    # Log total context size for debugging
    total_context_size = len(system_message_content) + len(user_message_content)
    logger.debug(f"[AGENT_REACT] Total context size: {total_context_size} chars (system: {len(system_message_content)}, user: {len(user_message_content)})")
    if total_context_size > 50000:
        logger.warning(f"[AGENT_REACT] Very large context detected: {total_context_size} chars - may cause performance issues")

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
