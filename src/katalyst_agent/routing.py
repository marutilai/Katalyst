from katalyst_agent.state import KatalystAgentState
from katalyst_agent.utils.logger import get_logger

logger = get_logger()

# NOTE: LangGraph routers must be pure functions: they CANNOT mutate state, only return a routing string.
# Any state mutation (e.g., setting error_message) must be done in a node, not in the router.

# Routing keys for graph transitions
FINISH_MAX_ITERATIONS = "FINISH_MAX_ITERATIONS"
FINISH_SUCCESSFUL_COMPLETION = "FINISH_SUCCESSFUL_COMPLETION"
EXECUTE_TOOL = "EXECUTE_TOOL"
REPROMPT_LLM = "REPROMPT_LLM"


def decide_next_action_router(state: KatalystAgentState) -> str:
    """
    Determines the next logical step based on the current agent state.
    Returns a string key that maps to a destination node or END.
    This function must NOT mutate state (LangGraph router requirement).
    """
    logger.info(f"Routing: Iteration {state.current_iteration}/{state.max_iterations}. Parsed tool: {state.parsed_tool_call}")

    # Priority 1: Max iterations
    if state.current_iteration >= state.max_iterations:
        logger.info("Routing decision: MAX_ITERATIONS_REACHED")
        return FINISH_MAX_ITERATIONS

    parsed_call = state.parsed_tool_call

    # Priority 2: Explicit completion signal from LLM
    if parsed_call and parsed_call.get("tool_name") == "attempt_completion":
        logger.info("Routing decision: ATTEMPT_COMPLETION_SIGNALED")
        return FINISH_SUCCESSFUL_COMPLETION

    # Priority 3: Valid tool call to be executed
    if parsed_call and parsed_call.get("tool_name"):
        logger.info(f"Routing decision: EXECUTE_TOOL ({parsed_call['tool_name']})")
        return EXECUTE_TOOL

    # Priority 4: LLM responded with text, but no tool call
    # Giving LLM error-feedback for course correction
    if state.llm_response_content and state.llm_response_content.strip():
        logger.warning("Routing decision: LLM_TEXT_RESPONSE_NO_TOOL")
        # Do NOT mutate state here. The error_message will be set in the prepare_reprompt_feedback node.
        return REPROMPT_LLM

    # Priority 5: Catch-all for unclear situations / LLM didn't respond meaningfully
    # Giving LLM error-feedback for course correction
    logger.error("Routing decision: UNHANDLED_STATE_OR_EMPTY_LLM_RESPONSE")
    # Do NOT mutate state here. The error_message will be set in the prepare_reprompt_feedback node.
    return REPROMPT_LLM 