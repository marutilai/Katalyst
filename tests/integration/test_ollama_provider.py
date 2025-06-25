"""Integration tests for Ollama provider configuration."""

import os
import pytest
from unittest.mock import patch, MagicMock
from katalyst.katalyst_core.config import get_llm_config, reset_config
from katalyst.katalyst_core.services.llms import get_llm_client, get_llm_params


@pytest.fixture(autouse=True)
def reset_config_fixture():
    """Reset config before and after each test."""
    reset_config()
    yield
    reset_config()


class TestOllamaProvider:
    """Test Ollama provider integration."""
    
    def test_ollama_provider_profile(self):
        """Test that Ollama provider profile is properly configured."""
        # Clear existing env vars that might override our test
        env_vars = {
            "KATALYST_LITELLM_PROVIDER": "ollama",
            "KATALYST_REASONING_MODEL": "",
            "KATALYST_EXECUTION_MODEL": "",
            "KATALYST_LLM_MODEL_FALLBACK": "",
            "KATALYST_LITELLM_TIMEOUT": ""
        }
        with patch.dict(os.environ, env_vars, clear=True):
            reset_config()  # Force config reload
            config = get_llm_config()
            
            assert config.get_provider() == "ollama"
            assert config.get_model_for_component("planner") == "ollama/qwen2.5-coder:7b"
            assert config.get_model_for_component("agent_react") == "ollama/phi4"
            assert config.get_fallback_models() == ["ollama/codestral"]
            assert config.get_timeout() == 60
            assert config.get_api_base() == "http://localhost:11434"
    
    def test_ollama_custom_api_base(self):
        """Test custom API base configuration for Ollama."""
        with patch.dict(os.environ, {
            "KATALYST_LITELLM_PROVIDER": "ollama",
            "KATALYST_LLM_API_BASE": "http://custom:8080"
        }):
            config = get_llm_config()
            assert config.get_api_base() == "http://custom:8080"
    
    def test_ollama_model_override(self):
        """Test model override for Ollama provider."""
        with patch.dict(os.environ, {
            "KATALYST_LITELLM_PROVIDER": "ollama",
            "KATALYST_REASONING_MODEL": "ollama/devstral",
            "KATALYST_EXECUTION_MODEL": "ollama/codestral"
        }):
            config = get_llm_config()
            
            assert config.get_model_for_component("planner") == "ollama/devstral"
            assert config.get_model_for_component("agent_react") == "ollama/codestral"
    
    def test_ollama_llm_params(self):
        """Test that LLM params include api_base for Ollama."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "ollama"}):
            params = get_llm_params("planner")
            
            assert params["model"] == "ollama/qwen2.5-coder:7b"
            assert params["timeout"] == 60
            assert params["api_base"] == "http://localhost:11434"
            assert params["temperature"] == 0.1
            assert params["fallbacks"] == ["ollama/codestral"]
    
    def test_ollama_config_summary(self):
        """Test config summary includes Ollama-specific fields."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "ollama"}):
            config = get_llm_config()
            summary = config.get_config_summary()
            
            assert summary["provider"] == "ollama"
            assert summary["profile"] == "ollama"
            assert summary["timeout"] == 60
            assert summary["models"]["reasoning"] == "ollama/qwen2.5-coder:7b"
            assert summary["models"]["execution"] == "ollama/phi4"
            assert summary["models"]["fallback"] == "ollama/codestral"
            assert summary["api_base"] == "http://localhost:11434"
    
    @patch('litellm.completion')
    def test_ollama_client_call(self, mock_completion):
        """Test that Ollama calls include proper parameters."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "ollama"}):
            # Mock the response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
            mock_completion.return_value = mock_response
            
            # Get client and params
            client = get_llm_client("planner", async_mode=False, use_instructor=False)
            params = get_llm_params("planner")
            
            # Make a call
            response = client(
                messages=[{"role": "user", "content": "test"}],
                **params
            )
            
            # Verify the call was made with correct parameters
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args[1]
            assert call_args["model"] == "ollama/qwen2.5-coder:7b"
            assert call_args["api_base"] == "http://localhost:11434"
            assert call_args["timeout"] == 60
            assert call_args["temperature"] == 0.1
    
    def test_ollama_provider_validation(self):
        """Test that unknown providers fall back correctly."""
        with patch.dict(os.environ, {
            "KATALYST_LITELLM_PROVIDER": "unknown",
            "KATALYST_LLM_PROFILE": "ollama"
        }):
            config = get_llm_config()
            # Should use ollama profile even though provider is unknown
            assert config.get_model_for_component("planner") == "ollama/qwen2.5-coder:7b"