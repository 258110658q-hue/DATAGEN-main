"""
DATAGEN Streamlit Frontend
启动方式: streamlit run frontend/streamlit_app.py
每次运行自动创建独立输出目录，不会污染 data/ 根目录。
"""
import streamlit as st
import sys
import os
import shutil
import time
from datetime import datetime

# 修复 Windows GBK 编码问题
for _stream_name in ('stdout', 'stderr'):
    try:
        getattr(sys, _stream_name).reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.environ["USER_AGENT"] = "DATAGEN-Streamlit/1.0"

# ── Monkey-patch: 终端交互 → 自动决策 ──
from langchain_core.messages import HumanMessage
import src.core.node as node_module
import src.core.workflow as workflow_module


def _auto_choice(state):
    msgs = list(state.messages) if hasattr(state, "messages") else []
    return {
        "messages": msgs + [HumanMessage(content="Continue the research process")],
        "hypothesis": getattr(state, "hypothesis", None),
        "current_instruction": "Continue the research process",
        "last_active_agent": "human",
    }


def _auto_review(state):
    return {"needs_revision": False, "revision_count": 0, "last_active_agent": "human"}


node_module.human_choice_node = _auto_choice
node_module.human_review_node = _auto_review
workflow_module.human_choice_node = _auto_choice
workflow_module.human_review_node = _auto_review

from src.system import MultiAgentSystem
from src.core.state import create_initial_state

AGENT_NAMES = {
    "hypothesis_agent": "假设生成", "process_agent": "流程调度",
    "visualization_agent": "图表生成", "code_agent": "代码执行",
    "search_agent": "信息搜索", "report_agent": "报告撰写",
    "quality_review_agent": "质量审核", "note_agent": "状态记录",
    "refiner_agent": "报告精炼", "human": "用户交互", "user": "用户",
}

# ═══════════════════ UI ═══════════════════

st.set_page_config(page_title="DATAGEN 数据分析", page_icon="📊", layout="wide")
st.title("📊 DATAGEN — 多 Agent 智能数据分析")
st.caption("基于 LangGraph 的 9 Agent 协作系统 | 模型: DeepSeek-Chat")

# 侧边栏
with st.sidebar:
    st.header("📁 输入数据 (data/)")
    data_dir = os.path.join(PROJECT_ROOT, "data")
    csv_files = []
    if os.path.exists(data_dir):
        for f in sorted(os.listdir(data_dir)):
            fp = os.path.join(data_dir, f)
            if os.path.isfile(fp) and not f.startswith("."):
                if f.endswith(".csv"):
                    csv_files.append(f)
                st.text(f"• {f}  ({os.path.getsize(fp)/1024:.1f} KB)")

    st.divider()
    st.header("📂 历史运行记录")
    run_dirs = []
    if os.path.exists(data_dir):
        for d in sorted(os.listdir(data_dir), reverse=True):
            dp = os.path.join(data_dir, d)
            if os.path.isdir(dp) and d.startswith("run_"):
                run_dirs.append(d)
                st.text(f"📁 {d}")
    if not run_dirs:
        st.text("（暂无）")

# 输入区域
col1, col2 = st.columns([3, 1])
with col1:
    user_input = st.text_area(
        "📝 分析任务",
        value="请分析 OnlineSalesData.csv 文件，进行数据清洗、描述性统计、趋势分析、区域对比、促销活动效果评估，生成可视化图表和中文报告。",
        height=100,
    )

with col2:
    st.markdown("### 🚀")
    run_button = st.button("▶ 开始分析", type="primary", use_container_width=True)
    cleanup = st.button("🧹 清理旧结果", use_container_width=True)
    if cleanup:
        cleaned = 0
        for d in run_dirs:
            dp = os.path.join(data_dir, d)
            try:
                shutil.rmtree(dp)
                cleaned += 1
            except Exception:
                pass
        if cleaned:
            st.success(f"已清理 {cleaned} 个历史目录")
            st.rerun()
        else:
            st.info("没有需要清理的目录")

