#!/usr/bin/env python3
"""
Analyze and display prompt sizes for all tools and system prompts across different nodes.
This helps understand the context usage breakdown in the Katalyst agent.
"""

import os
import sys
import importlib
from typing import Dict, List, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from katalyst.katalyst_core.utils.tools import get_tool_functions_map


def get_tool_prompt_sizes() -> List[Tuple[str, int]]:
    """Get sizes of all tool prompts."""
    tool_functions = get_tool_functions_map()
    tool_sizes = []
    
    for tool_name, func in tool_functions.items():
        prompt_module = getattr(func, '_prompt_module', tool_name)
        prompt_var = getattr(func, '_prompt_var', f'{tool_name.upper()}_PROMPT')
        try:
            module_path = f'katalyst.coding_agent.prompts.tools.{prompt_module}'
            module = importlib.import_module(module_path)
            prompt_str = getattr(module, prompt_var, '')
            if prompt_str:
                tool_sizes.append((tool_name, len(prompt_str)))
        except Exception as e:
            print(f"Warning: Could not load prompt for {tool_name}: {e}")
    
    return sorted(tool_sizes, key=lambda x: x[1], reverse=True)


def extract_system_prompt_from_node(file_path: str, node_name: str) -> int:
    """Extract system prompt size from a node file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for system message content
        if 'system_message_content = """' in content:
            start = content.find('system_message_content = """') + len('system_message_content = """')
            end = content.find('"""', start)
            if end > start:
                system_prompt = content[start:end]
                return len(system_prompt)
        
        # Also check for prompt = """ pattern (used in planner/replanner)
        if 'prompt = f"""' in content:
            start = content.find('prompt = f"""') + len('prompt = f"""')
            end = content.find('"""', start)
            if end > start:
                # This is a rough estimate as f-strings have substitutions
                system_prompt = content[start:end]
                return len(system_prompt)
                
    except Exception as e:
        print(f"Error reading {node_name}: {e}")
    
    return 0


def format_size(size: int) -> str:
    """Format size with thousands separator."""
    return f"{size:,}"


def print_separator():
    """Print a separator line."""
    print("-" * 60)


def main():
    print("=" * 60)
    print("KATALYST PROMPT SIZE ANALYSIS")
    print("=" * 60)
    print()
    
    # Analyze tool prompts
    print("TOOL PROMPTS")
    print_separator()
    tool_sizes = get_tool_prompt_sizes()
    total_tool_size = 0
    
    for tool_name, size in tool_sizes:
        print(f"{tool_name:<35} {format_size(size):>10} chars")
        total_tool_size += size
    
    print_separator()
    print(f"{'TOTAL TOOL PROMPTS':<35} {format_size(total_tool_size):>10} chars")
    print(f"{'Number of tools':<35} {len(tool_sizes):>10}")
    print()
    
    # Analyze node system prompts
    print("NODE SYSTEM PROMPTS")
    print_separator()
    
    nodes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                            'src/katalyst/coding_agent/nodes')
    
    node_files = {
        'executor': 'executor.py',
        'planner': 'planner.py',
        'replanner': 'replanner.py',
        'human_plan_verification': 'human_plan_verification.py'
    }
    
    node_sizes = []
    for node_name, file_name in node_files.items():
        file_path = os.path.join(nodes_dir, file_name)
        size = extract_system_prompt_from_node(file_path, node_name)
        if size > 0:
            node_sizes.append((node_name, size))
    
    # Sort by size
    node_sizes.sort(key=lambda x: x[1], reverse=True)
    total_node_size = 0
    
    for node_name, size in node_sizes:
        print(f"{node_name:<35} {format_size(size):>10} chars")
        total_node_size += size
    
    print_separator()
    print(f"{'TOTAL NODE PROMPTS':<35} {format_size(total_node_size):>10} chars")
    print()
    
    # Special analysis for executor
    print("EXECUTOR BREAKDOWN")
    print_separator()
    
    # Get base prompt size (without tools)
    executor_path = os.path.join(nodes_dir, 'executor.py')
    base_size = extract_system_prompt_from_node(executor_path, 'executor')
    
    print(f"{'Base instructions':<35} {format_size(base_size):>10} chars")
    print(f"{'Tool descriptions':<35} {format_size(total_tool_size):>10} chars")
    print(f"{'Total (base + tools)':<35} {format_size(base_size + total_tool_size):>10} chars")
    print()
    
    # Percentage breakdown
    if base_size + total_tool_size > 0:
        base_pct = (base_size / (base_size + total_tool_size)) * 100
        tools_pct = (total_tool_size / (base_size + total_tool_size)) * 100
        print(f"{'Base instructions %':<35} {base_pct:>9.1f}%")
        print(f"{'Tool descriptions %':<35} {tools_pct:>9.1f}%")
    
    print()
    print("SUMMARY")
    print_separator()
    print(f"The executor node has the largest prompt at ~{format_size(base_size + total_tool_size)} chars")
    print(f"Tool descriptions account for {tools_pct:.1f}% of the executor prompt")
    print(f"This leaves limited space for task context and conversation history")
    

if __name__ == "__main__":
    main()