from __future__ import annotations
#类型注解变成延迟求值
from .state import State
from typing import Literal, Union, cast, Any
from langchain_core.messages import AIMessage
import logging
import json

# Set up logger
logger = logging.getLogger(__name__) #创建日志记录器

# 定义节点路由的类型
NodeType = Literal['Visualization', 'Search', 'Coder', 'Report', 'Process', 'NoteTaker', 'Hypothesis', 'QualityReview']
ProcessNodeType = Literal['Coder', 'Search', 'Visualization', 'Report', 'Process', 'Refiner']

def get_state_attr(state: State | dict[str, Any], key: str, default: Any = None) -> Any:
    """安全地从状态对象中获取属性的辅助工具，无论该状态对象是 Pydantic 模型还是字典类型."""
    if isinstance(state, dict):#判断是不是字典，是的话用get取值
        return state.get(key, default)
    return getattr(state, key, default)#不是字典用这个，消除了类型判断
#系统有些地方把state当Pydantic 对象传来，有些地方当作普通字典传来，需要一个函数统一
def hypothesis_router(state: State) -> NodeType:
    """
    根据状态中是否存在假设来进行路由。
    """
    logger.info("Entering hypothesis_router")
    # 语义变化: 检查 'current_instruction' 代替 'process'
    current_instruction = get_state_attr(state, "current_instruction")
    #把整个状态对象传进去，帮我取current_instruction这个字段，取出来的值填入同名变量
    # 兼容中英文两种值（来自 human_choice_node 或历史数据）
    if current_instruction in ("继续执行研究流程", "Continue the research process"):
        return "Process"
    else:
        return "Hypothesis"

def QualityReview_router(state: State) -> str:
    """
    根据质量评审结果及流程判定进行路径分配。
    """
    logger.info("Entering QualityReview_router")
    messages = get_state_attr(state, "messages", [])
    needs_revision = get_state_attr(state, "needs_revision", False)
    revision_count = get_state_attr(state, "revision_count", 0)
    MAX_REVISIONS = 3
    
    # 检查是否需要修订
    if needs_revision:
        # 检查是否存在死循环 / 超限
        if revision_count > MAX_REVISIONS:
            logger.warning(f"Max revisions ({MAX_REVISIONS}) reached. Forcing progression to NoteTaker.")
            return "NoteTaker"
        #最新一条信息是QualityReview自己发的，倒数第二条才是要审查的那个Agent
        previous_node = messages[-2].name if len(messages) >= 2 else "NoteTaker"
        #消息数量不到两条了，说明之前没有Agent发过消息，直接当成NoteTaker处理就行了
        revision_routes = {
            "visualization_agent": "Visualization",
            "search_agent": "Search",
            "code_agent": "Coder",
            "report_agent": "Report"
        }#Agent质量不合格时，回到哪个节点？
        result = revision_routes.get((str(previous_node)), "NoteTaker")
        logger.info(f"Revision needed. Routing to: {result}")
        return result
    
    else:
        return "NoteTaker"
    

def process_router(state: State) -> ProcessNodeType:
    """
    根据状态中的流程判定进行路由。
    硬约束：process_phase 强制按 Coder → Visualization → Report 顺序执行。
    """
    logger.info("Entering process_router")
    next_step = get_state_attr(state, "next_workflow_step", "")
    phase = get_state_attr(state, "process_phase", 0)

    # === 硬约束：phase 强制顺序 ===
    # 0 → Coder, 1 → Visualization, 2 → Report, 3 → 允许 FINISH
    PHASE_FORCE = {0: "Coder", 1: "Visualization", 2: "Report"}

    valid_decisions = {"Coder", "Search", "Visualization", "Report"}

    if next_step == "FINISH":
        if phase < 3:
            forced = PHASE_FORCE[phase]
            logger.info(f"process_agent 说 FINISH 但 phase={phase}，强制路由到 {forced}")
            return cast(ProcessNodeType, forced)
        return "Refiner"

    if next_step in valid_decisions:
        # 禁止回退：phase 已推进时，不允许退回之前的 Agent
        if phase > 0:
            _order = ["Coder", "Visualization", "Report"]
            try:
                target_idx = _order.index(next_step)
                if target_idx < phase:
                    forced = PHASE_FORCE[phase]
                    logger.info(f"process_agent 说 {next_step} 但 phase={phase}（已回退），强制路由到 {forced}")
                    return cast(ProcessNodeType, forced)
            except ValueError:
                pass
        return cast(ProcessNodeType, next_step)

    # 安全优化：避免管理器持续故障时出现死循环
    step_count = get_state_attr(state, "step_count", 0)
    if step_count > 20:
        logger.warning(f"Step count ({step_count}) too high. Forcing FINISH.")
        return "Refiner"

    logger.warning(f"Invalid decision: {next_step}. Defaulting to 'Process'.")
    return "Process"

logger.info("Router module initialized")
