# React Agent Architecture for Katalyst

## Overview

This document outlines a fundamental architectural shift for Katalyst: moving from a mixed architecture (where only the executor uses React) to a **unified React agent architecture** where all major components (planner, executor, replanner) are React agents.

## Table of Contents

1. [The Evolution](#the-evolution)
2. [Core Insight: Shared Thread ID](#core-insight-shared-thread-id)
3. [Architecture Design](#architecture-design)
4. [Implementation Strategy](#implementation-strategy)
5. [Tool Organization](#tool-organization)
6. [Benefits & Trade-offs](#benefits--trade-offs)
7. [Migration Path](#migration-path)
8. [Code Examples](#code-examples)

## The Evolution

### Current Architecture
```
Planner (LLM) → Executor (React) → Replanner (LLM)
```
- Only executor can use tools
- Planner/Replanner make decisions blindly
- Complex context passing between components

### Proposed Architecture
```
Planner (React) → Executor (React) → Replanner (React)
```
- All components can investigate before deciding
- Shared conversation through thread ID
- Natural context flow

## Core Insight: Shared Thread ID

The key breakthrough is realizing that `create_react_agent` with a shared thread ID creates a **continuous conversation** across different agent instances:

```python
# Different agents, same conversation thread
planner = create_react_agent(tools=PLANNING_TOOLS, checkpointer=checkpointer)
executor = create_react_agent(tools=EXECUTION_TOOLS, checkpointer=checkpointer)
replanner = create_react_agent(tools=REPLANNING_TOOLS, checkpointer=checkpointer)

# All use the same thread ID
config = {"thread_id": "main-conversation"}
```

This means:
- Full conversation history is preserved
- Each agent sees what previous agents discovered
- No complex context sharing needed
- Natural flow like one person switching tools

## Architecture Design

### State Structure

```python
class KatalystState(BaseModel):
    # Core conversation state
    checkpointer: Optional[Any] = Field(None, exclude=True)
    thread_id: str = Field("main-conversation", description="Shared thread for all agents")
    
    # Current phase tracking
    current_phase: str = Field("planning", description="planning|execution|replanning")
    
    # Task management (unchanged)
    task: str
    task_queue: List[str]
    task_idx: int
    
    # Shared context (automatically via thread)
    # No need for complex message passing!
```

### Node Structure

Each node creates its specialized agent but continues the same conversation:

```python
def planner_node(state: KatalystState) -> KatalystState:
    """Planning phase with investigation tools"""
    planner = create_react_agent(
        model=get_llm("reasoning"),
        tools=PLANNING_TOOLS,
        checkpointer=state.checkpointer
    )
    
    result = planner.invoke(
        {"messages": [HumanMessage(f"Analyze and create a plan for: {state.task}")]},
        {"thread_id": state.thread_id}
    )
    
    # Extract plan from conversation
    state.task_queue = extract_plan_from_messages(result["messages"])
    return state

def executor_node(state: KatalystState) -> KatalystState:
    """Execution phase with coding tools"""
    executor = create_react_agent(
        model=get_llm("execution"),
        tools=EXECUTION_TOOLS,
        checkpointer=state.checkpointer
    )
    
    current_task = state.task_queue[state.task_idx]
    result = executor.invoke(
        {"messages": [HumanMessage(f"Execute this task: {current_task}")]},
        {"thread_id": state.thread_id}  # Same thread!
    )
    
    return state

def replanner_node(state: KatalystState) -> KatalystState:
    """Replanning phase with analysis tools"""
    replanner = create_react_agent(
        model=get_llm("reasoning"),
        tools=REPLANNING_TOOLS,
        checkpointer=state.checkpointer
    )
    
    result = replanner.invoke(
        {"messages": [HumanMessage("Review progress and adapt the plan")]},
        {"thread_id": state.thread_id}  # Same thread!
    )
    
    # Extract new plan
    state.task_queue = extract_adapted_plan(result["messages"])
    return state
```

## Implementation Strategy

### Phase 1: Tool Sets Definition

```python
PLANNING_TOOLS = [
    analyze_codebase,      # Explore project structure
    check_dependencies,    # Understand requirements
    read_documentation,    # Learn conventions
    search_patterns,       # Find similar code
    estimate_complexity,   # Gauge effort
    generate_plan         # Create task list
]

EXECUTION_TOOLS = [
    read_file,            # Read code
    write_file,           # Write code
    execute_command,      # Run commands
    search_files,         # Find files
    list_files,           # Browse structure
    create_subtask,       # Add new tasks
    attempt_completion    # Mark done
]

REPLANNING_TOOLS = [
    analyze_failures,     # Understand errors
    review_history,       # Check what was tried
    find_alternatives,    # Search different approaches
    check_constraints,    # Verify assumptions
    generate_new_plan    # Create adapted plan
]
```

### Phase 2: Conversation Flow

The beauty is the natural conversation flow:

```
Human: "Build a TODO app"

[Planner Agent with PLANNING_TOOLS]
AI: "Let me analyze the project structure..."
Tool: analyze_codebase() → "Found React 18, TypeScript, no backend"
AI: "I'll check what UI library you're using..."
Tool: check_dependencies() → "Found Material-UI v5"
AI: "Based on my analysis, here's the plan:
     1. Create Todo model with TypeScript
     2. Build TodoList component
     3. Add CRUD operations
     4. Style with Material-UI"

[Executor Agent with EXECUTION_TOOLS]
Human: "Execute task 1: Create Todo model"
AI: "I'll create the Todo model. First, let me see the project structure..."
Tool: list_files("src/models") → "Directory doesn't exist"
AI: "I'll create the models directory and Todo type..."
Tool: write_file("src/models/Todo.ts", "...") → "Created"

[Replanner Agent with REPLANNING_TOOLS] 
Human: "Task failed, please adapt"
AI: "Let me analyze what went wrong..."
Tool: analyze_failures() → "TypeScript config has strict mode issues"
AI: "I see the issue. The plan needs adjustment for strict TypeScript..."
```

## Tool Organization

### Tool Naming Convention

Prefix tools to prevent confusion:

```python
# Planning tools
plan_analyze_codebase()
plan_check_dependencies()
plan_estimate_complexity()

# Execution tools  
exec_read_file()
exec_write_file()
exec_run_command()

# Replanning tools
replan_analyze_failures()
replan_review_history()
replan_find_alternatives()
```

### Tool Metadata

Each tool should declare its purpose:

```python
@tool
def plan_analyze_codebase():
    """[PLANNING PHASE] Analyzes the codebase structure and conventions.
    Use during planning to understand the project before creating tasks."""
    ...
```

## Benefits & Trade-offs

### Benefits

1. **Intelligent Planning**: Planner can explore before deciding
2. **Informed Adaptation**: Replanner has full context and tools
3. **Natural Context Flow**: Conversation continues across phases
4. **Reduced Hallucination**: All decisions based on investigation
5. **Better Error Recovery**: Can analyze failures deeply
6. **Simpler Architecture**: No complex context passing

### Trade-offs

1. **More LLM Calls**: Each phase does more investigation
2. **Longer Execution Time**: Trading speed for accuracy
3. **Larger Conversation History**: Needs management over time
4. **Tool Complexity**: Three tool sets to maintain

## Migration Path

### Step 1: Extend Current Architecture
Keep current code but add React versions:
```python
if USE_REACT_PLANNER:
    planner_node = react_planner_node
else:
    planner_node = current_planner_node
```

### Step 2: Implement Planning Tools
Start with read-only planning tools:
- analyze_codebase
- check_dependencies
- read_documentation

### Step 3: Test with React Planner
Run parallel tests comparing:
- Current planner output
- React planner output
- Success rates

### Step 4: Implement Replanning Tools
Add analysis and adaptation tools:
- analyze_failures
- review_history
- generate_new_plan

### Step 5: Full Migration
Once validated, switch to full React architecture.

## Code Examples

### Complete Planner Implementation

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage

def create_planner_agent(state: KatalystState):
    """Create a React agent for planning phase"""
    
    # Planning-specific tools
    tools = [
        plan_analyze_codebase,
        plan_check_dependencies,
        plan_read_docs,
        plan_search_patterns,
        plan_generate_tasks
    ]
    
    # Create agent with planning tools
    return create_react_agent(
        model=get_llm_for_planning(),
        tools=tools,
        checkpointer=state.checkpointer
    )

def planner_node(state: KatalystState) -> KatalystState:
    """Planning node using React agent"""
    
    planner = create_planner_agent(state)
    
    # Create planning prompt
    planning_prompt = f"""
    Analyze the following task and create a detailed implementation plan:
    
    Task: {state.task}
    
    Please:
    1. Explore the codebase structure
    2. Check dependencies and constraints  
    3. Read relevant documentation
    4. Create a step-by-step plan
    
    Use the available tools to investigate before planning.
    """
    
    # Run planning phase
    result = planner.invoke(
        {"messages": [HumanMessage(planning_prompt)]},
        {"thread_id": state.thread_id}
    )
    
    # Extract structured plan from messages
    plan_data = extract_plan_from_messages(result["messages"])
    state.task_queue = plan_data["tasks"]
    state.original_plan = plan_data["tasks"]
    
    # Log what planner discovered
    logger.info(f"[PLANNER] Discovered: {plan_data['discoveries']}")
    logger.info(f"[PLANNER] Generated {len(state.task_queue)} tasks")
    
    return state
```

### Shared Context Example

```python
def demonstrate_context_sharing():
    """Show how context flows between agents"""
    
    checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
    thread_id = "demo-thread"
    
    # Planner discovers something
    planner = create_react_agent(
        model=llm,
        tools=[analyze_codebase],
        checkpointer=checkpointer
    )
    
    planner_result = planner.invoke(
        {"messages": [HumanMessage("Analyze this project")]},
        {"thread_id": thread_id}
    )
    # Planner: "I found this uses TypeScript with strict mode"
    
    # Executor sees planner's discovery
    executor = create_react_agent(
        model=llm,
        tools=[write_file],
        checkpointer=checkpointer
    )
    
    executor_result = executor.invoke(
        {"messages": [HumanMessage("Create a User type")]},
        {"thread_id": thread_id}  # Same thread!
    )
    # Executor: "I'll create a TypeScript type with strict mode compatibility
    #            (as discovered earlier)"
    
    # Full context preserved automatically!
```

## Conclusion

The React agent architecture represents a fundamental shift from "agents that sometimes use tools" to "agents that think by using tools." By leveraging shared thread IDs for context, we achieve a simple yet powerful architecture where specialized agents collaborate naturally through a continuous conversation.

This approach delivers:
- Better decision quality through investigation
- Natural context flow without complex state management  
- Specialized agents that work together seamlessly
- A more intelligent and adaptable system overall

The future of Katalyst is React agents all the way down.