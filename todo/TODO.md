# TODO

- Add interactive configuration using typer (or similar library) to let users adjust all input variables and API keys easily.
- Support beyond Python:
    - Add Tree-sitter support for C and C++ (grammar integration and code definition extraction)
    - Generalize the check_syntax utility (in src/katalyst_agent/tools/write_to_file.py) to support syntax checking for more languages (not just Python).
- Add System context about local env info including available cpu/memory
- Langfuse for observability
- /init command should understand the project: strcture, every function/file/class, etc.
- /init output should be kept in memory for project context (rag-retrieval for relevant context here)
- /init update init in the backgorund in regular intervals
- Telemetry for usage-based data collection
- Create several pre-defined plans and rag over them as needed to help planner
- Support understanding existing code base and making changes to it
