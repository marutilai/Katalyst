#!/usr/bin/env python
"""
Test script for the enhanced conversation agent.
Tests various scenarios to ensure proper routing and tool usage.
"""

import os
import sys
from katalyst.katalyst_core.state import KatalystState
from katalyst.conversation_agent.nodes.conversation import conversation
from katalyst.katalyst_core.config import set_llm_config, LLMConfig

def test_conversation_scenarios():
    """Test different types of inputs to the conversation agent."""
    
    # Set up configuration (use mock/test mode if available)
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  No OPENAI_API_KEY found, skipping live tests")
        return
    
    print("Testing Conversation Agent Scenarios\n" + "="*50)
    
    # Test scenarios
    test_cases = [
        {
            "name": "Simple Greeting",
            "input": "Hello!",
            "expects_tools": False,
            "description": "Should respond without using tools"
        },
        {
            "name": "Code Analysis Question",
            "input": "What logging libraries are used in this codebase?",
            "expects_tools": True,
            "description": "Should use grep/read tools to find logging usage"
        },
        {
            "name": "Architecture Question",
            "input": "How is the state management handled in this project?",
            "expects_tools": True,
            "description": "Should explore code to understand state architecture"
        },
        {
            "name": "Consultation Request",
            "input": "Should we add Redis caching to improve performance?",
            "expects_tools": True,
            "description": "Should analyze current setup and provide recommendations"
        },
        {
            "name": "Implementation Request",
            "input": "Implement a new caching layer",
            "expects_tools": False,
            "description": "Should explain that implementation requires explicit request"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📝 Test: {test_case['name']}")
        print(f"   Input: {test_case['input']}")
        print(f"   {test_case['description']}")
        
        # Create a fresh state for each test
        state = KatalystState(
            task=test_case["input"],
            messages=[],
            project_root_cwd=os.getcwd()
        )
        
        try:
            # Run the conversation agent
            result_state = conversation(state)
            
            # Check if response was added
            if result_state.messages:
                response = result_state.messages[-1].content
                print(f"   ✓ Response generated ({len(response)} chars)")
                print(f"   Response preview: {response[:150]}...")
            else:
                print(f"   ✗ No response generated")
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "="*50)
    print("Test scenarios complete!")

if __name__ == "__main__":
    # Note: This requires an active OpenAI API key to run live tests
    # In production, you'd want to use mocked tests instead
    test_conversation_scenarios()