from __future__ import annotations
from typing import Any, Union, TYPE_CHECKING
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
import logging
import json
import re
from pathlib import Path
import time

from .state import State
from ..config import WORKING_DIRECTORY

if TYPE_CHECKING:
    from .state import State
    from ..agents.base import BaseAgent

# 设置日志记录器
logger = logging.getLogger(__name__)

def get_state_attr(state: State | dict[str, Any], key: str, default: Any = None) -> Any:
    """安全从状态对象中获取属性的辅助工具，无论该状态对象是 Pydantic 模型还是字典类型."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)

def update_artifact_dict(current_artifacts: dict[str, str], new_output: dict[str, str] | str | Any) -> dict[str, str]:
    """
    用新输出更新工件字典。
    若输出为字符串（旧版格式），则对其进行封装。
    若输出为字典，则执行更新操作。
    """
    updated = current_artifacts.copy() if current_artifacts else {}

    if isinstance(new_output, dict):
        updated.update(new_output)
    elif isinstance(new_output, str) and new_output:
        #旧版 / 备用方案：为原始字符串输出生成带时间戳的密钥
        #此举可确保即便智能代理未完成全部迁移，数据也不会丢失
        timestamp = int(time.time())
        key = f"output_{timestamp}.txt"
        summary = new_output[:100] + "..." if len(new_output) > 100 else new_output
        updated[key] = summary

    return updated


def safe_get_content(output: Any, keys: list[str], default: str = "") -> str:
    """从输出结果中安全提取内容（支持 Pydantic、字典或字符串类型）。."""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        for key in keys:
            if key in output:
                return str(output[key])
        return str(output)

    for key in keys:
        if hasattr(output, key):
            val = getattr(output, key, None)
            if val is not None:
                return str(val)
    return str(output) if output else default

def extract_json_from_text(text: str) -> dict[str, Any] | None:
    """从文本中提取并解析 JSON，处理 markdown 块."""
    if not text:
        return None

    # 先尝试 markdown 代码块
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 '{' 和最后一个 '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1:
        try:
            return json.loads(text[start_idx:end_idx+1])
        except json.JSONDecodeError:
            pass

    return None

def get_structured_output(result: Any, agent: BaseAgent) -> Any:
    """从智能代理的运行结果中提取结构化输出，并启用备用解析方案."""
    # 1. result 字典中的直接结构化响应
    if isinstance(result, dict) and "structured_response" in result:
        return result["structured_response"]

    # 2. result 本身可能就是结构化对象（Pydantic）
    if hasattr(result, "dict") or hasattr(result, "model_dump"):
        return result

    # 3. 最后一条消息内容可能是一个 JSON 字符串
    content = ""
    if isinstance(result, dict) and "messages" in result and result["messages"]:
        content = result["messages"][-1].content
    elif hasattr(result, "content"):
        content = result.content
    elif isinstance(result, str):
        content = result

    if content:
        parsed = extract_json_from_text(content)
        if parsed:
            return parsed

    return None
        # 4. 回退到最后一条消息内容
        #调用Agent之后result格式是不确定的，这个函数用来捞出结构化数据

def agent_node(state: State, agent: BaseAgent, name: str) -> dict[str, Any]:
    """处理智能体的动作，并相应更新状态。."""
    logger.info(f"Processing agent: {name}")
    try:
        result = agent.invoke(state)#调用LLM

        # 稳健的结构化搜索
        output = get_structured_output(result, agent)
        #结果+agent名字输，输出结构化
        # 提取人工智能消息内容
        if output:
            content = safe_get_content(output, ["task", "feedback", "summary", "current_instruction"])
            ai_message = AIMessage(content=content, name=name)
            #提取成功
        else:
            #回退至上一条消息或原始结果
        #提取失败
            if isinstance(result, dict) and "messages" in result:
                ai_message = result["messages"][-1]
                output = ai_message.content
            else:
                output = str(result)
                ai_message = AIMessage(content=output, name=name)

        # 基础更新
        current_messages = list(get_state_attr(state, "messages", []))
        updates = {
            "messages": current_messages + [ai_message],
            "last_active_agent": name
        }
        #每条agent执行之后，把新消息加到消息历史中
        #记录上一个agent是什么
        # StateUpdater 协议
        if hasattr(agent, "get_state_updates"):
            agent_updates = agent.get_state_updates(state, output)
            if agent_updates:
                updates.update(agent_updates)
        # StateUpdater协议（agent 自主决定更新什么）
        # 递增工作流步骤计数器
        current_step = get_state_attr(state, "step_count", 0)
        updates["step_count"] = current_step + 1
        #每执行一次，步骤+1
        # 跟踪已完成的任务，用于工作流进度监控
        current_instruction = get_state_attr(state, "current_instruction", None)
        if current_instruction:
            completed = list(get_state_attr(state, "completed_tasks", []))
            if current_instruction not in completed:
                completed.append(current_instruction)
                updates["completed_tasks"] = completed
        #如果state里面有current_instruction，则把当前任务加入完成列表completed_tasks，方便后续监控流程进度
        return updates

    except Exception as e:
        logger.error(f"Error in {name}: {str(e)}", exc_info=True)
        current_messages = list(get_state_attr(state, "messages", []))
        return {
            "messages": current_messages + [AIMessage(content=f"Error: {str(e)}", name=name)],
            "last_active_agent": name
        }
        #ai执行出错时，不把工作流崩溃而是变成AImessage塞进历史，下次就可以看见某某agent出错了

def _is_non_interactive() -> bool:
    """检测是否应跳过人工交互，自动继续执行。"""
    import os as _os
    return _os.getenv("AUTO_MODE", "").lower() in ("1", "true", "yes")

def _last_agent_errored(state: State) -> bool:
    """检测上一个 Agent 的消息中是否包含错误。"""
    messages = get_state_attr(state, "messages", [])
    if messages:
        last_msg = messages[-1]
        content = getattr(last_msg, "content", "") or ""
        return "Error:" in str(content) or "GraphRecursionError" in str(content)
    return False

def human_choice_node(state: State) -> dict[str, Any]:
    """处理人工输入并选择下一步操作"""
    current_messages = list(get_state_attr(state, "messages", []))

    # 非交互模式下自动继续，或上一个 Agent 出错时自动继续
    if _is_non_interactive() or _last_agent_errored(state):
        reason = "自动模式" if _is_non_interactive() else "上一 Agent 出错"
        print(f"[自动] 跳过人工选择（{reason}）...")
        return {
            "messages": current_messages + [HumanMessage(content="继续执行研究流程")],
            "last_active_agent": "human",
            "current_instruction": "继续执行研究流程"
        }

    print("请选择下一步：")
    print("1. 重新生成假设")
    print("2. 继续开展研究工作")

    while True:
        choice = input("请输入你的选择（1 或 2）：")
        if choice in ["1", "2"]:
            break
        print("输入无效，请重新输入。")

    updates = {
        "messages": current_messages,
        "last_active_agent": "human"
    }

    if choice == "1":
        modification_areas = input("请输入需要修改的内容：")
        updates["messages"] = current_messages + [HumanMessage(content=f"重新生成假设。修改内容：{modification_areas}")]
        updates["hypothesis"] = None
    else:
        updates["messages"] = current_messages + [HumanMessage(content="继续执行研究流程")]
        updates["current_instruction"] = "继续执行研究流程"

    return updates

def create_message(message: Any, name: str) -> BaseMessage:
    """根据消息类型创建 BaseMessage 对象。"""
    if isinstance(message, dict):
        content = message.get("content", "")
        message_type = str(message.get("type", "ai")).lower()
    else:
        content = getattr(message, "content", str(message))
        message_type = str(getattr(message, "type", "ai")).lower()

    return HumanMessage(content=content) if message_type == "human" else AIMessage(content=content, name=name)

def note_agent_node(state: State, agent: BaseAgent, name: str) -> dict[str, Any]:
    """处理 note agent 的动作并更新整个状态。"""
    logger.info(f"Processing note agent: {name}")
    try:
        current_messages = list(get_state_attr(state, "messages", []))

        # 上下文窗口管理
        head_messages: list[BaseMessage] = []
        tail_messages: list[BaseMessage] = []
        processing_messages = current_messages

        if len(current_messages) > 6:
            head_messages = list(current_messages[:2])
            tail_messages = list(current_messages[-2:])
            # 为智能体创建包含精简消息的本地化状态
            # 注：如果智能体要求传入字典类对象，则需传入该类对象
            processing_messages = list(current_messages[2:-2])
            logger.debug("已裁剪消息用于处理")

        # 准备调用状态（如需兼容 Pydantic 模型，可转换为字典格式）
        invoke_state = state.dict() if hasattr(state, "dict") else dict(state)
        invoke_state["messages"] = processing_messages

        result = agent.invoke(invoke_state)
        output = get_structured_output(result, agent)

        if not output:
            logger.error(f"Note agent {name} failed to return structured response. Result: {str(result)[:500]}")
            # 尝试使用原始消息（如果可用）
            raw_content = ""
            if isinstance(result, dict) and "messages" in result and result["messages"]:
                raw_content = result["messages"][-1].content
            elif hasattr(result, "content"):
                raw_content = result.content

            return _create_error_state(state, AIMessage(content=f"Error: Agent {name} failed to return structured response. Raw: {raw_content[:200]}", name=name), name, "Missing structured response")

        # 将 NoteState 输出字段映射到新的 State 模式
        # 使用辅助函数进行安全的属性访问
        # 安全地从对象或字典中获取属性值
        def safe_get(obj, key, default=""):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        new_messages_data = safe_get(output, "messages", [])
        new_messages = [create_message(msg, name) for msg in new_messages_data] if isinstance(new_messages_data, list) else []
        messages: list[BaseMessage] = list(new_messages) if new_messages else list(processing_messages)
        combined_messages = head_messages + messages + tail_messages

        updated_state = {
            "messages": combined_messages,
            "hypothesis": str(safe_get(output, "hypothesis", "")),

            # 语义映射
            "current_instruction": str(safe_get(output, "current_instruction", safe_get(output, "process", ""))),
            "next_workflow_step": str(safe_get(output, "next_workflow_step", safe_get(output, "process_decision", ""))),

            # 工件映射
            "search_artifacts": update_artifact_dict({}, str(safe_get(output, "search_artifacts", safe_get(output, "searcher_state", "")))),
            "data_viz_artifacts": update_artifact_dict({}, str(safe_get(output, "data_viz_artifacts", safe_get(output, "visualization_state", "")))),
            "code_artifacts": update_artifact_dict({}, str(safe_get(output, "code_artifacts", safe_get(output, "code_state", "")))),
            "report_artifacts": update_artifact_dict({}, str(safe_get(output, "report_artifacts", safe_get(output, "report_section", "")))),

            "quality_feedback": str(safe_get(output, "quality_feedback", safe_get(output, "quality_review", ""))),
            "needs_revision": bool(safe_get(output, "needs_revision", False)),

            "last_active_agent": 'note_agent'
        }

        return updated_state

    except Exception as e:
        logger.error(f"Unexpected error in note_agent_node: {e}", exc_info=True)
        return _create_error_state(state, AIMessage(content=f"Unexpected error: {str(e)}", name=name), name, "Unexpected error")

def _create_error_state(state: State, error_message: AIMessage, name: str, error_type: str) -> dict[str, Any]:
    """当出现异常时创建错误状态."""
    logger.info(f"Creating error state for {name}: {error_type}")

    # 基于当前状态
    current_dict = state.dict() if hasattr(state, "dict") else dict(state)

    current_dict["messages"] = list(get_state_attr(state, "messages", [])) + [error_message]
    current_dict["last_active_agent"] = name

    return current_dict

def human_review_node(state: State) -> dict[str, Any]:
    """展示当前状态并处理用户交互。"""
    try:
        # 非交互模式下自动结束
        if _is_non_interactive():
            print("[自动] 非交互模式，自动结束研究流程...")
            return {
                "last_active_agent": "human",
                "needs_revision": False,
                "revision_count": 0
            }

        print("当前研究进度：")
        print(state)
        print("\n你是否需要进一步分析或修改？")

        while True:
            user_input = input("输入 yes 继续分析，或输入 no 结束：").lower()
            if user_input in ['yes', 'no']:
                break

        updates: dict[str, Any] = {"last_active_agent": "human"}

        if user_input == 'yes':
            while True:
                req = input("请输入你的请求：").strip()
                if req:
                    updates["messages"] = [HumanMessage(content=req)]
                    updates["needs_revision"] = True
                    break
        else:
            updates["needs_revision"] = False
            updates["revision_count"] = 0

        return updates

    except Exception as e:
        logger.error(f"人工审核出错：{str(e)}", exc_info=True)
        current_messages = list(get_state_attr(state, "messages", []))
        return {"messages": current_messages + [AIMessage(content=f"Error: {str(e)}", name="human_review")]}

def refiner_node(state: State, agent: BaseAgent, name: str) -> dict[str, Any]:
    """使用 refiner agent 处理报告材料。"""
    try:
        storage_path = Path(WORKING_DIRECTORY)
        materials = []

        # 收集材料（从工作目录读取所有 .md 文件）
        for fpath in storage_path.glob("*.md"):
             with open(fpath, "r", encoding="utf-8") as f:
                materials.append(f"MD file '{fpath.name}':\n{f.read()}")

        combined_materials = "\n\n".join(materials)
        report_content = f"Report materials:\n{combined_materials}"

        # 创建 refiner agent 的状态封装器
        # 如果 agent 要求使用特定键值，我们可能需要构建规范的输入内容。
        refiner_input = state.dict() if hasattr(state, "dict") else dict(state)
        refiner_input["messages"] = [HumanMessage(content=report_content)]

        result = agent.invoke(refiner_input)
        output = result.get("messages")[-1].content

        current_messages = list(get_state_attr(state, "messages", []))
        return {
            "messages": current_messages + [AIMessage(content=output, name=name)],
            "last_active_agent": name,
        }

    except Exception as e:
        logger.error(f"Error in {name}: {str(e)}", exc_info=True)
        current_messages = list(get_state_attr(state, "messages", []))
        return {"messages": current_messages + [AIMessage(content=f"Error: {str(e)}", name=name)]}

logger.info("Agent processing module initialized")
