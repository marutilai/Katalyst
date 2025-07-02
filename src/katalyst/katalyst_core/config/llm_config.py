"""
LLM Configuration Module

Provides centralized configuration for LLM providers and models,
with sensible defaults and easy provider switching.
"""

import os
from typing import Dict, Optional
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()

# Provider profiles with default models for different use cases
PROVIDER_PROFILES = {
    "openai": {
        "reasoning": "gpt-4.1",  # High-reasoning tasks (planner, replanner)
        "execution": "gpt-4.1",  # Fast execution tasks (agent_react, tools)
        "fallback": "gpt-4o",  # Fallback model
        "default_timeout": 45,
    },
    "anthropic": {
        "reasoning": "claude-3-opus-20240229",  # High-reasoning tasks
        "execution": "claude-3-haiku-20240307",  # Fast execution tasks
        "fallback": "claude-3-haiku-20240307",  # Fallback model
        "default_timeout": 60,
    },
    "gemini": {
        "reasoning": "gemini-1.5-pro",  # High-reasoning tasks
        "execution": "gemini-1.5-flash",  # Fast execution tasks
        "fallback": "gemini-1.5-flash",  # Fallback model
        "default_timeout": 45,
    },
    "groq": {
        "reasoning": "mixtral-8x7b-32768",  # High-reasoning tasks
        "execution": "llama3-8b-8192",  # Fast execution tasks
        "fallback": "llama3-8b-8192",  # Fallback model
        "default_timeout": 30,
    },
    "ollama": {
        "reasoning": "ollama/qwen2.5-coder:7b",  # Best performer for coding tasks
        "execution": "ollama/phi4",  # Fast execution model
        "fallback": "ollama/codestral",  # Fallback to larger model
        "default_timeout": 60,  # Local inference might need more time
        "api_base": "http://localhost:11434",  # Default Ollama endpoint
    },
}

# Component to model type mapping
COMPONENT_MODEL_MAPPING = {
    "planner": "reasoning",
    "replanner": "reasoning",
    "agent_react": "execution",
    "generate_directory_overview": "execution",
    "tool_runner": "execution",
    # Default for any other component
    "default": "execution",
}


class LLMConfig:
    """Manages LLM configuration with provider profiles and overrides."""

    def __init__(self):
        self._provider = None
        self._profile = None
        self._custom_models = {}
        self._timeout = None
        self._load_config()

    def _load_config(self):
        """Load configuration from environment variables."""
        # Get provider
        # Support both old and new env var names for backward compatibility
        self._provider = os.getenv("KATALYST_LLM_PROVIDER", 
                                   os.getenv("KATALYST_LITELLM_PROVIDER", "openai")).lower()

        # Get profile or use provider as profile name
        self._profile = os.getenv("KATALYST_LLM_PROFILE", self._provider).lower()

        # Check if profile exists, fall back to provider profile if not
        if self._profile not in PROVIDER_PROFILES:
            logger.warning(
                f"LLM profile '{self._profile}' not found, using provider '{self._provider}' profile"
            )
            self._profile = self._provider

        # Validate provider profile exists
        if self._profile not in PROVIDER_PROFILES:
            available = ", ".join(PROVIDER_PROFILES.keys())
            raise ValueError(
                f"Unknown provider profile '{self._profile}'. Available: {available}"
            )

        # Load custom model overrides
        if os.getenv("KATALYST_REASONING_MODEL"):
            self._custom_models["reasoning"] = os.getenv("KATALYST_REASONING_MODEL")
        if os.getenv("KATALYST_EXECUTION_MODEL"):
            self._custom_models["execution"] = os.getenv("KATALYST_EXECUTION_MODEL")
        if os.getenv("KATALYST_LLM_MODEL_FALLBACK"):
            self._custom_models["fallback"] = os.getenv("KATALYST_LLM_MODEL_FALLBACK")

        # Load timeout
        try:
            self._timeout = int(os.getenv("KATALYST_LLM_TIMEOUT", 
                                         os.getenv("KATALYST_LITELLM_TIMEOUT", "0")))
        except ValueError:
            self._timeout = 0

        logger.debug(
            f"LLM Config loaded - Provider: {self._provider}, Profile: {self._profile}, "
            f"Custom models: {self._custom_models}"
        )

    def get_model_for_component(self, component: str) -> str:
        """
        Get the appropriate model for a given component.

        Args:
            component: Component name (e.g., 'planner', 'agent_react')

        Returns:
            Model identifier string
        """
        # Determine model type for component
        model_type = COMPONENT_MODEL_MAPPING.get(
            component.lower(), COMPONENT_MODEL_MAPPING["default"]
        )

        # Check for custom override first
        if model_type in self._custom_models:
            return self._custom_models[model_type]

        # Use profile default
        profile = PROVIDER_PROFILES[self._profile]
        return profile.get(model_type, profile["execution"])

    def get_provider(self) -> str:
        """Get the configured provider."""
        return self._provider

    def get_timeout(self) -> int:
        """Get the configured timeout in seconds."""
        if self._timeout > 0:
            return self._timeout
        profile = PROVIDER_PROFILES[self._profile]
        return profile.get("default_timeout", 45)

    def get_fallback_models(self) -> list[str]:
        """Get list of fallback models."""
        if "fallback" in self._custom_models:
            return [self._custom_models["fallback"]]
        profile = PROVIDER_PROFILES[self._profile]
        return [profile.get("fallback", profile["execution"])]
    
    def get_api_base(self) -> Optional[str]:
        """Get the API base URL if configured for the provider."""
        # Check environment variable override first
        api_base = os.getenv("KATALYST_LLM_API_BASE")
        if api_base:
            return api_base
        
        # Check profile configuration
        profile = PROVIDER_PROFILES.get(self._profile, {})
        return profile.get("api_base")

    def get_config_summary(self) -> Dict[str, any]:
        """Get a summary of the current configuration."""
        summary = {
            "provider": self._provider,
            "profile": self._profile,
            "timeout": self.get_timeout(),
            "models": {
                "reasoning": self.get_model_for_component("planner"),
                "execution": self.get_model_for_component("agent_react"),
                "fallback": self.get_fallback_models()[0],
            },
            "custom_overrides": self._custom_models,
        }
        
        # Add api_base if available
        api_base = self.get_api_base()
        if api_base:
            summary["api_base"] = api_base
            
        return summary


# Global instance
_config = None


def get_llm_config() -> LLMConfig:
    """Get the global LLM configuration instance."""
    global _config
    if _config is None:
        _config = LLMConfig()
    return _config


def reset_config():
    """Reset the configuration (useful for testing)."""
    global _config
    _config = None
