#!/usr/bin/env python3
"""Test the action trace compression in state."""

from katalyst.katalyst_core.state import KatalystState
from langchain_core.agents import AgentAction
import json

# Create a mock state
state = KatalystState(
    project_root_cwd="/test",
    task="Test task",
    task_queue=["Test task"],
    original_plan=["Test task"]
)

# Add many actions to the trace
for i in range(15):
    action = AgentAction(
        tool=f"read_file",
        tool_input={"path": f"/file{i}.py"},
        log=f"Reading file {i}"
    )
    
    # Simulate a large observation (that would normally be processed)
    observation = json.dumps({
        "path": f"/file{i}.py",
        "content_ref": f"/file{i}.py",
        "content_summary": "1000 chars, 50 lines",
        "success": True
    }, indent=2)
    
    state.action_trace.append((action, observation))

print(f"Action trace has {len(state.action_trace)} entries")

# Calculate total size
total_size = sum(len(str(action)) + len(obs) for action, obs in state.action_trace)
print(f"Total action trace size: {total_size} chars")

# Show first and last entries
if state.action_trace:
    print(f"\nFirst entry tool: {state.action_trace[0][0].tool}")
    print(f"Last entry tool: {state.action_trace[-1][0].tool}")