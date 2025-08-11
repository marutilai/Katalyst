"""
Human Plan Verification Node - Allows users to review and approve/reject plans.

This module handles the human-in-the-loop verification of generated plans:
- Displays the generated plan to the user
- Asks for approval or feedback
- If feedback provided, triggers replanning with that feedback
- Respects auto_approve mode

This is a shared component used by both coding and data science agents.
"""
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.error_handling import ErrorType, create_error_message
from katalyst.app.ui.input_handler import InputHandler
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown


def human_plan_verification(state: KatalystState) -> KatalystState:
    """
    Present the generated plan to the user for approval or feedback.
    
    Primary Task: Get human verification for the generated plan.
    
    State Changes:
    - If approved: No changes, continues to executor
    - If feedback provided: Sets plan_feedback and triggers replanning
    - If cancelled: Sets response and clears task_queue
    
    Returns: The updated KatalystState
    """
    # Determine which agent we're in based on the next_agent field
    agent_type = state.next_agent if state.next_agent else "coding_agent"
    logger = get_logger(agent_type)
    logger.debug("[HUMAN_PLAN_VERIFICATION] Starting human plan verification...")
    
    # Skip verification if auto_approve is True
    if state.auto_approve:
        logger.info("[HUMAN_PLAN_VERIFICATION] auto_approve is True, skipping human verification")
        return state
    
    # Get user input function
    user_input_fn = state.user_input_fn or input
    
    # Setup console and input handler
    console = Console()
    input_handler = InputHandler(console)
    
    # Display the plan with Rich formatting
    console.print()
    console.print(Panel(
        Markdown("\n".join([f"- {task}" for task in state.task_queue])),
        title="📋 [bold cyan]Generated Plan[/bold cyan]",
        border_style="cyan"
    ))
    console.print()
    
    # Ask for approval
    console.print("[bold yellow]Do you want to proceed with this plan?[/bold yellow]")
    console.print("Options: [green]y[/green]es (approve) / [yellow]f[/yellow]eedback (provide feedback) / [red]c[/red]ancel\n")
    
    # Use the input handler to get user response
    user_response = input_handler.get_user_input("Your choice", user_input_fn).strip().lower()
    
    if user_response in ['y', 'yes', '']:
        logger.info("[HUMAN_PLAN_VERIFICATION] User approved the plan")
        return state
        
    elif user_response in ['f', 'feedback']:
        console.print("\n[bold yellow]Please provide your feedback:[/bold yellow]")
        feedback = input_handler.get_user_input("Feedback", user_input_fn).strip()
        
        if feedback:
            logger.info(f"[HUMAN_PLAN_VERIFICATION] User provided feedback: {feedback[:100]}...")
            # Set feedback - replanner will pick this up
            state.plan_feedback = feedback
            # Clear any previous errors
            state.error_message = None
            return state
        else:
            logger.info("[HUMAN_PLAN_VERIFICATION] No feedback provided, proceeding with plan")
            return state
            
    elif user_response in ['c', 'cancel']:
        logger.info("[HUMAN_PLAN_VERIFICATION] User cancelled the plan")
        # Clear task queue to prevent execution
        state.task_queue = []
        state.response = "Plan cancelled by user."
        return state
        
    else:
        # Default to proceeding with the plan
        logger.info(f"[HUMAN_PLAN_VERIFICATION] Unknown response '{user_response}', proceeding with plan")
        return state