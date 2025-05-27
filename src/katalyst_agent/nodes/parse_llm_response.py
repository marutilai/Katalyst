from katalyst_agent.state import KatalystAgentState
from katalyst_agent.utils.xml_parser import parse_tool_call
from katalyst_agent.utils.logger import get_logger
import copy


def parse_llm_response(state: KatalystAgentState) -> KatalystAgentState:
    """
    Parses the LLM response content to extract a tool call and updates the state.
    """
    logger = get_logger()
    logger.info(f"Entered parse_llm_response (iteration {getattr(state, 'current_iteration', '?')})")
    logger.debug(f"State: {state}")
    state_before = copy.deepcopy(state)
    if not state.llm_response_content:
        state.parsed_tool_call = None
        changed = {k: v for k, v in state.__dict__.items() if getattr(state_before, k, None) != v}
        if changed:
            logger.info(f"parse_llm_response changed state: {changed}")
        logger.info(f"Exiting parse_llm_response (iteration {getattr(state, 'current_iteration', '?')})")
        return state

    # Parse tool call from the LLM response
    tool_call_dict = parse_tool_call(state.llm_response_content)
    if tool_call_dict:
        tool_name, args = next(iter(tool_call_dict.items()))
        state.parsed_tool_call = {"tool_name": tool_name, "args": args}
    else:
        state.parsed_tool_call = None

    # Optionally print or log the 'thinking' part of the LLM response
    print("LLM Thinking/Response:", state.llm_response_content)

    changed = {k: v for k, v in state.__dict__.items() if getattr(state_before, k, None) != v}
    if changed:
        logger.info(f"parse_llm_response changed state: {changed}")
    logger.info(f"Exiting parse_llm_response (iteration {getattr(state, 'current_iteration', '?')})")
    return state
 