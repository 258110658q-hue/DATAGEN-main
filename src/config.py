import os
from dotenv import load_dotenv
import yaml
# 加载环境变量
load_dotenv()

# 设置API密钥和环境变量
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY')
# 从环境变量获取工作目录
WORKING_DIRECTORY = os.getenv('WORKING_DIRECTORY', './data')
# 从环境变量获取Conda相关路径（设为"none"可跳过conda）
CONDA_ENV = os.getenv('CONDA_ENV', '')
# 获取ChromeDriver路径（可选 - 推荐使用webdriver-manager）
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', './chromedriver/chromedriver')
# 获取配置目录
CONFIG_DIRECTORY = os.getenv('CONFIG_DIRECTORY', 'config')


class AgentModelsConfig:
    """用于从YAML文件加载Agent模型配置的配置类。"""

    def __init__(self, config_path: str = 'config/agent_models.yaml'):
        """通过加载YAML文件来初始化配置。

        Args:
            config_path: YAML配置文件的路径。

        Raises:
            FileNotFoundError: 如果配置文件不存在。
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {config_path}") from e

    @property
    def agents(self):
        """获取agents配置。"""
        return self._config.get('agents', {})

    def get_agent_config(self, agent_name: str):
        """获取指定Agent的配置。

        Args:
            agent_name: Agent的名称。

        Returns:
            Agent配置字典，如果未找到则返回空字典。
        """
        return self.agents.get(agent_name, {})

    def get_provider(self, agent_name: str):
        """获取指定Agent的提供商。

        Args:
            agent_name: Agent的名称。

        Returns:
            提供商名称，如果未找到则返回None。
        """
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('provider')

    def get_model_config(self, agent_name: str):
        """获取指定Agent的模型配置。

        Args:
            agent_name: Agent的名称。

        Returns:
            模型配置字典，如果未找到则返回空字典。
        """
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get('model_config', {})


# 创建全局实例
AGENT_MODELS = AgentModelsConfig(os.path.join(CONFIG_DIRECTORY, 'agent_models.yaml'))