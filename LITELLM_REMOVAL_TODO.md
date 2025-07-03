# LiteLLM Removal TODO

During the refactor to remove LiteLLM dependency (commit 6796cc1), some files were not fully updated and still reference the old LiteLLM-based services.

## Files that need updating:

1. **src/katalyst/katalyst_core/services/llms.py**
   - Still imports litellm
   - Needs to be removed or refactored to use LangChain models

2. **Files importing from llms.py:**
   - src/katalyst/coding_agent/tools/generate_directory_overview.py
   - src/katalyst/coding_agent/nodes/_replanner.py
   - src/katalyst/coding_agent/nodes/_planner.py
   - src/katalyst/coding_agent/nodes/_agent_react.py
   - src/katalyst/katalyst_core/utils/conversation_summarizer.py
   - src/katalyst/katalyst_core/utils/action_trace_summarizer.py

## Current Impact:
- Warning when loading tools: "Could not import module katalyst.coding_agent.tools.generate_directory_overview. Error: No module named 'litellm'"
- The generate_directory_overview tool is not available

## Solution:
These files need to be updated to use the new pattern with `get_langchain_chat_model` from `katalyst.katalyst_core.utils.langchain_models` instead of the old LiteLLM-based approach.