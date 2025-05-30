import os
from katalyst_agent.utils.logger import get_logger

def run_katalyst_task(user_input, project_state, graph):
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

    # Return the result for further state persistence
    return result 