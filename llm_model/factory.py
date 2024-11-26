from typing import Optional, Dict, Any
from enum import Enum
import os
from .base import BaseLLM
from .anthropic_llm import AnthropicLLM
from .gemini_llm import GeminiLLM
from .agent import Agent
from .openai_llm import OpenAILLM


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


class LLMFactory:
    """Factory class to create LLM instances and agents."""

    DEFAULT_MODELS = {
        LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        LLMProvider.OPENAI: "gpt-4-turbo-preview",
        LLMProvider.GEMINI: "gemini-pro",
    }

    @staticmethod
    def create_llm(
        provider: LLMProvider,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseLLM:
        """
        Create an LLM instance based on the provider.

        Args:
            provider: The LLM provider to use
            api_key: API key for the provider (optional, will check env vars if not provided)
            model: Model name to use (optional, will use default if not provided)
            **kwargs: Additional arguments to pass to the LLM constructor

        Returns:
            An instance of BaseLLM
        """
        if api_key is None:
            api_key = LLMFactory._get_api_key(provider)

        if model is None:
            model = LLMFactory.DEFAULT_MODELS[provider]

        if provider == LLMProvider.ANTHROPIC:
            return AnthropicLLM(model=model, api_key=api_key, **kwargs)
        elif provider == LLMProvider.GEMINI:
            return GeminiLLM(model=model, api_key=api_key, **kwargs)
        elif provider == LLMProvider.OPENAI:
            return OpenAILLM(model=model, api_key=api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @staticmethod
    def create_agent(
        provider: LLMProvider,
        system_prompt: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> Agent:
        """
        Create an Agent with the specified LLM provider.

        Args:
            provider: The LLM provider to use
            system_prompt: The system prompt for the agent
            api_key: API key for the provider (optional, will check env vars if not provided)
            model: Model name to use (optional, will use default if not provided)
            **kwargs: Additional arguments to pass to the LLM constructor

        Returns:
            An Agent instance configured with the specified LLM
        """
        llm = LLMFactory.create_llm(provider, api_key, model, **kwargs)
        return Agent(llm=llm, system_prompt=system_prompt)

    @staticmethod
    def _get_api_key(provider: LLMProvider) -> str:
        """Get API key from environment variables."""
        env_vars = {
            LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            LLMProvider.OPENAI: "OPENAI_API_KEY",
            LLMProvider.GEMINI: "GOOGLE_API_KEY",
        }

        env_var = env_vars.get(provider)
        api_key = os.getenv(env_var)

        if not api_key:
            raise ValueError(
                f"No API key found for {provider}. "
                f"Please set the {env_var} environment variable."
            )

        return api_key
