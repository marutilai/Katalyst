"""
Minimal React agent using LangGraph's default create_react_agent.
Uses custom ChatLiteLLM wrapper to support 100+ LLM providers through LiteLLM.

Supports all providers configured in the LLM config system:
- OpenAI (gpt-4, gpt-3.5-turbo, etc.)
- Anthropic (claude-3-opus, claude-3-haiku, etc.)
- Google (gemini-1.5-pro, gemini-1.5-flash, etc.)
- Groq (mixtral-8x7b, llama3-8b, etc.)
- Ollama (local models)
- And many more through LiteLLM
"""

from langgraph.prebuilt import create_react_agent
from katalyst.katalyst_core.services.litellm_chat_model import ChatLiteLLM
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain_core.agents import AgentAction, AgentFinish
from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import get_tool_functions_map, extract_tool_descriptions
from katalyst.katalyst_core.config import get_llm_config


def agent_react(state: KatalystState) -> KatalystState:
    """
    React agent using LangGraph's default create_react_agent.
    Supports all LiteLLM providers through the ChatLiteLLM wrapper.
    """
    logger = get_logger()
    logger.debug("[AGENT_REACT] Starting LangGraph default React agent with LiteLLM")
    
    # Get current task
    current_task = state.task_queue[state.task_idx] if state.task_queue else None
    if not current_task:
        logger.error("[AGENT_REACT] No current task available")
        state.error_message = "No task available for execution"
        return state
    
    # Get configured model from LLM config
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("agent_react")
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[AGENT_REACT] Using model: {model_name} (provider: {llm_config.get_provider()})")
    
    try:
        # Create ChatLiteLLM instance with configured model
        model = ChatLiteLLM(
            model=model_name,
            temperature=0,
            timeout=timeout,
            api_base=api_base,
            verbose=False  # Set to True for debugging
        )
    except Exception as e:
        logger.error(f"[AGENT_REACT] Failed to create ChatLiteLLM model: {e}")
        state.error_message = f"Failed to initialize model: {str(e)}"
        return state
    
    # Get tools and convert to LangChain format with descriptions from prompt files
    tool_functions = get_tool_functions_map()
    tool_descriptions_map = dict(extract_tool_descriptions())
    tools = []
    
    for tool_name, tool_func in tool_functions.items():
        # Get description from prompt file
        description = tool_descriptions_map.get(tool_name, f"Tool: {tool_name}")
        structured_tool = StructuredTool.from_function(
            func=tool_func,
            name=tool_name,
            description=description
        )
        tools.append(structured_tool)
    
    # Create the agent with LangGraph defaults
    agent = create_react_agent(
        model=model,
        tools=tools
    )
    
    # Build messages - just the current task with completion criteria
    # LangGraph handles its own message history internally
    task_instruction = f"""Task: {current_task}

IMPORTANT: To complete this task, you must actually implement it by creating/modifying files. 
A task is only complete when the code is written and functional, not when you've described what to do or asked questions.
If you need to make assumptions, make reasonable ones and proceed with implementation."""
    
    messages = [HumanMessage(content=task_instruction)]
    
    try:
        # Invoke the agent
        logger.debug(f"[AGENT_REACT] Invoking LangGraph agent for task: {current_task}")
        result = agent.invoke({"messages": messages})
        
        # Extract the last AI message
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if not ai_messages:
            state.error_message = "No AI response from agent"
            return state
            
        last_ai_message = ai_messages[-1]
        
        # Check if the agent wants to use tools
        if hasattr(last_ai_message, 'tool_calls') and last_ai_message.tool_calls:
            # Extract the first tool call
            tool_call = last_ai_message.tool_calls[0]
            
            state.agent_outcome = AgentAction(
                tool=tool_call["name"],
                tool_input=tool_call["args"],
                log=last_ai_message.content or ""
            )
            logger.info(f"[AGENT_REACT] Tool call: {tool_call['name']}")
            
        else:
            # No tool calls, agent is done with the task
            state.agent_outcome = AgentFinish(
                return_values={"output": last_ai_message.content},
                log=""
            )
            logger.info(f"[AGENT_REACT] Task completed")
            
    except Exception as e:
        logger.error(f"[AGENT_REACT] Error: {str(e)}")
        state.error_message = f"Agent error: {str(e)}"
    
    return state