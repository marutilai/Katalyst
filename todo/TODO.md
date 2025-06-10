# TODO

- Add interactive configuration using typer (or similar library) to let users adjust all input variables and API keys easily.
- Support beyond Python:
    - Add Tree-sitter support for C and C++ (grammar integration and code definition extraction)
    - Generalize the check_syntax utility (in src/katalyst_agent/tools/write_to_file.py) to support syntax checking for more languages (not just Python).
- Improve test coverage.
- [DONE] Explore LangGraph React/Code agents for planning
- Add System context about local env info including available cpu/memory
- Test Ollama for local models: CodeStral, DevStral, Phi4, QwenCoder
- Langfuse for observability
- Test for languages other than Python
- /init command should understand the project: strcture, every function/file/class, etc.
- /init output should be kept in memory for project context (rag-retrieval for relevant context here)
- /init update init in the backgorund in regular intervals
- Long-term memory management
- Telemetry for usage-based data collection
- Create several pre-defined plans and rag over them as needed to help planner
- capability for pausing and continuing the dag execution flow? ideally serializable & de-serializable execution state. 
- Support understanding existing code base and making changes to it