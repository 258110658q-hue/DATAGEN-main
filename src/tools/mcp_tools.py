"""MCP（Model Context Protocol）工具的 LangChain 工具适配器。

本模块提供将 MCP 工具包装为 LangChain 工具的适配器，
实现 MCP 服务器与 LangChain Agent 之间的无缝集成。

示例:
    from src.tools.mcp_tools import create_mcp_tool_adapters
    from src.core.mcp_manager import get_mcp_manager

    manager = get_mcp_manager()
    mcp_tools = await manager.discover_tools("filesystem")
    langchain_tools = create_mcp_tool_adapters(mcp_tools, "filesystem")
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field, create_model

from ..logger import setup_logger


logger = setup_logger()


def _create_args_schema(
    tool_name: str,
    input_schema: Dict[str, Any]
) -> Type[BaseModel]:
    """根据 JSON schema 创建用于工具参数的 Pydantic 模型。

    Args:
        tool_name: 工具名称（用于模型命名）。
        input_schema: 工具输入的 JSON schema。

    Returns:
        表示该 schema 的 Pydantic BaseModel 类。
    """
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    field_definitions = {}
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        description = prop_schema.get("description", "")
        default = ... if prop_name in required else None

        # 将 JSON schema 类型映射为 Python 类型
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_mapping.get(prop_type, str)

        # 处理可选类型
        if prop_name not in required:
            python_type = Optional[python_type]

        field_definitions[prop_name] = (
            python_type,
            Field(default=default, description=description)
        )

    # 创建动态 Pydantic 模型
    model_name = f"{tool_name.replace('-', '_').title()}Args"
    if not field_definitions:
        # 空 schema —— 创建一个简单的模型
        return create_model(model_name)

    return create_model(model_name, **field_definitions)


class MCPToolAdapter(BaseTool):
    """将 MCP 工具包装为 LangChain 工具的适配器。

    本适配器负责在 LangChain 的工具接口
    与 MCP 的工具调用协议之间进行转换。

    Attributes:
        name: 工具名称。
        description: 工具描述。
        mcp_server: 提供此工具的 MCP 服务器名称。
        mcp_tool_name: MCP 服务器上的原始工具名称。
        args_schema: 用于参数校验的 Pydantic 模型。
    """

    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    mcp_server: str = Field(..., description="MCP 服务器名称")
    mcp_tool_name: str = Field(..., description="原始 MCP 工具名称")
    args_schema: Type[BaseModel] = Field(..., description="参数 schema")

    def _run(self, **kwargs: Any) -> str:
        """同步执行 —— 包装异步调用。

        Args:
            **kwargs: 工具参数。

        Returns:
            工具执行结果（字符串）。
        """
        try:
            from ..core.mcp_manager import get_mcp_manager
            manager = get_mcp_manager()

            if manager._main_loop and manager._main_loop.is_running():
                # 使用专用的后台事件循环
                def _run_async():
                    return asyncio.run_coroutine_threadsafe(self._arun(**kwargs), manager._main_loop).result(timeout=120)

                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return executor.submit(_run_async).result()

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # 如果当前已在运行中的事件循环内，则必须在单独的线程中
                # 运行异步工具调用，以避免嵌套事件循环。
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(**kwargs)
                    )
                    return future.result(timeout=120)
            else:
                # 当前线程中没有正在运行的事件循环，可以安全地使用 asyncio.run
                return asyncio.run(self._arun(**kwargs))
        except Exception as e:
            error_msg = f"Error executing MCP tool {self.name}: {e}"
            logger.error(error_msg)
            return error_msg

    async def _arun(self, **kwargs: Any) -> str:
        """通过 MCP 管理器进行异步执行。

        Args:
            **kwargs: 工具参数。

        Returns:
            工具执行结果（字符串）。
        """
        from ..core.mcp_manager import get_mcp_manager

        manager = get_mcp_manager()
        result = await manager.call_tool(
            self.mcp_server,
            self.mcp_tool_name,
            kwargs
        )
        return result


def create_mcp_tool_adapter(
    tool_name: str,
    tool_description: str,
    input_schema: Dict[str, Any],
    server_name: str,
) -> MCPToolAdapter:
    """根据 MCP 工具信息创建一个 LangChain 工具适配器。

    Args:
        tool_name: MCP 工具的名称。
        tool_description: 工具的描述。
        input_schema: 工具输入的 JSON schema。
        server_name: MCP 服务器的名称。

    Returns:
        MCPToolAdapter 实例。
    """
    args_schema = _create_args_schema(tool_name, input_schema)

    # 创建带前缀的名称以避免冲突
    prefixed_name = f"mcp_{server_name}_{tool_name}"

    return MCPToolAdapter(
        name=prefixed_name,
        description=f"[MCP:{server_name}] {tool_description}",
        mcp_server=server_name,
        mcp_tool_name=tool_name,
        args_schema=args_schema,
    )


def create_mcp_tool_adapters(
    mcp_tools: List[Any],
    server_name: str,
) -> List[MCPToolAdapter]:
    """根据 MCP 工具列表创建 LangChain 工具适配器列表。

    Args:
        mcp_tools: MCPTool 对象列表。
        server_name: MCP 服务器的名称。

    Returns:
        MCPToolAdapter 实例列表。
    """
    adapters = []
    for tool in mcp_tools:
        try:
            adapter = create_mcp_tool_adapter(
                tool_name=tool.name,
                tool_description=tool.description,
                input_schema=tool.input_schema,
                server_name=server_name,
            )
            adapters.append(adapter)
            logger.debug(f"已为 MCP 工具创建适配器: {tool.name}")
        except Exception as e:
            logger.warning(f"为 {tool.name} 创建适配器失败: {e}")

    return adapters


async def get_mcp_tools_async(server_names: List[str]) -> List[MCPToolAdapter]:
    """异步从 MCP 服务器获取 LangChain 工具。

    Args:
        server_names: 要获取工具的 MCP 服务器名称列表。

    Returns:
        MCPToolAdapter 实例列表。
    """
    from ..core.mcp_manager import get_mcp_manager

    manager = get_mcp_manager()
    all_tools = []

    for server_name in server_names:
        try:
            mcp_tools = await manager.discover_tools(server_name)
            adapters = create_mcp_tool_adapters(mcp_tools, server_name)
            all_tools.extend(adapters)
            logger.info(
                f"从 MCP 服务器加载了 {len(adapters)} 个工具: {server_name}"
            )
        except Exception as e:
            logger.warning(
                f"从 {server_name} 加载工具失败: {e}"
            )

    return all_tools


def get_mcp_tools_sync(server_names: List[str]) -> List[MCPToolAdapter]:
    """同步从 MCP 服务器获取 LangChain 工具。

    这是一个用于同步上下文的便捷包装函数。

    Args:
        server_names: 要获取工具的 MCP 服务器名称列表。

    Returns:
        MCPToolAdapter 实例列表。
    """
    try:
        from ..core.mcp_manager import get_mcp_manager
        manager = get_mcp_manager()

        if manager._main_loop and manager._main_loop.is_running():
            def _get_async():
                return asyncio.run_coroutine_threadsafe(get_mcp_tools_async(server_names), manager._main_loop).result(timeout=120)

            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(_get_async).result()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    get_mcp_tools_async(server_names)
                )
                return future.result(timeout=120)
        else:
            return asyncio.run(get_mcp_tools_async(server_names))
    except Exception as e:
        logger.error(f"获取 MCP 工具失败: {e}")
        return []
