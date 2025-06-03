from katalyst_agent.state import KatalystAgentState
from katalyst_agent.utils.logger import get_logger


def prepare_reprompt_feedback(state: KatalystAgentState) -> KatalystAgentState:
    """
    If state.error_message is set, add it as a HumanMessage to chat_history for LLM feedback/correction,
    then clear error_message. If error_message is not set, infer the appropriate error message based on state.
    Used before reprompting the LLM after a routing error.
    """
    logger = get_logger()
    logger.info(f"Entered prepare_reprompt_feedback (iteration {getattr(state, 'current_iteration', '?')})")

    # LangGraph routers must be pure (no state mutation), so we set error_message here, not in the router.
    # This node is always called before reprompting the LLM if the router returns REPROMPT_LLM.

    # If error_message is not set, infer it based on the state context
    if not state.error_message:
        # If the LLM responded with text but no tool call, give specific feedback
        if state.llm_response_content and state.llm_response_content.strip():
            # This case corresponds to the router deciding REPROMPT_LLM due to LLM_TEXT_RESPONSE_NO_TOOL
            state.error_message = (
                "Your response did not include a tool call. "
                "Please use an available tool or 'attempt_completion'."
            )
            logger.info(f"prepare_reprompt_feedback: Inferred error_message for LLM_TEXT_RESPONSE_NO_TOOL: {state.error_message}")
        else:
            # If the LLM response was empty or unhandled, give a generic feedback
            # This case corresponds to the router deciding REPROMPT_LLM due to UNHANDLED_STATE_OR_EMPTY_LLM_RESPONSE
            state.error_message = (
                "The previous turn did not result in an actionable response. "
                "Please try again, using a valid tool or 'attempt_completion'."
            )
            logger.info(f"prepare_reprompt_feedback: Inferred error_message for UNHANDLED_STATE_OR_EMPTY_LLM_RESPONSE: {state.error_message}")
    else:
        # If state.error_message was already set (e.g., by a previous node like execute_tool failing),
        # this node doesn't need to overwrite it. Just log that it's being preserved.
        logger.info(f"prepare_reprompt_feedback: Preserving existing error_message: {state.error_message}")

    # This node's job is to ensure error_message is set.
    # generate_llm_prompt will consume it and then clear it from the state.
    logger.info(f"Exiting prepare_reprompt_feedback (iteration {getattr(state, 'current_iteration', '?')}) with error_message: {state.error_message}")
    return state