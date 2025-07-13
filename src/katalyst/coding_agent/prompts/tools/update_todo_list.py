UPDATE_TODO_LIST_TOOL_PROMPT = """# update_todo_list

Updates the current todo list by adding, removing, completing, reordering tasks, or showing the current list.

## Actions

### 1. **add** - Add a new task
```
update_todo_list(
    action="add",
    task_description="Implement user profile page with avatar upload",
    reason="User requested profile functionality"
)
```

### 2. **remove** - Remove a task
```
update_todo_list(
    action="remove", 
    task_index=3,
    reason="This task is no longer needed"
)
```

### 3. **complete** - Mark a task as completed
```
update_todo_list(
    action="complete",
    task_index=1,
    reason="Finished implementing authentication"
)
```

### 4. **reorder** - Move a task to a new position
```
update_todo_list(
    action="reorder",
    task_index=5,
    new_position=2,
    reason="This needs to be done earlier due to dependencies"
)
```

### 5. **show** - Display the current todo list
```
update_todo_list(
    action="show"
)
```

## Parameters

- **action** (required): The operation to perform
- **task_description**: Required for "add" action - the task to add
- **task_index**: Required for "remove", "complete", "reorder" - 1-based index
- **new_position**: Required for "reorder" - 1-based target position
- **reason**: Optional but recommended - explanation for the change

## Best Practices

1. **Track Progress**: Use "complete" action as you finish tasks
2. **Stay Organized**: Reorder tasks based on dependencies and priorities
3. **Be Specific**: Add clear, actionable task descriptions
4. **Document Changes**: Always provide a reason for modifications
5. **Regular Updates**: Show the list periodically to track progress

## Common Workflows

### Starting a Task
1. Show the current todo list
2. Identify the next task to work on
3. Begin implementation

### Discovering New Requirements
1. Add new tasks as you discover them
2. Reorder if they affect priorities
3. Document why they were added

### Completing Work
1. Mark tasks as complete when done
2. Remove tasks that are no longer relevant
3. Add follow-up tasks if needed

## Important Notes

- Task indices are 1-based (first task is index 1)
- Completed tasks remain in the list for visibility
- The tool maintains the todo list in the agent's state
- Changes are immediately reflected in the agent's context

## Error Handling

The tool will reject:
- Invalid actions
- Missing required parameters
- Out-of-range indices
- Meta-tasks (tasks about creating more tasks)
- Vague or non-actionable tasks
"""