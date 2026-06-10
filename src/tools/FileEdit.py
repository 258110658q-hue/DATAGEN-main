import os
from typing import Annotated, List
from pydantic import BaseModel, Field

from langchain_core.tools import tool
import pandas as pd

from ..logger import setup_logger
from ..config import WORKING_DIRECTORY

# 设置日志记录器
logger = setup_logger()

# 确保工作目录存在
if not os.path.exists(WORKING_DIRECTORY):
    os.makedirs(WORKING_DIRECTORY)
    logger.info(f"Created working directory: {WORKING_DIRECTORY}")

def normalize_path(file_path: str) -> str:
    """
    规范化文件路径以实现跨平台兼容。
    会尝试多种路径组合，确保在 run_dir 等不同工作目录下都能找到文件。

    Args:
    file_path (str): 要规范化的文件路径

    Returns:
    str: 规范化后的文件路径
    """
    # 去除会导致双重嵌套的常见前缀
    clean_path = file_path.replace("\\", "/").lstrip("./")
    # 如果 WORKING_DIRECTORY 已经以 data/ 结尾，则移除 data/ 前缀
    wd_clean = WORKING_DIRECTORY.replace("\\", "/").rstrip("/")
    if clean_path.startswith(wd_clean.lstrip("./") + "/"):
        clean_path = clean_path[len(wd_clean.lstrip("./")) + 1:]

    # 首选：WORKING_DIRECTORY + clean_path
    primary = os.path.normpath(os.path.join(WORKING_DIRECTORY, clean_path))
    if os.path.exists(primary):
        return primary

    # 备选1：如果 clean_path 包含 data/ 前缀，尝试去掉它（文件可能直接在 WORKING_DIRECTORY 下）
    if clean_path.startswith("data/"):
        fallback = os.path.normpath(os.path.join(WORKING_DIRECTORY, clean_path[5:]))
        if os.path.exists(fallback):
            return fallback

    # 备选2：尝试仅用文件名在 WORKING_DIRECTORY 下查找
    basename = os.path.basename(clean_path)
    fallback2 = os.path.normpath(os.path.join(WORKING_DIRECTORY, basename))
    if os.path.exists(fallback2):
        return fallback2

    # 都不存在，返回首选路径（让后续报 FileNotFoundError）
    return primary

@tool
def collect_data(
    data_path: Annotated[str, "Path to the CSV file (required, e.g. 'data.csv' or 'OnlineSalesData.csv')"],
    nrows: Annotated[int | None, "Number of rows to read"] = None,
    usecols: Annotated[list[str] | None, "List of column names to read"] = None,
    skiprows: Annotated[int | None, "Number of rows to skip at the beginning"] = None
) -> Annotated[pd.DataFrame, "The collected data from the CSV file"]:
    """
    从 CSV 文件中收集数据，支持选择性读取选项。
    """
    data_path = normalize_path(data_path)
    logger.info(f"Attempting to read CSV file: {data_path}")
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    for encoding in encodings:
        try:
            data = pd.read_csv(
                data_path,
                encoding=encoding,
                nrows=nrows,
                usecols=usecols,
                skiprows=skiprows
            )
            logger.info(f"Successfully read CSV file with encoding: {encoding}")
            return data
        except Exception as e:
            logger.warning(f"Error with encoding {encoding}: {e}")
    logger.error("Unable to read file with provided encodings")
    raise ValueError("Unable to read file with provided encodings")

@tool
def create_document(
    points: Annotated[List[str], "List of points to be included in the document"],
    file_name: Annotated[str, "Name of the file to save the document"]
) -> Annotated[str, "Message indicating where the document was saved"]:
    """
    创建并保存一个 Markdown 格式的文本文档。

    此函数接收一个要点列表，并将其作为编号条目写入 Markdown 文件中。

    """
    try:
        file_path = normalize_path(file_name)
        logger.info(f"Creating document: {file_path}")
        with open(file_path, "w", encoding='utf-8') as file:
            for i, point in enumerate(points):
                file.write(f"{i + 1}. {point}\n")
        logger.info(f"Document created successfully: {file_path}")
        return f"Outline saved to {file_path}"
    except Exception as e:
        logger.error(f"Error while saving outline: {str(e)}")
        return f"Error while saving outline: {str(e)}"

