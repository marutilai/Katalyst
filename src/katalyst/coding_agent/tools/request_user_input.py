from typing import List
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
from katalyst.katalyst_core.utils.error_handling import create_error_message, ErrorType
from katalyst.katalyst_core.utils.exceptions import UserInputRequiredException
from katalyst.app.ui.input_handler import InputHandler
from rich.console import Console
import json


def format_response(question_to_ask_user: str, user_final_answer: str) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    return json.dumps(
        {
            "question_to_ask_user": question_to_ask_user,
            "user_final_answer": user_final_answer,
        }
    )


@katalyst_tool(
    prompt_module="request_user_input", prompt_var="REQUEST_USER_INPUT_TOOL_PROMPT",
    categories=["planner", "executor", "replanner"]
)
def request_user_input(
    question_to_ask_user: str, suggested_responses: List[str], user_input_fn=None
) -> str:
    """
    Asks the user a question to gather more information, providing suggested answers.
    Parameters:
      - question_to_ask_user: str (the question to ask the user)
      - suggested_responses: list of suggestion strings
      - user_input_fn: function to use for user input (defaults to input) - for testing only
    Returns the user's answer as a JSON string (with 'question_to_ask_user' and 'user_final_answer' keys).
    """
    logger = get_logger()
    logger.debug(
        f"Entered request_user_input with question='{question_to_ask_user}', suggested_responses='{suggested_responses}'"
    )

    if user_input_fn is None:
        user_input_fn = input
        logger.debug("Using default input function")
    else:
        logger.debug(f"Using provided user_input_fn: {user_input_fn}")

    if not isinstance(question_to_ask_user, str) or not question_to_ask_user.strip():
        error_msg = create_error_message(
            ErrorType.TOOL_ERROR,
            "No valid 'question_to_ask_user' provided to request_user_input.",
            "request_user_input"
        )
        logger.error(error_msg)
        return error_msg

    if not isinstance(suggested_responses, list) or not suggested_responses:
        error_msg = create_error_message(
            ErrorType.TOOL_ERROR,
            "The 'suggested_responses' parameter is required and must be a non-empty list. "
            f"When asking '{question_to_ask_user}', you must provide appropriate answer options for the user to choose from.",
            "request_user_input"
        )
        logger.error(error_msg)
        return error_msg

    suggestions_for_user = [
        s.strip() for s in suggested_responses if isinstance(s, str) and s.strip()
    ]
    
    logger.debug(f"Filtered suggestions: {suggestions_for_user}")
    
    # Ensure we have at least some valid options after filtering
    if not suggestions_for_user:
        error_msg = create_error_message(
            ErrorType.TOOL_ERROR,
            "All provided suggestions were empty or invalid. "
            f"When asking '{question_to_ask_user}', you must provide valid, non-empty answer options.",
            "request_user_input"
        )
        logger.error(error_msg)
        return error_msg
    
    # Use enhanced input handler for better UI
    input_handler = InputHandler()
    
    # Check if we're in an interactive terminal
    import sys
    import os
    is_interactive = sys.stdin.isatty() and os.isatty(0)
    logger.debug(f"Is interactive terminal: {is_interactive}, stdin: {sys.stdin}, stdout: {sys.stdout}")
    
    # For now, raise an exception in non-test environments to interrupt execution
    if user_input_fn is None and not is_interactive:
        logger.info("[TOOL] Raising UserInputRequiredException to interrupt agent execution")
        raise UserInputRequiredException(
            question=question_to_ask_user,
            suggested_responses=suggested_responses,
            tool_name="request_user_input"
        )
    
    # If a custom user_input_fn is provided, use the old behavior for compatibility
    if user_input_fn != input:
        # Legacy behavior for testing
        manual_answer_prompt = "Let me enter my own answer"
        suggestions_for_user.append(manual_answer_prompt)
        
        print(f"\n[Katalyst Question To User]\n{question_to_ask_user}")
        print("Suggested answers:")
        for idx, suggestion_text in enumerate(suggestions_for_user, 1):
            print(f"  {idx}. {suggestion_text}")
        
        user_choice_str = user_input_fn(
            "Your answer (enter number or type custom answer): "
        ).strip()
        actual_answer = ""
        
        if user_choice_str.isdigit():
            try:
                choice_idx = int(user_choice_str)
                if 1 <= choice_idx <= len(suggestions_for_user):
                    actual_answer = suggestions_for_user[choice_idx - 1]
                    if actual_answer == manual_answer_prompt:
                        actual_answer = user_input_fn(
                            f"\nYour custom answer to '{question_to_ask_user}': "
                        ).strip()
                else:
                    actual_answer = user_choice_str
            except ValueError:
                actual_answer = user_choice_str
        else:
            actual_answer = user_choice_str
    else:
        # Use arrow navigation for normal operation
        console = Console()
        
        console.print(f"\n[bold cyan]Katalyst Question:[/bold cyan]")
        console.print(f"{question_to_ask_user}\n")
        
        # Add custom answer option
        menu_options = [{"label": sug, "value": sug} for sug in suggestions_for_user]
        menu_options.append({"label": "Enter custom answer", "value": "__custom__"})
        
        logger.debug(f"Menu options to display: {menu_options}")
        
        # Show arrow menu
        selected = input_handler.prompt_arrow_menu(
            title="Select an answer",
            options=menu_options,
            quit_keys=["escape"]
        )
        
        if selected is None:
            # User cancelled
            actual_answer = "[USER_CANCELLED]"
        elif selected == "__custom__":
            # User wants to enter custom answer
            actual_answer = input_handler.prompt_text(
                f"Your answer to '{question_to_ask_user}': "
            ).strip()
        else:
            actual_answer = selected

    if not actual_answer:
        logger.error("User did not provide a valid answer.")
        return format_response(question_to_ask_user, "[USER_NO_ANSWER_PROVIDED]")

    logger.debug(f"User responded with: {actual_answer}")
    result = format_response(question_to_ask_user, actual_answer)
    logger.info(f"[TOOL] request_user_input returning result: {result}")
    return result
