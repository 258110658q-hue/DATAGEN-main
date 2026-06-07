import logging #日志库
from . import config
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from .core.workflow import WorkflowManager
from .core.language_models import LanguageModelManager
from .core.state import create_initial_state
from .logger import setup_logger

# 使用统一日志记录器
logger = setup_logger()

class MultiAgentSystem:
    def __init__(self):
        # 导入时配置已完成加载
        self.memory = MemorySaver()#对话的记忆能力
        self.lm_manager = LanguageModelManager()#调用逻辑
        self.workflow_manager = WorkflowManager(#工作流
            lm_manager=self.lm_manager,
            working_directory=config.WORKING_DIRECTORY
        )

    def run(self, user_input: str) -> None:
        graph = self.workflow_manager.get_graph()
        #获取这个图就是我们在WorkflowManager中定义的所有节点和边的集合。
        #使用工厂函数实现统一的状态初始化
        initial_state = create_initial_state(user_input)
        
        events = graph.stream(
            initial_state,
            {"configurable": {"thread_id": "1"}, "recursion_limit": 3000},
            stream_mode="values",
            debug=False
        )
        
        for event in events:
            message = event["messages"][-1]
            if isinstance(message, tuple):
                print(message, end='', flush=True)
            else:
                message.pretty_print()
            #如果是元组，就打印，是basemessage就让输出更好看
if __name__ == "__main__":
    system = MultiAgentSystem()
    user_input = input("Please enter your research topic: ")
    system.run(user_input)