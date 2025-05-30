import os
import json
from dotenv import load_dotenv
from katalyst_agent.graph import build_compiled_graph
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils import welcome_screens
from katalyst_agent.config import ONBOARDING_FLAG, STATE_FILE

# Load environment variables from .env file
load_dotenv()

def ensure_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "\n[ERROR] OpenAI API key not found!\n"
            "Please set the OPENAI_API_KEY environment variable or add it to your .env file in this directory.\n"
            "You can get an API key from https://platform.openai.com/account/api-keys\n"
        )
        key = input("Enter your OpenAI API key (or leave blank to exit): ").strip()
        if key:
            with open(".env", "a") as f:
                f.write(f"\nOPENAI_API_KEY={key}\n")
            print("API key saved to .env. Please restart Katalyst.")
        exit(1)

def maybe_show_welcome():
    project_state = load_project_state()
    current_mode = project_state.get("current_mode", "code")
    if not ONBOARDING_FLAG.exists():
        welcome_screens.screen_1_welcome_and_security()
        welcome_screens.screen_2_trust_folder(os.getcwd())
        welcome_screens.screen_3_final_tips(os.getcwd(), current_mode)
        ONBOARDING_FLAG.write_text("onboarded\n")
    else:
        welcome_screens.screen_3_final_tips(os.getcwd(), current_mode)

def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Create a KATALYST.md file with instructions
/exit      Exit the agent
/mode      Change the current mode
(Type your coding task or command below)
""")

def handle_init():
    with open("KATALYST.md", "w") as f:
        f.write("# Instructions for Katalyst\n")
    print("KATALYST.md created.")

def load_project_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_project_state(state):
    logger = get_logger()
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"Failed to save project state to {STATE_FILE}: {e}")

def repl():
    show_help()
    graph = build_compiled_graph()  # Build the graph once
    project_state = load_project_state()
    while True:
        user_input = input("> ").strip()
        if user_input == "/help":
            show_help()
        elif user_input == "/init":
            handle_init()
        elif user_input == "/exit":
            print("Goodbye!")
            break
        elif user_input == "":
            continue
        elif user_input.startswith("/mode"):
            # Robust /mode command: show current, set, or handle invalid input
            parts = user_input.split(" ", 1)
            active_mode_for_display = project_state.get("current_mode", "code")
            if len(parts) == 1 and parts[0] == "/mode":
                print(f"Current mode: {active_mode_for_display}. To change, type: /mode [architect|code]")
                continue
            elif len(parts) == 2:
                _, new_mode_str = parts
                new_mode = new_mode_str.strip().lower()
                if new_mode in ["architect", "code"]:
                    project_state["current_mode"] = new_mode
                    save_project_state(project_state)
                    print(f"Mode switched to: {project_state['current_mode']}")
                else:
                    print(f"Invalid mode: '{new_mode}'. Available modes: 'architect', 'code'.")
                continue
            else:
                print("Usage: /mode [architect|code] or /mode to see current.")
                continue
        else:
            llm_provider = os.getenv("KATALYST_PROVIDER", "openai")
            llm_model_name = os.getenv("KATALYST_MODEL", "gpt-4.1-nano")
            auto_approve = os.getenv("KATALYST_AUTO_APPROVE", "false").lower() == "true"
            max_iterations = int(os.getenv("KATALYST_MAX_ITERATIONS", 10))

            # Only persist chat_history and current_mode (and add more if needed)
            loaded_history = project_state.get("chat_history", [])
            current_mode = project_state.get("current_mode", "code")

            # Build a clean initial state for each new task, only including persistent fields
            initial_state = {
                "task": user_input,
                "current_mode": current_mode,  # Persisted and user-changeable
                "llm_provider": llm_provider,
                "llm_model_name": llm_model_name,
                "auto_approve": auto_approve,
                "max_iterations": max_iterations,
                "chat_history": loaded_history,  # Persisted chat history
                # Do NOT include transient fields like error_message, tool_output, etc.
            }

            result = graph.invoke(initial_state)

            logger = get_logger()
            logger.info("\n\n==================== 🎉🎉🎉  FINAL ITERATION COMPLETE  🎉🎉🎉 ====================\n")
            final_parsed_call = result.get('parsed_tool_call')
            final_iteration = result.get('current_iteration', 0)
            max_iter = result.get('max_iterations', 10)

            # Print result summary
            if final_parsed_call and final_parsed_call.get('tool_name') == 'attempt_completion':
                completion_message = final_parsed_call.get('args', {}).get('result', 'Task successfully completed (no specific result message provided).')
                print(f"\n--- KATALYST TASK COMPLETED ---")
                print(completion_message)
            elif final_iteration >= max_iter:
                print(f"\n--- KATALYST MAX ITERATIONS ({max_iter}) REACHED ---")
                last_llm_response = result.get('llm_response_content')
                if last_llm_response:
                    print(f"Last LLM thought: {last_llm_response}")
            else:
                print("\n--- KATALYST RUN FINISHED (Reason not explicitly 'completion' or 'max_iterations') ---")
                last_llm_response = result.get('llm_response_content')
                if last_llm_response:
                    print(f"Last LLM response: {last_llm_response}")

            # Print the full chat history for transparency/debugging
            print("\n--- FULL CHAT HISTORY ---")
            chat_history = result.get('chat_history', [])
            for msg_idx, msg in enumerate(chat_history):
                print(f"Message {msg_idx}: [{msg.__class__.__name__}] {getattr(msg, 'content', str(msg))}")

            print("Katalyst Agent is now ready to use!")

            # Update and save project state after each command
            # Only persist fields that should be remembered across tasks/sessions
            project_state.update({
                "chat_history": result.get("chat_history", []),  # Persist chat history
                # current_mode is already up to date in project_state
                # TODO: Add more fields to persist as needed
            })
            save_project_state(project_state)

def main():
    ensure_openai_api_key()
    maybe_show_welcome()
    repl()

if __name__ == "__main__":
    main()
