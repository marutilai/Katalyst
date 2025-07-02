"""Tests for the LLM service module with new configuration."""

import os
import pytest

# Skip this entire test file since llms service uses litellm which has been removed
pytestmark = pytest.mark.skip("llms service uses litellm which has been removed")

from unittest.mock import patch, MagicMock
from katalyst.katalyst_core.services.llms import (
    get_llm_client,
    get_llm_params,
)
from katalyst.katalyst_core.config import reset_config


class TestLLMService:
    """Test LLM service functionality."""

    def setup_method(self):
        """Reset config before each test."""
        reset_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_get_llm_params_model_selection(self):
        """Test model selection for components via get_llm_params."""
        with patch.dict(
            os.environ,
            {
                "KATALYST_REASONING_MODEL": "test-reasoning",
                "KATALYST_EXECUTION_MODEL": "test-execution",
            },
            clear=True,
        ):
            reset_config()
            assert get_llm_params("planner")["model"] == "test-reasoning"
            assert get_llm_params("replanner")["model"] == "test-reasoning"
            assert get_llm_params("agent_react")["model"] == "test-execution"

    def test_get_llm_client_sync_instructor(self):
        """Test getting synchronous instructor client."""
        client = get_llm_client("planner", async_mode=False, use_instructor=True)
        # Should return instructor-wrapped client
        assert hasattr(client, "chat")

    def test_get_llm_client_async_instructor(self):
        """Test getting asynchronous instructor client."""
        client = get_llm_client("agent_react", async_mode=True, use_instructor=True)
        # Should return instructor-wrapped async client
        assert hasattr(client, "chat")

    def test_get_llm_client_sync_raw(self):
        """Test getting synchronous raw litellm client."""
        with patch("katalyst.katalyst_core.services.llms.completion") as mock_completion:
            client = get_llm_client("planner", async_mode=False, use_instructor=False)
            assert client == mock_completion

    def test_get_llm_client_async_raw(self):
        """Test getting asynchronous raw litellm client."""
        with patch("katalyst.katalyst_core.services.llms.acompletion") as mock_acompletion:
            client = get_llm_client("agent_react", async_mode=True, use_instructor=False)
            assert client == mock_acompletion

    def test_get_llm_params(self):
        """Test getting LLM parameters for a component."""
        with patch.dict(
            os.environ,
            {
                "KATALYST_REASONING_MODEL": "test-model",
                "KATALYST_LITELLM_TIMEOUT": "90",
            },
            clear=True,
        ):
            reset_config()
            params = get_llm_params("planner")
            assert params["model"] == "test-model"
            assert params["timeout"] == 90
            assert params["temperature"] == 0.3  # Default temperature in get_llm_params

    def test_get_llm_params_different_components(self):
        """Test params differ based on component type."""
        with patch.dict(
            os.environ,
            {
                "KATALYST_REASONING_MODEL": "reasoning-model",
                "KATALYST_EXECUTION_MODEL": "execution-model",
            },
            clear=True,
        ):
            reset_config()
            planner_params = get_llm_params("planner")
            agent_params = get_llm_params("agent_react")
            
            assert planner_params["model"] == "reasoning-model"
            assert agent_params["model"] == "execution-model"

    def test_get_llm_params_includes_fallbacks(self):
        """Test that get_llm_params includes fallback models."""
        with patch.dict(
            os.environ,
            {
                "KATALYST_LLM_MODEL_FALLBACK": "fallback-model",
                "KATALYST_LITELLM_TIMEOUT": "60",
            },
            clear=True,
        ):
            reset_config()
            params = get_llm_params("planner")
            assert params["fallbacks"] == ["fallback-model"]
            assert params["timeout"] == 60

    def test_provider_switching(self):
        """Test switching between providers updates models correctly."""
        # Test OpenAI
        with patch.dict(
            os.environ,
            {"KATALYST_LITELLM_PROVIDER": "openai"},
            clear=True,
        ):
            reset_config()
            assert "gpt" in get_llm_params("planner")["model"].lower()

        # Test Anthropic
        with patch.dict(
            os.environ,
            {
                "KATALYST_LITELLM_PROVIDER": "anthropic",
                "KATALYST_LLM_PROFILE": "anthropic",
            },
            clear=True,
        ):
            reset_config()
            assert "claude" in get_llm_params("planner")["model"].lower()