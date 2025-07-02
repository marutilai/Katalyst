# Using Katalyst with Ollama

Katalyst has native support for Ollama through LangChain integration, allowing you to run powerful coding agents locally.

## Setup

1. Install Ollama from https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull qwen2.5-coder:7b  # Recommended for coding tasks
   # or
   ollama pull codestral          # Alternative coding model
   ```

3. Set the provider to ollama:
   ```bash
   export KATALYST_LITELLM_PROVIDER=ollama
   ```

## Running Katalyst with Ollama

```bash
# Start Katalyst
katalyst

# In the REPL, you can also switch provider:
> /provider
# Select ollama

# Or set a specific model:
> /model
# Enter: qwen2.5-coder:7b
```

## Default Ollama Models

- **Reasoning tasks** (planner, replanner): `qwen2.5-coder:7b`
- **Execution tasks** (agent_react): `phi4`
- **Fallback**: `codestral`

## Benefits of Native Integration

1. **Better compatibility** - Works seamlessly with LangGraph's create_react_agent
2. **No wrapper overhead** - Direct integration with LangChain
3. **Full tool support** - All tools work properly with function calling
4. **Local execution** - Keep your code and data private

## Supported Providers

Katalyst now supports these providers natively:
- OpenAI (`langchain-openai`)
- Anthropic (`langchain-anthropic`) 
- Ollama (`langchain-ollama`)
- Groq (install `langchain-groq`)
- Together (install `langchain-together`)

Each provider uses native LangChain integration for optimal performance and compatibility.