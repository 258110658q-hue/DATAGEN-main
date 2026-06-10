from typing import Any, Dict, List, Optional
from langchain.tools import BaseTool

from .basetool import execute_code, execute_command, list_directory
from .FileEdit import create_document, read_document, edit_document, collect_data
from .internet import google_search, scrape_webpages
from ..logger import setup_logger

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.agent_toolkits.load_tools import load_tools

logger = setup_logger()

# 初始化复杂工具
try:
    api_wrapper = WikipediaAPIWrapper(wiki_client=None)
    wikipedia = WikipediaQueryRun(api_wrapper=api_wrapper)
except Exception as e:
    logger.warning(f"Failed to initialize Wikipedia tool: {e}")
    wikipedia = None

try:
    arxiv_tools = load_tools(["arxiv"])
    arxiv = arxiv_tools[0] if arxiv_tools else None
except Exception as e:
    logger.warning(f"Failed to initialize Arxiv tool: {e}")
    arxiv = None

class ToolFactory:
    """按名称创建和检索工具实例的工厂类。"""

    _registry = {
        "execute_code": execute_code,
        "execute_command": execute_command,
        "list_directory": list_directory,
        "create_document": create_document,
        "read_document": read_document,
        "edit_document": edit_document,
        "collect_data": collect_data,
        "google_search": google_search,
        "scrape_webpages": scrape_webpages,
        "wikipedia": wikipedia,
        "arxiv": arxiv,
    }

    @classmethod
    def get_tool(cls, tool_name: str) -> Optional[BaseTool]:
        """按名称获取工具实例。

        Args:
            tool_name: 要检索的工具名称。

        Returns:
            工具实例，如果未找到则返回 None。
        """
        tool = cls._registry.get(tool_name)
        if not tool:
            logger.warning(f"Tool not found in registry: {tool_name}")
            return None
        return tool

    @classmethod
    def get_tools(cls, tool_names: List[str]) -> List[BaseTool]:
        """按名称列表获取工具实例。

        Args:
            tool_names: 要检索的工具名称列表。

        Returns:
            工具实例列表。对于缺失的工具会记录警告日志。
        """
        tools = []
        for name in tool_names:
            tool = cls.get_tool(name)
            if tool:
                tools.append(tool)
        return tools

    @classmethod
    def list_available_tools(cls) -> List[str]:
        """列出注册表中所有可用的工具名称。"""
        return list(cls._registry.keys())

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取当前工具配置。

        Returns:
            包含所有工具限制和设置的字典。
        """
        from .tool_config import TOOL_CONFIG
        return TOOL_CONFIG.to_dict()

    @classmethod
    def get_limits(cls) -> Dict[str, Any]:
        """获取当前执行和文件操作的限制。

        Returns:
            包含超时、内存和文件大小限制的字典。
        """
        from .tool_config import TOOL_CONFIG
        return {
            "execution": {
                "timeout_seconds": TOOL_CONFIG.execution.timeout_seconds,
                "max_memory_mb": TOOL_CONFIG.execution.max_memory_mb,
                "max_output_chars": TOOL_CONFIG.execution.max_output_chars,
                "progress_timeout_seconds": TOOL_CONFIG.execution.progress_timeout_seconds,
            },
            "file_operations": {
                "max_read_bytes": TOOL_CONFIG.file_ops.max_read_bytes,
                "max_read_lines": TOOL_CONFIG.file_ops.max_read_lines,
                "max_write_bytes": TOOL_CONFIG.file_ops.max_write_bytes,
            },
            "security_scan_enabled": TOOL_CONFIG.enable_security_scan,
            "write_validation_enabled": TOOL_CONFIG.enable_write_validation,
        }

    @classmethod
    async def get_mcp_tools_async(
        cls, server_names: List[str]
    ) -> List[BaseTool]:
        """从MCP服务器异步获取LangChain工具。

        Args:
            server_names: 要获取工具的MCP服务器名称列表。

        Returns:
            来自MCP服务器的LangChain工具实例列表。
        """
        from .mcp_tools import get_mcp_tools_async
        return await get_mcp_tools_async(server_names)

    @classmethod
    def get_mcp_tools(cls, server_names: List[str]) -> List[BaseTool]:
        """从MCP服务器同步获取LangChain工具。

        这是同步上下文的便捷包装方法。

        Args:
            server_names: 要获取工具的MCP服务器名称列表。

        Returns:
            来自MCP服务器的LangChain工具实例列表。
        """
        from .mcp_tools import get_mcp_tools_sync
        return get_mcp_tools_sync(server_names)
