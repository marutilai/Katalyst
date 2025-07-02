"""
LiteLLM Chat Model Wrapper for LangChain

Provides a LangChain-compatible chat model that uses LiteLLM under the hood,
enabling support for 100+ LLM providers through a unified interface.
"""

from typing import Any, Dict, Iterator, List, Optional, Union, Tuple
import litellm
from litellm import completion, acompletion
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()


class ChatLiteLLM(BaseChatModel):
    """Chat model wrapper for LiteLLM.
    
    This wrapper allows using any LiteLLM-supported model with LangChain/LangGraph.
    Supports 100+ LLM providers including OpenAI, Anthropic, Google, Groq, Ollama, etc.
    
    Example:
        >>> from katalyst.katalyst_core.services import ChatLiteLLM
        >>> model = ChatLiteLLM(model="gpt-4", temperature=0)
        >>> response = model.invoke([HumanMessage(content="Hello!")])
    """
    
    # Model configuration
    model: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: Optional[Union[float, Tuple[float, float]]] = 60
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    
    # Additional LiteLLM parameters
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
    
    # Internal configuration
    streaming: bool = False
    verbose: bool = False
    
    @property
    def _llm_type(self) -> str:
        """Return type of language model."""
        return "litellm-chat"
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return a dictionary of identifying parameters."""
        params = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "streaming": self.streaming,
        }
        if self.api_base:
            params["api_base"] = self.api_base
        if self.top_p is not None:
            params["top_p"] = self.top_p
        return params
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to LiteLLM format."""
        litellm_messages = []
        
        for message in messages:
            if isinstance(message, SystemMessage):
                litellm_messages.append({
                    "role": "system",
                    "content": message.content
                })
            elif isinstance(message, HumanMessage):
                litellm_messages.append({
                    "role": "user", 
                    "content": message.content
                })
            elif isinstance(message, AIMessage):
                msg_dict = {
                    "role": "assistant",
                    "content": message.content or ""
                }
                # Handle tool calls if present
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.get("id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": str(tc.get("args", {}))
                            }
                        }
                        for i, tc in enumerate(message.tool_calls)
                    ]
                litellm_messages.append(msg_dict)
            elif isinstance(message, ToolMessage):
                litellm_messages.append({
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": getattr(message, 'tool_call_id', None)
                })
            else:
                # Fallback for other message types
                litellm_messages.append({
                    "role": "user",
                    "content": str(message.content)
                })
                
        return litellm_messages
    
    def _create_chat_result(self, response: Any) -> ChatResult:
        """Convert LiteLLM response to LangChain ChatResult."""
        generations = []
        
        for choice in response.choices:
            message_dict = choice.message.model_dump()
            content = message_dict.get('content', '')
            
            # Create AIMessage with content
            ai_message = AIMessage(content=content)
            
            # Add tool calls if present
            if 'tool_calls' in message_dict and message_dict['tool_calls']:
                ai_message.tool_calls = [
                    {
                        "id": tc.get("id", f"call_{i}"),
                        "name": tc["function"]["name"],
                        "args": tc["function"].get("arguments", {})
                    }
                    for i, tc in enumerate(message_dict['tool_calls'])
                ]
            
            generation = ChatGeneration(
                message=ai_message,
                generation_info={
                    "finish_reason": choice.finish_reason,
                    "index": choice.index
                }
            )
            generations.append(generation)
        
        # Add usage info if available
        llm_output = {}
        if hasattr(response, 'usage'):
            llm_output["usage"] = response.usage.model_dump()
        if hasattr(response, 'model'):
            llm_output["model"] = response.model
            
        return ChatResult(generations=generations, llm_output=llm_output)
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response using LiteLLM."""
        # Convert messages
        litellm_messages = self._convert_messages(messages)
        
        # Prepare parameters
        params = {
            "model": self.model,
            "messages": litellm_messages,
            "temperature": self.temperature,
            "stream": False,
            **kwargs
        }
        
        # Add optional parameters
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.timeout is not None:
            params["timeout"] = self.timeout
        if self.api_base is not None:
            params["api_base"] = self.api_base
        if self.api_key is not None:
            params["api_key"] = self.api_key
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            params["presence_penalty"] = self.presence_penalty
        if stop is not None:
            params["stop"] = stop
        elif self.stop is not None:
            params["stop"] = self.stop
            
        if self.verbose:
            logger.debug(f"[ChatLiteLLM] Calling {self.model} with {len(litellm_messages)} messages")
        
        try:
            # Call LiteLLM
            response = completion(**params)
            
            # Convert to ChatResult
            return self._create_chat_result(response)
            
        except Exception as e:
            logger.error(f"[ChatLiteLLM] Error calling {self.model}: {str(e)}")
            raise
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Stream the response."""
        # Convert messages
        litellm_messages = self._convert_messages(messages)
        
        # Prepare parameters (same as _generate but with stream=True)
        params = {
            "model": self.model,
            "messages": litellm_messages,
            "temperature": self.temperature,
            "stream": True,
            **kwargs
        }
        
        # Add optional parameters (same as _generate)
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.timeout is not None:
            params["timeout"] = self.timeout
        if self.api_base is not None:
            params["api_base"] = self.api_base
        if self.api_key is not None:
            params["api_key"] = self.api_key
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            params["presence_penalty"] = self.presence_penalty
        if stop is not None:
            params["stop"] = stop
        elif self.stop is not None:
            params["stop"] = self.stop
            
        if self.verbose:
            logger.debug(f"[ChatLiteLLM] Streaming from {self.model}")
        
        try:
            # Stream from LiteLLM
            response_stream = completion(**params)
            
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = AIMessageChunk(content=chunk.choices[0].delta.content)
                    yield ChatGenerationChunk(message=delta)
                    
                    if run_manager:
                        run_manager.on_llm_new_token(chunk.choices[0].delta.content)
                        
        except Exception as e:
            logger.error(f"[ChatLiteLLM] Error streaming from {self.model}: {str(e)}")
            raise
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate - uses LiteLLM's acompletion."""
        # Convert messages
        litellm_messages = self._convert_messages(messages)
        
        # Prepare parameters (same as sync version)
        params = {
            "model": self.model,
            "messages": litellm_messages,
            "temperature": self.temperature,
            "stream": False,
            **kwargs
        }
        
        # Add optional parameters
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.timeout is not None:
            params["timeout"] = self.timeout
        if self.api_base is not None:
            params["api_base"] = self.api_base
        if self.api_key is not None:
            params["api_key"] = self.api_key
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            params["presence_penalty"] = self.presence_penalty
        if stop is not None:
            params["stop"] = stop
        elif self.stop is not None:
            params["stop"] = self.stop
            
        if self.verbose:
            logger.debug(f"[ChatLiteLLM] Async calling {self.model}")
        
        try:
            # Call LiteLLM async
            response = await acompletion(**params)
            
            # Convert to ChatResult
            return self._create_chat_result(response)
            
        except Exception as e:
            logger.error(f"[ChatLiteLLM] Async error calling {self.model}: {str(e)}")
            raise