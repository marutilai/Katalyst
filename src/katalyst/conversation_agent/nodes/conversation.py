"""
Conversation Node - ReAct agent for analysis and consultation.

This node:
1. Handles greetings and simple interactions
2. Analyzes code using read-only tools
3. Provides recommendations without making changes
4. Guides users to request implementation explicitly
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_litellm_client
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, create_tools_with_context
from katalyst.katalyst_core.utils.checkpointer_manager import checkpointer_manager
from katalyst.coding_agent.nodes.summarizer import get_summarization_node
from katalyst.conversation_agent.prompts.system_capabilities import get_system_capabilities


# Conversation prompt for the ReAct agent with examples to guide tool usage
conversation_prompt = """You are Katalyst, an AI assistant for general chat, code analysis, and technical consultation.

Tools: read, grep, glob, ls, list_code_definitions (read-only access)
Use tools ONLY when examining THIS codebase. Not for general knowledge or chat.

WHEN TO USE TOOLS:
✓ "What logging framework is used?" → grep imports, read files
✓ "How is auth handled?" → ls auth files, read implementation
✓ "Are we using DI?" → grep patterns, analyze code
✓ "Should we add caching?" → analyze current setup first

WHEN NOT TO USE TOOLS:
✗ "Hello" → Just greet back
✗ "What is DI?" → General explanation
✗ "What can you do?" → Use self-knowledge
✗ "Add caching" → Explain you analyze only, suggest coding agent

KEY RULES:
- Capability questions → Use your system knowledge
- Implementation requests → Direct to coding agent  
- "Our code/this project" → Always use tools
- General questions → No tools needed
- Cite specific files/lines when analyzing

Current task: {input}

Decision: Do I need to examine actual code, or can I use general knowledge?

{agent_scratchpad}"""


def conversation(state: KatalystState) -> KatalystState:
    """
    ReAct conversation agent that can analyze code and answer questions.
    
    Always has access to read-only tools, but the LLM decides when to use them
    based on the prompt examples and context.
    """
    logger = get_logger("conversation_agent")
    logger.debug("[CONVERSATION] Starting conversation ReAct agent...")
    
    # Get user input
    user_input = state.task
    if state.messages:
        # Check for more recent human message
        for msg in reversed(state.messages):
            if isinstance(msg, HumanMessage):
                user_input = msg.content
                break
    
    logger.debug(f"[CONVERSATION] Processing: {user_input[:100]}...")
    
    # Get LLM configuration
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[CONVERSATION] Using model: {model_name} (provider: {provider})")
    
    # Get LLM model
    model = get_litellm_client(
        model_name=model_name,
        provider=provider,
        timeout=timeout,
        api_base=api_base
    )
    
    try:
        logger.info("[CONVERSATION] Creating ReAct agent with read-only tools")
        
        # Get conversation tools (read-only) - always available
        tool_functions = get_tool_functions_map(category="conversation")
        tools = create_tools_with_context(tool_functions, "CONVERSATION", state)
        
        logger.debug(f"[CONVERSATION] Available tools: {list(tool_functions.keys())}")
        
        # Get summarization node for pre_model_hook
        summarize_messages = get_summarization_node()
        
        # Include system capabilities in the prompt for self-awareness
        full_prompt = conversation_prompt + "\n\n" + get_system_capabilities()
        
        # Create ReAct agent with tools always available
        # The prompt will guide when to use them
        agent = create_react_agent(
            model,
            tools,
            prompt=full_prompt,
            checkpointer=checkpointer_manager.get_checkpointer(),
            pre_model_hook=summarize_messages  # Enable conversation summarization
        )
        
        # Prepare input with context
        agent_input = {
            "input": user_input,
            "messages": state.messages[-10:] if state.messages else []  # Include recent context
        }
        
        # Execute agent - it will decide whether to use tools based on the prompt
        result = agent.invoke(agent_input)
        
        # Extract response
        if "messages" in result:
            # Get the last AI message from the result
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage):
                    response_content = msg.content
                    break
            else:
                response_content = "I've analyzed the request but couldn't generate a response."
        else:
            response_content = result.get("output", "Analysis complete.")
        
        # Log files that were examined (for context sharing)
        tools_used = False
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tools_used = True
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get('name', 'unknown')
                        if tool_name == 'read':
                            path = tool_call.get('args', {}).get('path')
                            logger.debug(f"[CONVERSATION] Read file: {path}")
                        else:
                            logger.debug(f"[CONVERSATION] Used tool: {tool_name}")
        
        if tools_used:
            logger.info("[CONVERSATION] Agent used tools for analysis")
        else:
            logger.info("[CONVERSATION] Agent responded without using tools")
        
        # Add response to state messages
        ai_message = AIMessage(content=response_content)
        state.messages.append(ai_message)
        
        # Store response in state for display
        state.response = response_content
        
        logger.info(f"[CONVERSATION] Response generated ({len(response_content)} chars)")
        
    except Exception as e:
        error_msg = f"I encountered an error while processing your request: {str(e)}"
        logger.error(f"[CONVERSATION] Error: {e}")
        
        # Add error response
        ai_message = AIMessage(content=error_msg)
        state.messages.append(ai_message)
        
        # Store error response in state for display
        state.response = error_msg
    
    logger.debug("[CONVERSATION] Conversation agent complete")
    return state