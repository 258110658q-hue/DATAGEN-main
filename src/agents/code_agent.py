from typing import Any, Dict, List, TYPE_CHECKING

from ..tools.basetool import execute_code, execute_command, list_directory
from ..tools.FileEdit import read_document
from .base import BaseAgent
from ..config import WORKING_DIRECTORY
from ..core.schemas import ArtifactSchema
from ..core.node import update_artifact_dict, get_state_attr

if TYPE_CHECKING:
    from ..core.language_models import LanguageModelManager
    from ..core.state import State

class CodeAgent(BaseAgent):
    """负责编写和执行 Python 代码以进行数据处理的 Agent。"""

    def __init__(self, language_model_manager: "LanguageModelManager", team_members: List[str], working_directory: str = WORKING_DIRECTORY):
        """
        初始化 CodeAgent。

        Args:
            language_model_manager: 语言模型配置管理器。
            team_members: 协作团队角色列表。
            working_directory: Agent 数据将存储的目录。
        """
        super().__init__(
            agent_name="code_agent",
            language_model_manager=language_model_manager,
            team_members=team_members,
            working_directory=working_directory
        )
        self.response_format = ArtifactSchema

    def _get_tools(self) -> List:
        """获取用于代码生成和执行的工具列表。"""
        return [read_document, execute_code, execute_command, list_directory]

    def get_state_updates(self, state: "State", output: Any) -> Dict[str, Any]:
        """返回代码产物的状态更新。

        Args:
            state: 当前工作流状态。
            output: Agent 的 ArtifactSchema 输出或字典。

        Returns:
            包含 'code_artifacts' 字段更新的字典。
        """
        def safe_get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        current = get_state_attr(state, "code_artifacts", {})
        # 如果输出包含 'artifacts' 键/属性，则使用它，否则使用整个输出
        new_data = safe_get(output, "artifacts", output)

        return {"code_artifacts": update_artifact_dict(current, new_data)}
