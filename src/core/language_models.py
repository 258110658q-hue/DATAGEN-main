from __future__ import annotations
from typing import Any, TYPE_CHECKING
from ..logger import setup_logger
from ..llm.factory import ProviderFactory
from ..config import AGENT_MODELS

if TYPE_CHECKING:
    from ..llm.providers.base import BaseProvider

class LanguageModelManager:
    def __init__(self) -> None:
        """初始化语言模型管理器"""
        self.logger = setup_logger()
        self.provider_factory = ProviderFactory()

    def get_provider(self, agent_name: str) -> BaseProvider:
        """获取指定 Agent 的 provider。"""
        provider_name = AGENT_MODELS.get_provider(agent_name)
        if not provider_name:
            raise ValueError(f"No provider configured for agent '{agent_name}'")
        return self.provider_factory.create_provider(provider_name)

    def get_model_config(self, agent_name: str) -> dict[str, Any]:
        """获取指定 Agent 的模型配置。"""
        config = AGENT_MODELS.get_model_config(agent_name)
        if not config:
            raise ValueError(f"No model config configured for agent '{agent_name}'")
        return config

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """获取指定 Agent 的完整配置。"""
        return AGENT_MODELS.get_agent_config(agent_name)
