import os
from dotenv import load_dotenv
from pathlib import Path
from katalyst_agent.state import KatalystAgentState
from katalyst_agent.graph import build_compiled_graph
from katalyst_agent.utils.logger import get_logger
from src.katalyst_agent.utils import welcome_screens

# Load environment variables from .env file
load_dotenv()

ONBOARDING_FLAG = Path.home() / ".katalyst_agent_onboarded"

def maybe_show_welcome():
    if not ONBOARDING_FLAG.exists():
        welcome_screens.screen_1_welcome_and_security()
        welcome_screens.screen_2_trust_folder(os.getcwd())
        welcome_screens.screen_3_final_tips(os.getcwd())
        ONBOARDING_FLAG.write_text("onboarded\n")
    else:
        print("Welcome back to Katalyst Agent! (onboarding skipped)")

def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Create a KATALYST.md file with instructions
/exit      Exit the agent
(Type your coding task or command below)
""")

def handle_init():
    with open("KATALYST.md", "w") as f:
        f.write("# Instructions for Katalyst\n")
    print("KATALYST.md created.")

def repl():
    show_help()
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
        else:
            # --- AGENT LOGIC STARTS HERE ---
            llm_provider = os.getenv("KATALYST_PROVIDER", "openai")
            llm_model_name = os.getenv("KATALYST_MODEL", "gpt-4.1-nano")
            auto_approve = os.getenv("KATALYST_AUTO_APPROVE", "false").lower() == "true"
            max_iterations = int(os.getenv("KATALYST_MAX_ITERATIONS", 10))

            initial_state = {
                "task": user_input,
                "current_mode": "code",  # or let user choose mode
                "llm_provider": llm_provider,
                "llm_model_name": llm_model_name,
                "auto_approve": auto_approve,
                "max_iterations": max_iterations,
            }

            graph = build_compiled_graph()
            result = graph.invoke(initial_state)

            # Print the result (reuse your old main.py logic here)
            logger = get_logger()
            logger.info("\n\n==================== 🎉🎉🎉  FINAL ITERATION COMPLETE  🎉🎉🎉 ====================\n")
            final_parsed_call = result.get('parsed_tool_call')
            final_iteration = result.get('current_iteration', 0)
            max_iter = result.get('max_iterations', 10)

            # Case 1: Task completed via attempt_completion tool
            if final_parsed_call and final_parsed_call.get('tool_name') == 'attempt_completion':
                completion_message = final_parsed_call.get('args', {}).get('result', 'Task successfully completed (no specific result message provided).')
                print(f"\n--- KATALYST TASK COMPLETED ---")
                print(completion_message)
            # Case 2: Max iterations reached
            elif final_iteration >= max_iter:
                print(f"\n--- KATALYST MAX ITERATIONS ({max_iter}) REACHED ---")
                last_llm_response = result.get('llm_response_content')
                if last_llm_response:
                    print(f"Last LLM thought: {last_llm_response}")
            # Case 3: Fallback (graph ended for another reason)
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

def main():
    maybe_show_welcome()
    repl()

if __name__ == "__main__":
    main()
