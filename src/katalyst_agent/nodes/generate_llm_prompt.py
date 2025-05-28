from katalyst_agent.state import KatalystAgentState
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
)
from typing import List
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.prompts.system import get_system_prompt


def generate_llm_prompt(state: KatalystAgentState) -> KatalystAgentState:
    """
    Prepares the messages for the next LLM call, but does not modify chat_history.
    The new messages for this turn are computed locally and not stored on the state.
    """
    logger = get_logger()
    logger.info(f"Entered generate_llm_prompt (iteration {getattr(state, 'current_iteration', '?')})")
    # These are the new messages for *this specific turn*
    current_turn_messages: List[BaseMessage] = []

    if state.current_iteration == 0:
        system_prompt_content = get_system_prompt(state)
        current_turn_messages.append(SystemMessage(content=system_prompt_content))
        current_turn_messages.append(HumanMessage(content=f"Proceed with the task: {state.task}"))
    else:
        if state.error_message:
            current_turn_messages.append(
                HumanMessage(content=f"[Error Encountered, please address]:\n{state.error_message}")
            )
        elif state.tool_output:
            current_turn_messages.append(HumanMessage(content=f"[Tool Output]:\n{state.tool_output}"))
        if state.user_feedback:
            current_turn_messages.append(
                HumanMessage(content=f"[User Feedback]:\n{state.user_feedback}")
            )

    # The messages to send to LLM are: the entire current chat_history PLUS any new messages for this turn.
    messages_to_send_to_llm = list(state.chat_history)
    messages_to_send_to_llm.extend(current_turn_messages)

    state.messages_for_next_llm_call = messages_to_send_to_llm
    state.tool_output = None
    state.error_message = None
    state.user_feedback = None

    logger.info(f"generate_llm_prompt prepared {len(current_turn_messages)} new input message(s).")
    logger.info(f"Exiting generate_llm_prompt.")
    return state
 