# User Input Request Handling in Katalyst

## Why Custom Implementation Was Needed

- **LangGraph's create_react_agent limitation**: The prebuilt agent doesn't pause for individual tool calls - it runs to completion
- **Global interrupt not suitable**: LangGraph's interrupt feature applies to ALL tools, but we only want to pause for `request_user_input`
- **Selective interruption required**: Other tools (file operations, searches) should execute without interruption
- **Terminal UI constraints**: User input menus must run in main REPL thread where terminal controls work properly

## Implementation Architecture

- **Exception-based signaling**: `request_user_input` tool raises `UserInputRequiredException` instead of blocking
- **State-based communication**: Exception details stored in `KatalystState` fields:
  - `needs_user_input`: Flag to indicate input required
  - `user_input_required`: Contains question and suggested responses
  - `user_input_response`: Stores user's answer for resume
- **Graph routing to END**: When `needs_user_input=True`, router sends to END node to pause execution
- **REPL detection and handling**: Main loop checks for flag, displays menu, collects response
- **Resume with injected response**: Executor injects ToolMessage with user's answer and continues

## Flow Sequence

1. **Agent calls tool**: Agent invokes `request_user_input(question, options)`
2. **Tool raises exception**: `UserInputRequiredException` thrown with question details
3. **Executor catches**: Updates state with question, sets `needs_user_input=True`
4. **Graph pauses**: Router sees flag, routes to END instead of continuing
5. **REPL prompts user**: Detects flag, shows question with menu options
6. **User responds**: Selection made via InputHandler's arrow menu
7. **State updated**: Response stored in `user_input_response` field
8. **Graph resumes**: REPL re-invokes graph with response
9. **Executor injects**: Creates ToolMessage with answer, appends to messages
10. **Agent continues**: Receives response and proceeds with task