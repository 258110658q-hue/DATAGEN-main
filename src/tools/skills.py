from typing import Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ..core.agent_config_loader import get_agent_config_loader
from ..logger import setup_logger

logger = setup_logger()


class LookupSkillInput(BaseModel):
    """LookupSkill 工具的输入模型。"""
    skill_name: str = Field(description="要查询的技能名称（来自可用技能列表）")


class LookupSkill(BaseTool):
    """用于查询技能详细说明的工具。"""

    name: str = "lookup_skill"
    description: str = (
        "获取特定技能的详细说明和内容。"
        "当你需要技能中定义的过程性知识或工作流程时使用此工具。"
    )
    args_schema: Type[BaseModel] = LookupSkillInput

    def _run(self, skill_name: str) -> str:
        loader = get_agent_config_loader()
        content = loader.get_skill_content(skill_name)

        if content:
            logger.info(f"Agent 查询了技能：{skill_name}")
            return content
        else:
            msg = f"Error：技能 '{skill_name}' 未找到。请检查'可用技能'列表。"
            logger.warning(f"技能查询失败：{skill_name}")
            return msg

    async def _arun(self, skill_name: str) -> str:
        # 复用同步实现以保持简洁
        return self._run(skill_name)
