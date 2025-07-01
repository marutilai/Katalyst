import os
import json
import warnings
from dotenv import load_dotenv

# Suppress tree-sitter deprecation warning
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

from katalyst.katalyst_core.graph import build_compiled_graph
from katalyst.katalyst_core.utils.logger import get_logger, _LOG_FILE
from katalyst.app.onboarding import welcome_screens
from katalyst.app.config import ONBOARDING_FLAG
from katalyst.katalyst_core.utils.environment import ensure_openai_api_key
from katalyst.app.cli.commands import (
    show_help,
    handle_init_command,
    handle_provider_command,
    handle_model_command,
)
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.agents import AgentFinish
from langgraph.errors import GraphRecursionError

# Import async cleanup to register cleanup handlers
import katalyst.katalyst_core.utils.async_cleanup

# Load environment variables from .env file
load_dotenv()


def maybe_show_welcome():
    if not ONBOARDING_FLAG.exists():
        welcome_screens.screen_1_welcome_and_security()
        welcome_screens.screen_2_trust_folder(os.getcwd())
        welcome_screens.screen_3_final_tips(os.getcwd())
        ONBOARDING_FLAG.write_text("onboarded\n")
    else:
        welcome_screens.screen_3_final_tips(os.getcwd())


def print_run_summary(final_state: dict):
    """
    Prints a nicely formatted summary of the agent run's outcome.
    """
    logger = get_logger()
    final_user_response = final_state.get("response")
    if final_user_response:
        if "limit exceeded" in final_user_response.lower():
            print(f"\n--- KATALYST RUN STOPPED DUE TO LIMIT ---")
            print(final_user_response)
        else:
            print(f"\n--- KATALYST TASK CONCLUDED ---")
            print(final_user_response)
    else:
        print("\n--- KATALYST RUN FINISHED (No explicit overall response message) ---")
        completed_tasks = final_state.get("completed_tasks", [])
        if completed_tasks:
            print("Summary of completed sub-tasks:")
            for i, (task_desc, summary) in enumerate(completed_tasks):
                print(f"  {i+1}. '{task_desc}': {summary}")
        else:
            print("No sub-tasks were marked as completed with a summary.")
        last_agent_outcome = final_state.get("agent_outcome")
        if isinstance(last_agent_outcome, AgentFinish):
            print(
                f"Last agent step was a finish with output: {last_agent_outcome.return_values.get('output')}"
            )
        elif last_agent_outcome:
            print(f"Last agent step was an action: {last_agent_outcome.tool}")
    print(f"[INFO] Full logs are available in: {_LOG_FILE}")
    print("\nKatalyst Agent is now ready for a new task!")


def repl(user_input_fn=input):
    """
    This is the main REPL loop for the Katalyst agent.
    It handles user input (supports custom user_input_fn), command parsing, and graph execution.
    """
    show_help()
    logger = get_logger()
    checkpointer = MemorySaver()
    graph = build_compiled_graph().with_config(checkpointer=checkpointer)
    conversation_id = "katalyst-main-thread"
    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": int(os.getenv("KATALYST_RECURSION_LIMIT", 250)),
    }
    while True:
        user_input = user_input_fn("> ").strip()

        if user_input == "/help":
            show_help()
        elif user_input == "/init":
            handle_init_command(graph, config)
        elif user_input == "/provider":
            handle_provider_command()
        elif user_input == "/model":
            handle_model_command()
        elif user_input == "/exit":
            print("Goodbye!")
            break
            continue
        logger.info(
            "\n==================== 🚀🚀🚀  KATALYST RUN START  🚀🚀🚀 ===================="
            )
        logger.info(f"[MAIN_REPL] Starting new task: '{user_input}'")
        # Only pass new input for this turn; let checkpointer handle memory
        current_input = {
            "task": user_input,
            "auto_approve": os.getenv("KATALYST_AUTO_APPROVE", "false").lower()
            == "true",
            "project_root_cwd": os.getcwd(),
            "user_input_fn": user_input_fn,
        }
        final_state = None
        try:
            final_state = graph.invoke(current_input, config)
        except GraphRecursionError:
            msg = (
                f"[GUARDRAIL] Recursion limit ({config['recursion_limit']}) reached. "
                "The agent is likely in a loop. Please simplify the task or "
                "increase the KATALYST_RECURSION_LIMIT environment variable if needed."
            )
            logger.error(msg)
            print(f"\n[ERROR] {msg}")
            continue
        except Exception as e:
            logger.exception("An error occurred during graph execution.")
            print(f"\n[ERROR] An unexpected error occurred: {e}")
            continue
        logger.info(
            "\n==================== 🎉🎉🎉  KATALYST RUN COMPLETE  🎉🎉🎉 ===================="
            )
        if final_state:
            print_run_summary(final_state)
        else:
            print("[ERROR] The agent run did not complete successfully.")


def main():
    ensure_openai_api_key()
    maybe_show_welcome()
    try:
        repl()
    except Exception as e:
        get_logger().exception("Unhandled exception in main loop.")
        print(f"An unexpected error occurred: {e}. See the log file for details.")


if __name__ == "__main__":
    main()
