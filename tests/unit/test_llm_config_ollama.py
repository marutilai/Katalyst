"""Unit tests for Ollama-specific LLM configuration."""

import os
import pytest
from unittest.mock import patch
from katalyst.katalyst_core.config.llm_config import LLMConfig, PROVIDER_PROFILES


class TestOllamaConfig:
    """Test Ollama-specific configuration functionality."""
    
    def test_ollama_in_provider_profiles(self):
        """Test that Ollama is properly defined in provider profiles."""
        assert "ollama" in PROVIDER_PROFILES
        
        ollama_profile = PROVIDER_PROFILES["ollama"]
        assert ollama_profile["reasoning"] == "ollama/qwen2.5-coder:7b"
        assert ollama_profile["execution"] == "ollama/phi4"
        assert ollama_profile["fallback"] == "ollama/codestral"
        assert ollama_profile["default_timeout"] == 60
        assert ollama_profile["api_base"] == "http://localhost:11434"
    
    def test_get_api_base_from_profile(self):
        """Test getting API base from provider profile."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "ollama"}, clear=True):
            config = LLMConfig()
            assert config.get_api_base() == "http://localhost:11434"
    
    def test_get_api_base_from_env_override(self):
        """Test API base environment variable override."""
        with patch.dict(os.environ, {
            "KATALYST_LITELLM_PROVIDER": "ollama",
            "KATALYST_LLM_API_BASE": "http://custom:8080"
        }, clear=True):
            config = LLMConfig()
            assert config.get_api_base() == "http://custom:8080"
    
    def test_get_api_base_non_ollama_provider(self):
        """Test that non-Ollama providers return None for api_base."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "openai"}, clear=True):
            config = LLMConfig()
            assert config.get_api_base() is None
    
    def test_config_summary_with_api_base(self):
        """Test that config summary includes api_base when available."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "ollama"}, clear=True):
            config = LLMConfig()
            summary = config.get_config_summary()
            
            assert "api_base" in summary
            assert summary["api_base"] == "http://localhost:11434"
    
    def test_config_summary_without_api_base(self):
        """Test that config summary excludes api_base when not available."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "openai"}, clear=True):
            config = LLMConfig()
            summary = config.get_config_summary()
            
            assert "api_base" not in summary
    
    def test_ollama_model_naming_convention(self):
        """Test that Ollama models follow the ollama/ prefix convention."""
        ollama_profile = PROVIDER_PROFILES["ollama"]
        
        for model_type in ["reasoning", "execution", "fallback"]:
            model_name = ollama_profile[model_type]
            assert model_name.startswith("ollama/"), f"{model_type} model should have ollama/ prefix"
    
    def test_ollama_timeout_configuration(self):
        """Test Ollama timeout configuration."""
        with patch.dict(os.environ, {"KATALYST_LITELLM_PROVIDER": "ollama"}, clear=True):
            config = LLMConfig()
            # Should use Ollama's default timeout
            assert config.get_timeout() == 60
        
        with patch.dict(os.environ, {
            "KATALYST_LITELLM_PROVIDER": "ollama",
            "KATALYST_LITELLM_TIMEOUT": "120"
        }, clear=True):
            config = LLMConfig()
            # Should use custom timeout
            assert config.get_timeout() == 120