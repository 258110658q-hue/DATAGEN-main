from typing import Type
from langchain_ollama import ChatOllama

from .base import BaseProvider

class OllamaProvider(BaseProvider):
    """Ollama 模型提供者。"""

    def get_model_class(self) -> Type:
        """返回 ChatOllama 类。"""
        return ChatOllama