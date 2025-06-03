from typing import Dict, List
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
import json


def format_response(question: str, answer: str) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    return json.dumps({
        "question": question,
        "answer": answer
    })


@katalyst_tool(prompt_module="ask_followup_question", prompt_var="ASK_FOLLOWUP_QUESTION_PROMPT")
def ask_followup_question(question: str, follow_up: List[str] = None, mode: str = None, auto_approve: bool = True) -> str:
    """
    Asks the user a follow-up question to gather more information, providing suggested answers.
    Parameters:
      - question: str (the question to ask the user)
      - follow_up: list of suggestion strings
    Returns the user's answer as a JSON string (with 'question' and 'answer' keys).
    """
    logger = get_logger()
    logger.info(f"Entered ask_followup_question with question='{question}', follow_up_list='{follow_up}'")

    if not isinstance(question, str) or not question.strip():
        logger.error("No valid 'question' provided to ask_followup_question.")
        return format_response(question if isinstance(question, str) else "[No Question]", "[ERROR] No valid question provided to tool.")
    
    if not isinstance(follow_up, list) or not follow_up:
        logger.error("No 'follow_up' suggestions list provided by LLM for ask_followup_question.")
        return format_response(question, "[ERROR] No follow_up suggestions list provided by LLM.")

    suggestions_for_user = [s.strip() for s in follow_up if isinstance(s, str) and s.strip()]
    manual_answer_prompt = "Let me enter my own answer"
    suggestions_for_user.append(manual_answer_prompt)

    print(f"\n[Katalyst Question To User]\n{question}")
    print("Suggested answers:")
    for idx, suggestion_text in enumerate(suggestions_for_user, 1):
        print(f"  {idx}. {suggestion_text}")
    
    user_choice_str = input("Your answer (enter number or type custom answer): ").strip()
    actual_answer = ""

    if user_choice_str.isdigit():
        try:
            choice_idx = int(user_choice_str)
            if 1 <= choice_idx <= len(suggestions_for_user):
                actual_answer = suggestions_for_user[choice_idx - 1]
                if actual_answer == manual_answer_prompt:
                    actual_answer = input(f"\nYour custom answer to '{question}': ").strip()
            else:
                logger.warning(f"Invalid number choice: {user_choice_str}. Treating as custom answer.")
                actual_answer = user_choice_str 
        except ValueError:
            logger.warning(f"Could not parse '{user_choice_str}' as int despite isdigit(). Treating as custom answer.")
            actual_answer = user_choice_str
    else:
        actual_answer = user_choice_str

    if not actual_answer:
        logger.error("User did not provide a valid answer.")
        return format_response(question, "[USER_NO_ANSWER_PROVIDED]")

    logger.info(f"User responded with: {actual_answer}")
    return format_response(question, actual_answer)
