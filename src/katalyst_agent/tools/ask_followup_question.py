from typing import Dict
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
from textwrap import dedent


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
def ask_followup_question(arguments: Dict) -> str:
    """
    Asks the user a follow-up question to gather more information, providing suggested answers.
    Expects arguments to contain:
      - 'question': str
      - 'follow_up': list of suggested answers (each as a string)
    Returns the user's answer as a string (either a suggestion or a custom answer), formatted with XML-style tags.
    """
    logger = get_logger()
    logger.info(f"Entered ask_followup_question with arguments: {arguments}")

    # Extract question and follow-up suggestions from arguments
    question = arguments.get('question')
    follow_up = arguments.get('follow_up')

    # Validate required arguments
    if not question:
        logger.error("No 'question' provided to ask_followup_question.")
        return format_response("[ERROR] No question provided.", "")
    
    if not follow_up or not isinstance(follow_up, list):
        logger.error("No valid 'follow_up' suggestions provided to ask_followup_question.")
        return format_response(question, "[ERROR] No follow-up suggestions provided.")

    # Add explicit custom answer option
    manual_answer_prompt = "Let me enter my own answer"
    suggestions = follow_up + [manual_answer_prompt]

    # Print the question and suggestions to the user
    print(f"\n[Follow-up Question]\n{question}")
    print("Suggested answers:")
    for idx, suggestion in enumerate(suggestions, 1):
        print(f"  {idx}. {suggestion}")
    print("Type the number of your choice, or enter a custom answer:")

    # Get user input (number or custom answer)
    user_input = input("Your answer: ").strip()

    # If user enters a number, use the corresponding suggestion
    if user_input.isdigit():
        idx = int(user_input)
        if 1 <= idx <= len(suggestions):
            answer = suggestions[idx - 1]
            if answer == manual_answer_prompt:
                # Prompt for custom answer
                answer = input(f"\n{question}: ").strip()
                if not answer:
                    logger.error("User did not provide a custom answer.")
                    return format_response(question, "[ERROR] No answer provided.")
            logger.info(f"User selected: {answer}")
            logger.info("Exiting ask_followup_question")
            return format_response(question, answer)
    # Otherwise, use the custom input
    answer = user_input
    if not answer:
        logger.error("User did not provide any answer.")
        return format_response(question, "[ERROR] No answer provided.")
    logger.info(f"User provided custom answer: {answer}")
    logger.info("Exiting ask_followup_question")
    return format_response(question, answer)
