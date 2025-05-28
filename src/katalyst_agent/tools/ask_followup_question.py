from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
from textwrap import dedent
import re


def format_response(question: str, answer: str) -> str:
    """
    Standardizes the output as an XML-style string for downstream processing.
    """
    return dedent(f"""
    [ask_followup_question for '{question}'] Result:
    <answer>
    {answer}
    </answer>
    """)


@katalyst_tool
# For consistency with other tools, include mode and auto_approve, but they are not used here.
def ask_followup_question(question: str, follow_up: str, mode: str = None, auto_approve: bool = False) -> str:
    """
    Asks the user a follow-up question to gather more information, providing suggested answers.
    Parameters:
      - question: str (the question to ask the user)
      - follow_up: string of <suggest> tags
    Returns the user's answer as a string (either a suggestion or a custom answer), formatted with XML-style tags.
    """
    logger = get_logger()
    logger.info(f"Entered ask_followup_question with question='{question}', follow_up_xml_str='{follow_up}'")

    if not isinstance(question, str) or not question.strip():
        logger.error("No valid 'question' provided to ask_followup_question.")
        return format_response(question if isinstance(question, str) else "[No Question]", "[ERROR] No valid question provided to tool.")
    
    # The LLM is supposed to provide the <follow_up> block containing <suggest> tags.
    # The content of <follow_up> is passed as a string here.
    if not isinstance(follow_up, str) or not follow_up.strip():
        logger.error("No 'follow_up' XML string provided by LLM for ask_followup_question.")
        return format_response(question, "[ERROR] No follow_up suggestions XML string provided by LLM.")

    # Parse the <suggest> tags from the follow_up string
    # re.findall will return a list of strings, e.g., ["OptA", "OptB"]
    suggestions_from_xml = re.findall(r"<suggest>(.*?)</suggest>", follow_up, re.DOTALL)
    
    if not suggestions_from_xml:
         logger.warning("No <suggest> tags found within the <follow_up> XML content provided by LLM.")
         # If LLM must provide suggestions, this is an error for the LLM to correct.
         return format_response(question, "[ERROR] No <suggest> tags were found inside the <follow_up> block provided by LLM.")

    manual_answer_prompt = "Let me enter my own answer"
    # The suggestions for the user are those parsed from XML + the manual option
    suggestions_for_user = [s.strip() for s in suggestions_from_xml] + [manual_answer_prompt]

    # --- THIS PART WILL NOW BE REACHED ---
    print(f"\n[Katalyst Question To User]\n{question}") # Clearer print label
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
            else: # Invalid number
                logger.warning(f"Invalid number choice: {user_choice_str}. Treating as custom answer.")
                actual_answer = user_choice_str 
        except ValueError:
            logger.warning(f"Could not parse '{user_choice_str}' as int despite isdigit(). Treating as custom answer.")
            actual_answer = user_choice_str
    else: # Not a digit, so it's a custom answer
        actual_answer = user_choice_str

    if not actual_answer: # If custom answer was empty or invalid selection led to empty
        logger.error("User did not provide a valid answer.")
        # It's important to return a formatted response so the LLM knows the outcome
        return format_response(question, "[USER_NO_ANSWER_PROVIDED]")

    logger.info(f"User responded with: {actual_answer}")
    return format_response(question, actual_answer)