@tool
def read_document(
    file_name: Annotated[str, "Name of the file to read"],
    start: Annotated[int, "Starting line number (use 0 for beginning)"] = 0,
    end: Annotated[int, "Ending line number (use -1 for end of file)"] = -1
) -> Annotated[str, "Content of the document"]:
    """
    读取指定文档并进行安全验证。

    此函数从指定文件读取文档并返回其内容。
    安全功能：
    - 路径验证（阻止路径检查）
    - 文件大小验证
    - 行数限制

    Args:
        file_name: 要读取的文件名。
        start: 起始行号（0 索引，默认值：0）。
        end: 结束行号（-1 表示文件末尾，默认值：-1）。

    Returns:
        文档内容或错误消息。
    """
    from .validators import PathValidator
    from .tool_config import TOOL_CONFIG

    try:
        file_path = normalize_path(file_name)

        # === 验证 ===
        try:
            PathValidator.validate_read(file_path)
        except (PermissionError, ValueError) as e:
            logger.warning(f"Read validation failed for {file_path}: {e}")
            return f"Error: {e}"

        with open(file_path, "r", encoding='utf-8') as file:
            lines = file.readlines()

        # 应用行数限制
        max_lines = TOOL_CONFIG.file_ops.max_read_lines
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated_notice = f"\n\n... [TRUNCATED: showing first {max_lines} lines]"
        else:
            truncated_notice = ""

        # 处理特殊值
        if start == 0 and end == -1:
            content = "".join(lines)
        elif end == -1:
            content = "".join(lines[start:])
        else:
            content = "".join(lines[start:end])

        return content + truncated_notice
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def write_document(
    content: Annotated[str, "Content to be written to the document"],
    file_name: Annotated[str, "Name of the file to save the document"]
) -> Annotated[str, "Message indicating where the document was saved"]:
    """
    创建并保存一个 Markdown 文档并进行验证。

    此函数接收一个内容字符串并将其写入文件。
    安全功能：
    - 路径验证（阻止路径检查）
    - 内容大小验证
    - 内容质量警告（检测 TODO/FIXME）

    Args:
        content: 要写入文件的内容。
        file_name: 要保存的文件名。

    Returns:
        成功消息或错误信息。
    """
    from .validators import PathValidator, ContentValidator

    try:
        file_path = normalize_path(file_name)

        # === 路径验证 ===
        try:
            PathValidator.validate_write(file_path)
        except PermissionError as e:
            logger.warning(f"Write path validation failed: {e}")
            return f"Error: {e}"

        # === 内容验证 ===
        is_valid, message = ContentValidator.validate_and_log(content, file_path)
        if not is_valid:
            return f"Error: {message}"

        logger.info(f"Writing document: {file_path}")
        with open(file_path, "w", encoding='utf-8') as file:
            file.write(content)
        logger.info(f"Document written successfully: {file_path}")

        result = f"Document saved to {file_path}"
        if message:  # 警告
            result += f" ({message})"
        return result
    except Exception as e:
        logger.error(f"Error while saving document: {str(e)}")
        return f"Error while saving document: {str(e)}"

class LineInsert(BaseModel):
    line_number: int = Field(description="要插入的行号")
    text: str = Field(description="要插入的文本")


@tool
def edit_document(
    file_name: Annotated[str, "Name of the file to edit"],
    inserts: Annotated[List[LineInsert], "List of line insertions"]
) -> Annotated[str, "Message indicating where the document was saved"]:
    """通过在指定行号插入文本来编辑文档。"""
    try:
        file_path = normalize_path(file_name)
        with open(file_path, "r", encoding='utf-8') as file:
            lines = file.readlines()

        inserts_dict = {insert.line_number: insert.text for insert in inserts}
        sorted_inserts = sorted(inserts_dict.items())

        for line_number, text in sorted_inserts:
            if 1 <= line_number <= len(lines) + 1:
                lines.insert(line_number - 1, text + "\n")

        with open(file_path, "w", encoding='utf-8') as file:
            file.writelines(lines)

        return f"Document edited and saved to {file_path}"
    except Exception as e:
        return f"Error while editing document: {str(e)}"



logger.info("Document management tools initialized")
