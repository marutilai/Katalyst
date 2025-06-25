# Ollama Integration Guide for Katalyst

This guide explains how to use Ollama for local model inference with the Katalyst ReAct agent.

## Overview

Ollama integration allows you to run Katalyst entirely offline using local language models. This provides:
- **Privacy**: All processing happens locally, no data sent to external APIs
- **Cost Savings**: No API usage fees
- **Offline Operation**: Work without internet connectivity
- **Model Control**: Choose and customize models for your specific needs

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
ollama pull phi4           # Microsoft's compact model
ollama pull codestral      # Mistral's code model (22B)
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
export KATALYST_LITELLM_MODEL=ollama/qwen2.5-coder:7b

# Or use the interactive CLI
# Type: /model
# Choose from the available options
```

## Available Models

### Recommended Models

| Model | Size | Best For | Memory Required |
|-------|------|----------|-----------------|
| `qwen2.5-coder:7b` | 7B | General coding tasks, fast responses | 8GB RAM |
| `phi4` | 14B | Fast execution, good reasoning | 16GB RAM |
| `codestral` | 22B | Complex code generation | 24GB RAM |
| `devstral` | 24B | Agentic software engineering | 32GB RAM |

### Model Selection Guide

- **For most users**: Start with `qwen2.5-coder:7b` - it offers the best balance of performance and quality
- **For faster responses**: Use `phi4` for quicker but slightly less accurate results
- **For complex tasks**: Use `codestral` or `devstral` if you have sufficient RAM

## Configuration Options

### Environment Variables

```bash
# Provider configuration
export KATALYST_LITELLM_PROVIDER=ollama

# Model selection (use full ollama/ prefix)
export KATALYST_LITELLM_MODEL=ollama/qwen2.5-coder:7b

# Custom API endpoint (if not using default)
export KATALYST_LLM_API_BASE=http://localhost:11434

# Timeout for local inference (seconds)
export KATALYST_LITELLM_TIMEOUT=120
```

### Using Different Models for Different Tasks

Katalyst uses different models for reasoning vs execution tasks:

```bash
# High-quality reasoning (planning)
export KATALYST_REASONING_MODEL=ollama/devstral

# Fast execution (tool use)
export KATALYST_EXECUTION_MODEL=ollama/phi4

# Fallback model
export KATALYST_LLM_MODEL_FALLBACK=ollama/qwen2.5-coder:7b
```

## Benchmarking Models

To evaluate which model works best for your use case:

```bash
# Run the benchmark test (requires Ollama to be running)
SKIP_OLLAMA_BENCHMARK=false pytest tests/agent/test_ollama_model_benchmark.py::TestOllamaModelBenchmark::test_benchmark_ollama_models -v

# Results will be saved in the test output directory
```

Or run the quick smoke test:
```bash
pytest tests/agent/test_ollama_model_benchmark.py::test_ollama_integration_smoke_test -v
```

The benchmark evaluates:
- Response latency
- Output quality for coding tasks
- Memory usage
- Token generation speed

## Troubleshooting

### Common Issues

1. **"Ollama not accessible" error**
   - Ensure Ollama is running: `ollama serve`
   - Check if models are downloaded: `ollama list`

2. **Slow responses**
   - Use a smaller model (7B instead of 22B+)
   - Ensure you have sufficient RAM
   - Close other memory-intensive applications

3. **Model not found**
   - Pull the model first: `ollama pull model-name`
   - Use the full model name with `ollama/` prefix

4. **Connection refused**
   - Check if Ollama is running on the correct port
   - Set custom endpoint: `export KATALYST_LLM_API_BASE=http://localhost:11434`

### Performance Tips

1. **Model Loading**: First request to a model may be slow as it loads into memory
2. **Context Length**: Shorter contexts generally result in faster responses
3. **GPU Acceleration**: Ollama automatically uses GPU if available
4. **Memory Management**: Monitor RAM usage, especially with larger models

## Advanced Usage

### Custom Model Configuration

Create custom model variants with specific parameters:

```bash
# Create a custom model with different temperature
ollama create mymodel -f ./Modelfile
```

Example Modelfile:
```
FROM qwen2.5-coder:7b
PARAMETER temperature 0.1
PARAMETER top_p 0.9
SYSTEM You are an expert Python developer focused on clean, efficient code.
```

### Running Multiple Models

You can run different models for different components:

```python
# In your environment
export KATALYST_LITELLM_PROVIDER=ollama
export KATALYST_REASONING_MODEL=ollama/devstral
export KATALYST_EXECUTION_MODEL=ollama/phi4
```

## Integration Testing

To verify your Ollama setup:

```bash
# Test basic connectivity
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Hello"
}'

# Run Katalyst with a simple task
export KATALYST_LITELLM_PROVIDER=ollama
katalyst "Create a hello world Python script"
```

## Best Practices

1. **Start Small**: Begin with smaller models and upgrade if needed
2. **Monitor Resources**: Keep an eye on RAM and CPU usage
3. **Experiment**: Different models excel at different tasks
4. **Update Regularly**: Keep Ollama and models updated for improvements

## Limitations

- Local models may not match the capability of large cloud models
- Requires significant local compute resources
- First-time model loading can be slow
- Context windows may be smaller than cloud alternatives

## Security Benefits

Using Ollama provides enhanced security:
- No data leaves your machine
- Complete control over model behavior
- No API keys to manage or secure
- Suitable for sensitive codebases

---

For more information, visit the [Ollama documentation](https://github.com/ollama/ollama) or run `ollama --help`.