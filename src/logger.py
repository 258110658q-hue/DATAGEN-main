import logging
import sys

class SilenceFilter(logging.Filter):
    """过滤掉不需要在控制台中显示的噪音消息。"""
    def filter(self, record):
        msg = record.getMessage()
        # 噪音子串黑名单
        blacklist = [
            "asynchronous generator",
            "cancel scope",
            "different task than it was entered in",
            "Loaded",
            "tools from MCP",
            "Created adapter",
            "Connected to MCP",
            "Connecting to MCP",
            "Discovered",
            "Client does not support MCP Roots",
            "Traceback",
            "GeneratorExit"
        ]
        return not any(term in msg for term in blacklist)

# 配置日志
def setup_logger(log_file:str='agent.log'):
    # 清除根 logger 的所有 handler，防止其他模块产生重复日志
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)

    logger = logging.getLogger("src") # 使用顶层名称
    logger.setLevel(logging.DEBUG)
    logger.propagate = False # 防止重复输出日志

    if logger.hasHandlers():
        logger.handlers.clear()

    # 格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 文件 handler（保留所有日志用于调试）
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 控制台 handler（过滤后的进度信息）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 添加 handler
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 再次强制全局抑制，确保生效
    for name in ["asyncio", "anyio", "httpx", "httpcore", "langchain", "langgraph"]:
        logging.getLogger(name).setLevel(logging.CRITICAL)

    return logger
