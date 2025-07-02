#!/usr/bin/env python3
"""Test script to verify observation processing reduces scratchpad size."""

import json
from katalyst.coding_agent.nodes._tool_runner import _process_observation_for_trace

# Simulate a large read_file observation
large_file_content = """
def example_function():
    # This is a large file with lots of content
    for i in range(100):
        print(f"Line {i}")
""" * 100  # Make it large

read_file_obs = {
    "path": "/path/to/large_file.py",
    "start_line": 1,
    "end_line": 500,
    "content": large_file_content,
    "content_ref": "/path/to/large_file.py",
    "success": True
}

# Test processing
original = json.dumps(read_file_obs, indent=2)
processed = _process_observation_for_trace(original, "read_file")

print(f"Original observation size: {len(original)} chars")
print(f"Processed observation size: {len(processed)} chars")
print(f"Size reduction: {(1 - len(processed)/len(original))*100:.1f}%")
print("\nProcessed observation (first 500 chars):")
print(processed[:500])

# Test write_to_file with large content
write_obs = {
    "path": "/path/to/output.py",
    "content": "x" * 1000,
    "success": True,
    "created": True
}

original_write = json.dumps(write_obs, indent=2)
processed_write = _process_observation_for_trace(original_write, "write_to_file")

print(f"\n\nWrite observation original: {len(original_write)} chars")
print(f"Write observation processed: {len(processed_write)} chars")
print(f"Size reduction: {(1 - len(processed_write)/len(original_write))*100:.1f}%")