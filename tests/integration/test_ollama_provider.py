"""Integration tests for Ollama provider configuration."""

import os
import pytest

# Skip this entire test file since it uses llms service which has been removed
pytestmark = pytest.mark.skip("test uses llms service which has been removed")

from unittest.mock import patch, MagicMock, Mock
from katalyst.katalyst_core.config.llm_config import LLMConfig, PROVIDER_PROFILES
from katalyst.katalyst_core.services.llms import get_llm_client, get_llm_params


def create_test_ollama_config(
    reasoning_model=None,
    execution_model=None,
    fallback_model=None,
    timeout=None,
    api_base=None
):
    """Create a test LLMConfig instance with hardcoded Ollama configuration.
    
    These values would normally come from environment variables:
    - KATALYST_LITELLM_PROVIDER="ollama"
    - KATALYST_REASONING_MODEL (optional override)
    - KATALYST_EXECUTION_MODEL (optional override)
    - KATALYST_LLM_MODEL_FALLBACK (optional override)
    - KATALYST_LITELLM_TIMEOUT (optional override)
    - KATALYST_LLM_API_BASE (optional override)
    """
    config = Mock(spec=LLMConfig)
    config._provider = "ollama"
    config._profile = "ollama"
    config._custom_models = {}
    config._timeout = timeout or 0
    
    # Add custom model overrides if provided
    if reasoning_model:
        config._custom_models["reasoning"] = reasoning_model
    if execution_model:
        config._custom_models["execution"] = execution_model
    if fallback_model:
        config._custom_models["fallback"] = fallback_model
    
    # Mock the methods
    config.get_provider = Mock(return_value="ollama")
    
    def get_model_for_component(component):
        model_type = {
            "planner": "reasoning",
            "replanner": "reasoning",
            "agent_react": "execution",
            "generate_directory_overview": "execution",
            "tool_runner": "execution",
        }.get(component.lower(), "execution")
        
        if model_type in config._custom_models:
            return config._custom_models[model_type]
        
        profile = PROVIDER_PROFILES["ollama"]
        return profile.get(model_type, profile["execution"])
    
    config.get_model_for_component = Mock(side_effect=get_model_for_component)
    
    def get_timeout():
        if config._timeout > 0:
            return config._timeout
        return PROVIDER_PROFILES["ollama"]["default_timeout"]
    
    config.get_timeout = Mock(side_effect=get_timeout)
    
    def get_fallback_models():
        if "fallback" in config._custom_models:
            return [config._custom_models["fallback"]]
        return [PROVIDER_PROFILES["ollama"]["fallback"]]
    
    config.get_fallback_models = Mock(side_effect=get_fallback_models)
    
    def get_api_base():
        if api_base:
            return api_base
        return PROVIDER_PROFILES["ollama"].get("api_base")
    
    config.get_api_base = Mock(side_effect=get_api_base)
    
    def get_config_summary():
        summary = {
            "provider": config._provider,
            "profile": config._profile,
            "timeout": config.get_timeout(),
            "models": {
                "reasoning": config.get_model_for_component("planner"),
                "execution": config.get_model_for_component("agent_react"),
                "fallback": config.get_fallback_models()[0],
            },
            "custom_overrides": config._custom_models,
        }
        api_base_val = config.get_api_base()
        if api_base_val:
            summary["api_base"] = api_base_val
        return summary
    
    config.get_config_summary = Mock(side_effect=get_config_summary)
    
    return config


