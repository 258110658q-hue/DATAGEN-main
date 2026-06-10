from typing import Type

from langchain_openai import ChatOpenAI

from .base import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek 模型提供者（兼容 OpenAI API）。"""

    def get_model_class(self) -> Type:
        return ChatOpenAI
