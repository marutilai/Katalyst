from katalyst_agent.state import KatalystAgentState
from katalyst_agent.utils.xml_parser import parse_tool_call
from katalyst_agent.utils.logger import get_logger


def parse_llm_response(state: KatalystAgentState) -> KatalystAgentState:
    """
    Parses the LLM response content to extract a tool call and updates the state.
    """
    logger = get_logger()
    logger.info(f"Entered parse_llm_response with state: {state}")
    if not state.llm_response_content:
        state.parsed_tool_call = None
        logger.info(f"Exiting parse_llm_response with updated state: {state}")
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

    logger.info(f"Exiting parse_llm_response with updated state: {state}")
    return state
