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


# Conversation prompt for the ReAct agent with examples to guide tool usage
conversation_prompt = """You are Katalyst, an AI assistant specialized in code analysis and consultation.

You have access to read-only tools (read, grep, glob, ls, list_code_definitions) to explore codebases. Use them when you need to examine actual code or verify facts about the codebase.

EXAMPLES OF WHEN TO USE TOOLS:

Example 1 - Greeting (NO TOOLS):
User: "Hello!"
You: "Hello! I'm Katalyst, your code analysis assistant. I can help you understand your codebase, analyze patterns, and provide recommendations. What would you like to explore?"

Example 2 - Code analysis (USE TOOLS):
User: "What logging framework is being used?"
You: "Let me examine the codebase to identify the logging framework."
[Use grep to search for logging imports, read relevant files]
"Based on my analysis, the project uses..."

Example 3 - Architecture question (USE TOOLS):
User: "How is authentication handled?"
You: "I'll explore the authentication implementation for you."
[Use ls to find auth-related files, read key modules, grep for auth patterns]
"After examining the auth module in auth.py and middleware in..."

Example 4 - General knowledge (NO TOOLS):
User: "What is dependency injection?"
You: "Dependency injection is a design pattern where..."

Example 5 - Specific implementation check (USE TOOLS):
User: "Are we using dependency injection?"
You: "Let me check how dependencies are managed in your code."
[Use grep to find DI patterns, read relevant files]
"After analyzing your codebase, I found..."

Example 6 - Consultation with analysis (USE TOOLS):
User: "Should we add caching?"
You: "Let me first understand your current architecture to provide an informed recommendation."
[Use tools to explore current setup, identify bottlenecks]
"Based on my analysis of your current implementation..."

Example 7 - Implementation request (NO TOOLS for implementation):
User: "Add Redis caching to the API"
You: "I can analyze your current setup and provide recommendations for adding Redis caching, but I cannot modify code. To implement changes, please explicitly request 'implement Redis caching' and the coding agent will handle it. Would you like me to analyze your current architecture first?"

KEY PRINCIPLES:
- Use tools when you need to examine actual code or verify facts about THIS codebase
- Don't use tools for general knowledge, greetings, or clarifications
- Always use tools when asked about "our code", "this project", "the codebase", etc.
- Be specific and cite actual files and line numbers when you examine code
- If asked to implement/create/write/modify, explain you can only analyze and suggest

Current task: {input}

Think step-by-step: Do I need to examine the actual codebase to answer this, or can I respond with general knowledge?

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
        
        # Create ReAct agent with tools always available
        # The prompt will guide when to use them
        agent = create_react_agent(
            model,
            tools,
            prompt=conversation_prompt,
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
        
        logger.info(f"[CONVERSATION] Response generated ({len(response_content)} chars)")
        
    except Exception as e:
        error_msg = f"I encountered an error while processing your request: {str(e)}"
        logger.error(f"[CONVERSATION] Error: {e}")
        
        # Add error response
        ai_message = AIMessage(content=error_msg)
        state.messages.append(ai_message)
    
    logger.debug("[CONVERSATION] Conversation agent complete")
    return state