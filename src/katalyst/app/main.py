import os
import json
import warnings
import signal
import sys
import time
import sqlite3
from dotenv import load_dotenv
from opentelemetry import trace as trace_api
# Suppress tree-sitter deprecation warning
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

from katalyst.app import config
from katalyst.supervisor.main_graph import build_main_graph
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.checkpointer_manager import checkpointer_manager
from katalyst.katalyst_core.state import KatalystState
from katalyst.app.onboarding import welcome_screens
from katalyst.app.config import ONBOARDING_FLAG
from katalyst.katalyst_core.utils.environment import ensure_openai_api_key
from katalyst.app.cli.commands import (
    show_help,
    handle_init_command,
    handle_provider_command,
    handle_model_command,
)
import subprocess

from katalyst.app.ui.input_handler import InputHandler
from katalyst.app.execution_controller import execution_controller
from katalyst.app.config import CHECKPOINT_DB
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.agents import AgentFinish
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from rich.console import Console
from rich.table import Table
from katalyst.katalyst_core.utils.task_manager import TaskManager

# Import async cleanup to register cleanup handlers
import katalyst.katalyst_core.utils.async_cleanup
from katalyst.app.instrumentation import init_instrumentation


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

    # Check for conversation agent response first
    response = final_state.get("response")
    if response:
        # Display the conversation response as the main output
        console.print("\n[bold green]Response:[/bold green]")
        console.print(response)
        console.print()  # Add blank line after response
        return  # Don't show task summary for conversation responses
    
    completed_tasks = final_state.get("completed_tasks", [])
    
    # Check if we hit any limits
    error_msg = final_state.get("error_message", "")
    if error_msg and "limit exceeded" in error_msg.lower():
        input_handler.show_status(
            error_msg,
            status="warning",
            title="KATALYST RUN STOPPED DUE TO LIMIT",
        )
    elif completed_tasks:
        # Normal completion with tasks
        console.print("\n[bold green]KATALYST RUN COMPLETE[/bold green]")
        console.print("\n[bold]Summary of completed tasks:[/bold]")
        for i, (task_desc, summary) in enumerate(completed_tasks):
            console.print(f"  [cyan]{i+1}.[/cyan] '{task_desc}': {summary}")
    else:
        # Only show "no sub-tasks" message if tasks were actually created
        task_queue = final_state.get("task_queue", [])
        original_plan = final_state.get("original_plan", [])
        
        # If tasks were created (either in queue or original plan), show the message
        if task_queue or original_plan:
            console.print(
                "[dim]No sub-tasks were marked as completed with a summary.[/dim]"
            )
    last_agent_outcome = final_state.get("agent_outcome")
    if isinstance(last_agent_outcome, AgentFinish):
        console.print(
            f"[dim]Last agent step was a finish with output: {last_agent_outcome.return_values.get('output')}[/dim]"
        )
    elif last_agent_outcome:
        console.print(
            f"[dim]Last agent step was an action: {last_agent_outcome.tool}[/dim]"
        )

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
            self.console.print(
                "\n\n[bold red]Double interrupt detected. Exiting Katalyst...[/bold red]"
            )
            self.console.print("[green]Goodbye![/green]")
            os._exit(0)  # Force exit immediately
        else:
            self.interrupt_count = 1
            self.last_interrupt_time = current_time
            self.console.print(
                "\n[yellow]Press Ctrl+C again to exit Katalyst.[/yellow]"
            )
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
    tracer = trace_api.get_tracer(__name__)

    # Use persistent SQLite checkpointer
    checkpointer = SqliteSaver.from_conn_string(str(CHECKPOINT_DB))

    # Store checkpointer in the manager for global access
    checkpointer_manager.set_checkpointer(checkpointer)

    # Check if we have an existing session
    has_previous_session = CHECKPOINT_DB.exists()
    with tracer.start_as_current_span("session_start") as span:
        # Set up more unique and informative span attributes
        
        project_name = getattr(config, "PROJECT_NAME", "katalyst")
        current_folder = os.path.basename(os.getcwd())
        # conversation_id is set just below, so use a placeholder for now
        temp_conversation_id = "pending"
        span.set_attribute("session_id", f"{project_name}-{temp_conversation_id}")
        span.set_attribute("project_name", project_name)
        span.set_attribute("current_folder", current_folder)
        span.set_attribute("cwd", os.getcwd())
        graph = build_main_graph().with_config(checkpointer=checkpointer)
        conversation_id = "katalyst-main-thread"
        graph_config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": config.RECURSION_LIMIT,
        }

        # Setup interrupt handler for REPL
        interrupt_handler = ReplInterruptHandler(console)
        signal.signal(signal.SIGINT, interrupt_handler)

        # Show session status
        if has_previous_session:
            console.print(
                "\n[cyan]Resuming previous session... (use /new to start fresh)[/cyan]\n"
            )
        else:
            console.print("\n[green]Starting new session...[/green]\n")

        # Initialize state for mode tracking - retrieve from checkpoint if exists
        # Get the last state from checkpointer to preserve execution_mode
        last_mode = "action"  # default
        try:
            # Try to get the last checkpoint state
            checkpoint_state = checkpointer.get(graph_config)
            if checkpoint_state and checkpoint_state.values:
                # Extract execution_mode from the saved state
                last_mode = checkpoint_state.values.get("execution_mode", "action")
        except Exception as e:
            logger.debug(f"Could not retrieve previous mode from checkpoint: {e}")
        
        state = KatalystState(task="", project_root_cwd=os.getcwd(), execution_mode=last_mode)
        
        # Get TaskManager singleton and load tasks from previous session
        task_manager = TaskManager.get_instance()
        if task_manager.load() and (task_manager.pending or task_manager.in_progress):
            console.print("[yellow]📋 Resuming task list from previous session:[/yellow]")
            console.print(task_manager.get_summary())
            console.print("")  # Empty line for spacing

        # Define available commands for interactive selection
        slash_commands = [
            {"label": "/help", "value": "/help", "description": "Show help message"},
            {
                "label": "/init",
                "value": "/init",
                "description": "Generate developer guide (KATALYST.md)",
            },
            {"label": "/provider", "value": "/provider", "description": "Set LLM provider"},
            {"label": "/model", "value": "/model", "description": "Set LLM model"},
            {"label": "/config", "value": "/config", "description": "Run interactive configuration for environment variables"},
            {
                "label": "/new",
                "value": "/new",
                "description": "Start a new conversation (clear history)",
            },
            {"label": "/mode", "value": "/mode", "description": "Show or set execution mode (plan/action)"},
            {"label": "/toggle", "value": "/toggle", "description": "Toggle between plan and action modes"},
            {"label": "/exit", "value": "/exit", "description": "Exit the agent"},
        ]

        while True:
            try:
                # Get current mode for prompt
                current_mode = state.execution_mode
                mode_prefix = "[PLAN]" if current_mode == "plan" else "[ACTION]"
                mode_color = "cyan" if current_mode == "plan" else "green"
                
                # Use styled prompt for better visibility with mode indicator
                if user_input_fn == input:
                    user_input = input_handler.prompt_text(
                        f"[bold {mode_color}]{mode_prefix} >[/bold {mode_color}] ", default="", show_default=False
                    ).strip()
                else:
                    # For testing, use the provided function
                    user_input = user_input_fn(f"{mode_prefix} > ").strip()
            except KeyboardInterrupt:
                # Interrupt during input - already handled by signal handler
                continue
            except EOFError:
                # Handle Ctrl+D
                console.print(
                    "\n[yellow]Use /exit to quit or Ctrl+C twice to force exit.[/yellow]"
                )
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
                    "[bold green]>[/bold green] /", default="", show_default=False
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
            elif user_input == "/config":
                # Run the Typer-based interactive configuration
                try:
                    subprocess.run([sys.executable, "-m", "katalyst.app.cli.configure", "run"], check=True)
                except Exception as e:
                    console.print(f"[red]Failed to run interactive configuration: {e}[/red]")
                continue
            elif user_input == "/new":
                # Clear the checkpoint data for current thread
                try:
                    checkpointer.delete_checkpoint(config)
                    console.print(
                        "[green]Conversation history cleared. Starting fresh![/green]"
                    )

                    # Also clear todos when starting fresh
                    if task_manager.clear():
                        console.print("[green]Todo list cleared.[/green]")
                    else:
                        console.print("[yellow]Note: Could not clear todo list.[/yellow]")

                except sqlite3.Error as e:
                    logger.error(f"Database error while clearing checkpoint: {e}")
                    console.print(
                        "[red]Error: Could not clear conversation history due to a database issue.[/red]"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to clear checkpoint with an unexpected error: {e}"
                    )
                    console.print(
                        "[yellow]Note: Could not clear previous session data.[/yellow]"
                    )
                continue
            elif user_input.startswith("/mode"):
                # Handle mode command
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    # Just /mode - show current mode
                    current_mode = state.execution_mode
                    mode_icon = "📋" if current_mode == "plan" else "⚡"
                    console.print(f"\n{mode_icon} Current mode: [bold cyan]{current_mode.upper()}[/bold cyan]")
                    if current_mode == "plan":
                        console.print("[dim]Plan mode: All requests go to conversation agent for analysis only[/dim]")
                    else:
                        console.print("[dim]Action mode: Full execution with all agents available[/dim]")
                else:
                    # /mode <plan|action>
                    new_mode = parts[1].lower()
                    if new_mode in ["plan", "action"]:
                        # Update mode in state
                        state.execution_mode = new_mode
                        # Save the mode change to checkpoint by updating the state
                        try:
                            # Create a minimal update to persist the mode
                            mode_update = {
                                "execution_mode": new_mode,
                                "task": "",
                                "project_root_cwd": os.getcwd(),
                            }
                            graph.update_state(graph_config, mode_update)
                        except Exception as e:
                            logger.debug(f"Could not persist mode change: {e}")
                        
                        mode_icon = "📋" if new_mode == "plan" else "⚡"
                        console.print(f"\n{mode_icon} Switched to [bold cyan]{new_mode.upper()}[/bold cyan] mode")
                        if new_mode == "plan":
                            console.print("[dim]You are now in plan mode - all requests will be analyzed only[/dim]")
                        else:
                            console.print("[dim]You are now in action mode - full execution capabilities enabled[/dim]")
                    else:
                        console.print("[red]Invalid mode. Use 'plan' or 'action'[/red]")
                continue
            elif user_input == "/toggle":
                # Toggle between plan and action modes
                current_mode = state.execution_mode
                new_mode = "plan" if current_mode == "action" else "action"
                state.execution_mode = new_mode
                # Save the mode change to checkpoint
                try:
                    mode_update = {
                        "execution_mode": new_mode,
                        "task": "",
                        "project_root_cwd": os.getcwd(),
                    }
                    graph.update_state(graph_config, mode_update)
                except Exception as e:
                    logger.debug(f"Could not persist mode change: {e}")
                
                mode_icon = "📋" if new_mode == "plan" else "⚡"
                console.print(f"\n{mode_icon} Toggled to [bold cyan]{new_mode.upper()}[/bold cyan] mode")
                if new_mode == "plan":
                    console.print("[dim]You are now in plan mode - all requests will be analyzed only[/dim]")
                else:
                    console.print("[dim]You are now in action mode - full execution capabilities enabled[/dim]")
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
                "auto_approve": config.AUTO_APPROVE,
                "project_root_cwd": os.getcwd(),
                "user_input_fn": user_input_fn,
                "execution_mode": state.execution_mode,
                "messages": [
                    HumanMessage(content=user_input)
                ],  # Add message for supervisor
            }
            final_state = None
            try:
                # Wrap graph execution with cancellation support
                final_state = execution_controller.wrap_execution(
                    graph.invoke, current_input, graph_config
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
                input_handler.show_status(
                    msg, status="error", title="Recursion Limit Exceeded"
                )
                continue
            except Exception as e:
                logger.exception("An error occurred during graph execution.")
                input_handler.show_status(
                    f"An unexpected error occurred: {e}",
                    status="error",
                    title="Execution Error",
                )
                continue
            
            # Check if the agent needs user input
            if final_state and final_state.get("needs_user_input"):
                logger.info("[MAIN_REPL] Agent requesting user input")
                user_input_data = final_state.get("user_input_required", {})
                
                if user_input_data:
                    question = user_input_data.get("question", "Please provide input:")
                    suggested_responses = user_input_data.get("suggested_responses", [])
                    
                    # Display the question
                    console.print(f"\n[bold yellow]📝 Agent Question:[/bold yellow]")
                    console.print(f"{question}\n")
                    
                    # Add "Enter custom response" option
                    display_options = suggested_responses + ["Enter custom response"]
                    
                    # Use InputHandler's menu system for selection
                    selected_option = input_handler.prompt_arrow_menu(
                        title="Select your response:",
                        options=[{"label": opt, "value": opt} for opt in display_options],
                        quit_keys=["escape"]
                    )
                    
                    if selected_option is None:
                        # User cancelled
                        input_handler.show_status(
                            "User input cancelled. Agent execution stopped.",
                            status="warning"
                        )
                        continue
                    
                    # Handle custom input
                    if selected_option == "Enter custom response":
                        user_response = input_handler.prompt_text(
                            "[bold yellow]Your response:[/bold yellow] ",
                            default="",
                            show_default=False
                        ).strip()
                        if not user_response:
                            input_handler.show_status(
                                "Empty response provided. Agent execution stopped.",
                                status="warning"
                            )
                            continue
                    else:
                        user_response = selected_option
                    
                    logger.info(f"[MAIN_REPL] User provided response: {user_response}")
                    
                    # Update the state with the user's response
                    resume_input = {
                        "task": state.task,  # Keep original task
                        "auto_approve": config.AUTO_APPROVE,
                        "project_root_cwd": os.getcwd(),
                        "user_input_fn": user_input_fn,
                        "execution_mode": state.execution_mode,
                        "user_input_response": user_response,  # Add user's response
                        "needs_user_input": False,  # Clear the flag
                        "messages": final_state.get("messages", [])  # Preserve messages
                    }
                    
                    # Resume execution with user's response
                    logger.info("[MAIN_REPL] Resuming agent execution with user response")
                    try:
                        final_state = execution_controller.wrap_execution(
                            graph.invoke, resume_input, graph_config
                        )
                    except KeyboardInterrupt:
                        msg = "Execution cancelled by user during resume. Ready for new command."
                        logger.info(f"[USER_CANCEL] {msg}")
                        input_handler.show_status(msg, status="warning", title="Cancelled")
                        execution_controller.reset()
                        continue
                    except Exception as e:
                        logger.exception("Error during resumed execution")
                        input_handler.show_status(
                            f"Error resuming execution: {e}",
                            status="error",
                            title="Resume Error"
                        )
                        continue
            
            logger.info(
                "\n==================== 🎉🎉🎉  KATALYST RUN COMPLETE  🎉🎉🎉 ===================="
            )
            if final_state:
                print_run_summary(final_state, input_handler)
            else:
                input_handler.show_status(
                    "The agent run did not complete successfully.", status="error"
                )


def main():
    ensure_openai_api_key()
    maybe_show_welcome()
    init_instrumentation()
    try:
        repl()
    except Exception as e:
        get_logger().exception("Unhandled exception in main loop.")
        print(f"An unexpected error occurred: {e}. See the log file for details.")


if __name__ == "__main__":
    main() 