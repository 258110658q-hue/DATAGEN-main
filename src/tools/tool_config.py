from __future__ import annotations
"""工具安全和资源限制的集中配置。

本模块提供工具限制的数据类以及配置管理器，
通过 YAML 加载设置并在缺失时回退到默认值。
"""

from dataclasses import dataclass, field
from typing import List, Optional
import os
import yaml
from pathlib import Path

from ..logger import setup_logger

logger = setup_logger()

# 默认常量
DEFAULT_MAX_OUTPUT_CHARS = 50000
DEFAULT_MAX_READ_BYTES = 5 * 1024 * 1024  # 5MB
DEFAULT_MAX_READ_LINES = 10000
DEFAULT_MAX_WRITE_BYTES = 10 * 1024 * 1024  # 10MB


@dataclass
class ExecutionLimits:
    """代码执行的资源限制。

    Attributes:
        timeout_seconds: 最大执行时间。None 表示无限制。
        max_memory_mb: 最大内存使用量（仅 Linux）。None 表示无限制。
        max_output_chars: 超过此限制时截断输出。
        progress_timeout_seconds: 若设置，则在有 stdout 活动时重置超时。
        blocked_patterns: 需要阻止的代码模式（安全）。
    """
    timeout_seconds: Optional[int] = None
    max_memory_mb: Optional[int] = None
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS
    progress_timeout_seconds: Optional[int] = None
    blocked_patterns: List[str] = field(default_factory=lambda: [
        "os.system",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
        "shutil.rmtree",
        "eval(",
        "exec(",
        "__import__",
    ])


@dataclass
class FileOperationLimits:
    """文件读写操作的限制。

    Attributes:
        max_read_bytes: 可读取的最大文件大小。
        max_read_lines: 可返回的最大行数。
        max_write_bytes: 可写入的最大内容大小。
        allowed_extensions: 允许的文件扩展名白名单。
        blocked_paths: 不可访问的路径。
    """
    max_read_bytes: int = DEFAULT_MAX_READ_BYTES
    max_read_lines: int = DEFAULT_MAX_READ_LINES
    max_write_bytes: int = DEFAULT_MAX_WRITE_BYTES
    allowed_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".md", ".txt", ".csv", ".json", ".yaml", ".yml",
        ".log", ".png", ".jpg", ".jpeg", ".html", ".css", ".js"
    ])
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/sys", "/proc", "/root", "~/.ssh", "/var/log"
    ])


class ToolConfig:
    """所有工具的集中配置管理器。

    从 YAML 配置文件加载设置，缺失时回退到默认值。
    通过全局 TOOL_CONFIG 提供类似单例的访问模式。
    """

    def __init__(
        self,
        execution: Optional[ExecutionLimits] = None,
        file_ops: Optional[FileOperationLimits] = None,
        enable_security_scan: bool = True,
        enable_write_validation: bool = True
    ):
        """初始化工具配置。

        Args:
            execution: 执行限制配置。
            file_ops: 文件操作限制配置。
            enable_security_scan: 是否扫描代码中的危险模式。
            enable_write_validation: 是否在写入前验证内容。
        """
        self.execution = execution or ExecutionLimits()
        self.file_ops = file_ops or FileOperationLimits()
        self.enable_security_scan = enable_security_scan
        self.enable_write_validation = enable_write_validation

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> ToolConfig:
        """从 YAML 文件加载配置，缺失时以默认值作为回退。

        Args:
            config_path: YAML 配置文件的路径（相对于项目根目录）。

        Returns:
            带有已加载设置或默认设置的 ToolConfig 实例。
        """
        if config_path is None:
            config_dir = os.getenv('CONFIG_DIRECTORY', 'config')
            config_path = os.path.join(config_dir, "tool_limits.yaml")
        settings = {}

        # 尝试多个路径以找到配置文件
        possible_paths = [
            Path(config_path),
            Path(os.getcwd()) / config_path,
            Path(__file__).parent.parent.parent.parent / config_path,
        ]

        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        settings = yaml.safe_load(f) or {}
                    logger.info(f"从 {path} 加载工具限制配置")
                    break
                except Exception as e:
                    logger.warning(f"从 {path} 加载工具限制配置失败：{e}")

        if not settings:
            logger.debug("未找到工具限制配置文件，使用默认设置")

        # 解析执行设置
        exec_settings = settings.get("execution", {})
        exec_limits = ExecutionLimits(
            timeout_seconds=exec_settings.get("timeout_seconds"),
            max_memory_mb=exec_settings.get("max_memory_mb"),
            max_output_chars=exec_settings.get("max_output_chars", 50000),
            progress_timeout_seconds=exec_settings.get("progress_timeout_seconds"),
            blocked_patterns=exec_settings.get("blocked_patterns", ExecutionLimits().blocked_patterns),
        )

        # 解析文件操作设置
        file_settings = settings.get("file_operations", {})
        file_limits = FileOperationLimits(
            max_read_bytes=file_settings.get("max_read_bytes", 5 * 1024 * 1024),
            max_read_lines=file_settings.get("max_read_lines", 10000),
            max_write_bytes=file_settings.get("max_write_bytes", 10 * 1024 * 1024),
            allowed_extensions=file_settings.get("allowed_extensions", FileOperationLimits().allowed_extensions),
            blocked_paths=file_settings.get("blocked_paths", FileOperationLimits().blocked_paths),
        )

        return cls(
            execution=exec_limits,
            file_ops=file_limits,
            enable_security_scan=settings.get("enable_security_scan", True),
            enable_write_validation=settings.get("enable_write_validation", True),
        )

    def to_dict(self) -> dict:
        """将当前配置导出为字典。"""
        return {
            "execution": {
                "timeout_seconds": self.execution.timeout_seconds,
                "max_memory_mb": self.execution.max_memory_mb,
                "max_output_chars": self.execution.max_output_chars,
                "progress_timeout_seconds": self.execution.progress_timeout_seconds,
                "blocked_patterns": self.execution.blocked_patterns,
            },
            "file_operations": {
                "max_read_bytes": self.file_ops.max_read_bytes,
                "max_read_lines": self.file_ops.max_read_lines,
                "max_write_bytes": self.file_ops.max_write_bytes,
                "allowed_extensions": self.file_ops.allowed_extensions,
                "blocked_paths": self.file_ops.blocked_paths,
            },
            "enable_security_scan": self.enable_security_scan,
            "enable_write_validation": self.enable_write_validation,
        }


# 全局单例实例
try:
    TOOL_CONFIG = ToolConfig.load()
except Exception as e:
    logger.error(f"初始化 ToolConfig 时出错：{e}，使用默认设置")
    TOOL_CONFIG = ToolConfig()
