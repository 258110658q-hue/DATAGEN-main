from __future__ import annotations
from typing import Annotated, Any
from pydantic import BaseModel, ConfigDict, Field
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages


class State(BaseModel):
    """
    多智能体研究工作流的标准共享状态。
    本设计兼具操作日志与成果摘要功能。
    """
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True, 
        validate_assignment=True,
        extra='ignore'  # 模型传入未定义的字段，忽略而不是报错
    )

    # === 上下文层 ===
    messages: list[BaseMessage] = Field(
        default_factory=list,
        description="工作流中交互的消息序列"
    )
    last_active_agent: str | None = Field(
        default=None, 
        description="最后一个执行操作的智能体"
    )
    step_count: int = Field(
        default=0, 
        description="防止无限循环的安全防护机制"
    )

    # === 流程控制 ===
    current_instruction: str | None = Field(
        default=None, 
        description="分配给下一个智能体的具体任务"
    )
    next_workflow_step: str | None = Field(
        default=None, 
        description="待转发的下一个节点 / 代理程序"
    )
    
    # === 待转发的下一个节点 / 代理程序 ===
    todo_list: list[str] = Field(
        default_factory=list, 
        description="待处理子任务列表"
    )
    completed_tasks: list[str] = Field(
        default_factory=list, 
        description="已完成子任务列表"
    )

    # === 领域产物 (Dict[Path, Description]) ===
    hypothesis: str | None = Field(
        default=None, 
        description="当前研究假设"
    )
    
    search_artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="{文件路径: 摘要} 映射，存储搜索结果"
    )
    data_viz_artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="{文件路径: 摘要} 映射，存储可视化产物"
    )
    code_artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="{文件路径: 摘要} 映射，存储代码文件"
    )
    report_artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="{章节: 路径/内容} 映射，存储报告章节"
    )

    # === Review Loop ===
    quality_feedback: str | None = Field(
        default=None, 
        description="质量评审反馈"
    )
    needs_revision: bool = Field(
        default=False, 
        description="触发修订循环的标记"
    )
    revision_count: int = Field(
        default=0,
        description="连续修改尝试计数器"
    )

    # === 流程阶段计数器（硬约束，不靠模型） ===
    process_phase: int = Field(
        default=0,
        description="0=假设完成, 1=code完成, 2=viz完成, 3=report完成, 4=可FINISH"
    )

    # === Legacy Compatibility (Optional) ===
    # 必要时可使用属性或别名，但我们将按照要求执行强制中断。

def create_initial_state(user_input: str) -> dict[str, Any]:
    """用于为 LangGraph 创建初始状态字典的工厂函数"""
    return {
        "messages": [HumanMessage(content=user_input)],
        "last_active_agent": "user",
        "step_count": 0,
        "todo_list": [],
        "completed_tasks": [],
        "search_artifacts": {},
        "data_viz_artifacts": {},
        "code_artifacts": {},
        "report_artifacts": {},
        "needs_revision": False,
        "revision_count": 0,
        "process_phase": 0,
    }
