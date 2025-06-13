from typing import Dict, List
from src.katalyst_core.utils.logger import get_logger
from src.katalyst_core.utils.tools import katalyst_tool
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
    prompt_module="request_user_input", prompt_var="REQUEST_USER_INPUT_PROMPT"
)
def request_user_input(
    question_to_ask_user: str, suggested_responses: List[str] = None
) -> str:
    """
    Asks the user a question to gather more information, providing suggested answers.
    Parameters:
      - question_to_ask_user: str (the question to ask the user)
      - suggested_responses: list of suggestion strings
    Returns the user's answer as a JSON string (with 'question_to_ask_user' and 'user_final_answer' keys).
    """
    logger = get_logger()
    logger.debug(
        f"Entered request_user_input with question='{question_to_ask_user}', suggested_responses='{suggested_responses}'"
    )

    if not isinstance(question_to_ask_user, str) or not question_to_ask_user.strip():
        logger.error("No valid 'question_to_ask_user' provided to request_user_input.")
        return format_response(
            question_to_ask_user
            if isinstance(question_to_ask_user, str)
            else "[No Question]",
            "[ERROR] No valid question provided to tool.",
        )

    if not isinstance(suggested_responses, list) or not suggested_responses:
        logger.error(
            "No 'suggested_responses' list provided by LLM for request_user_input."
        )
        return format_response(
            question_to_ask_user, "[ERROR] No suggested_responses list provided by LLM."
        )

    suggestions_for_user = [
        s.strip() for s in suggested_responses if isinstance(s, str) and s.strip()
    ]
    manual_answer_prompt = "Let me enter my own answer"
    suggestions_for_user.append(manual_answer_prompt)

    print(f"\n[Katalyst Question To User]\n{question_to_ask_user}")
    print("Suggested answers:")
    for idx, suggestion_text in enumerate(suggestions_for_user, 1):
        print(f"  {idx}. {suggestion_text}")

    user_choice_str = input(
        "Your answer (enter number or type custom answer): "
    ).strip()
    actual_answer = ""

    if user_choice_str.isdigit():
        try:
            choice_idx = int(user_choice_str)
            if 1 <= choice_idx <= len(suggestions_for_user):
                actual_answer = suggestions_for_user[choice_idx - 1]
                if actual_answer == manual_answer_prompt:
                    actual_answer = input(
                        f"\nYour custom answer to '{question_to_ask_user}': "
                    ).strip()
            else:
                logger.warning(
                    f"Invalid number choice: {user_choice_str}. Treating as custom answer."
                )
                actual_answer = user_choice_str
        except ValueError:
            logger.warning(
                f"Could not parse '{user_choice_str}' as int despite isdigit(). Treating as custom answer."
            )
            actual_answer = user_choice_str
    else:
        actual_answer = user_choice_str

    if not actual_answer:
        logger.error("User did not provide a valid answer.")
        return format_response(question_to_ask_user, "[USER_NO_ANSWER_PROVIDED]")

    logger.info(f"User responded with: {actual_answer}")
    return format_response(question_to_ask_user, actual_answer)
