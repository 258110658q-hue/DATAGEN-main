import sys
import logging
import os
import warnings
import asyncio
import threading

# 0. 修复 Windows GBK 编码问题 — 强制所有标准流使用 UTF-8
#    否则 LangChain 的 pretty_print() 会在遇到 ✓ 等字符时崩溃
for _stream_name in ('stdout', 'stderr'):
    try:
        getattr(sys, _stream_name).reconfigure(encoding='utf-8')
    except Exception:
        pass  # 该流不支持 reconfigure（例如被管道/重定向后）

# 1. 抑制 USER_AGENT 警告
os.environ["USER_AGENT"] = "mydataapp/1.0"
#我的程序名字叫 什么，别再警告我没设置身份了！
# 2. 设置流拦截器，过滤掉库/子进程中的非必要输出
class OutputFilter:
    #输出过滤器类，过滤掉不需要的输出
    def __init__(self, stream, blacklist):
        self.stream = stream
        self.blacklist = blacklist
    def write(self, data):
        if not any(term in data for term in self.blacklist):
            self.stream.write(data)
            #for term in ["词1", "词2", "词3"]:

    def flush(self):
        self.stream.flush()#给人感觉流式的输出
    def __getattr__(self, name):#把当前类 "没有的属性和方法"，全部转发给 self.stream 去处理。
        return getattr(self.stream, name)

# 将 sys.stderr（标准错误输出流）替换为我们自定义的 OutputFilter 实例，
# 大多数 MCP 服务端噪声都出现在 stderr 中
sys.stderr = OutputFilter(sys.stderr, [
    "Secure MCP Filesystem Server",
    "Client does not support MCP Roots",
    "USER_AGENT environment variable not set",
    "FutureWarning"
])

from src.logger import setup_logger
from src.core.mcp_manager import get_mcp_manager

# 初始化日志
logger = setup_logger()
warnings.filterwarnings("ignore")

from src.system import MultiAgentSystem
#MultiAgentSystem是整个系统的入口类，负责协调多个智能体完成用户任务。

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
#让他调用正确的sys包，设定文件位置
def run_mcp_loop(loop):
    """运行用于 MCP 连接的后台事件循环."""
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except Exception as e:
        logger.error(f"MCP 后台循环异常: {e}")
        #相当于是一个FastAPI后端一样，一直运行的服务端口，

def main():
    """主入口点"""
    # 创建并启动后台事件循环，以维持 MCP 长连接
    mcp_loop = asyncio.new_event_loop()
    mcp_thread = threading.Thread(target=run_mcp_loop, args=(mcp_loop,), daemon=True)
    mcp_thread.start()

    # 向 MCP 管理器注册该循环，告诉工具：后台线程在哪里
    manager = get_mcp_manager()
    manager._main_loop = mcp_loop

    try:
        system = MultiAgentSystem()

        # 示例用法
        user_input = '''
        请分析当前目录下的 OnlineSalesData.csv 文件（用collect_data读取它，CSV列名为：日期、销售额、利润、客户数、区域、产品类别、促销活动）。
        任务：
        1. 先用collect_data工具读取 OnlineSalesData.csv 文件
        2. 进行数据清洗、描述性统计、销售趋势分析、区域对比、促销活动效果评估
        3. 使用机器学习方法（如随机森林、聚类等）挖掘数据规律
        4. 生成可视化图表（图表标题和坐标轴使用中文）
        5. 撰写完整的中文分析报告
        '''
        system.run(user_input)
    finally:
        # 清理资源
        if mcp_loop.is_running():
            mcp_loop.call_soon_threadsafe(mcp_loop.stop)
        mcp_thread.join(timeout=2)

if __name__ == "__main__":
    main()
