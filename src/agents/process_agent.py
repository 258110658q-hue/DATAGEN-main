from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, List, TYPE_CHECKING

from ..core.language_models import LanguageModelManager
from .base import BaseAgent
from ..config import WORKING_DIRECTORY

if TYPE_CHECKING:
    from ..core.state import State

class ProcessRouteSchema(BaseModel):
    """选择下一角色并分配任务。
    属性说明：
    下一流程步骤：即将执行操作的角色（可视化、检索、编码、报告或结束）。
    当前指令：选定智能体需要执行的详细任务说明。
    待办列表：待完成的子任务清单。

    """
    next_workflow_step: Literal["FINISH", "Visualization", "Search", "Coder", "Report"] = Field(
        description="即将执行的下一角色"
    )
    current_instruction: str = Field(
        description="下一智能体的详细指令"
    )
    todo_list: List[str] = Field(
        default_factory=list,
        description="项目当前待办任务清单"
    )
    
class ProcessAgent(BaseAgent):
    """负责监督与协调数据分析项目的专员"""

    def __init__(self, language_model_manager: LanguageModelManager, team_members: List[str], working_directory: str = WORKING_DIRECTORY):
        """初始化流程智能体。
        参数说明：
        language_model_manager：语言模型配置管理器。
        team_members：协作团队成员角色列表。
        working_directory：智能体数据的存储目录，默认使用配置项中的工作目录。
        """
        super().__init__(
            agent_name="process_agent",
            language_model_manager=language_model_manager,
            team_members=team_members,
            working_directory=working_directory,
            response_format=ProcessRouteSchema
        )

    def _get_tools(self) -> List:
        """此智能体未使用该功能."""
        return []

    def get_state_updates(self, state: "State", output: Any) -> Dict[str, Any]:
        """返回流程路由决策的状态更新。

        参数：
        state：当前工作流状态。
        output：智能体的流程路由模式输出或字典。
        返回值：
        包含工作流路由字段的字典。

        """
        def safe_get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        return {
            "current_instruction": safe_get(output, "current_instruction", safe_get(output, "task", "")),
            "next_workflow_step": safe_get(output, "next_workflow_step", safe_get(output, "next", "")),
            "todo_list": safe_get(output, "todo_list", [])
        }