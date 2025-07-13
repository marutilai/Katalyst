CREATE_TODO_LIST_TOOL_PROMPT = """# create_todo_list

Creates a comprehensive todo list for completing a complex task by breaking it down into manageable subtasks.

## When to Use This Tool

Use this tool when:
- Starting a new complex task or project
- The user's request involves multiple steps or components
- You need to plan out the implementation approach
- Breaking down a large feature into smaller deliverables

Do NOT use this tool for:
- Simple, single-step tasks
- Tasks that are already well-defined
- When you already have an active todo list (use update_todo_list instead)

## Usage Examples

### Example 1: Creating a web application
```
create_todo_list(
    task_description="Build a todo list web application with React frontend and Python backend",
    include_verification=True
)
```

### Example 2: Implementing a complex feature
```
create_todo_list(
    task_description="Add user authentication system with JWT tokens, password reset, and email verification",
    include_verification=True
)
```

### Example 3: Refactoring project
```
create_todo_list(
    task_description="Refactor the database layer to use SQLAlchemy ORM instead of raw SQL queries",
    include_verification=False
)
```

## Best Practices

1. **Be Specific**: Provide detailed task descriptions that include:
   - Technologies to use
   - Key requirements
   - Any constraints or preferences

2. **Review and Adjust**: After creating the todo list:
   - Review the generated tasks
   - Use update_todo_list to modify if needed
   - Ensure tasks are in logical order

3. **Task Granularity**: The tool will create tasks that are:
   - Meaningful units of work
   - Not too granular (avoid "create file X")
   - Not too broad (avoid "implement everything")

4. **Verification**: Set include_verification=True to:
   - Get user feedback on the plan
   - Allow adjustments before starting
   - Ensure alignment with user expectations

## Output Format

The tool returns a JSON response with:
- `success`: Whether the todo list was created successfully
- `message`: Human-readable message with the todo list
- `todo_list`: Array of task descriptions
- `task_count`: Number of tasks created
- `error`: Error message if creation failed

## Important Notes

- This tool generates a plan but doesn't execute it
- Tasks are focused on implementation, not setup
- The tool assumes basic development environment is ready
- Use update_todo_list to modify the list after creation
"""