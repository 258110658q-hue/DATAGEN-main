from langgraph.graph import StateGraph, END, START#图，入口，出口
from langgraph.checkpoint.memory import MemorySaver
from typing import cast #类型提示工具，不做任何运行时转换

from .state import State
from .node import agent_node, human_choice_node, note_agent_node, human_review_node, refiner_node
from .router import QualityReview_router, hypothesis_router, process_router

from ..agents.factory import AgentFactory


class WorkflowManager:
    def __init__(self, lm_manager, working_directory):
        """
        结合语言模型管理器与工作目录初始化工作流管理器。
        参数说明：
        lm_manager：语言模型管理器实例
        working_directory (str)：工作目录的路径
        """
        self.lm_manager = lm_manager  #管理LLM配置和调用
        self.working_directory = working_directory#agent 在这个目录下读写文件
        self.workflow = None  # 后面会被赋值为 StateGraph 实例
        self.memory = None    # 后面会被赋值为 MemorySaver 实例
        self.graph = None     # 后面会被赋值为编译好的图
        self.members = ["Hypothesis", "Process", "Visualization", "Search", "Coder", "Report", "QualityReview", "note", "Refiner"]
        self.agents = self.create_agents() #把九个agent创建出来
        self.setup_workflow()  #用这些agent搭好流程图

    def create_agents(self):
        """创建所有系统agent"""
        # 创建agent字典
        agents = {}

        # 通过工厂创建agent：没有工厂每次创建都要写一大堆参数，工厂模式帮我们封装了这个过程
        #然后只需要说"给我一个 hypothesis_agent"，工厂就帮你造好了：
        agent_factory = AgentFactory(
            language_model_manager=self.lm_manager,
            team_members=self.members,
            working_directory=self.working_directory
        )

        # 通过工厂类创建每个智能体
        '''消除重复：公共配置只传一次，不重复写 9 遍
2. 统一创建逻辑：如果创建过程需要改（比如要加日志），只改工厂类，不用改 9 个地方'''
        agents["hypothesis_agent"] = agent_factory.create_agent("hypothesis_agent")
        agents["process_agent"] = agent_factory.create_agent("process_agent")
        agents["visualization_agent"] = agent_factory.create_agent("visualization_agent")
        agents["code_agent"] = agent_factory.create_agent("code_agent")
        agents["search_agent"] = agent_factory.create_agent("search_agent")
        agents["report_agent"] = agent_factory.create_agent("report_agent")
        agents["quality_review_agent"] = agent_factory.create_agent("quality_review_agent")
        agents["note_agent"] = agent_factory.create_agent("note_agent")
        agents["refiner_agent"] = agent_factory.create_agent("refiner_agent")

        return agents

    def setup_workflow(self):
        """搭建工作流图表，创建空图"""
        self.workflow = StateGraph(State)
        
        #用于将通用节点输入转换为我们状态类型的辅助封装器
        #参数不匹配，闭包一下灵活传参，你调用的时候只写agent和名字，state会自动输入
        def _wrap_agent_node(agent, name):
            def action(state, config=None, store=None):
                return agent_node(cast(State, state), agent, name)
            return action
        def _wrap_note_agent(agent, name):
            def action(state, config=None, store=None):
                return note_agent_node(cast(State, state), agent, name)
            return action
        def _wrap_refiner(agent, name):
            def action(state, config=None, store=None):
                return refiner_node(cast(State, state), agent, name)
            return action
        '''add_node需要三个参数，graph调用的时候只会注入state，所以我们用闭包把agent和name绑在一起'''
        # 添加节点
        # _wrap_agent_node(self.agents["hypothesis_agent"], "hypothesis_agent")返回一个action函数，state在运行的时候会注入
        self.workflow.add_node("Hypothesis", _wrap_agent_node(self.agents["hypothesis_agent"], "hypothesis_agent"))
        self.workflow.add_node("Process", _wrap_agent_node(self.agents["process_agent"], "process_agent"))
        self.workflow.add_node("Visualization", _wrap_agent_node(self.agents["visualization_agent"], "visualization_agent"))
        self.workflow.add_node("Search", _wrap_agent_node(self.agents["search_agent"], "search_agent"))
        self.workflow.add_node("Coder", _wrap_agent_node(self.agents["code_agent"], "code_agent"))
        self.workflow.add_node("Report", _wrap_agent_node(self.agents["report_agent"], "report_agent"))
        self.workflow.add_node("QualityReview", _wrap_agent_node(self.agents["quality_review_agent"], "quality_review_agent"))
        self.workflow.add_node("NoteTaker", _wrap_note_agent(self.agents["note_agent"], "note_agent"))
        self.workflow.add_node("HumanChoice", human_choice_node)#人机交互节点，不需要LLM agent
        self.workflow.add_node("HumanReview", human_review_node)
        self.workflow.add_node("Refiner", _wrap_refiner(self.agents["refiner_agent"], "refiner_agent"))

        # 添加边
        self.workflow.add_edge(START, "Hypothesis")
        self.workflow.add_edge("Hypothesis", "HumanChoice")
        #先进规划假设，再进人工选择
        self.workflow.add_conditional_edges(
            "HumanChoice", #从哪个节点出发
            hypothesis_router, #调用的函数
            {
                "Hypothesis": "Hypothesis",#函数返回的可能性1
                "Process": "Process"#函数返回的可能性2
            }
        )

        self.workflow.add_conditional_edges(
            "Process",#同上
            process_router,
            {
                "Coder": "Coder",#函数返回什么就去哪里
                "Search": "Search",
                "Visualization": "Visualization",
                "Report": "Report",
                "Process": "Process",
                "Refiner": "Refiner",
            }
        )

        for member in ["Visualization", 'Search', 'Coder', 'Report']:
            self.workflow.add_edge(member, "QualityReview")
            #上面四个运行完了都要去质量审核
        self.workflow.add_conditional_edges(
            "QualityReview",
            QualityReview_router,
            {
                'Visualization': "Visualization",
                'Search': "Search",
                'Coder': "Coder",
                'Report': "Report",
                'NoteTaker': "NoteTaker",
            }
        )

        self.workflow.add_edge("NoteTaker", "Process")
        self.workflow.add_edge("Refiner", "HumanReview")
        '''fn = lambda state: "hello"
        def fn(state):
        return "hello"'''
        self.workflow.add_conditional_edges(
            "HumanReview",
            # 使用 getattr 提升对 Pydantic 状态处理的稳定性
            #根据if后面的条件返回Process或者END
            #getattr(对象, "属性名", 默认值) 从对手身上取属性，没有则返回默认
            #为什么用 getattr 而不用 state.needs_revision？因为 state 是 Pydantic 模型
            #属性可能不存在，直接 state.needs_revision 会抛异常，而 getattr 遇到不存在的属性会优雅地返回默认值 False。
            lambda state: "Process" if state and getattr(state, "needs_revision", False) else "END",
            {
                "Process": "Process",
                "END": END
            }
        )
        #state也会是True或者False，如果没有值就去右边取，反正就是防止报错
        # 编译工作流
        #langgraph提供的检查点，每执行完一个节点都会把当前的state存一份
        #可以断点回复，支持循环
        self.memory = MemorySaver()
        self.graph = self.workflow.compile()
        #compile把搭建好的设计图编译成可执行的对象
        #可以.invoke和.stream了

    def get_graph(self):
        """返回已编译的工作流图"""
        return self.graph
