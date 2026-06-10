from typing import Type

from langchain_groq import ChatGroq

from .base import BaseProvider


class ChatGroqProvider(BaseProvider):
    """ChatGroq 模型的提供器。"""

    def get_model_class(self) -> Type:
        """返回 ChatGroq 类。"""
        return ChatGroq
