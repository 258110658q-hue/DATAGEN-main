from __future__ import annotations
import logging
import asyncio
import os
import yaml
import re
import anyio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

"""本模块提供 MCP 服务器连接的管理以及为 Agent 暴露工具的功能。
它使用官方 MCP Python SDK 通过 stdio 传输进行真实的服务器通信。

参考: https://modelcontextprotocol.io/
"""


from ..logger import setup_logger


logger = setup_logger()
# 静默嘈杂的系统日志记录器
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("anyio").setLevel(logging.CRITICAL)


# 常量
MCP_SERVER_STOP_TIMEOUT = 5
CONNECTION_TIMEOUT = 30


@dataclass
class MCPServerConfig:
    """MCP 服务器的配置。

    Attributes:
        name: 服务器标识符。
        command: 启动服务器的命令。
        args: 命令行参数。
        env: 服务器的环境变量。
        description: 人类可读的描述。
    """
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass
class MCPResource:
    """MCP 服务器暴露的资源。

    Attributes:
        uri: 唯一的资源标识符。
        name: 人类可读的名称。
        mime_type: 资源的 MIME 类型。
        description: 可选的描述。
    """
    uri: str
    name: str
    mime_type: str = "text/plain"
    description: str = ""


@dataclass
class MCPTool:
    """MCP 服务器暴露的工具。

    Attributes:
        name: 工具标识符。
        description: 人类可读的描述。
        input_schema: 工具输入的 JSON schema。
        server_name: 提供该工具的服务器的名称。
    """
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


@dataclass
class MCPServerConnection:
    """到 MCP 服务器的活动连接。

    Attributes:
        name: 服务器名称标识符。
        session: 用于通信的 MCP ClientSession。
        client_context: 传输的上下文管理器（例如 stdio）。
        session_context: 会话的上下文管理器。
        loop: 该连接所属的事件循环。
    """
    name: str
    session: Any  # mcp.ClientSession
    client_context: Any  # 传输的上下文管理器
    session_context: Any  # 会话的上下文管理器
    loop: Any = None  # 该连接所属的事件循环


