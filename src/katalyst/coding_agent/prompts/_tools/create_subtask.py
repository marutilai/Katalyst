from textwrap import dedent

CREATE_SUBTASK_PROMPT = dedent("""
# create_subtask Tool

Description: Dynamically create new subtasks when you discover complexity during task execution. Helps break down large tasks into manageable pieces.

## When to Use:
- Current task has multiple independent components you discovered during exploration
- Task is too broad to complete effectively in one go  
- You need to defer part of the work for better organization
- You found multiple models/files/components that each need separate handling

## When NOT to Use:
- Task is already specific enough (e.g., "Create User model")
- You're just listing the next few tool calls you'll make
- You've already created 5 subtasks for the current task
- The work is sequential and doesn't benefit from separation

## Parameters:
- task_description: (string, required) Clear, goal-oriented description of the subtask
- reason: (string, required) Why this subtask is needed (helps understand the decomposition)
- insert_position: (string, optional) Where to insert - "after_current" or "end_of_queue"

## Guidelines:
1. Create goal-oriented tasks, not tool-specific ones
   - ❌ "Use write_to_file to create user.py"
   - ✅ "Implement User model with authentication fields"

2. Keep subtasks at appropriate granularity
   - ❌ "Build entire authentication system" (too broad)
   - ❌ "Write line 1 of user.py" (too specific)
   - ❌ "Create models directory" (file operation, not a task)
   - ✅ "Create User model with validation"
   - ✅ "Set up database models with relationships"

3. File operations are NOT tasks
   - ❌ "Create routers directory with __init__.py"
   - ❌ "Write empty __init__.py file" 
   - ❌ "Add imports to main.py"
   - ✅ "Implement API routing structure"
   - These are just implementation details within a larger task

4. Limit subtask creation (max 5 per parent task)
   - Group related work when possible
   - Don't decompose just for the sake of it

## Examples:

### Example 1: Discovering multiple models
{
  "thought": "Current task is 'Create data models'. I found we need User, Todo, and Category models.",
  "action": "create_subtask",
  "action_input": {
    "task_description": "Implement User model with authentication fields and methods",
    "reason": "User model is complex with auth requirements, needs focused implementation",
    "insert_position": "after_current"
  }
}

### Example 2: Complex feature decomposition  
{
  "thought": "Task 'Implement authentication' needs auth models, API endpoints, and middleware",
  "action": "create_subtask", 
  "action_input": {
    "task_description": "Create authentication API endpoints for login, logout, and token refresh",
    "reason": "API endpoints are independent from model creation and need separate testing",
    "insert_position": "after_current"
  }
}

## Output Format:
JSON with success status, message, and number of tasks created

Example output:
{"success": true, "message": "Subtask creation request processed. Task: 'Implement User model'", "tasks_created": 1}
""")