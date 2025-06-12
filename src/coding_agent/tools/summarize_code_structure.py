import os
from typing import List, Dict, Any, TypedDict, Annotated
from katalyst_core.utils.tools import katalyst_tool
from katalyst_core.utils.file_utils import list_files_recursively, should_ignore_path
from katalyst_core.services.llms import get_llm_instructor_async
from katalyst_core.utils.logger import get_logger
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from pydantic import BaseModel
import operator

# Import the map and reduce prompts
from src.coding_agent.prompts.tools.summarize_code_structure_map import (
    SUMMARIZE_CODE_STRUCTURE_MAP_PROMPT,
)
from src.coding_agent.prompts.tools.summarize_code_structure_reduce import (
    SUMMARIZE_CODE_STRUCTURE_REDUCE_PROMPT,
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
    prompt_module="summarize_code_structure",
    prompt_var="SUMMARIZE_CODE_STRUCTURE_PROMPT",
)
async def summarize_code_structure(
    path: str, respect_gitignore: bool = True
) -> Dict[str, Any]:
    llm = get_llm_instructor_async()
    model = os.getenv("KATALYST_LITELLM_MODEL", "gpt-4.1")
    logger.info(f"[summarize_code_structure] Summarizing: {path}")

    # Gather files to summarize
    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        files = list_files_recursively(path, respect_gitignore=respect_gitignore)
    else:
        return {"error": f"Path not found: {path}"}
    files = [
        f for f in files if not should_ignore_path(f, os.getcwd(), respect_gitignore)
    ]
    # Deduplicate files while preserving order
    files = list(dict.fromkeys(files))
    logger.info(f"[summarize_code_structure] Files to summarize: {files}")
    if not files:
        return {"error": f"No files to summarize in: {path}"}

    # Node: Summarize a single file (map step)
    async def generate_summary(file_path: str) -> Dict[str, List[FileSummaryDict]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"[summarize_code_structure] Failed to read {file_path}: {e}")
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
        prompt = SUMMARIZE_CODE_STRUCTURE_MAP_PROMPT.replace("{context}", content)
        logger.debug(
            f"[summarize_code_structure] Map prompt for {file_path}:\n{prompt[:5000]}"
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
        prompt = SUMMARIZE_CODE_STRUCTURE_REDUCE_PROMPT.replace("{docs}", docs)
        logger.debug(f"[summarize_code_structure] Reduce prompt:\n{prompt[:5000]}")
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