class MCPManager:
    """管理 MCP 服务器连接和工具暴露。

    此管理器处理：
    - 加载 MCP 服务器配置
    - 通过 stdio 传输启动和停止 MCP 服务器
    - 发现服务器上的工具和资源
    - 在已连接的服务器上调用工具
    - 根据 Agent 的配置为其提供工具

    Attributes:
        config_path: MCP 配置文件的路径。
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """初始化 MCP 管理器。

        Args:
            config_path: MCP 配置文件的路径。
        """
        if config_path is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            config_dir = os.getenv('CONFIG_DIRECTORY', 'config')
            config_path = os.path.join(config_dir, "mcp.yaml")

        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._servers: Dict[str, MCPServerConfig] = {}
        self._connections: Dict[str, MCPServerConnection] = {}
        self._connection_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._mcp_stderr_file = None

        # 设置循环异常处理器以吞掉嘈杂的 anyio/asyncio 错误
        try:
            loop = asyncio.get_event_loop()
            def silent_exception_handler(loop, context):
                msg = context.get("message", "")
                if "asynchronous generator" in msg or "cancel scope" in msg:
                    return
                loop.default_exception_handler(context)
            loop.set_exception_handler(silent_exception_handler)
        except Exception:
            pass

    def _get_lock(self, server_name: str) -> asyncio.Lock:
        """获取或创建一个特定服务器的锁。"""
        if server_name not in self._connection_locks:
            self._connection_locks[server_name] = asyncio.Lock()
        return self._connection_locks[server_name]

    @property
    def config(self) -> Dict[str, Any]:
        """延迟加载 MCP 配置。

        Returns:
            配置字典。
        """
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def get_server_config(self, name: str) -> Optional[MCPServerConfig]:
        """获取特定 MCP 服务器的配置。

        Args:
            name: 服务器名称。

        Returns:
            MCPServerConfig，如果未找到则返回 None。
        """
        if name in self._servers:
            return self._servers[name]

        servers = self.config.get("servers", {})
        if name not in servers:
            logger.warning(f"未找到 MCP 服务器: {name}")
            return None

        server_config = servers[name]
        mcp_config = MCPServerConfig(
            name=name,
            command=server_config.get("command", ""),
            args=server_config.get("args", []),
            env=server_config.get("env", {}),
            description=server_config.get("description", ""),
        )
        self._servers[name] = mcp_config
        return mcp_config

    def get_enabled_servers(self, agent_name: str) -> List[MCPServerConfig]:
        """获取为某个 Agent 启用的 MCP 服务器列表。

        Args:
            agent_name: Agent 的名称。

        Returns:
            已启用的服务器的 MCPServerConfig 列表。
        """
        from .agent_config_loader import get_agent_config_loader

        loader = get_agent_config_loader()
        mcp_config = loader.load_mcp_config(agent_name)

        servers = []
        for name in mcp_config.get("servers", {}).keys():
            config = self.get_server_config(name)
            if config:
                servers.append(config)

        return servers

    async def connect(self, server_name: str) -> bool:
        """通过 stdio 传输连接到 MCP 服务器。

        Args:
            server_name: 要连接的服务器的名称。

        Returns:
            如果连接成功则返回 True，否则返回 False。
        """
        # 获取或创建该服务器的锁
        async with self._global_lock:
            if server_name not in self._connection_locks:
                self._connection_locks[server_name] = asyncio.Lock()
        """带锁连接到 MCP 服务器。"""
        async with self._get_lock(server_name):
            # 检查是否已连接且处于活动状态
            if server_name in self._connections:
                conn = self._connections[server_name]
                if conn.session:
                    return True
                else:
                    # 清理已损坏的连接
                    await self._close_server_connection(server_name)

            config = self.get_server_config(server_name)
            if not config:
                logger.error(f"未找到 MCP 服务器的配置: {server_name}")
                return False

            try:
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client

                env = os.environ.copy()
                for key, value in config.env.items():
                    env[key] = value

                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=env
                )

                logger.info(f"正在连接到 MCP 服务器: {server_name}...")

                # 重定向 stderr 以避免 MCP 服务器的控制台噪音
                if self._mcp_stderr_file is None:
                    try:
                        # 确保 logs 目录存在
                        os.makedirs("logs", exist_ok=True)
                        self._mcp_stderr_file = open("logs/mcp_servers.log", "a", encoding="utf-8")
                    except Exception:
                        self._mcp_stderr_file = sys.stderr

                # 使用上下文管理器，但手动处理以保持流存活
                client_context = stdio_client(server_params, errlog=self._mcp_stderr_file)
                read_stream, write_stream = await client_context.__aenter__()

                session_context = ClientSession(read_stream, write_stream)
                session = await session_context.__aenter__()
                await session.initialize()

                self._connections[server_name] = MCPServerConnection(
                    name=server_name,
                    client_context=client_context,
                    session_context=session_context,
                    session=session,
                    loop=asyncio.get_running_loop()
                )
                logger.info(f"成功连接到 {server_name}")
                return True
            except Exception as e:
                logger.error(f"连接 {server_name} 失败: {str(e)}", exc_info=True)
                return False

    async def _close_server_connection(self, server_name: str) -> None:
        """内部辅助函数，用于干净地关闭一个连接。"""
        conn = self._connections.pop(server_name, None)
        if conn:
            try:
                # 尝试优雅地关闭会话和客户端上下文。
                # 捕获 anyio 特定的任务不匹配或已关闭资源错误，
                # 这些错误发生在循环切换或任务被突然终止时。
                if conn.session_context:
                    try:
                        await conn.session_context.__aexit__(None, None, None)
                    except (anyio.ClosedResourceError, RuntimeError, Exception) as e:
                        logger.debug(f"关闭 {server_name} 的会话上下文时发生非致命错误: {e}")

                if conn.client_context:
                    try:
                        await conn.client_context.__aexit__(None, None, None)
                    except (anyio.ClosedResourceError, RuntimeError, Exception) as e:
                        logger.debug(f"关闭 {server_name} 的客户端上下文时发生非致命错误: {e}")
            except Exception as e:
                logger.debug(f"清理 {server_name} 时发生错误: {e}")

    async def disconnect(self, server_name: str) -> None:
        """断开与 MCP 服务器的连接。

        Args:
            server_name: 要断开连接的服务器的名称。
        """
        async with self._get_lock(server_name):
            await self._close_server_connection(server_name)
            logger.info(f"已断开与 MCP 服务器的连接: {server_name}")

    async def close_all(self) -> None:
        """断开所有 MCP 服务器的连接。"""
        server_names = list(self._connections.keys())
        for name in server_names:
            await self.disconnect(name)
        logger.info("所有 MCP 连接已关闭")

    async def _get_or_create_connection(
        self, server_name: str
    ) -> Optional[MCPServerConnection]:
        """获取现有连接或创建一个新连接，具有循环感知能力。"""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if server_name in self._connections:
            conn = self._connections[server_name]
            # 验证连接是否对当前循环有效
            if conn.loop is current_loop and conn.session:
                return conn
            else:
                logger.debug(f"检测到 {server_name} 存在过期或循环不匹配的连接。正在重新连接...")
                await self.disconnect(server_name)

        success = await self.connect(server_name)
        if not success:
            return None

        return self._connections.get(server_name)

    async def discover_tools(self, server_name: str) -> List[MCPTool]:
        """从 MCP 服务器发现工具，具有健壮的重试机制。

        Args:
            server_name: MCP 服务器的名称。

        Returns:
            从服务器发现的 MCPTool 对象列表。
        """
        for attempt in range(2):
            conn = await self._get_or_create_connection(server_name)
            if not conn:
                logger.error(f"无法发现工具: 未连接到 {server_name}")
                return []

            try:
                tools_response = await conn.session.list_tools()

                tools = []
                for tool in tools_response.tools:
                    tools.append(MCPTool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                        server_name=server_name,
                    ))
                logger.info(f"从 {server_name} 发现了 {len(tools)} 个工具")
                return tools
            except Exception as e:
                logger.warning(f"从 {server_name} 发现工具失败 (尝试 {attempt+1}/2): {e}")
                # 重试前强制断开连接
                await self.disconnect(server_name)
                if attempt == 1:
                    logger.error(f"已达到 {server_name} 工具发现的最大重试次数")
                    return []

    async def list_resources(self, server_name: str) -> List[MCPResource]:
        """列出 MCP 服务器上可用的资源。

        Args:
            server_name: MCP 服务器的名称。

        Returns:
            MCPResource 对象列表。
        """
        conn = await self._get_or_create_connection(server_name)
        if not conn:
            logger.error(f"无法列出资源: 未连接到 {server_name}")
            return []

        try:
            resources_response = await conn.session.list_resources()
            resources = []
            for resource in resources_response.resources:
                resources.append(MCPResource(
                    uri=str(resource.uri),
                    name=resource.name or str(resource.uri),
                    mime_type=resource.mimeType if hasattr(resource, 'mimeType') else "text/plain",
                    description=resource.description if hasattr(resource, 'description') else "",
                ))
            logger.info(f"从 {server_name} 找到了 {len(resources)} 个资源")
            return resources
        except Exception as e:
            logger.error(f"从 {server_name} 列出资源失败: {e}")
            return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """在服务器上调用工具，具有健壮的重试和会话验证机制。"""
        if arguments is None:
            arguments = {}

        for attempt in range(3):
            try:
                # 使用循环感知的连接获取器，确保我们使用的是
                # 绑定到当前事件循环的连接。
                conn = await self._get_or_create_connection(server_name)
                if not conn or not conn.session:
                    raise Exception(f"未能建立或检索到 {server_name} 的有效连接")

                # 调用工具
                from mcp import types as mcp_types
                result = await conn.session.call_tool(tool_name, arguments)

                # 从结果中提取内容
                contents = []
                for content in result.content:
                    text = ""
                    if isinstance(content, mcp_types.TextContent):
                        text = content.text
                    elif hasattr(content, 'text'):
                        text = content.text
                    elif hasattr(content, 'data'):
                        contents.append(f"[二进制数据: {len(content.data)} 字节]")
                        continue
                    else:
                        text = str(content)

                    # 过滤掉有时会泄漏到 stdout 的常见 MCP 启动横幅
                    if "Secure MCP Filesystem Server running on stdio" in text:
                        continue
                    if "Client does not support MCP Roots" in text:
                        continue

                    if text:
                        contents.append(text)

                return "\n".join(contents)

            except Exception as e:
                error_msg = str(e) or e.__class__.__name__
                logger.warning(f"工具调用失败 (尝试 {attempt+1}/3) 针对 {server_name}.{tool_name}: {error_msg}")
                if attempt < 2:
                    # 重试前强制断开连接并清除会话
                    await self.disconnect(server_name)
                    # 对 filesystem 使用稍长的退避时间，以允许操作系统资源清理
                    backoff = 1.0 if server_name != "filesystem" else 1.5
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"已达到 {server_name} 上工具 {tool_name} 的最大重试次数")
                    raise e

    async def read_resource(self, server_name: str, uri: str) -> str:
        """从 MCP 服务器读取资源。

        Args:
            server_name: MCP 服务器的名称。
            uri: 要读取的资源的 URI。

        Returns:
            作为字符串的资源内容。
        """
        conn = await self._get_or_create_connection(server_name)
        if not conn:
            return f"错误: 未连接到 MCP 服务器 {server_name}"

        try:
            from mcp import types as mcp_types

            result = await conn.session.read_resource(uri)

            contents = []
            for content in result.contents:
                if isinstance(content, mcp_types.TextContent):
                    contents.append(content.text)
                elif hasattr(content, 'text'):
                    contents.append(content.text)
                else:
                    contents.append(str(content))

            return "\n".join(contents)

        except Exception as e:
            error_msg = f"读取资源 {uri} 时出错: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools_for_agent(self, agent_name: str) -> List[MCPTool]:
        """获取为某个 Agent 启用的 MCP 服务器上的所有工具（同步包装器）。

        这是一个运行异步版本的同步包装器。
        对于新代码，建议直接使用 discover_tools()。

        Args:
            agent_name: Agent 的名称。

        Returns:
            MCPTool 对象列表。
        """
        servers = self.get_enabled_servers(agent_name)
        if not servers:
            return []

        async def _gather_tools():
            all_tools = []
            for server in servers:
                tools = await self.discover_tools(server.name)
                all_tools.extend(tools)
            return all_tools

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if self._main_loop and self._main_loop.is_running():
                # 使用专用的后台循环
                from concurrent.futures import Future
                def _run():
                    return asyncio.run_coroutine_threadsafe(_gather_tools(), self._main_loop).result(timeout=60)

                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return executor.submit(_run).result()

            if loop and loop.is_running():
                # 我们在异步上下文中，在单独的线程中创建一个新任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _gather_tools())
                    return future.result(timeout=60)
            else:
                return asyncio.run(_gather_tools())
        except Exception as e:
            logger.warning(f"获取 {agent_name} 的工具失败: {e}")
            return []

    def _load_config(self) -> Dict[str, Any]:
        """从 YAML 文件加载 MCP 配置。

        Returns:
            配置字典。
        """
        if not self.config_path.exists():
            logger.warning(f"未找到 MCP 配置: {self.config_path}")
            return {"servers": {}, "defaults": []}

        try:
            content = self.config_path.read_text(encoding="utf-8")
            config = yaml.safe_load(content)
            return self._expand_env_vars(config)
        except yaml.YAMLError as e:
            logger.error(f"解析 MCP 配置失败: {e}")
            return {"servers": {}, "defaults": []}

    def _expand_env_vars(self, obj: Any) -> Any:
        """递归展开配置中的环境变量。

        Args:
            obj: 配置对象。

        Returns:
            环境变量已展开的对象。
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            pattern = re.compile(r"\$\{([^}]+)\}")
            def replace(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            return pattern.sub(replace, obj)
        return obj


# 单例实例
_default_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """获取默认的 MCPManager 单例。

    Returns:
        MCPManager 实例。
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = MCPManager()
    return _default_manager


def reset_mcp_manager() -> None:
    """重置 MCPManager 单例。

    用于测试或需要重新配置时。
    """
    global _default_manager
    if _default_manager is not None:
        # 尝试清理连接
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and not loop.is_running():
                loop.run_until_complete(_default_manager.close_all())
            elif not loop:
                asyncio.run(_default_manager.close_all())
        except Exception:
            pass
    _default_manager = None
