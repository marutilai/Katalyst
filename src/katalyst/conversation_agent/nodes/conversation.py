"""
Conversation Node - Handles greetings, clarifications, and off-topic requests.

This node:
1. Analyzes user input to determine intent
2. Generates appropriate responses
3. Helps users articulate their needs clearly
"""

from langchain_core.messages import AIMessage

from katalyst.katalyst_core.state import KatalystState
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.config import get_llm_config
from katalyst.katalyst_core.utils.langchain_models import get_langchain_chat_model


# Conversation prompt for analyzing and responding to user input
conversation_prompt = """You are Katalyst, a helpful AI assistant specialized in coding and data science tasks.

Analyze the user's input and provide an appropriate response based on these categories:

1. GREETING (hi, hello, hey, good morning, etc.)
   - Respond warmly and ask what they'd like help with
   - Mention your capabilities (coding and data science)

2. VAGUE REQUEST (help me, I need something, can you assist, etc.)
   - Ask for specific details about what they need
   - Provide examples of what you can help with

3. CAPABILITY QUESTION (what can you do, how do you work, etc.)
   - Explain your coding and data science capabilities
   - Give concrete examples of tasks you can handle

4. OFF-TOPIC REQUEST (non-coding/data science tasks)
   - Politely explain your specialization
   - Redirect to coding or data science if possible
   - Be helpful but clear about your scope

5. CLEAR TASK (already specific about coding or data science)
   - Acknowledge their request
   - Indicate readiness to help
   - DO NOT start working on it - just acknowledge

User input: {user_input}

Provide a natural, helpful response. Be concise but friendly. Your goal is to either:
- Help the user clarify what they need (for vague inputs)
- Guide them toward coding/data science tasks (for off-topic)
- Acknowledge clear requests (for specific tasks)

Remember: You're just having a conversation, not executing any tasks yet."""


def conversation(state: KatalystState) -> KatalystState:
    """
    Handle conversational inputs that need clarification or redirection.
    
    This node:
    - Responds to greetings
    - Asks for clarification on vague requests
    - Redirects off-topic requests
    - Acknowledges clear tasks
    """
    logger = get_logger("conversation_agent")
    logger.debug("[CONVERSATION] Starting conversation node...")
    
    # Get user input from the last message or task
    user_input = state.task
    if state.messages:
        # Check if there's a more recent human message
        for msg in reversed(state.messages):
            if hasattr(msg, 'type') and msg.type == 'human':
                user_input = msg.content
                break
    
    logger.debug(f"[CONVERSATION] Processing input: {user_input}")
    
    # Get configured model
    llm_config = get_llm_config()
    model_name = llm_config.get_model_for_component("planner")  # Use same model as planner
    provider = llm_config.get_provider()
    timeout = llm_config.get_timeout()
    api_base = llm_config.get_api_base()
    
    logger.debug(f"[CONVERSATION] Using model: {model_name} (provider: {provider})")
    
    # Get conversation model
    conversation_model = get_langchain_chat_model(
        model_name=model_name,
        provider=provider,
        temperature=0.7,  # Slightly higher temp for more natural conversation
        timeout=timeout,
        api_base=api_base
    )
    
    try:
        # Generate response
        prompt = conversation_prompt.format(user_input=user_input)
        response = conversation_model.invoke(prompt)
        
        # Add response to messages
        ai_message = AIMessage(content=response.content)
        state.messages.append(ai_message)
        
        logger.info(f"[CONVERSATION] Generated response: {response.content}")
        
    except Exception as e:
        error_msg = f"I encountered an error while processing your request: {str(e)}"
        logger.error(f"[CONVERSATION] Error: {e}")
        
        # Add error response
        ai_message = AIMessage(content=error_msg)
        state.messages.append(ai_message)
    
    logger.debug("[CONVERSATION] End of conversation node.")
    return state