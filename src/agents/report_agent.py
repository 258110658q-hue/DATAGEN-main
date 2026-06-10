from typing import Any, Dict, List, TYPE_CHECKING

from ..tools.basetool import list_directory
from ..tools.FileEdit import create_document, read_document, edit_document
from .base import BaseAgent
from ..config import WORKING_DIRECTORY
from ..core.schemas import ArtifactSchema
from ..core.node import update_artifact_dict, get_state_attr

if TYPE_CHECKING:
    from ..core.language_models import LanguageModelManager
    from ..core.state import State

class ReportAgent(BaseAgent):
    """负责撰写综合性研究报告的 Agent。"""

    def __init__(self, language_model_manager: "LanguageModelManager", team_members: List[str], working_directory: str = WORKING_DIRECTORY):
        """
        初始化 ReportAgent。

        Args:
            language_model_manager: 语言模型配置管理器。
            team_members: 协作团队成员角色列表。
            working_directory: Agent 数据存储的目录。
        """
        super().__init__(
            agent_name="report_agent",
            language_model_manager=language_model_manager,
            team_members=team_members,
            working_directory=working_directory
        )
        self.response_format = ArtifactSchema

    def _get_tools(self) -> List:
        """获取用于报告撰写的工具列表。"""
        return [create_document, read_document, edit_document, list_directory]

    def get_state_updates(self, state: "State", output: Any) -> Dict[str, Any]:
        """返回报告产物的状态更新。

        Args:
            state: 当前工作流状态。
            output: Agent 的 ArtifactSchema 输出。

        Returns:
            包含 'report_artifacts' 字段更新的字典。
        """
        current = get_state_attr(state, "report_artifacts", {})
        new_data = getattr(output, "artifacts", output)
        return {"report_artifacts": update_artifact_dict(current, new_data)}
