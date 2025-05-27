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
    logger = get_logger()
    logger.info(f"Entered generate_llm_prompt with state: {state}")
    
    # These are the new messages for *this specific turn*
    current_turn_messages: List[BaseMessage] = []

    if state.current_iteration == 0:  # Only for the very first iteration
        system_prompt_content = get_system_prompt(state)
        current_turn_messages.append(SystemMessage(content=system_prompt_content))
        current_turn_messages.append(HumanMessage(content=f"Proceed with the task: {state.task}"))
    else:
        # For subsequent turns, new messages are based on tool output, feedback, or errors
        if state.tool_output:
            # If your LLM expects ToolMessage for tool results
            # For XML-based, a HumanMessage might be fine to show "what the tool did"
            current_turn_messages.append(HumanMessage(content=f"[Tool Output]:\n{state.tool_output}"))
            # Or if using native tool calling later, you'd use ToolMessage(content=..., tool_call_id=...)
        if state.user_feedback:
            current_turn_messages.append(
                HumanMessage(content=f"[User Feedback]:\n{state.user_feedback}")
            )
        # Always include error_message if set (even if set by the router or elsewhere)
        if state.error_message:
            current_turn_messages.append(
                HumanMessage(content=f"[Error Encountered, please address]:\n{state.error_message}")
            )
        # If after a tool/error/feedback there are no new messages,
        # it implies something might be off, or the LLM should just continue.
        # For now, we assume there will be *some* new input if not the first turn.
        # If current_turn_messages is empty here, it means the LLM needs to respond to the existing chat_history.
        # This case might need specific handling if you want to force a new user-like message.
        # However, for now, an empty current_turn_messages means only chat_history is sent.

    # Prepare messages for the LLM: current history + new messages for this turn
    # The invoke_llm node will send state.messages_for_next_llm_call
    # state.chat_history should contain ALL messages up to *before* this new LLM call.
    
    # The messages to send to LLM are:
    # The *entire current chat_history* PLUS any *new messages generated just for this turn*.
    messages_to_send_to_llm = list(state.chat_history)  # Make a copy
    messages_to_send_to_llm.extend(current_turn_messages)

    state.messages_for_next_llm_call = messages_to_send_to_llm
    
    # Update the main chat_history with only the *newly generated messages for this turn*
    # The AIMessage from the LLM will be added by the invoke_llm node later.
    state.chat_history.extend(current_turn_messages)

    # Reset consumed fields
    state.tool_output = None
    state.error_message = None
    state.user_feedback = None
    logger.info(f"Exiting generate_llm_prompt with updated state.")
    return state
