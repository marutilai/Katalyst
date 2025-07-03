"""
Human Plan Verification Node - Allows users to review and approve/reject plans.

This module handles the human-in-the-loop verification of generated plans:
- Displays the generated plan to the user
- Asks for approval or feedback
- If feedback provided, triggers replanning with that feedback
- Respects auto_approve mode
"""
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.error_handling import ErrorType, create_error_message
from katalyst.app.ui.input_handler import InputHandler
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
# MINIMAL: Removed message imports since chat_history is not used
# from langchain_core.messages import HumanMessage, SystemMessage


def human_plan_verification(state: KatalystState) -> KatalystState:
    """
    Present the generated plan to the user for approval or feedback.
    
    Primary Task: Get human verification for the generated plan.
    
    State Changes:
    - If approved: No changes, continues to agent_react
    - If feedback provided: Sets plan_feedback and triggers replanning
    - If cancelled: Sets response and clears task_queue
    
    Returns: The updated KatalystState
    """
    logger = get_logger()
    logger.debug("[HUMAN_PLAN_VERIFICATION] Starting human plan verification...")
    
    # Skip verification if auto_approve is True
    if state.auto_approve:
        logger.info("[HUMAN_PLAN_VERIFICATION] auto_approve is True, skipping human verification")
        # MINIMAL: Removed chat_history append
        return state
    
    # Get user input function
    user_input_fn = state.user_input_fn or input
    
    # Setup console and input handler
    console = Console()
    input_handler = InputHandler(console)
    
    # Display the plan with Rich formatting
    console.print("\n" + "="*60)
    console.print("🤖 [bold]KATALYST PLAN VERIFICATION[/bold]")
    console.print("="*60)
    console.print(f"\n[bold]Task:[/bold] {state.task}\n")
    console.print("[bold]Generated Plan:[/bold]")
    for i, task in enumerate(state.task_queue, 1):
        console.print(f"  {i}. {task}")
    console.print("\n" + "-"*60)
    
    # For test compatibility, use old method if custom user_input_fn provided
    if user_input_fn != input:
        print("\nDo you approve this plan?")
        print("- Type 'yes' or 'y' to approve and continue")
        print("- Type 'no' or provide feedback for a better plan")
        print("- Type 'cancel' to stop")
        response = user_input_fn("\nYour response [yes]: ").strip() or "yes"
    else:
        # Use arrow navigation for normal operation
        options = [
            {"label": "Approve and continue", "value": "yes"},
            {"label": "Provide feedback for a better plan", "value": "feedback"},
            {"label": "Cancel operation", "value": "cancel"}
        ]
        
        selected = input_handler.prompt_arrow_menu(
            title="Do you approve this plan?",
            options=options,
            quit_keys=["escape"]
        )
        
        # Handle menu result
        if selected is None:  # User pressed ESC
            response = "cancel"
        elif selected == "feedback":
            response = "no"  # Will trigger feedback prompt below
        else:
            response = selected
    
    if response.lower() in ['yes', 'y']:
        # Approve plan
        logger.info("[HUMAN_PLAN_VERIFICATION] User approved plan")
        # MINIMAL: Removed chat_history append
        
    elif response.lower() == 'cancel':
        # Cancel operation
        logger.info("[HUMAN_PLAN_VERIFICATION] User cancelled operation")
        state.response = "Operation cancelled by user"
        state.task_queue = []
        # MINIMAL: Removed chat_history append
        
    else:
        # User provided feedback - treat anything else as feedback
        feedback = response
        if response.lower() in ['no', 'n']:
            # If they just said no, ask for specific feedback
            if user_input_fn != input:
                feedback = user_input_fn("\nWhat would you like to change about the plan? ").strip()
            else:
                feedback = input_handler.prompt_text(
                    "\n[bold]What would you like to change about the plan?[/bold] "
                ).strip()
        
        logger.info(f"[HUMAN_PLAN_VERIFICATION] User provided feedback: {feedback}")
        
        # MINIMAL: Removed chat_history append
        
        # Clear task queue and set feedback for planner
        state.task_queue = []
        state.plan_feedback = feedback
        # Use proper error handling mechanism
        state.error_message = create_error_message(
            ErrorType.REPLAN_REQUESTED, 
            "User provided feedback for plan improvement",
            "HUMAN_PLAN_VERIFICATION"
        )
    
    logger.debug("[HUMAN_PLAN_VERIFICATION] End of human plan verification")
    return state