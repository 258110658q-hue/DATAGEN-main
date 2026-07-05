import os
import sys
import platform
from typing import Annotated
import subprocess
from langchain_core.tools import tool

from ..logger import setup_logger
from ..config import WORKING_DIRECTORY,CONDA_ENV

# 初始化日志记录器
logger = setup_logger()

# 确保存储目录存在
if not os.path.exists(WORKING_DIRECTORY):
    os.makedirs(WORKING_DIRECTORY)
    logger.info(f"已创建存储目录: {WORKING_DIRECTORY}")

def get_platform_specific_command(command: str) -> tuple:
    """
    获取平台相关的命令执行详情。
    如果设置了 CONDA_ENV 且 conda 可用，则使用 conda run 执行，否则直接执行。
    返回一个 (shell_command, shell_type, executable) 元组
    """
    import shutil

    if CONDA_ENV and CONDA_ENV.lower() != "none" and shutil.which("conda"):
        full_command = f"conda run -n {CONDA_ENV} {command}"
    else:
        full_command = command

    system = platform.system().lower()
    if system == "windows":
        return (full_command, True, None)
    else:
        return (full_command, True, "/bin/bash")


@tool
def execute_code(
    input_code: Annotated[str, "要执行的 Python 代码。"],
    codefile_name: Annotated[str, "Python 代码文件名或完整路径。"] = 'code.py',
    timeout: Annotated[int | None, "执行超时时间（秒）。None = 无限制。"] = None,
    memory_mb: Annotated[int | None, "内存限制（MB，仅 Linux）。None = 无限制。"] = None,
    progress_timeout: Annotated[int | None, "仅在 N 秒内无输出时触发超时。适用于 ML/DL 场景。"] = None,
) -> Annotated[dict, "执行结果，包含输出和文件路径"]:
    """
    在指定的 conda 环境中执行 Python 代码并返回结果。

    此函数接收 Python 代码作为输入，将其写入文件，在指定的 conda 环境中执行，
    并返回输出或执行过程中遇到的任何错误。

    安全特性：
    - 执行前扫描代码中的危险模式
    - 可选的超时和内存限制
    - 输出过大时会被截断

    Args:
        input_code: 要执行的 Python 代码。
        codefile_name: 保存代码的文件名（默认: code.py）。
        timeout: 固定超时时间（秒）。None = 无限制。
        memory_mb: 内存限制（MB，仅 Linux）。None = 无限制。
        progress_timeout: 仅在 N 秒内无 stdout 输出时触发超时（用于长时间运行的 ML/DL 任务）。

    Returns:
        包含结果状态、输出/错误和文件路径的字典。
    """
    from .tool_config import TOOL_CONFIG
    from .security import SecurityScanner, ResourceLimiter

    code_file_path = None
    try:
        # === 安全扫描 ===
        if TOOL_CONFIG.enable_security_scan:
            scan_result = SecurityScanner.scan_code(input_code)
            if not scan_result.is_safe:
                logger.warning(f"安全扫描已阻止代码: {scan_result.violations}")
                return {
                    "result": "Security violation",
                    "error": f"Code blocked: {'; '.join(scan_result.violations)}",
                    "file_path": None
                }
            if scan_result.warnings:
                logger.info(f"安全扫描警告: {scan_result.warnings}")

        # 确保 WORKING_DIRECTORY 存在
        os.makedirs(WORKING_DIRECTORY, exist_ok=True)

        # 处理 codefile_name，确保它是有效路径
        if os.path.isabs(codefile_name):
            code_file_path = codefile_name
        else:
            # 如果 codefile_name 以 data/ 开头且 WORKING_DIRECTORY 本来就指向 data/ 目录，
            # 去掉重复的 data/ 前缀，防止拼接出 data/data/xxx 的路径
            clean_name = codefile_name.replace("\\", "/")
            wd_clean = WORKING_DIRECTORY.replace("\\", "/").rstrip("/")
            if clean_name.startswith("data/") and wd_clean.endswith("/data"):
                clean_name = clean_name[5:]  # 去掉 "data/" 前缀
            code_file_path = os.path.join(WORKING_DIRECTORY, clean_name)

        # 针对当前平台规范化路径，并转为绝对路径（防止执行时 cwd 不同导致路径错误）
        code_file_path = os.path.abspath(os.path.normpath(code_file_path))

        logger.info(f"代码将写入文件: {code_file_path}")

        # 使用 UTF-8 编码将代码写入文件
        with open(code_file_path, 'w', encoding='utf-8') as code_file:
            code_file.write(input_code)

        logger.info(f"代码已写入文件: {code_file_path}")

        # 获取平台相关的命令（使用完整路径引用脚本文件）
        # 设置 PYTHONIOENCODING=utf-8 防止脚本中的 emoji/中文在 GBK 下崩溃
        # 使用主进程的 Python（保证能访问 venv 里装的 pandas/matplotlib 等包）
        python_cmd = f'"{sys.executable}" -X utf8 "{code_file_path}"'
        full_command, shell, executable = get_platform_specific_command(python_cmd)

        logger.info(f"正在执行命令: {full_command}")

        # === 带资源限制执行 ===
        limiter = ResourceLimiter(
            timeout=timeout,
            memory_mb=memory_mb,
            progress_timeout=progress_timeout,
        )

        try:
            result = limiter.execute(
                command=full_command,
                cwd=WORKING_DIRECTORY,
                shell=shell,
                executable=executable,
            )
        except TimeoutError as e:
            logger.error(f"执行超时: {e}")
            return {
                "result": "Timeout",
                "error": str(e),
                "file_path": code_file_path
            }

        # 捕获标准输出和错误输出
        output = result.stdout
        error_output = result.stderr

        if result.returncode == 0:
            logger.info("代码执行成功")
            return {
                "result": "Code executed successfully",
                "output": output + "\n\nIf you have completed all tasks, respond with FINAL ANSWER.",
                "file_path": code_file_path
            }
        else:
            logger.error(f"代码执行失败: {error_output}")
            return {
                "result": "Failed to execute",
                "error": error_output,
                "file_path": code_file_path
            }
    except Exception as e:
        logger.exception("执行代码时发生错误")
        return {
            "result": "Error occurred",
            "error": str(e),
            "file_path": code_file_path if 'code_file_path' in locals() else "Unknown"
        }

@tool
def execute_command(
    command: Annotated[str, "要执行的命令。"]
) -> Annotated[str, "命令的输出。"]:
    """
    在指定的 Conda 环境中执行命令并返回其输出。

    此函数激活 Conda 环境，执行给定的命令，
    并返回输出或执行过程中遇到的任何错误。
    请使用 pip 安装包。

    """
    try:
        # 获取平台相关的命令
        full_command, shell, executable = get_platform_specific_command(command)

        logger.info(f"正在执行命令: {command}")

        # 执行命令并捕获输出
        result = subprocess.run(
            full_command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            executable=executable,
            cwd=WORKING_DIRECTORY
        )
        logger.info("命令执行成功")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"执行命令时出错: {e.stderr}")
        return f"Error: {e.stderr}"

logger.info("模块初始化成功")

@tool
def list_directory(directory: Annotated[str, "要列出内容的目录路径。"]
) -> Annotated[str, "目录内容"]:
    """列出指定目录的内容。"""
    try:
        if not directory:
            directory = WORKING_DIRECTORY
        logger.info(f"正在列出目录内容: {directory}")
        contents = os.listdir(directory)
        return f"Directory contents:\n" + "\n".join(contents)
    except Exception as e:
        return f"Error: {str(e)}"