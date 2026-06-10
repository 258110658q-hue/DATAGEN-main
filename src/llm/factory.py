from __future__ import annotations
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProvider


class ProviderFactory:
    """创建 LLM provider 的工厂类，支持延迟加载。

    每个 provider 仅在请求时才被导入，因此用户无需为不使用的 provider 安装对应的包。
    """

    def create_provider(self, provider_name: str, **kwargs: Any) -> BaseProvider:
        """
        根据 provider 名称创建对应的 provider 实例。

        Args:
            provider_name: 要创建的 provider 的名称。
            **kwargs: 用于 provider 配置的额外关键字参数。

        Returns:
            所请求的 provider 的实例。

        Raises:
            NotImplementedError: 如果该 provider 的创建尚未实现。
            ImportError: 如果所需的 provider 包未安装。
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