if run_button:
    if not user_input.strip():
        st.warning("请输入分析任务")
    else:
        st.divider()

        # 创建本次运行的独立输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(data_dir, f"run_{timestamp}")
        os.makedirs(run_dir, exist_ok=True)

        # 复制输入 CSV 到运行目录（两个位置，兼容 Agent 的不同路径写法）
        for cf in csv_files:
            shutil.copy2(os.path.join(data_dir, cf), os.path.join(run_dir, cf))
            # 同时在 run_dir/data/ 下创建副本，兼容 Agent 使用 data/xxx.csv 路径
            run_data_subdir = os.path.join(run_dir, "data")
            os.makedirs(run_data_subdir, exist_ok=True)
            shutil.copy2(os.path.join(data_dir, cf), os.path.join(run_data_subdir, cf))

        # 设置本次运行的工作目录
        import src.config as cfg
        original_wd = cfg.WORKING_DIRECTORY
        cfg.WORKING_DIRECTORY = run_dir
        # 同时更新 FileEdit 里的引用
        import src.tools.FileEdit as fe
        fe.WORKING_DIRECTORY = run_dir
        import src.tools.basetool as bt
        bt.WORKING_DIRECTORY = run_dir

        status_area = st.empty()

        try:
            status_area.info(f"⏳ 初始化 Agent 系统... | 输出目录: `{run_dir}`")
            system = MultiAgentSystem()
            initial_state = create_initial_state(user_input.strip())
            graph = system.workflow_manager.get_graph()

            seen_agents = []
            all_outputs = []
            run_dir_path = run_dir

            status_area.info("🤖 Agent 团队正在工作中...")

            for event in graph.stream(
                initial_state,
                {"configurable": {"thread_id": "1"}, "recursion_limit": 3000},
                stream_mode="values",
                debug=False,
            ):
                if isinstance(event, dict):
                    agent = event.get("last_active_agent", "?")
                    display = AGENT_NAMES.get(agent, agent)
                    if display not in seen_agents:
                        seen_agents.append(display)

                    msgs = event.get("messages", [])
                    if msgs:
                        last = msgs[-1]
                        content = getattr(last, "content", "") if hasattr(last, "content") else str(last)
                        if content and len(content) > 10:
                            all_outputs.append((display, content))

            status_area.success(f"✅ 分析完成！共 {len(seen_agents)} 个 Agent 参与协作")

            # Agent 流程
            st.subheader("🤖 Agent 协作流程")
            for name in seen_agents:
                st.markdown(f"&nbsp;&nbsp;✅ {name}")

            # 输出内容
            st.subheader("📋 关键输出")
            meaningful = [(a, c) for a, c in all_outputs if "Error" not in c and len(c) > 20]
            for i, (agent, content) in enumerate(meaningful[-8:]):
                preview = content[:120].replace("\n", " ")
                with st.expander(f"{i+1}. [{agent}] {preview}...", expanded=(i >= len(meaningful) - 3)):
                    st.text(content)

            # 生成的文件
            st.subheader(f"📁 本次输出: `{run_dir_path}`")
            if os.path.exists(run_dir_path):
                all_files = [f for f in os.listdir(run_dir_path) if not f.endswith(".csv")]
                if all_files:
                    for f in sorted(all_files):
                        fp = os.path.join(run_dir_path, f)
                        st.text(f"📄 {f}  ({os.path.getsize(fp)/1024:.1f} KB)")
                else:
                    st.text("（Agent 未生成新文件）")

        except Exception as e:
            status_area.error(f"❌ 分析出错: {e}")
            import traceback
            st.code(traceback.format_exc())
        finally:
            # 恢复原始工作目录
            cfg.WORKING_DIRECTORY = original_wd
            fe.WORKING_DIRECTORY = original_wd
            bt.WORKING_DIRECTORY = original_wd
