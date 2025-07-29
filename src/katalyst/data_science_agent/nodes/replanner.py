"""
Data Science Replanner Node - Uses create_react_agent for analysis verification and replanning.

This node:
1. Creates a replanner agent with verification tools
2. Reviews the analysis completed so far
3. Decides if the analysis objectives are met
4. Creates additional investigation tasks if needed
"""

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.models import ReplannerOutput
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.checkpointer_manager import checkpointer_manager
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model
from katalyst.katalyst_core.utils.tools import (
    get_tool_functions_map,
    create_tools_with_context,
)
from katalyst.coding_agent.nodes.summarizer import get_summarization_node


# Data science replanner prompt
replanner_prompt = """You are a senior data scientist reviewing analysis progress and determining next steps.

Your role is to:
1. Review the analysis completed so far
2. Assess whether the original objectives have been met
3. Identify gaps in understanding or missing analyses
4. Decide if more investigation is needed

Use your tools to:
- Check analysis outputs and visualizations (ls, read_file)
- Verify statistical validity of findings (execute_data_code)
- Review saved results and reports (read_file)
- Get user confirmation on analysis direction (request_user_input)

VERIFICATION GUIDELINES:
- Check if key questions have been answered with data
- Verify statistical significance of findings
- Ensure visualizations effectively communicate insights
- Validate that conclusions are supported by evidence
- Consider if additional analyses would add value

FILE ORGANIZATION:
- Ensure outputs are organized in appropriate directories:
  - data/: Processed datasets, feature files, intermediate results
  - models/: Trained models, model artifacts, performance metrics
  - visualizations/: Charts, plots, graphs, visual analysis outputs
  - docs/: Reports, summaries, methodology documentation
- Check that filenames are descriptive and indicate their content

DECISION CRITERIA:
- Set is_complete to true if:
  * Original analysis objectives are fully ACHIEVED
  * Key insights have been discovered and documented
  * Findings are properly validated
  * Results are ready for stakeholder consumption

- Set is_complete to false and provide new tasks if:
  * Important patterns remain unexplored
  * Initial findings raise new questions
  * Additional validation is needed
  * User feedback suggests new directions
  * User goals were not achieved

Example additional tasks:
- Perform statistical significance testing on key findings
- Create additional visualizations for stakeholder presentation
- Investigate anomalies discovered during initial analysis
- Build predictive model based on identified patterns
- Generate comprehensive analysis report with recommendations
"""


def replanner(state: KatalystState) -> KatalystState:
    """
    Use a replanner agent to verify analysis and decide next steps.
    """
    logger = get_logger("data_science_agent")
    logger.debug("[DS_REPLANNER] Starting data science replanner node...")

    # Check if all tasks are completed (no need to replan)
    if not state.error_message and state.task_idx >= len(state.task_queue):
        logger.debug("[DS_REPLANNER] All tasks completed. Nothing to replan.")
        state.task_queue = []
        return state

    # Get checkpointer from manager
    checkpointer = checkpointer_manager.get_checkpointer()

    # Check if we have a checkpointer
    if not checkpointer:
        logger.error("[DS_REPLANNER] No checkpointer available from manager")
        state.error_message = "No checkpointer available for conversation"
        return state

    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("replanner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()

    logger.debug(f"[DS_REPLANNER] Using model: {model_name} (provider: {provider})")

    # Get replanner model
    replanner_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0,
        timeout=timeout,
        api_base=api_base,
    )

    # Get replanner tools with logging context (verification tools)
    tool_functions = get_tool_functions_map(category="replanner")
    tools = create_tools_with_context(tool_functions, "DS_REPLANNER")

    # Get summarization node for conversation compression
    summarization_node = get_summarization_node()

    # Create replanner agent with structured output and summarization
    replanner_agent = create_react_agent(
        model=replanner_model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=replanner_prompt,  # Set as system prompt
        response_format=ReplannerOutput,  # Use structured output
        pre_model_hook=summarization_node,  # Enable conversation summarization
    )

    # Format context about what has been done
    context = f"""
ANALYSIS OBJECTIVE: {state.task}

ORIGINAL ANALYSIS PLAN:
{chr(10).join(f"{i+1}. {task}" for i, task in enumerate(state.original_plan)) if state.original_plan else "No original plan provided."}

COMPLETED INVESTIGATIONS:
{chr(10).join(f"✓ {task}: {summary}" for task, summary in state.completed_tasks) if state.completed_tasks else "No investigations marked as completed yet."}

TOOL EXECUTION HISTORY:
"""

    # Add execution history
    if hasattr(state, "tool_execution_history") and state.tool_execution_history:
        current_task = None
        for record in state.tool_execution_history:
            if record["task"] != current_task:
                current_task = record["task"]
                context += f"\n=== Investigation: {current_task} ===\n"
            context += f"- {record['tool_name']}: {record['status']}"
            if record["status"] == "error":
                context += f" (Error: {record['summary']})"
            context += "\n"
    else:
        context += "No tool executions recorded yet.\n"

    # Create verification message
    verification_message = HumanMessage(
        content=f"""{context}

Please review the analysis completed so far and decide if the objectives have been met or if additional investigation is needed."""
    )

    # Add to messages
    state.messages.append(verification_message)

    try:
        # Use the replanner agent to verify and decide
        logger.info("[DS_REPLANNER] Invoking replanner agent to review analysis")
        result = replanner_agent.invoke({"messages": state.messages})

        # Update messages
        state.messages = result.get("messages", state.messages)

        # Extract structured response
        structured_response = result.get("structured_response")

        if structured_response and isinstance(structured_response, ReplannerOutput):
            if structured_response.is_complete:
                # Analysis is complete
                logger.info("[DS_REPLANNER] Analysis objectives complete")
                state.task_queue = []
                state.task_idx = 0

                # Extract summary from AI message
                ai_messages = [
                    msg for msg in state.messages if isinstance(msg, AIMessage)
                ]
                if ai_messages:
                    # Use the last AI message content as summary
                    pass
                else:
                    pass

            else:
                # More investigation needed
                if structured_response.subtasks:
                    # Update state with new investigation tasks
                    logger.info(
                        f"[DS_REPLANNER] Creating new analysis plan with {len(structured_response.subtasks)} tasks"
                    )
                    state.task_queue = structured_response.subtasks
                    state.task_idx = 0
                    state.error_message = None

                    # Log new plan
                    plan_message = (
                        "Continuing with additional investigations:\n"
                        + "\n".join(
                            f"{i+1}. {task}"
                            for i, task in enumerate(structured_response.subtasks)
                        )
                    )
                    logger.info(f"[DS_REPLANNER] {plan_message}")
                else:
                    logger.error(
                        "[DS_REPLANNER] Structured response indicates more work needed but no subtasks provided"
                    )
                    state.error_message = (
                        "Replanner indicated more analysis needed but provided no tasks"
                    )
        else:
            # Fallback: check if there's an error message in the result
            logger.error(
                f"[DS_REPLANNER] No structured response received. Result keys: {list(result.keys())}"
            )
            state.error_message = "Failed to get structured response from replanner"

            # Log any AI messages for debugging
            ai_messages = [msg for msg in state.messages if isinstance(msg, AIMessage)]
            if ai_messages:
                logger.debug(
                    f"[DS_REPLANNER] Last AI message: {ai_messages[-1].content[:200]}..."
                )

    except Exception as e:
        logger.error(f"[DS_REPLANNER] Failed to replan: {str(e)}")
        state.error_message = f"Analysis replanning failed: {str(e)}"

    logger.debug("[DS_REPLANNER] End of data science replanner node.")
    return state
