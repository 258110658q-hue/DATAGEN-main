"""代码执行的安全扫描与资源限制。
本模块提供以下功能：
安全扫描器：通过静态分析检测危险代码模式
资源限制器：为代码执行设置超时与内存限制
"""

import ast
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import List, Optional

from ..logger import setup_logger
from .tool_config import TOOL_CONFIG

logger = setup_logger()

# Constants
DEFAULT_POLL_INTERVAL_SECONDS = 0.1


@dataclass
class ScanResult:
    """安全扫描结果。
    属性说明：
    is_safe：代码是否通过安全检测。
    violations：检测到的安全违规项列表。
    warnings：非阻断类警告（例如：风险导入项）
    """
    is_safe: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SecurityScanner:
    """针对危险代码模式的静态分析。
    结合正则表达式匹配与抽象语法树分析，在代码运行前检测潜在的危险代码。
    """

    #切勿调用的危险内置函数（不可修改）
    DANGEROUS_BUILTINS: frozenset = frozenset({"eval", "exec", "compile", "__import__"})

    # 需发出警告的高危模块（不可修改）
    RISKY_MODULES: frozenset = frozenset({"os", "subprocess", "shutil", "socket", "ctypes"})

    #预编译模式，提升匹配速度（首次使用时生成）
    _compiled_pattern: Optional[re.Pattern] = None

    @classmethod
    def _get_blocked_pattern(cls) -> re.Pattern:
        """获取或创建预编译的拦截模式正则表达式。"""
        if cls._compiled_pattern is None:
            patterns = TOOL_CONFIG.execution.blocked_patterns
            # 转义特殊正则字符，并用 | 拼接
            escaped = [re.escape(p) for p in patterns]
            cls._compiled_pattern = re.compile('|'.join(escaped))
        return cls._compiled_pattern

    @classmethod
    def scan_code(cls, code: str) -> ScanResult:
        """扫描代码以排查安全漏洞。

        Args:
            code: 要扫描的 Python 源代码。

        Returns:
           包含安全状态以及所有违规项、警告信息的扫描结果。
        """
        violations = []
        warnings = []

        # 基于模式的检测（快速，使用预编译正则表达式）
        pattern = cls._get_blocked_pattern()
        matches = pattern.findall(code)
        for match in matches:
            violations.append(f"Blocked pattern detected: '{match}'")

        # 基于 AST 的检测（更精确，能捕获实际调用）
        try:
            tree = ast.parse(code)
            ast_violations, ast_warnings = cls._analyze_ast(tree)
            violations.extend(ast_violations)
            warnings.extend(ast_warnings)
        except SyntaxError as e:
            # 不因语法错误而阻断——留待运行时处理
            warnings.append(f"Syntax error during scan: {e}")

        return ScanResult(
            is_safe=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )

    @classmethod
    def _analyze_ast(cls, tree: ast.AST) -> tuple:
        """分析 AST 以检测危险代码模式（单次遍历）。

        Args:
            tree: 已解析的 AST 树。

        Returns:
            (violations, warnings) 元组。
        """
        violations = []
        warnings = []

        for node in ast.walk(tree):
            # 检测危险内置函数调用
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in cls.DANGEROUS_BUILTINS:
                    violations.append(f"Dangerous builtin call: {func_name}()")

            # 检测高风险模块导入
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.RISKY_MODULES:
                        warnings.append(f"Risky module import: {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in cls.RISKY_MODULES:
                    warnings.append(f"Risky module import: {node.module}")

            # 检测风险模式下的属性访问
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "os" and node.attr == "system":
                    violations.append("os.system() is blocked")
                elif node.value.id == "shutil" and node.attr == "rmtree":
                    violations.append("shutil.rmtree() is blocked")

        return violations, warnings


def _enqueue_output(pipe, queue: Queue, stop_event: threading.Event) -> None:
    """从管道逐行读取并放入队列（在线程中运行）。

    Args:
        pipe: 来自 subprocess 的 stdout 或 stderr 管道。
        queue: 用于存放输出行的队列。
        stop_event: 用于通知线程停止的事件。
    """
    try:
        for line in iter(pipe.readline, ''):
            if stop_event.is_set():
                break
            if line:
                queue.put(line)
        pipe.close()
    except (ValueError, OSError):
        # 管道已关闭
        pass


class ResourceLimiter:
    """以用户可控的资源限制执行代码。

    支持以下限制方式：
    - 固定超时：运行 N 秒后强制终止
    - 基于进度的超时：仅在 N 秒内无 stdout 输出时终止
    - 内存限制：通过 resource.setrlimit 设置（仅 Linux）

    使用多线程实现跨平台的非阻塞 stdout 读取。
    """

    def __init__(
        self,
        timeout: Optional[int] = None,
        memory_mb: Optional[int] = None,
        max_output_chars: Optional[int] = None,
        progress_timeout: Optional[int] = None,
    ):
        """初始化资源限制器。

        Args:
            timeout: 固定超时时间（秒）。None 表示无限制。
            memory_mb: 内存限制（MB，仅 Linux）。None 表示无限制。
            max_output_chars: 超出时截断输出。None 表示使用配置默认值。
            progress_timeout: 仅在 N 秒内无 stdout 输出时触发超时。
        """
        self.timeout = timeout
        self.memory_mb = memory_mb
        self.max_output_chars = max_output_chars or TOOL_CONFIG.execution.max_output_chars
        self.progress_timeout = progress_timeout

    def execute(
        self,
        command: List[str],
        cwd: str,
        shell: bool = False,
        executable: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """以资源限制执行命令。

        Args:
            command: 要执行的命令（列表，若 shell=True 则可传字符串）。
            cwd: 工作目录。
            shell: 是否使用 shell 执行。
            executable: Shell 可执行文件路径（如 /bin/bash）。

        Returns:
            包含 stdout/stderr 的 CompletedProcess。

        Raises:
            TimeoutError: 当执行时间超出超时限制时抛出。
        """
        # 如果指定了内存限制，则应用（仅 Linux）
        preexec_fn = None
        if self.memory_mb is not None:
            preexec_fn = self._create_preexec_fn()

        # 无超时设置——直接运行
        if self.timeout is None and self.progress_timeout is None:
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=shell,
                executable=executable,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                preexec_fn=preexec_fn,
            )
            return self._truncate_output(result)

        # 使用 Popen 加多线程实现跨平台的超时监控
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=shell,
            executable=executable,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            preexec_fn=preexec_fn,
        )

        # 设置多线程输出读取
        stdout_queue: Queue = Queue()
        stderr_queue: Queue = Queue()
        stop_event = threading.Event()

        stdout_thread = threading.Thread(
            target=_enqueue_output,
            args=(process.stdout, stdout_queue, stop_event),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=_enqueue_output,
            args=(process.stderr, stderr_queue, stop_event),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()

        start_time = time.time()
        last_output_time = start_time
        stdout_lines = []
        stderr_lines = []

        try:
            while True:
                elapsed = time.time() - start_time
                idle_time = time.time() - last_output_time

                # 检查进程是否已结束
                return_code = process.poll()
                if return_code is not None:
                    # 进程已完成——排空剩余输出
                    stop_event.set()
                    stdout_thread.join(timeout=1.0)
                    stderr_thread.join(timeout=1.0)
                    
                    while not stdout_queue.empty():
                        try:
                            stdout_lines.append(stdout_queue.get_nowait())
                        except Empty:
                            break
                    while not stderr_queue.empty():
                        try:
                            stderr_lines.append(stderr_queue.get_nowait())
                        except Empty:
                            break
                    break

                # 从队列读取可用输出
                try:
                    line = stdout_queue.get(timeout=DEFAULT_POLL_INTERVAL_SECONDS)
                    stdout_lines.append(line)
                    last_output_time = time.time()
                except Empty:
                    pass

                # 非阻塞式排空 stderr
                while not stderr_queue.empty():
                    try:
                        stderr_lines.append(stderr_queue.get_nowait())
                    except Empty:
                        break

                # 超时判断逻辑
                if self.progress_timeout is not None:
                    if idle_time > self.progress_timeout:
                        process.kill()
                        raise TimeoutError(
                            f"No output for {self.progress_timeout}s "
                            f"(total elapsed: {elapsed:.1f}s)"
                        )
                elif self.timeout is not None:
                    if elapsed > self.timeout:
                        process.kill()
                        raise TimeoutError(
                            f"Execution exceeded {self.timeout}s timeout"
                        )

        except TimeoutError:
            stop_event.set()
            process.kill()
            process.wait()
            raise

        result = subprocess.CompletedProcess(
            args=command,
            returncode=return_code,
            stdout=''.join(stdout_lines),
            stderr=''.join(stderr_lines),
        )

        return self._truncate_output(result)

    def _create_preexec_fn(self):
        """创建用于内存限制的 preexec 函数（仅 Linux）。"""
        memory_mb = self.memory_mb

        def set_limits():
            try:
                import resource
                memory_bytes = memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
            except (ImportError, ValueError, OSError):
                pass  # 当前平台不可用

        return set_limits

    def _truncate_output(
        self,
        result: subprocess.CompletedProcess
    ) -> subprocess.CompletedProcess:
        """若输出超过 max_output_chars 则截断。"""
        if self.max_output_chars and len(result.stdout) > self.max_output_chars:
            result.stdout = (
                result.stdout[:self.max_output_chars] +
                f"\n\n... [OUTPUT TRUNCATED at {self.max_output_chars} chars]"
            )
        return result

