# Ollama Integration Guide for Katalyst

This comprehensive guide explains how to use Ollama for local model inference with the Katalyst coding agent.

## Overview

Ollama integration allows you to run Katalyst entirely offline using local language models. This provides:
- **Privacy**: All processing happens locally, no data sent to external APIs
- **Cost Savings**: No API usage fees
- **Offline Operation**: Work without internet connectivity
- **Model Control**: Choose and customize models for your specific needs
- **Better Compatibility**: Native LangChain integration for optimal performance

## Prerequisites

1. **Install Ollama**: Download from [ollama.ai](https://ollama.ai)
2. **Start Ollama Server**: Run `ollama serve` (usually starts automatically)
3. **Pull Models**: Download the models you want to use

## Quick Start

### 1. Pull Recommended Models

```bash
# Recommended for coding tasks (7B model, fast and efficient)
ollama pull qwen2.5-coder:7b

# Alternative models
ollama pull phi4           # Microsoft's compact model (fast execution)
ollama pull codestral      # Mistral's code model (22B, robust)
ollama pull devstral       # Agentic model for software tasks (24B)
```

### 2. Configure Katalyst

Set the provider to Ollama:

```bash
# Using environment variable
export KATALYST_LITELLM_PROVIDER=ollama

# Or use the interactive CLI
katalyst
# Then type: /provider
# Select option 3 for Ollama
```

### 3. Select a Model

```bash
# Using environment variable
export KATALYST_REASONING_MODEL=ollama/qwen2.5-coder:7b
export KATALYST_EXECUTION_MODEL=ollama/phi4

# Or use the CLI
katalyst
# Type: /model
# Enter your desired model (e.g., qwen2.5-coder:7b)
```

### 4. Run Katalyst

```bash
katalyst
# Now you can use Katalyst with local models!
```

## Default Model Configuration

Katalyst uses different models for different components:

- **Reasoning tasks** (planner, replanner): `ollama/qwen2.5-coder:7b`
- **Execution tasks** (agent_react): `ollama/phi4`
- **Fallback model**: `ollama/codestral`

These defaults are optimized for a balance of quality and performance.

## Model Selection Guide

### For Best Coding Performance
- **QwenCoder 2.5 (7B)**: Best overall for coding tasks
- **CodeStral (22B)**: Higher quality but slower
- **DevStral (24B)**: Optimized for agentic workflows

### For Fast Execution
- **Phi-4**: Microsoft's efficient model
- **QwenCoder 2.5 (7B)**: Good balance of speed and quality

### For Limited Resources
- **Phi-4**: Smallest memory footprint
- **QwenCoder 2.5 (7B)**: Reasonable memory usage

## Advanced Configuration

### Custom API Base
If Ollama is running on a different host or port:

```bash
export KATALYST_LLM_API_BASE=http://192.168.1.100:11434
```

### Timeout Configuration
For slower hardware or larger models:

```bash
export KATALYST_LITELLM_TIMEOUT=120  # 2 minutes
```

### Using Multiple Models
You can configure different models for different tasks:

```bash
# Use larger model for planning
export KATALYST_REASONING_MODEL=ollama/codestral

# Use faster model for execution
export KATALYST_EXECUTION_MODEL=ollama/phi4
```

## Benchmarking Models

To evaluate which model works best for your use case:

```bash
# Run the benchmark test (requires Ollama to be running)
SKIP_OLLAMA_BENCHMARK=false pytest tests/e2e/test_ollama_model_benchmark.py::TestOllamaModelBenchmark::test_benchmark_ollama_models -v

# Or run the quick smoke test:
pytest tests/e2e/test_ollama_model_benchmark.py::test_ollama_integration_smoke_test -v
```

The benchmark evaluates:
- Response latency
- Quality for coding tasks
- Memory usage
- Token generation speed

Results are saved as a JSON report with detailed metrics.

## Benefits of Native Integration

1. **Better compatibility** - Works seamlessly with LangGraph's create_react_agent
2. **No wrapper overhead** - Direct integration with LangChain
3. **Full tool support** - All tools work properly with function calling
4. **Local execution** - Keep your code and data private

## Troubleshooting

### "Connection refused" error
- Ensure Ollama is running: `ollama serve`
- Check if Ollama is listening: `curl http://localhost:11434`

### Model not found
- Pull the model first: `ollama pull <model-name>`
- List available models: `ollama list`

### Slow performance
- Try a smaller model (e.g., phi4 instead of codestral)
- Increase timeout: `export KATALYST_LITELLM_TIMEOUT=180`
- Check system resources (RAM, CPU usage)

### Function calling issues
- Ensure you're using a model that supports function calling
- QwenCoder and Phi-4 have good function calling support

## Security Benefits

Using Ollama provides enhanced security:
- **No API Keys**: No risk of credential exposure
- **Data Privacy**: Code never leaves your machine
- **Air-gapped Operation**: Can work in isolated environments
- **Compliance**: Meets strict data residency requirements

## Supported Providers

Katalyst supports these providers natively through LangChain:
- OpenAI (`langchain-openai`)
- Anthropic (`langchain-anthropic`) 
- Ollama (`langchain-ollama`)
- Groq (install `langchain-groq`)
- Together (install `langchain-together`)

Each provider uses native LangChain integration for optimal performance and compatibility.

## What Was Implemented

### Technical Details
1. **Provider Configuration**: Added `ollama` provider profile with recommended models
2. **API Base Support**: Added support for custom Ollama endpoints
3. **CLI Integration**: Updated `/provider` and `/model` commands
4. **Testing Infrastructure**: Comprehensive unit and integration tests
5. **Benchmarking Tool**: Model evaluation script for performance comparison

### Configuration Details
- Timeout: 60 seconds (configurable)
- Default API base: `http://localhost:11434`
- Environment variables: Full support for all Katalyst configuration options

## Next Steps

1. **Try different models** to find the best fit for your use case
2. **Run benchmarks** to compare performance on your hardware
3. **Fine-tune models** with Ollama's customization features
4. **Report issues** if you encounter any problems

Happy coding with local models! 🚀