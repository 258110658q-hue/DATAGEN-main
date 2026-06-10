from typing import Type

from langchain_openai import AzureChatOpenAI

from .base import BaseProvider


class AzureChatOpenAIProvider(BaseProvider):
    """Azure OpenAI 模型的服务提供者。"""

    def get_model_class(self) -> Type:
        """返回 AzureChatOpenAI 类。"""
        return AzureChatOpenAI
