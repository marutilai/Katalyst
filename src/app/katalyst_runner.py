# src/app/katalyst_runner.py
import os
from src.katalyst_core.state import KatalystState  # Import your Pydantic state model
from src.katalyst_core.utils.logger import get_logger
from src.katalyst_core.utils.logger import _LOG_FILE
from langchain_core.agents import AgentFinish  # To check agent_outcome
from langgraph.errors import GraphRecursionError
from src.katalyst_core.utils.state_utils import load_persisted_state
from typing import List


def run_katalyst_task(
    user_input: str,
    project_state: dict,
    graph,
) -> KatalystState:  # Added type hints
    """
    Prepares the initial state for a Katalyst task run, invokes the graph,
    and prints a summary of the outcome.
    """
    logger = get_logger()
    logger.info(
        "\n==================== 🚀🚀🚀  KATALYST RUN START  🚀🚀🚀 ====================\n"
    )
    logger.info(f"[KATALYST_RUNNER] Starting new task: '{user_input}'")

    # --- Prepare Initial State for the Graph ---
    # These are loaded from environment or have defaults
    llm_provider = os.getenv("KATALYST_LITELLM_PROVIDER", "openai")
    llm_model_name = os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1-nano")
    auto_approve = os.getenv("KATALYST_AUTO_APPROVE", "false").lower() == "true"

    # Max iterations for inner and outer loops can also come from config or be fixed

    # Load persisted parts of the state
    loaded_chat_history = load_persisted_state(project_state, "chat_history", [], List)
    loaded_playbook_guidelines = load_persisted_state(
        project_state, "playbook_guidelines", None, str
    )

    initial_cwd = os.getcwd()
    # Construct the initial state dictionary for Pydantic model validation
    # KatalystState Pydantic model will fill in defaults for other fields.
    initial_state_dict = {
        "task": user_input,
        "project_root_cwd": initial_cwd,
        "llm_provider": llm_provider,  # This should be part of KatalystState if nodes need it
        "llm_model_name": llm_model_name,  # This too
        "auto_approve": auto_approve,
        "chat_history": loaded_chat_history,
        "playbook_guidelines": loaded_playbook_guidelines,
        # task_queue, task_idx, completed_tasks, action_trace, cycles will be initialized by planner/nodes
        # error_message, response, agent_outcome will be None or default
        # max_inner_cycles and max_outer_cycles will use Pydantic defaults if not overridden
    }
    # Note: Your initialize_katalyst_run node now takes this dict and creates the Pydantic model.

    # --- Invoke the Graph ---
    # The 'result' will be the final KatalystState Pydantic object
    recursion_limit = int(os.getenv("KATALYST_RECURSION_LIMIT", 250))
    try:
        raw_state = graph.invoke(
            initial_state_dict, {"recursion_limit": recursion_limit}
        )
    except GraphRecursionError:
        msg = (
            f"[GUARDRAIL] Recursion limit ({recursion_limit}) reached. "
            "Please increase the KATALYST_RECURSION_LIMIT environment variable if needed."
        )
        logger.error(msg)
        print(msg)
        return None

    # If it's not already a KatalystState, convert it
    if not isinstance(raw_state, KatalystState):
        final_state = KatalystState(**dict(raw_state))
    else:
        final_state = raw_state

    logger.info(
        "\n\n==================== 🎉🎉🎉  KATALYST RUN COMPLETE  🎉🎉🎉 ====================\n"
    )

    # --- Print Result Summary based on the final KatalystState ---
    final_user_response = (
        final_state.response
    )  # This is the primary field for overall outcome

    if final_user_response:
        if (
            "limit exceeded" in final_user_response.lower()
        ):  # Check for guardrail messages
            print(f"\n--- KATALYST RUN STOPPED DUE TO LIMIT ---")
            print(final_user_response)
        else:  # Assumed successful completion if 'response' is set and not an error
            print(f"\n--- KATALYST TASK CONCLUDED ---")
            print(final_user_response)
    else:
        # This case might occur if the graph ends unexpectedly or routing to END happens
        # without state.response being explicitly set by planner/replanner/guardrails.
        print("\n--- KATALYST RUN FINISHED (No explicit overall response message) ---")
        if final_state.completed_tasks:
            print("Summary of completed sub-tasks:")
            for i, (task_desc, summary) in enumerate(final_state.completed_tasks):
                print(f"  {i+1}. '{task_desc}': {summary}")
        else:
            print("No sub-tasks were marked as completed with a summary.")

        # Fallback to last agent outcome if no overall response
        last_agent_outcome = final_state.agent_outcome
        if isinstance(last_agent_outcome, AgentFinish):
            print(
                f"Last agent step was a finish with output: {last_agent_outcome.return_values.get('output')}"
            )
        elif last_agent_outcome:  # Could be an AgentAction if it stopped mid-tool
            print(f"Last agent step was an action: {last_agent_outcome.tool}")

    # --- Print Full Chat History (always useful) ---
    # Move chat history to debug log, not terminal
    chat_history = final_state.chat_history
    if chat_history:
        logger.debug("\n--- FULL CHAT HISTORY ---")
        for msg_idx, msg in enumerate(chat_history):
            content = getattr(msg, "content", None)
            if (
                content is None
                and hasattr(msg, "additional_kwargs")
                and "content" in msg.additional_kwargs
            ):
                content = msg.additional_kwargs["content"]
            logger.debug(
                f"Message {msg_idx}: [{msg.__class__.__name__}] {content if content is not None else str(msg)}"
            )
        print(f"[LOGGER] Logs are written to: {_LOG_FILE}")
    else:
        print("  (No chat history recorded for this run)")

    print("\nKatalyst Agent is now ready for a new task!")

    # Return the final state (Pydantic model) for persistence
    return final_state
