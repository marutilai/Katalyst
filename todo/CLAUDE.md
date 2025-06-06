# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Katalyst is a multi-agent coding assistant built on LangGraph that implements a two-level hierarchical agent structure:

### Core Architecture Pattern
```
OUTER LOOP (Plan-and-Execute):
planner → ⟮ INNER LOOP ⟯ → advance_pointer → replanner
      ↘                        ↑                ↘
       └────────── LOOP ───────┘      new-plan/END └──► END

INNER LOOP (ReAct over single task):
agent_react → tool_runner → agent_react (repeat until AgentFinish)
```

### Key Components

- **State Management**: `KatalystState` (state.py) - Pydantic model tracking task queues, chat history, execution trace, and loop guardrails
- **Graph Definition**: `build_compiled_graph()` (graph.py) - LangGraph state graph with conditional routing
- **Routing Logic**: `routing.py` - Controls flow between nodes based on state conditions
- **CLI Interface**: `main.py` + `cli/commands.py` - REPL with commands like `/help`, `/init`, `/provider`, `/model`, `/exit`

### Node Functions
- `planner`: Generates initial ordered sub-task list
- `agent_react`: LLM step yielding AgentAction/AgentFinish
- `tool_runner`: Executes Python tools from AgentAction
- `advance_pointer`: Increments task index, resets inner cycle counters
- `replanner`: Builds fresh plan or final answer when current plan exhausted

## Development Commands

### Running the Agent
```bash
python -m katalyst_agent.main
```

### CLI Commands (within REPL)
- `/help` - Show available commands
- `/init` - Create KATALYST.md file with project documentation
- `/provider` - Set LLM provider (openai/anthropic)
- `/model` - Set LLM model (gpt4.1/gpt-4.1-mini for OpenAI, sonnet4/opus4 for Anthropic)
- `/exit` - Exit the agent

### Environment Variables
- `KATALYST_LITELLM_PROVIDER` - LLM provider selection
- `KATALYST_LITELLM_MODEL` - Model selection within provider
- `KATALYST_AUTO_APPROVE` - Skip interactive confirmation for file operations

## Project Structure

- `katalyst_agent/main.py` - Entry point and REPL
- `katalyst_agent/graph.py` - LangGraph definition and compilation
- `katalyst_agent/state.py` - Pydantic state model
- `katalyst_agent/routing.py` - Conditional routing logic
- `katalyst_agent/nodes/` - Individual graph node implementations
- `katalyst_agent/tools/` - Available tools for agent actions
- `katalyst_agent/cli/` - CLI commands and state persistence
- `katalyst_agent/onboarding/` - Welcome screens and documentation templates
- `katalyst_agent/utils/` - Logging, environment setup, error handling

## Important Implementation Details

### State Persistence
- Project state persisted between sessions via `cli/persistence.py`
- Chat history maintained across runs
- Supports loading/saving project-specific state

### Safety Guardrails
- `max_inner_cycles` (default: 20) - Prevents infinite ReAct loops
- `max_outer_cycles` (default: 10) - Prevents infinite replanning
- Error handling with `[GRAPH_RECURSION]` and `[REPLAN_REQUESTED]` markers

### Tool Integration
Tools in `tools/` directory include file operations, code analysis, command execution, and completion detection. Each tool follows LangChain tool interface.