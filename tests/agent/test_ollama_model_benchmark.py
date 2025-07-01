"""
Agent tests for benchmarking Ollama models.

This module evaluates different Ollama models for the Katalyst ReAct agent on:
1. Latency (response time)
2. Memory footprint  
3. Reasoning accuracy for coding tasks
4. Token generation speed
"""

import os
import sys
import time
import json
import pytest
from typing import Dict, List, Any, Optional
from datetime import datetime
from litellm import completion
from pathlib import Path

from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()

# Models to benchmark
OLLAMA_MODELS = [
    "ollama/qwen2.5-coder:7b",
    "ollama/phi4", 
    "ollama/codestral",
    "ollama/devstral"
]

# Test prompts for different types of tasks
TEST_PROMPTS = {
    "simple_reasoning": {
        "messages": [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Write a Python function to calculate the factorial of a number."}
        ],
        "expected_quality": ["def", "factorial", "return", "if", "else"]
    },
    "code_analysis": {
        "messages": [
            {"role": "system", "content": "You are a code analysis expert."},
            {"role": "user", "content": """Analyze this Python code and identify any issues:
def process_data(items):
    result = []
    for i in range(len(items)):
        if items[i] > 0:
            result.append(items[i] * 2)
    return result
"""}
        ],
        "expected_quality": ["iterate", "enumerate", "pythonic", "list comprehension"]
    },
    "react_agent": {
        "messages": [
            {"role": "system", "content": "You are a ReAct agent. Think step by step."},
            {"role": "user", "content": """Task: Find all Python files in a project that import 'json' module.

Available tools:
- search_files(pattern: str) -> List[str]: Search for files matching pattern
- read_file(path: str) -> str: Read file contents
- grep(pattern: str, file: str) -> List[str]: Search for pattern in file

Think about your approach, then choose an action."""}
        ],
        "expected_quality": ["thought", "action", "search", "grep", "json"]
    }
}


class OllamaBenchmark:
    def __init__(self, api_base: str = "http://localhost:11434"):
        self.api_base = api_base
        self.results = {}
        
    def get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB using psutil if available."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)  # in MB
        except ImportError:
            logger.warning("psutil not installed, memory usage will not be reported.")
            return None
        
    def measure_quality(self, response: str, expected_keywords: List[str]) -> float:
        """Simple quality metric based on keyword presence."""
        response_lower = response.lower()
        found = sum(1 for keyword in expected_keywords if keyword in response_lower)
        return found / len(expected_keywords)
        
    def benchmark_model(self, model: str) -> Dict[str, Any]:
        """Benchmark a single model across all test prompts."""
        logger.info(f"Starting benchmark for {model}")
        model_results = {
            "model": model,
            "tests": {},
            "avg_latency": 0,
            "avg_quality": 0,
            "memory_delta": 0,
            "errors": []
        }
        
        initial_memory = self.get_memory_usage()
        total_latency = 0
        total_quality = 0
        test_count = 0
        
        for test_name, test_data in TEST_PROMPTS.items():
            logger.info(f"  Running test: {test_name}")
            try:
                # Measure latency
                start_time = time.time()
                response = completion(
                    model=model,
                    messages=test_data["messages"],
                    api_base=self.api_base,
                    temperature=0.1,
                    timeout=60
                )
                end_time = time.time()
                
                latency = end_time - start_time
                response_text = response.choices[0].message.content
                
                # Measure quality
                quality = self.measure_quality(response_text, test_data["expected_quality"])
                
                # Calculate tokens per second
                # Note: This is approximate as we don't have exact token counts from Ollama
                response_length = len(response_text.split())
                tokens_per_second = response_length / latency if latency > 0 else 0
                
                model_results["tests"][test_name] = {
                    "latency": latency,
                    "quality": quality,
                    "tokens_per_second": tokens_per_second,
                    "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text
                }
                
                total_latency += latency
                total_quality += quality
                test_count += 1
                
            except Exception as e:
                logger.error(f"  Error in test {test_name}: {e}")
                model_results["errors"].append({
                    "test": test_name,
                    "error": str(e)
                })
        
        # Calculate averages
        if test_count > 0:
            model_results["avg_latency"] = total_latency / test_count
            model_results["avg_quality"] = total_quality / test_count
        
        # Measure memory delta
        final_memory = self.get_memory_usage()
        model_results["memory_delta"] = final_memory - initial_memory
        
        return model_results
    
    def run_benchmark(self) -> Dict[str, Any]:
        """Run benchmark for all models."""
        logger.info("Starting Ollama model benchmarks")
        logger.info(f"API Base: {self.api_base}")
        
        # Check if Ollama is running
        try:
            completion(
                model="ollama/phi4",
                messages=[{"role": "user", "content": "test"}],
                api_base=self.api_base,
                timeout=10
            )
        except Exception as e:
            logger.error(f"Ollama not accessible at {self.api_base}: {e}")
            logger.error("Please ensure Ollama is running with: ollama serve")
            pytest.skip("Ollama not available")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "api_base": self.api_base,
            "models": {}
        }
        
        for model in OLLAMA_MODELS:
            try:
                # Pull model if not available
                logger.info(f"Ensuring {model} is available...")
                os.system(f"ollama pull {model.replace('ollama/', '')}")
                
                results["models"][model] = self.benchmark_model(model)
            except Exception as e:
                logger.error(f"Failed to benchmark {model}: {e}")
                results["models"][model] = {"error": str(e)}
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a markdown report from benchmark results."""
        report = f"""# Ollama Model Benchmark Report

