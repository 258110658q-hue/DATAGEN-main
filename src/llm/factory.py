from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider


class ProviderFactory:
    """A factory class for creating LLM providers with lazy loading.

    Each provider is imported only when requested, so users don't need
    to install packages for providers they aren't using.
    """

    def create_provider(self, provider_name: str, **kwargs: Any) -> BaseProvider:
        """
        Creates a provider instance based on the provider name.

        Args:
            provider_name: The name of the provider to create.
            **kwargs: Additional keyword arguments for provider configuration.

        Returns:
            An instance of the requested provider.

        Raises:
            NotImplementedError: If the provider creation is not implemented.
            ImportError: If the required provider package is not installed.
        """
        if provider_name == "openai":
            from .openai import OpenAIProvider
            return OpenAIProvider()
        elif provider_name == "anthropic":
            from .anthropic import AnthropicProvider
            return AnthropicProvider()
        elif provider_name == "google":
            from .google import GoogleProvider
            return GoogleProvider()
        elif provider_name == "ollama":
            from .ollama import OllamaProvider
            return OllamaProvider()
        elif provider_name == "azure":
            from .azure import AzureChatOpenAIProvider
            return AzureChatOpenAIProvider()
        elif provider_name == "groq":
            from .groq import ChatGroqProvider
            return ChatGroqProvider()
        elif provider_name == "deepseek":
            from .deepseek import DeepSeekProvider
            return DeepSeekProvider()
        else:
            raise NotImplementedError(f"Provider creation for '{provider_name}' is not implemented.")
