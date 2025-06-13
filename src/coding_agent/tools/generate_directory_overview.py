import os
from typing import List, Dict, Any, TypedDict, Annotated
from src.katalyst_core.utils.tools import katalyst_tool
from src.katalyst_core.utils.file_utils import (
    list_files_recursively,
    should_ignore_path,
)
from src.katalyst_core.services.llms import get_llm_instructor_async
from src.katalyst_core.utils.logger import get_logger
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from pydantic import BaseModel
import operator

# Import the map and reduce prompts
from src.coding_agent.prompts.tools.generate_directory_overview_map import (
    GENERATE_DIRECTORY_OVERVIEW_MAP_PROMPT,
)
from src.coding_agent.prompts.tools.generate_directory_overview_reduce import (
    GENERATE_DIRECTORY_OVERVIEW_REDUCE_PROMPT,
)

logger = get_logger()


# TypedDicts for state
class FileSummaryDict(TypedDict):
    file_path: str
    summary: str
    key_classes: List[str]
    key_functions: List[str]


class ReduceSummaryDict(TypedDict):
    overall_summary: str
    main_components: List[str]


class OverallState(TypedDict):
    contents: List[str]
    summaries: Annotated[List[FileSummaryDict], operator.add]
    final_summary: ReduceSummaryDict


# Pydantic models for LLM response parsing
class FileSummaryModel(BaseModel):
    file_path: str
    summary: str
    key_classes: List[str]
    key_functions: List[str]


class ReduceSummaryModel(BaseModel):
    overall_summary: str
    main_components: List[str]


@katalyst_tool(
    prompt_module="generate_directory_overview",
    prompt_var="GENERATE_DIRECTORY_OVERVIEW_PROMPT",
)
async def generate_directory_overview(
    dir_path: str, respect_gitignore: bool = True
) -> Dict[str, Any]:
    """Provides a high-level overview and documentation of a codebase by analyzing all files in a directory.

    This tool recursively scans a directory, summarizes each source file's purpose and key
    components, and creates a final architectural summary. It uses a map-reduce pattern where
    each file is first summarized independently (map) and then combined into an overall summary (reduce).

    When to Use:
        - Understanding/documenting an entire project, module, or large directory
        - Getting up to speed on a new codebase quickly
        - Generating documentation or architectural overviews
        - Analyzing the structure and relationships between files

    Args:
        dir_path (str): Directory path to analyze. Must be a directory, not a file.
        respect_gitignore (bool, optional): Whether to respect .gitignore patterns.
            Defaults to True.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - summaries (List[Dict]): List of file summaries, each containing:
                - file_path (str): Path to the summarized file
                - summary (str): Concise summary of file's purpose and logic
                - key_classes (List[str]): Important classes in the file
                - key_functions (List[str]): Important functions in the file
            - overall_summary (str): Concise summary of the entire codebase
            - main_components (List[str]): Most important files/components
            - error (str, optional): Error message if something went wrong

    Example:
        >>> result = await generate_directory_overview("src/")
        >>> print(result["overall_summary"])
        "This is a Python CLI application with a modular architecture..."
        >>> print(result["summaries"][0])
        {
            "file_path": "src/main.py",
            "summary": "Main entry point with CLI argument parsing",
            "key_classes": ["App"],
            "key_functions": ["main", "parse_args"]
        }
    """
    llm = get_llm_instructor_async()
    model = os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1")
    logger.info(f"[generate_directory_overview] Analyzing directory: {dir_path}")

    # Validate path is a directory
    if not os.path.exists(dir_path):
        return {"error": f"Directory not found: {dir_path}"}
    if not os.path.isdir(dir_path):
        return {"error": f"Path must be a directory, not a file: {dir_path}"}

    # Gather files to summarize
    files = list_files_recursively(dir_path, respect_gitignore=respect_gitignore)
    files = [
        f for f in files if not should_ignore_path(f, os.getcwd(), respect_gitignore)
    ]
    # Deduplicate files while preserving order
    files = list(dict.fromkeys(files))
    logger.info(f"[generate_directory_overview] Files to summarize: {files}")
    if not files:
        return {"error": f"No files to summarize in directory: {dir_path}"}

    # Node: Summarize a single file (map step)
    async def generate_summary(file_path: str) -> Dict[str, List[FileSummaryDict]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(
                f"[generate_directory_overview] Failed to read {file_path}: {e}"
            )
            return {
                "summaries": [
                    {
                        "file_path": file_path,
                        "summary": f"ERROR: {e}",
                        "key_classes": [],
                        "key_functions": [],
                    }
                ]
            }
        prompt = GENERATE_DIRECTORY_OVERVIEW_MAP_PROMPT.replace("{context}", content)
        logger.debug(
            f"[generate_directory_overview] Map prompt for {file_path}:\n{prompt[:5000]}"
        )
        response = await llm.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            response_model=FileSummaryModel,
            temperature=0.2,
        )
        # Ensure file_path is correctly set from the input, not the LLM's potential hallucination
        summary_data = response.model_dump()
        summary_data["file_path"] = file_path
        return {"summaries": [summary_data]}

    # Edge: Map each file to a summary node using Send objects
    def map_summaries(state: OverallState):
        return [Send("generate_summary", f) for f in state["contents"]]

    # Node: Reduce all file summaries into an overall summary (reduce step)
    async def generate_final_summary(
        state: OverallState,
    ) -> Dict[str, ReduceSummaryDict]:
        docs = "\n".join(
            [
                f"File: {s['file_path']}\nSummary: {s['summary']}"
                for s in state["summaries"]
                if "summary" in s
            ]
        )
        prompt = GENERATE_DIRECTORY_OVERVIEW_REDUCE_PROMPT.replace("{docs}", docs)
        logger.debug(f"[generate_directory_overview] Reduce prompt:\n{prompt[:5000]}")
        response = await llm.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            response_model=ReduceSummaryModel,
            temperature=0.2,
        )
        return {"final_summary": response.model_dump()}

    def route_after_summaries(state: OverallState) -> str:
        """Decide whether to run the reduce step or end the graph."""
        if len(state["contents"]) <= 1:
            # If only one file (or none), no reduce step is needed.
            return "end"
        else:
            # If multiple files, proceed to the reduce step.
            return "reduce"

    # --- Build the LangGraph graph ---
    graph = StateGraph(OverallState)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("generate_final_summary", generate_final_summary)
    # Fan-out: This conditional edge is used to send each file in 'contents' to the 'generate_summary' node in parallel.
    # Although conditional edges are typically used for branching based on state, here we use it as a fan-out pattern:
    # map_summaries returns a list of Send objects (one per file), so each file is processed independently by the map node.
    # This is a bit unconventional, but is the recommended LangGraph pattern for parallel map-reduce workflows.
    graph.add_conditional_edges(START, map_summaries, ["generate_summary"])
    graph.add_conditional_edges(
        "generate_summary",
        route_after_summaries,
        {"end": END, "reduce": "generate_final_summary"},
    )
    graph.add_edge("generate_final_summary", END)
    app = graph.compile()

    # --- Run the graph ---
    initial_state: OverallState = {
        "contents": files,
        "summaries": [],
        "final_summary": {"overall_summary": "", "main_components": []},
    }
    result = await app.ainvoke(initial_state)

    return {
        "summaries": result["summaries"],
        **(result.get("final_summary", {})),
    }
