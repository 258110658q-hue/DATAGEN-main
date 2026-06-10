"""文件操作的路径和内容校验器。

本模块提供：
- PathValidator: 校验文件路径的安全性
- ContentValidator: 在写入前校验内容
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

from ..logger import setup_logger
from .tool_config import TOOL_CONFIG

logger = setup_logger()


class PathValidator:
    """校验文件路径的安全性。

    检查项：
    - 路径不在禁止访问的目录中
    - 文件扩展名在允许列表中
    - 文件大小在限制范围内
    """

    @classmethod
    def check_path(cls, file_path: str) -> None:
        """确保路径不在禁止访问的目录中。

        Args:
            file_path: 要校验的路径。

        Raises:
            PermissionError: 如果路径在禁止访问的目录中。
        """
        try:
            resolved = Path(file_path).resolve()
        except (OSError, ValueError) as e:
            raise PermissionError(f"Invalid path: {file_path}") from e

        for blocked in TOOL_CONFIG.file_ops.blocked_paths:
            try:
                blocked_resolved = Path(os.path.expanduser(blocked)).resolve()
            except (OSError, ValueError):
                # 跳过无效的禁止路径
                continue

            if str(resolved).startswith(str(blocked_resolved)):
                raise PermissionError(
                    f"Access denied: {file_path} is in blocked path '{blocked}'"
                )

    @classmethod
    def check_extension(cls, file_path: str) -> None:
        """确保文件扩展名在允许列表中。

        Args:
            file_path: 要校验的路径。

        Raises:
            PermissionError: 如果扩展名不在允许列表中。
        """
        ext = Path(file_path).suffix.lower()
        allowed = TOOL_CONFIG.file_ops.allowed_extensions

        # 允许没有扩展名的文件
        if not ext:
            return

        if ext not in allowed:
            raise PermissionError(
                f"File type '{ext}' not allowed. Allowed: {', '.join(allowed)}"
            )

    @classmethod
    def check_file_size(cls, file_path: str) -> None:
        """确保读取的文件大小在限制范围内。

        Args:
            file_path: 要检查的路径。

        Raises:
            ValueError: 如果文件超过 max_read_bytes 限制。
        """
        if not os.path.exists(file_path):
            return

        size = os.path.getsize(file_path)
        max_size = TOOL_CONFIG.file_ops.max_read_bytes

        if size > max_size:
            raise ValueError(
                f"File too large: {size:,} bytes (max: {max_size:,} bytes = {max_size // 1024 // 1024}MB)"
            )

    @classmethod
    def validate_read(cls, file_path: str) -> None:
        """执行所有读取校验。

        Args:
            file_path: 要校验的路径。

        Raises:
            PermissionError: 如果路径或扩展名不被允许。
            ValueError: 如果文件太大。
        """
        cls.check_path(file_path)
        cls.check_extension(file_path)
        cls.check_file_size(file_path)

    @classmethod
    def validate_write(cls, file_path: str) -> None:
        """执行所有针对路径的写入校验。

        Args:
            file_path: 要校验的路径。

        Raises:
            PermissionError: 如果路径或扩展名不被允许。
        """
        cls.check_path(file_path)
        cls.check_extension(file_path)


class ContentValidator:
    """在写入前校验内容。

    检查项包括：
    - 内容大小限制
    - 不完整内容标记（TODO、FIXME 等）
    - 潜在的敏感数据（API 密钥、密码）
    """

    # 避免"内容过短"警告的最小内容长度
    MIN_CONTENT_LENGTH = 10

    # 可能表示内容不完整的标记
    INCOMPLETE_MARKERS = ["TODO", "FIXME", "XXX", "TBD", "HACK", "（待补）", "..."]

    # 用于检测敏感数据的正则模式
    SENSITIVE_PATTERNS = [
        (r"['\"]sk-[a-zA-Z0-9]{32,}['\"]", "OpenAI API key"),
        (r"['\"]AKIA[A-Z0-9]{16}['\"]", "AWS access key"),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password"),
        (r"['\"][a-f0-9]{32}['\"]", "Potential API key/hash"),
    ]

    @classmethod
    def validate_content(
        cls,
        content: str,
        file_path: str,
    ) -> Tuple[bool, List[str]]:
        """在写入前校验内容。

        Args:
            content: 要校验的内容。
            file_path: 目标文件路径（用于上下文）。

        Returns:
            包含 (is_valid, warnings) 的元组。
            is_valid 仅在内容超过大小限制时为 False。
            warnings 是发现的非阻塞性问题列表。
        """
        warnings = []

        # 检查大小限制
        content_bytes = len(content.encode('utf-8'))
        max_bytes = TOOL_CONFIG.file_ops.max_write_bytes

        if content_bytes > max_bytes:
            return False, [
                f"Content too large: {content_bytes:,} bytes "
                f"(max: {max_bytes:,} bytes)"
            ]

        # 如果写入校验功能被禁用，跳过后续校验
        if not TOOL_CONFIG.enable_write_validation:
            return True, []

        # 检查不完整标记
        for marker in cls.INCOMPLETE_MARKERS:
            if marker in content:
                warnings.append(f"Found incomplete marker: '{marker}'")
                break  # 仅报告第一个标记

        # 检查敏感数据模式
        for pattern, description in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, content):
                warnings.append(f"Potential {description} detected - review before commit")
                break  # 仅报告第一个匹配

        # 检查空内容或几乎为空的内容
        stripped = content.strip()
        if not stripped:
            warnings.append("Content is empty")
        elif len(stripped) < cls.MIN_CONTENT_LENGTH:
            warnings.append("Content is very short - verify completeness")

        return True, warnings

    @classmethod
    def validate_and_log(
        cls,
        content: str,
        file_path: str,
    ) -> Tuple[bool, str]:
        """校验内容并返回格式化的结果。

        Args:
            content: 要校验的内容。
            file_path: 目标文件路径。

        Returns:
            包含 (is_valid, message) 的元组。
        """
        is_valid, warnings = cls.validate_content(content, file_path)

        if not is_valid:
            error_msg = f"Validation failed: {warnings[0]}"
            logger.error(error_msg)
            return False, error_msg

        if warnings:
            warning_msg = f"Warnings: {'; '.join(warnings)}"
            logger.warning(f"Write validation for {file_path}: {warning_msg}")
            return True, warning_msg

        return True, ""
