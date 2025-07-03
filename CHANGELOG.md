# Changelog

All notable changes to Katalyst will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## [Unreleased]

### Added
- **Interactive command palette** - Type `/` to see all available commands in a formatted table
- **Improved terminal input handling** - Better arrow menu navigation and fallback for non-TTY environments

### Fixed
- **Double Ctrl+C exit handling** - Now properly exits on double Ctrl+C using `os._exit()` instead of `sys.exit()`
- **Terminal I/O issues in tests** - Fixed `request_user_input` tests to work in non-TTY environments

### Changed
- **Replaced litellm with native LangChain chat models** - Created new `llms.py` service module for better compatibility
- **Simplified help display** - Shows only implemented commands without unnecessary features

### Removed
- **Legacy litellm dependency** - Fully migrated to LangChain chat models
- **Unused test files** - Renamed legacy test files with underscore prefix (_test_*.py)


## [0.7.0] - 2025-01-07

### Added
- **Persistent Agent Architecture** - Single agent instance maintained across all tasks for better performance
- **Native LangChain Model Support** for OpenAI, Anthropic, Ollama, Groq, and Together
- **Tool Execution History** tracking across all tasks for improved replanner context
- **File caching system** for `read_file` and `list_files` operations with automatic cache invalidation on writes
- **Three-level redundancy protection** to prevent repetitive tool calls:
  - Consecutive duplicate detection
  - Threshold-based blocking (default: 3 repetitions)
  - Deterministic state tracking for read operations
- **Context compression** for chat history and action traces to prevent token limit issues
- **Human-in-the-loop plan verification** - review and approve plans before execution
- **Fuzzy matching** in `apply_source_code_diff` tool for more reliable code modifications
- **Content reference system** to prevent file content hallucination in write operations

### Fixed
- **"No AIMessage found in input" infinite loop** by maintaining agent conversation continuity
- **Performance issues** - reduced runtime from 7+ minutes to ~2 minutes
- Context bloat during long agent sessions through intelligent compression
- Infinite loops from repetitive tool calls with escalating feedback
- Path validation and error handling improvements across all file operations
- Agent task context clarity for better decision making

### Changed
- **Complete refactor to use LangGraph's `create_react_agent`** instead of custom implementation
- **Minimized state complexity** by commenting out unused fields (action_trace, chat_history, operation_context, etc.)
- **Simplified tool runner, planner, and replanner** to leverage LangGraph defaults
- Improved agent prompts for better task understanding and execution
- Enhanced error messages with actionable feedback
- Standardized path handling across all tools

### Removed
- **LiteLLM integration** - replaced with native LangChain models
- **Custom React agent implementation** - now using LangGraph's built-in create_react_agent
- **Unused state fields** - commented out for minimal implementation

## [0.6.1] - 2025-06-23

### Added
- **Tool Repetition Detector** to prevent infinite loops with configurable thresholds
- **Fuzzy matching** in `apply_source_code_diff` for handling whitespace/formatting differences
- **Conversation summarizer** utility for intelligent context compression
- **Chat history compression** with automatic triggering at 50+ messages

### Fixed
- Path validation and standardized path handling across all tools
- Dependency awareness in agent prompts
- Tool hallucination defense mechanisms

### Changed
- Improved error messages with retry prompts for common failures
- Enhanced agent search behavior and tool selection logic

## [0.6.2] - 2025-06-26

### Added
- **Line count validation** in `write_to_file` tool to detect content truncation
- **Ollama integration** for local LLM inference support

### Fixed
- File search clarity in agent prompts
- Agent tool selection improvements

## [0.6.1] - 2025-06-23

### Added
- **Content reference system** to prevent file content hallucination
- **LLM configuration** with centralized provider profiles
- Memory management for multi-turn conversations

### Fixed
- CLI entry point for src-layout compatibility
- Test failures in playbook search and directory overview
- Content reference hallucination in `write_to_file` tool

### Changed
- Cleaned up redundant debug logs for better readability

## [0.6.0] - 2025-06-12

### Added
- **Playbook system** for reusable task patterns
- **Adaptive task planning** with dynamic replanning capabilities
- **Create subtask** tool for better task decomposition

### Fixed
- Graph recursion error logging
- CLI entry point compatibility with src-layout
- Various routing and state management issues

### Changed
- Migrated to src-layout project structure
- Improved error handling and logging throughout

## [0.5.0] - 2025-05-29

### Added
- **Initial release** of Katalyst coding agent
- Core agent architecture with planner, executor, and tool runner nodes
- Basic file operation tools (`read_file`, `write_to_file`, `list_files`, `search_files`)
- Code manipulation tools (`apply_source_code_diff`, `list_code_definitions`)
- Command execution and user interaction tools
- LangGraph-based state management and routing

### Fixed
- Various initialization and setup issues
- Tool validation and error handling

### Changed
- Established base architecture and patterns