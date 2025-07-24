#!/usr/bin/env python3
"""Manual e2e test for the persistent agent implementation."""
import os
import sys
import pytest
from dotenv import load_dotenv

load_dotenv()

pytestmark = pytest.mark.e2e


@pytest.mark.skip(reason="Manual e2e test - requires LLM API keys")
def test_persistent_agent():
    from katalyst.coding_agent.graph import build_coding_graph
    from katalyst.katalyst_core.utils.logger import get_logger
    
    logger = get_logger()
    
    # Try to use Anthropic if available
    if os.getenv("ANTHROPIC_API_KEY"):
        print("Using Anthropic provider...")
        os.environ["KATALYST_LLM_PROVIDER"] = "anthropic"
        os.environ["KATALYST_REASONING_MODEL"] = "claude-3-5-sonnet-20241022"
        os.environ["KATALYST_EXECUTION_MODEL"] = "claude-3-5-haiku-20241022"
    elif not os.getenv("OPENAI_API_KEY"):
        print("Error: No API keys found (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        sys.exit(1)
    
    print("Building graph...")
    graph = build_coding_graph()
    
    # Test directory
    test_dir = os.path.join(os.getcwd(), "test_outputs")
    os.makedirs(test_dir, exist_ok=True)
    
    # Simple test task
    test_input = {
        "task": "create a simple hello.py file that prints 'Hello from Katalyst!'",
        "auto_approve": True,
        "project_root_cwd": test_dir,
        "user_input_fn": lambda x: ""  # No user input needed
    }
    
    print(f"Running test task in {test_dir}...")
    try:
        result = graph.invoke(test_input)
        print("\n✅ Test completed successfully!")
        
        # Check if file was created
        hello_path = os.path.join(test_dir, "hello.py")
        if os.path.exists(hello_path):
            print(f"✅ File created: {hello_path}")
            with open(hello_path, 'r') as f:
                content = f.read()
                print(f"File contents:\n{content}")
        else:
            print("❌ hello.py was not created")
            
        # Print summary
        if result.get("response"):
            print(f"\nFinal response: {result['response']}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        logger.exception("Test failed")
        raise

if __name__ == "__main__":
    test_persistent_agent()