from pydantic import BaseModel, Field
from typing import Sequence, List, TYPE_CHECKING, Any

from langchain_core.messages import BaseMessage

from ..tools.FileEdit import read_document
from ..tools.basetool import list_directory
from .base import BaseAgent
from ..config import WORKING_DIRECTORY
from ..core.state import State

if TYPE_CHECKING:
    from ..core.language_models import LanguageModelManager


class NoteOutput(BaseModel):
    """NoteAgent 输出的 Pydantic 模型。"""
    messages: List[Any] = Field(default_factory=list, description="要添加或更新的新消息")
    hypothesis: str = Field(default="", description="更新后的研究假设")
    current_instruction: str = Field(default="", description="更新后的当前指令")
    next_workflow_step: str = Field(default="", description="更新后的下一步工作流步骤")
    search_artifacts: str = Field(default="", description="要归档的搜索结果")
    data_viz_artifacts: str = Field(default="", description="要归档的可视化产物")
    code_artifacts: str = Field(default="", description="要归档的代码产物")
    report_artifacts: str = Field(default="", description="要归档的报告章节")
    quality_feedback: str = Field(default="", description="质量反馈（如有）")
    needs_revision: bool = Field(default=False, description="是否需要修订")

class NoteAgent(BaseAgent):
    """负责记录研究过程笔记的 Agent。"""

    def __init__(self, language_model_manager: "LanguageModelManager", team_members: List[str], working_directory: str = WORKING_DIRECTORY):
        """
        初始化 NoteAgent。

        Args:
            language_model_manager: 语言模型配置管理器。
            team_members: 协作团队成员角色列表。
            working_directory: Agent 数据存储目录。
        """
        super().__init__(
            agent_name="note_agent",
            language_model_manager=language_model_manager,
            team_members=team_members,
            working_directory=working_directory,
            response_format=NoteOutput
        )

    def _get_tools(self) -> List:
        """获取 NoteAgent 的工具列表。"""
        return [read_document, list_directory]
