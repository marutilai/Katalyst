from katalyst_agent.state import KatalystAgentState
from katalyst_agent.services.llms import get_llm
from langchain_core.messages import AIMessage
from katalyst_agent.utils.logger import get_logger


def invoke_llm(state: KatalystAgentState) -> KatalystAgentState:
    """
    Loads the LLM and invokes it with messages_for_next_llm_call.
    Updates llm_response_content, chat_history, current_iteration, and resets messages_for_next_llm_call.
    """
    logger = get_logger()
    logger.info(f"Entered invoke_llm with state: {state}")
    if not state.messages_for_next_llm_call:
        raise ValueError("No messages prepared for LLM call.")

    # Load LLM instance
    llm_instance = get_llm()

    # LLM call
    response = llm_instance.invoke(state.messages_for_next_llm_call)
    ai_message = AIMessage(content=response.content)

    # Update state
    state.llm_response_content = ai_message.content
    state.chat_history.append(ai_message) # add AI message to chat history
    state.current_iteration += 1
    state.messages_for_next_llm_call = None
    logger.info(f"Exiting invoke_llm with updated state.")
    return state
