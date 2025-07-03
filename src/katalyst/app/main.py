import os
import json
import warnings
import signal
import sys
import time
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
from katalyst.app.ui.input_handler import InputHandler
from katalyst.app.execution_controller import execution_controller
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.agents import AgentFinish
from langgraph.errors import GraphRecursionError
from rich.console import Console
from rich.table import Table

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


def print_run_summary(final_state: dict, input_handler: InputHandler = None):
    """
    Prints a nicely formatted summary of the agent run's outcome.
    """
    logger = get_logger()
    console = Console()
    if not input_handler:
        input_handler = InputHandler(console)
    
    final_user_response = final_state.get("response")
    if final_user_response:
        if "limit exceeded" in final_user_response.lower():
            input_handler.show_status(
                final_user_response,
                status="warning",
                title="KATALYST RUN STOPPED DUE TO LIMIT"
            )
        else:
            input_handler.show_status(
                final_user_response,
                status="success",
                title="KATALYST TASK CONCLUDED"
            )
    else:
        console.print("\n[bold]KATALYST RUN FINISHED[/bold] (No explicit overall response message)")
        completed_tasks = final_state.get("completed_tasks", [])
        if completed_tasks:
            console.print("\n[bold]Summary of completed sub-tasks:[/bold]")
            for i, (task_desc, summary) in enumerate(completed_tasks):
                console.print(f"  [cyan]{i+1}.[/cyan] '{task_desc}': {summary}")
        else:
            console.print("[dim]No sub-tasks were marked as completed with a summary.[/dim]")
        last_agent_outcome = final_state.get("agent_outcome")
        if isinstance(last_agent_outcome, AgentFinish):
            console.print(
                f"[dim]Last agent step was a finish with output: {last_agent_outcome.return_values.get('output')}[/dim]"
            )
        elif last_agent_outcome:
            console.print(f"[dim]Last agent step was an action: {last_agent_outcome.tool}[/dim]")
    
    console.print(f"\n[blue]Full logs are available in: {_LOG_FILE}[/blue]")
    console.print("\n[green]Katalyst Agent is now ready for a new task![/green]")


class ReplInterruptHandler:
    """Handles interrupt signals for the REPL with double-press detection."""
    
    def __init__(self, console):
        self.console = console
        self.last_interrupt_time = 0
        self.interrupt_count = 0
        self.double_press_window = 0.5
    
    def __call__(self, signum, frame):
        """Handle SIGINT with double-press detection."""
        current_time = time.time()
        time_since_last = current_time - self.last_interrupt_time
        
        # Check if this is a second press within the window
        if time_since_last <= self.double_press_window and self.interrupt_count >= 1:
            self.console.print("\n\n[bold red]Double interrupt detected. Exiting Katalyst...[/bold red]")
            self.console.print("[green]Goodbye![/green]")
            os._exit(0)  # Force exit immediately
        else:
            self.interrupt_count = 1
            self.last_interrupt_time = current_time
            self.console.print("\n[yellow]Press Ctrl+C again to exit Katalyst.[/yellow]")
            # Raise KeyboardInterrupt to cancel current input
            raise KeyboardInterrupt()


def repl(user_input_fn=input):
    """
    This is the main REPL loop for the Katalyst agent.
    It handles user input (supports custom user_input_fn), command parsing, and graph execution.
    """
    show_help()
    logger = get_logger()
    console = Console()
    input_handler = InputHandler(console)
    checkpointer = MemorySaver()
    graph = build_compiled_graph().with_config(checkpointer=checkpointer)
    conversation_id = "katalyst-main-thread"
    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": int(os.getenv("KATALYST_RECURSION_LIMIT", 250)),
    }
    
    # Setup interrupt handler for REPL
    interrupt_handler = ReplInterruptHandler(console)
    signal.signal(signal.SIGINT, interrupt_handler)
    
    # Define available commands for interactive selection
    slash_commands = [
        {"label": "/help", "value": "/help", "description": "Show help message"},
        {"label": "/init", "value": "/init", "description": "Generate developer guide (KATALYST.md)"},
        {"label": "/provider", "value": "/provider", "description": "Set LLM provider"},
        {"label": "/model", "value": "/model", "description": "Set LLM model"},
        {"label": "/exit", "value": "/exit", "description": "Exit the agent"},
    ]
    
    while True:
        try:
            # Use styled prompt for better visibility
            if user_input_fn == input:
                user_input = input_handler.prompt_text("[bold green]>[/bold green] ", default="", show_default=False).strip()
            else:
                # For testing, use the provided function
                user_input = user_input_fn("> ").strip()
        except KeyboardInterrupt:
            # Interrupt during input - already handled by signal handler
            continue
        except EOFError:
            # Handle Ctrl+D
            console.print("\n[yellow]Use /exit to quit or Ctrl+C twice to force exit.[/yellow]")
            continue
        
        # Skip empty input
        if not user_input:
            continue

        # Handle slash command selection
        if user_input == "/":
            # Display commands in a nice table format
            console.print("\n[bold cyan]Available Commands:[/bold cyan]")
            
            # Create a table for better formatting
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Command", style="bold green", no_wrap=True)
            table.add_column("Description", style="dim")
            
            for cmd in slash_commands:
                table.add_row(cmd["label"], cmd["description"])
            
            console.print(table)
            console.print("\n[dim]Type a command or press Enter to cancel[/dim]")
            
            # Get user input for the command
            command_input = input_handler.prompt_text(
                "[bold green]>[/bold green] /", 
                default="", 
                show_default=False
            ).strip()
            
            if command_input:
                # Add the slash back if user didn't type it
                if not command_input.startswith("/"):
                    user_input = "/" + command_input
                else:
                    user_input = command_input
            else:
                # User cancelled
                continue

        if user_input == "/help":
            show_help()
            continue
        elif user_input == "/init":
            handle_init_command(graph, config)
            continue
        elif user_input == "/provider":
            handle_provider_command()
            continue
        elif user_input == "/model":
            handle_model_command()
            continue
        elif user_input == "/exit":
            print("Goodbye!")
            break
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
            # Wrap graph execution with cancellation support
            final_state = execution_controller.wrap_execution(
                graph.invoke, current_input, config
            )
        except KeyboardInterrupt:
            # Handle ESC or Ctrl+C
            msg = "Execution cancelled by user. Ready for new command."
            logger.info(f"[USER_CANCEL] {msg}")
            input_handler.show_status(msg, status="warning", title="Cancelled")
            execution_controller.reset()
            continue
        except GraphRecursionError:
            msg = (
                f"Recursion limit ({config['recursion_limit']}) reached. "
                "The agent is likely in a loop. Please simplify the task or "
                "increase the KATALYST_RECURSION_LIMIT environment variable if needed."
            )
            logger.error(f"[GUARDRAIL] {msg}")
            input_handler.show_status(msg, status="error", title="Recursion Limit Exceeded")
            continue
        except Exception as e:
            logger.exception("An error occurred during graph execution.")
            input_handler.show_status(
                f"An unexpected error occurred: {e}",
                status="error",
                title="Execution Error"
            )
            continue
        logger.info(
            "\n==================== 🎉🎉🎉  KATALYST RUN COMPLETE  🎉🎉🎉 ===================="
            )
        if final_state:
            print_run_summary(final_state, input_handler)
        else:
            input_handler.show_status(
                "The agent run did not complete successfully.",
                status="error"
            )


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