Generated: {results['timestamp']}
API Base: {results['api_base']}

## Summary

| Model | Avg Latency (s) | Avg Quality | Memory Delta (MB) | Errors |
|-------|-----------------|-------------|-------------------|--------|
"""
        
        for model_name, model_data in results["models"].items():
            if "error" in model_data:
                report += f"| {model_name} | ERROR | ERROR | ERROR | {model_data['error']} |\n"
            else:
                avg_latency = f"{model_data['avg_latency']:.2f}"
                avg_quality = f"{model_data['avg_quality']:.2%}"
                memory_delta = f"{model_data['memory_delta']:.1f}"
                errors = len(model_data['errors'])
                report += f"| {model_name} | {avg_latency} | {avg_quality} | {memory_delta} | {errors} |\n"
        
        report += "\n## Detailed Results\n\n"
        
        for model_name, model_data in results["models"].items():
            if "error" in model_data:
                continue
                
            report += f"### {model_name}\n\n"
            
            for test_name, test_results in model_data.get("tests", {}).items():
                report += f"#### {test_name}\n"
                report += f"- Latency: {test_results['latency']:.2f}s\n"
                report += f"- Quality Score: {test_results['quality']:.2%}\n"
                report += f"- Tokens/sec: {test_results['tokens_per_second']:.1f}\n"
                report += f"- Response Preview: {test_results['response_preview']}\n\n"
            
            if model_data.get("errors"):
                report += f"#### Errors\n"
                for error in model_data["errors"]:
                    report += f"- {error['test']}: {error['error']}\n"
                report += "\n"
        
        report += """## Recommendations

Based on the benchmark results:

1. **Best Overall Performance**: Models with the best balance of latency and quality
2. **Fastest Response**: Models with lowest average latency
3. **Highest Quality**: Models with highest quality scores
4. **Most Efficient**: Models with lowest memory footprint

Consider your specific use case when choosing a model:
- For interactive coding assistance: Prioritize low latency
- For complex reasoning tasks: Prioritize quality
- For resource-constrained environments: Consider memory usage
"""
        
        return report


@pytest.mark.agent
@pytest.mark.skipif(
    os.getenv("SKIP_OLLAMA_BENCHMARK", "true").lower() == "true",
    reason="Ollama benchmark tests are expensive and disabled by default"
)
class TestOllamaModelBenchmark:
    """Test class for Ollama model benchmarks."""
    
    def test_benchmark_ollama_models(self, tmp_path):
        """Run comprehensive benchmark of Ollama models."""
        benchmark = OllamaBenchmark()
        results = benchmark.run_benchmark()
        
        # Save results
        results_file = tmp_path / "ollama_benchmark_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Generate report
        report = benchmark.generate_report(results)
        report_file = tmp_path / "ollama_benchmark_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        logger.info(f"Results saved to {results_file}")
        logger.info(f"Report saved to {report_file}")
        
        # Basic assertions
        assert len(results["models"]) > 0
        assert results["timestamp"]
        assert results["api_base"]
        
        # Check that at least one model was benchmarked successfully
        successful_models = [m for m, data in results["models"].items() if "error" not in data]
        assert len(successful_models) > 0, "At least one model should be benchmarked successfully"


@pytest.mark.agent  
def test_ollama_integration_smoke_test():
    """Quick smoke test to verify Ollama integration works."""
    # Save existing env vars
    saved_env = {}
    env_vars = ["KATALYST_LITELLM_PROVIDER", "KATALYST_REASONING_MODEL", 
                "KATALYST_EXECUTION_MODEL", "KATALYST_LLM_MODEL_FALLBACK"]
    for var in env_vars:
        if var in os.environ:
            saved_env[var] = os.environ[var]
            del os.environ[var]
    
    try:
        # Set Ollama provider
        os.environ["KATALYST_LITELLM_PROVIDER"] = "ollama"
        
        from katalyst.katalyst_core.config import get_llm_config, reset_config
        from katalyst.katalyst_core.services.llms import get_llm_params
        
        reset_config()
        config = get_llm_config()
        
        # Verify configuration
        assert config.get_provider() == "ollama"
        assert config.get_api_base() == "http://localhost:11434"
        
        # Get params for a component
        params = get_llm_params("planner")
        assert params["model"].startswith("ollama/")
        assert params["api_base"] == "http://localhost:11434"
        
        logger.info("✅ Ollama integration configured correctly")
        
    except Exception as e:
        pytest.fail(f"Ollama integration smoke test failed: {e}")
    finally:
        # Restore env vars
        if "KATALYST_LITELLM_PROVIDER" in os.environ:
            del os.environ["KATALYST_LITELLM_PROVIDER"]
        for var, value in saved_env.items():
            os.environ[var] = value
        reset_config()