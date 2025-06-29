"""Tests for the LLM configuration system."""

import os
import pytest
from unittest.mock import patch
from katalyst.katalyst_core.config.llm_config import (
    LLMConfig,
    get_llm_config,
    reset_config,
    PROVIDER_PROFILES,
    COMPONENT_MODEL_MAPPING,
)


class TestLLMConfig:
    """Test LLM configuration functionality."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_default_configuration(self):
        """Test default configuration loads correctly."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_llm_config()
            assert config.get_provider() == "openai"
            assert config.get_timeout() == 45
            assert config.get_model_for_component("planner") == "gpt-4.1"
            assert config.get_model_for_component("agent_react") == "gpt-4.1"

    def test_provider_profiles(self):
        """Test different provider profiles."""
        # Test Anthropic profile
        with patch.dict(
            os.environ,
            {"KATALYST_LITELLM_PROVIDER": "anthropic", "KATALYST_LLM_PROFILE": "anthropic"},
            clear=True,
        ):
            reset_config()
            config = get_llm_config()
            assert config.get_provider() == "anthropic"
            assert config.get_model_for_component("planner") == "claude-3-opus-20240229"
            assert config.get_model_for_component("agent_react") == "claude-3-haiku-20240307"

        # Test Gemini profile
        with patch.dict(
            os.environ,
            {"KATALYST_LITELLM_PROVIDER": "gemini", "KATALYST_LLM_PROFILE": "gemini"},
            clear=True,
        ):
            reset_config()
            config = get_llm_config()
            assert config.get_provider() == "gemini"
            assert config.get_model_for_component("planner") == "gemini-1.5-pro"
            assert config.get_model_for_component("agent_react") == "gemini-1.5-flash"

    def test_custom_model_overrides(self):
        """Test custom model overrides via environment variables."""
        with patch.dict(
            os.environ,
            {
                "KATALYST_LITELLM_PROVIDER": "openai",
                "KATALYST_REASONING_MODEL": "custom-reasoning-model",
                "KATALYST_EXECUTION_MODEL": "custom-execution-model",
                "KATALYST_LLM_MODEL_FALLBACK": "custom-fallback-model",
            },
            clear=True,
        ):
            reset_config()
            config = get_llm_config()
            assert config.get_model_for_component("planner") == "custom-reasoning-model"
            assert config.get_model_for_component("agent_react") == "custom-execution-model"
            assert config.get_fallback_models() == ["custom-fallback-model"]

    def test_component_model_mapping(self):
        """Test component to model type mapping."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_llm_config()
            # Reasoning components
            assert config.get_model_for_component("planner") == "gpt-4.1"
            assert config.get_model_for_component("replanner") == "gpt-4.1"
            # Execution components
            assert config.get_model_for_component("agent_react") == "gpt-4.1"
            assert config.get_model_for_component("generate_directory_overview") == "gpt-4.1"
            # Unknown component defaults to execution
            assert config.get_model_for_component("unknown_component") == "gpt-4.1"

    def test_timeout_configuration(self):
        """Test timeout configuration."""
        # Test custom timeout
        with patch.dict(
            os.environ, {"KATALYST_LITELLM_TIMEOUT": "120"}, clear=True
        ):
            reset_config()
            config = get_llm_config()
            assert config.get_timeout() == 120

        # Test invalid timeout falls back to profile default
        with patch.dict(
            os.environ, {"KATALYST_LITELLM_TIMEOUT": "invalid"}, clear=True
        ):
            reset_config()
            config = get_llm_config()
            assert config.get_timeout() == 45  # OpenAI default

    def test_invalid_provider_profile(self):
        """Test handling of invalid provider profile."""
        with patch.dict(
            os.environ,
            {"KATALYST_LITELLM_PROVIDER": "invalid", "KATALYST_LLM_PROFILE": "invalid"},
            clear=True,
        ):
            reset_config()
            with pytest.raises(ValueError) as exc_info:
                get_llm_config()
            assert "Unknown provider profile" in str(exc_info.value)

    def test_config_summary(self):
        """Test configuration summary output."""
        with patch.dict(
            os.environ,
            {
                "KATALYST_LITELLM_PROVIDER": "anthropic",
                "KATALYST_LLM_PROFILE": "anthropic",
                "KATALYST_REASONING_MODEL": "custom-claude-opus",
            },
            clear=True,
        ):
            reset_config()
            config = get_llm_config()
            summary = config.get_config_summary()
            
            assert summary["provider"] == "anthropic"
            assert summary["profile"] == "anthropic"
            assert summary["timeout"] == 60  # Anthropic default
            assert summary["models"]["reasoning"] == "custom-claude-opus"
            assert summary["models"]["execution"] == "claude-3-haiku-20240307"
            assert summary["custom_overrides"] == {"reasoning": "custom-claude-opus"}

    def test_singleton_behavior(self):
        """Test that get_llm_config returns the same instance."""
        config1 = get_llm_config()
        config2 = get_llm_config()
        assert config1 is config2

        # After reset, should get new instance
        reset_config()
        config3 = get_llm_config()
        assert config3 is not config1