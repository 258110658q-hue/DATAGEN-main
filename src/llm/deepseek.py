from typing import Type

from langchain_openai import ChatOpenAI

from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """Provider for DeepSeek models (OpenAI-compatible API)."""

    def get_model_class(self) -> Type:
        return ChatOpenAI
