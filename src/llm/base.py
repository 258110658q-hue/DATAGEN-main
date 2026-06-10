from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BaseProvider(ABC):
    """LLM 提供商的抽象基类。"""

    @abstractmethod
    def get_model_class(self) -> type[Any]:
        """
        获取该提供商的模型类。

        Returns:
            语言模型的类（例如 ChatOpenAI）。
        """
        pass
