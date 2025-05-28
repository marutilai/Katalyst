from katalyst_agent.state import KatalystAgentState
from katalyst_agent.services.llms import get_llm
from langchain_core.messages import AIMessage
from katalyst_agent.utils.logger import get_logger
import copy


def invoke_llm(state: KatalystAgentState) -> KatalystAgentState:
    """
    Loads the LLM and invokes it with messages_for_next_llm_call.
    Updates llm_response_content, chat_history, current_iteration, and resets messages_for_next_llm_call.
    The new messages for this turn are computed by comparing messages_for_next_llm_call and chat_history.
    """
    logger = get_logger()
    logger.info(f"Entered invoke_llm (iteration {getattr(state, 'current_iteration', '?')})")
    logger.debug(f"State: {state}")
    state_before = copy.deepcopy(state)
    if not state.messages_for_next_llm_call:
        logger.error("invoke_llm: No messages prepared in state.messages_for_next_llm_call.")
        state.error_message = "Internal error: messages_for_next_llm_call was empty."
        return state

    # Load LLM instance
    llm_instance = get_llm()

    # LLM call
    response = llm_instance.invoke(state.messages_for_next_llm_call)
    ai_message = AIMessage(content=response.content)

    # Compute the new messages for this turn
    new_inputs_for_this_turn = state.messages_for_next_llm_call[len(state.chat_history):]
    # Update chat_history: append the new inputs and the AI response
    state.chat_history.extend(new_inputs_for_this_turn)
    state.chat_history.append(ai_message)

    state.llm_response_content = ai_message.content
    state.current_iteration += 1
    state.messages_for_next_llm_call = None

    changed = {k: v for k, v in state.__dict__.items() if getattr(state_before, k, None) != v}
    if changed:
        logger.info(f"invoke_llm changed state: {changed}")
    logger.info(f"Exiting invoke_llm (iteration {getattr(state, 'current_iteration', '?')})")
    return state
