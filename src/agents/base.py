from __future__ import annotations
"""Base agent class with external configuration support.

This module provides the abstract base class for all agents in the system.
It integrates with the AgentConfigLoader for external system prompts and
supports fallback to hardcoded prompts for backward compatibility.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

from ..logger import setup_logger
from ..config import WORKING_DIRECTORY

if TYPE_CHECKING:
    from ..core.language_models import LanguageModelManager
    from ..core.agent_config_loader import AgentConfigLoader

logger = setup_logger()


class BaseAgent(ABC):
    """An abstract base class for all agents.

    Supports both external configuration (via AgentConfigLoader) and
    hardcoded system prompts for backward compatibility.

    Attributes:
        agent_name: The name of the agent for configuration lookup.
        language_model_manager: Manager for language model configuration.
        team_members: List of team member roles for collaboration.
        working_directory: The directory where the agent's data will be stored.
        response_format: Optional format specification for structured output.
    """


    # Constants
    SYSTEM_PROMPT_PREFIX = "SYSTEM_PROMPT:"

    # Class-level config loader (shared across all agents)
    _config_loader: AgentConfigLoader | None = None

    @classmethod
    def get_config_loader(cls) -> AgentConfigLoader:
        """Get or create the shared AgentConfigLoader instance.

        Returns:
            AgentConfigLoader instance.
        """
        if cls._config_loader is None:
            from ..core.agent_config_loader import AgentConfigLoader
            cls._config_loader = AgentConfigLoader()
        return cls._config_loader

    def __init__(
        self,
        agent_name: str,
        language_model_manager: LanguageModelManager,
        team_members: list[str],
        working_directory: str = WORKING_DIRECTORY,
        response_format: Any = None
    ) -> None:
        """Initialize the base agent with common creation logic.

        Args:
            agent_name: The name of the agent for configuration lookup.
            language_model_manager: Manager for language model configuration.
            team_members: List of team member roles for collaboration.
            working_directory: The directory where the agent's data will be stored.
            response_format: Optional format specification for structured output.
        """
        self.agent_name = agent_name
        self.language_model_manager = language_model_manager
        self.team_members = team_members
        self.working_directory = working_directory
        self.response_format = response_format

        # Create the language model
        self.model = self._create_model()

        # Load system prompt (external config → fallback to hardcoded)
        role_prompt = self._load_system_prompt()
        
        # Load all tools in priority order
        tools = self._load_all_tools()

        # Get agent-specific runtime config
        agent_config = self.language_model_manager.get_agent_config(self.agent_name)
        self.max_iterations = agent_config.get('max_iterations', 15)

        # Create the agent executor
        self.agent = self._create_base_agent(
            self.model,
            tools,
            role_prompt,
            team_members,
            response_format,
            max_iterations=self.max_iterations,
        )

    def _load_all_tools(self) -> list[Any]:
        """Load all tools from various sources in priority order.
        
        Attempts external config tools first, falls back to hardcoded tools
        if config is empty, then appends skill tools and MCP tools.
        
        Returns:
            Combined list of all available tools.
        """
        tools: list[Any] = []
        
        # Load from external config first
        config_tools = self._load_tools_from_config()
        if config_tools:
            tools.extend(config_tools)
            logger.info(f"Loaded {len(config_tools)} tools from config for {self.agent_name}")
        else:
            # Fallback to hardcoded tools
            hardcoded_tools = self._get_tools()
            if hardcoded_tools:
                tools.extend(hardcoded_tools)
                logger.debug(f"Using {len(hardcoded_tools)} hardcoded tools for {self.agent_name}")

        # Append skill tools if configured
        try:
            loader = self.get_config_loader()
            metadata = loader.load_metadata(self.agent_name)
            if metadata.skills:
                from ..tools.skills import LookupSkill
                tools.append(LookupSkill())
                logger.info(f"Added LookupSkill tool for {self.agent_name}")
        except Exception as e:
            logger.warning(f"Failed to check skills for {self.agent_name}: {e}")

        # Append MCP tools if configured
        mcp_tools = self._load_mcp_tools()
        if mcp_tools:
            tools.extend(mcp_tools)
            logger.info(f"Loaded {len(mcp_tools)} MCP tools for {self.agent_name}")
        
        return tools

    def _load_tools_from_config(self) -> list[Any]:
        """Load tools from external configuration.

        Returns:
            List of tool instances, or empty list if no tools configured.
        """
        try:
            loader = self.get_config_loader()
            metadata = loader.load_metadata(self.agent_name)
            
            if not metadata.tools:
                return []
                
            from ..tools.factory import ToolFactory
            tools = ToolFactory.get_tools(metadata.tools)
            return tools
        except Exception as e:
            logger.warning(f"Failed to load tools from config for {self.agent_name}: {e}")
            return []

    def _load_mcp_tools(self) -> list[Any]:
        """Load MCP tools based on agent configuration.

        Reads the agent's MCP server configuration and creates LangChain
        tool adapters for all tools exposed by the configured MCP servers.

        Returns:
            List of MCP tool adapters, or empty list if no MCP servers configured.
        """
        try:
            loader = self.get_config_loader()
            mcp_config = loader.load_mcp_config(self.agent_name)
            server_names = list(mcp_config.get("servers", {}).keys())

            if not server_names:
                return []

            from ..tools.factory import ToolFactory
            mcp_tools = ToolFactory.get_mcp_tools(server_names)
            return mcp_tools
        except Exception as e:
            logger.warning(f"Failed to load MCP tools for {self.agent_name}: {e}")
            return []

    def _create_base_agent(
        self,
        model,
        tools: list,
        role_prompt: str,
        team_members: list[str],
        response_format: Any = None,
        max_iterations: int = 15,
    ):
        """Create an agent with the given parameters.

        Args:
            model: The language model to use for the agent.
            tools: List of tools available to the agent.
            role_prompt: The role prompt defining the agent's behavior.
            team_members: List of team member roles for collaboration.
            response_format: Optional format specification for structured output.
        """
        
        # Prepare system prompt
        tool_names = ", ".join([tool.name for tool in tools])
        team_members_str = ", ".join(team_members)

        # 统一的停止指令，追加到所有 Agent 的系统提示中
        STOP_INSTRUCTION = (
            "\n\n【关键指令】当你已经收集到足够的信息并完成任务后，"
            "必须直接输出最终答案的纯文本，不要再调用任何工具。"
            "不要用相同的参数反复调用同一个工具。"
            "对于数据采集任务，调用工具 2-3 次就足够了。"
        )

        # 检查 role_prompt 是否包含完整的系统提示
        if role_prompt.startswith(self.SYSTEM_PROMPT_PREFIX):
            # 直接使用完整的系统提示（去掉前缀）+ 停止指令
            system_prompt = role_prompt[len(self.SYSTEM_PROMPT_PREFIX):] + STOP_INSTRUCTION
        else:
            # 使用系统提示组合逻辑
            system_prompt = (
                "你是数据分析团队中的一名专业 AI 助手。"
                "你的职责是完成研究流程中的特定任务。"
                "使用提供的工具来推进你的任务。"
                "如果你无法完全完成任务，请说明你已完成的工作以及下一步需要做什么。"
                "始终追求准确和清晰的输出。"
                f"你可以使用以下工具：{tool_names}。"
                f"你的具体角色：{role_prompt}\n"
                "根据你的专长自主工作，使用你可用的工具。"
                "不要请求澄清。"
                f"你的其他团队成员将根据各自的专长与你协作。"
                f"你被选中是有原因的！你是团队中的 {self.agent_name}，团队成员包括：{team_members_str}。\n"
                "需要时使用 ListDirectoryContents 工具检查目录内容的更新。\n"
                "【重要】当你已经获得足够信息完成任务时，直接输出最终答案的纯文本，不要继续调用工具。"
                "绝不用相同参数重复调用同一工具。"
            )

        # Create agent
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            response_format=response_format,
        )

        # Iterate limits configuration
        # Verify if the agent supports max_iterations (e.g. AgentExecutor)
        if hasattr(agent, "max_iterations"):
            agent.max_iterations = max_iterations
            logger.info(f"Set max_iterations={max_iterations} for {self.agent_name}")
        else:
             pass

        logger.info(f"{self.agent_name} created successfully")
        return agent

    def _create_model(self) -> ChatOpenAI:
        """Create a model instance for this agent.

        Returns:
            Configured language model instance.
        """
        provider = self.language_model_manager.get_provider(self.agent_name)
        model_class = provider.get_model_class()
        config = self.language_model_manager.get_model_config(self.agent_name).copy()
        
        # Add a default timeout to prevent indefinite hanging
        if "timeout" not in config:
            config["timeout"] = 60
            
        return model_class(**config)

    def invoke(self, state: Any) -> Any:
        """Invoke the agent with a given state.

        Args:
            state: The current state of the workflow.

        Returns:
            The agent's response (type may vary).
        """
        # Pass max_iterations as recursion_limit in config
        config = {"recursion_limit": self.max_iterations}
        return self.agent.invoke(state, config=config)

    def _load_system_prompt(self) -> str:
        """Load system prompt from external config or fallback to hardcoded.

        This method implements a two-stage loading strategy:
        1. Try to load from external AGENT.md configuration
        2. Fall back to the subclass's _get_system_prompt() method

        Returns:
            System prompt string.
        """
        try:
            loader = self.get_config_loader()
            prompt = loader.load_system_prompt(self.agent_name)
            logger.info(f"Loaded external config for {self.agent_name}")
            return prompt
        except FileNotFoundError:
            # Fallback to hardcoded prompt from subclass
            logger.debug(
                f"No external config for {self.agent_name}, using hardcoded prompt"
            )
            return self._get_system_prompt()
        except Exception as e:
            logger.warning(
                f"Failed to load external config for {self.agent_name}: {e}, "
                "falling back to hardcoded prompt"
            )
            return self._get_system_prompt()

    def _get_system_prompt(self) -> str:
        """Get the hardcoded system prompt for this agent.

        Subclasses can override this to provide a fallback system prompt
        when external configuration is not available.

        Returns:
            A string containing the system prompt.
        """
        return ""

    @abstractmethod
    def _get_tools(self) -> list[Any]:
        """Get the list of tools specific to this agent.

        Returns:
            A list of tools the agent can use.
        """
        pass

    def get_state_updates(self, state: Any, output: Any) -> dict[str, Any]:
        """Return state field updates based on agent output.
        
        Default implementation returns empty dict (no custom updates).
        Subclasses can override to provide custom state mapping.
        
        This method implements the StateUpdater protocol, allowing agents
        to decouple their state update logic from the central agent_node.
        
        Args:
            state: The current workflow state.
            output: The agent's structured or raw output.
            
        Returns:
            Dict mapping state field names to their new values.
        """
        return {}