from typing import Any, Dict, List, TYPE_CHECKING

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.agent_toolkits.load_tools import load_tools

from .base import BaseAgent
from ..tools.basetool import list_directory
from ..tools.FileEdit import collect_data
from ..tools.internet import google_search, scrape_webpages
from ..config import WORKING_DIRECTORY

if TYPE_CHECKING:
    from ..core.language_models import LanguageModelManager
    from ..core.state import State

class HypothesisAgent(BaseAgent):
    """负责生成研究假设的 Agent。"""

    def __init__(self, language_model_manager: "LanguageModelManager", team_members: List[str], working_directory: str = WORKING_DIRECTORY):
        """
        初始化 HypothesisAgent。

        Args:
            language_model_manager: 语言模型配置管理器。
            team_members: 协作用户角色列表。
            working_directory: Agent 数据存储目录。
        """
        super().__init__(
            agent_name="hypothesis_agent",
            language_model_manager=language_model_manager,
            team_members=team_members,
            working_directory=working_directory
        )

    def _get_tools(self) -> List:
        """获取用于假设生成的工具列表。"""
        api_wrapper = WikipediaAPIWrapper(wiki_client=None)
        wikipedia = WikipediaQueryRun(api_wrapper=api_wrapper)
        base_tools = [
            collect_data,
            wikipedia,
            google_search,
            scrape_webpages,
            list_directory
        ] + load_tools(["arxiv"])

        return base_tools

    def get_state_updates(self, state: "State", output: Any) -> Dict[str, Any]:
        """返回假设生成输出的状态更新。

        Args:
            state: 当前工作流状态。
            output: Agent 的输出（假设内容）。

        Returns:
            包含 'hypothesis' 字段更新的字典。
        """
        # 提取假设文本，确保字符串序列化
        if isinstance(output, str):
            hypothesis_text = output
        elif hasattr(output, "hypothesis"):
            hypothesis_text = str(output.hypothesis)
        elif hasattr(output, "content"):
            hypothesis_text = str(output.content)
        else:
            hypothesis_text = str(output)

        return {"hypothesis": hypothesis_text}
