from katalyst_agent.state import KatalystAgentState
from katalyst_agent.prompts.tools.apply_diff import APPLY_DIFF_PROMPT
from katalyst_agent.prompts.tools.ask_followup_question import ASK_FOLLOWUP_QUESTION_PROMPT
from katalyst_agent.prompts.tools.attempt_completion import ATTEMPT_COMPLETION_PROMPT
from katalyst_agent.prompts.tools.execute_command import EXECUTE_COMMAND_PROMPT
from katalyst_agent.prompts.tools.list_code_definitions import LIST_CODE_DEFINITION_NAMES_PROMPT
from katalyst_agent.prompts.tools.list_files import LIST_FILES_PROMPT
from katalyst_agent.prompts.tools.read_file import READ_FILE_TOOL_PROMPT
from katalyst_agent.prompts.tools.search_files import SEARCH_FILES_PROMPT
from katalyst_agent.prompts.tools.write_to_file import WRITE_TO_FILE_PROMPT
from katalyst_agent.prompts.tools_formatting import TOOLS_FORMATTING_PROMPT
from textwrap import dedent

def get_system_prompt(state: KatalystAgentState) -> str:
    """
    Builds the system prompt for the LLM, including a description of the task, mode, and all tool prompts.
    """
    base_prompt = dedent(f"""
    You are a coding agent. Your current task is:
    {state.task}
    
    You are operating in mode: {state.current_mode}.
    """)
    # Concatenate all tool prompts, including formatting instructions
    all_tool_prompts = "\n\n".join([
        TOOLS_FORMATTING_PROMPT,
        APPLY_DIFF_PROMPT,
        ASK_FOLLOWUP_QUESTION_PROMPT,
        ATTEMPT_COMPLETION_PROMPT,
        EXECUTE_COMMAND_PROMPT,
        LIST_CODE_DEFINITION_NAMES_PROMPT,
        LIST_FILES_PROMPT,
        READ_FILE_TOOL_PROMPT,
        SEARCH_FILES_PROMPT,
        WRITE_TO_FILE_PROMPT,
    ])
    return base_prompt + "\n\n" + all_tool_prompts