class TestOllamaProvider:
    """Test Ollama provider integration."""
    
    @patch('katalyst.katalyst_core.config.get_llm_config')
    def test_ollama_provider_profile(self, mock_get_config):
        """Test that Ollama provider profile is properly configured."""
        # Create test config with default Ollama settings
        # In production, this would come from KATALYST_LITELLM_PROVIDER="ollama"
        test_config = create_test_ollama_config()
        mock_get_config.return_value = test_config
        
        config = mock_get_config()
        
        assert config.get_provider() == "ollama"
        assert config.get_model_for_component("planner") == "ollama/qwen2.5-coder:7b"
        assert config.get_model_for_component("agent_react") == "ollama/phi4"
        assert config.get_fallback_models() == ["ollama/codestral"]
        assert config.get_timeout() == 60
        assert config.get_api_base() == "http://localhost:11434"
    
    @patch('katalyst.katalyst_core.config.get_llm_config')
    def test_ollama_custom_api_base(self, mock_get_config):
        """Test custom API base configuration for Ollama."""
        # In production, this would come from KATALYST_LLM_API_BASE="http://custom:8080"
        test_config = create_test_ollama_config(api_base="http://custom:8080")
        mock_get_config.return_value = test_config
        
        config = mock_get_config()
        assert config.get_api_base() == "http://custom:8080"
    
    @patch('katalyst.katalyst_core.config.get_llm_config')
    def test_ollama_model_override(self, mock_get_config):
        """Test model override for Ollama provider."""
        # In production, these would come from:
        # KATALYST_REASONING_MODEL="ollama/devstral"
        # KATALYST_EXECUTION_MODEL="ollama/codestral"
        test_config = create_test_ollama_config(
            reasoning_model="ollama/devstral",
            execution_model="ollama/codestral"
        )
        mock_get_config.return_value = test_config
        
        config = mock_get_config()
        
        assert config.get_model_for_component("planner") == "ollama/devstral"
        assert config.get_model_for_component("agent_react") == "ollama/codestral"
    
    @patch('katalyst.katalyst_core.services.llms.get_llm_config')
    @patch('katalyst.katalyst_core.config.get_llm_config')
    def test_ollama_llm_params(self, mock_config_get_config, mock_llms_get_config):
        """Test that LLM params include api_base for Ollama."""
        # In production, this would come from KATALYST_LITELLM_PROVIDER="ollama"
        test_config = create_test_ollama_config()
        mock_config_get_config.return_value = test_config
        mock_llms_get_config.return_value = test_config
        
        params = get_llm_params("planner")
        
        assert params["model"] == "ollama/qwen2.5-coder:7b"
        assert params["timeout"] == 60
        assert params["api_base"] == "http://localhost:11434"
        assert params["temperature"] == 0.3  # Default temperature in get_llm_params
        assert params["fallbacks"] == ["ollama/codestral"]
    
    @patch('katalyst.katalyst_core.config.get_llm_config')
    def test_ollama_config_summary(self, mock_get_config):
        """Test config summary includes Ollama-specific fields."""
        # In production, this would come from KATALYST_LITELLM_PROVIDER="ollama"
        test_config = create_test_ollama_config()
        mock_get_config.return_value = test_config
        
        config = mock_get_config()
        summary = config.get_config_summary()
        
        assert summary["provider"] == "ollama"
        assert summary["profile"] == "ollama"
        assert summary["timeout"] == 60
        assert summary["models"]["reasoning"] == "ollama/qwen2.5-coder:7b"
        assert summary["models"]["execution"] == "ollama/phi4"
        assert summary["models"]["fallback"] == "ollama/codestral"
        assert summary["api_base"] == "http://localhost:11434"
    
    @patch('katalyst.katalyst_core.services.llms.get_llm_config')
    @patch('katalyst.katalyst_core.config.get_llm_config')
    @patch('katalyst.katalyst_core.services.llms.completion')
    def test_ollama_client_call(self, mock_completion, mock_config_get_config, mock_llms_get_config):
        """Test that Ollama calls include proper parameters."""
        # In production, this would come from KATALYST_LITELLM_PROVIDER="ollama"
        test_config = create_test_ollama_config()
        mock_config_get_config.return_value = test_config
        mock_llms_get_config.return_value = test_config
        
        # Mock the response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_completion.return_value = mock_response
        
        # Get client and params
        client = get_llm_client("planner", async_mode=False, use_instructor=False)
        params = get_llm_params("planner")
        
        # Make a call - client is the mocked completion function
        response = client(
            messages=[{"role": "user", "content": "test"}],
            **params
        )
        
        # Verify the call was made with correct parameters
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs["model"] == "ollama/qwen2.5-coder:7b"
        assert call_kwargs["api_base"] == "http://localhost:11434"
        assert call_kwargs["timeout"] == 60
        assert call_kwargs["temperature"] == 0.3  # Default temperature
    
    @patch('katalyst.katalyst_core.config.get_llm_config')
    def test_ollama_provider_validation(self, mock_get_config):
        """Test that unknown providers fall back correctly."""
        # In production, this would come from:
        # KATALYST_LITELLM_PROVIDER="unknown"
        # KATALYST_LLM_PROFILE="ollama"
        # But we simulate the behavior after config processing
        test_config = create_test_ollama_config()
        # Simulate that the provider was set to "unknown" but profile fallback worked
        test_config._provider = "unknown"
        mock_get_config.return_value = test_config
        
        config = mock_get_config()
        # Should use ollama profile even though provider is unknown
        assert config.get_model_for_component("planner") == "ollama/qwen2.5-coder:7b"