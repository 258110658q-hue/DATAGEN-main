# DATAGEN — 多智能体数据分析系统

DATAGEN 是一个基于 **LangGraph** 编排的**多智能体（Multi-Agent）数据分析研究系统**。9 个专业智能体围绕共享状态协作，从数据中自动生成研究假设、执行代码分析、搜索外部信息、创建可视化图表，最终撰写并润色完整的研究报告。

## 目录

- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [架构概览](#架构概览)
- [智能体说明](#智能体说明)
  - [1. Hypothesis Agent — 假设生成器](#1-hypothesis-agent--假设生成器)
  - [2. Process Agent — 流程调度器](#2-process-agent--流程调度器)
  - [3. Code Agent — 代码执行器](#3-code-agent--代码执行器)
  - [4. Search Agent — 信息检索器](#4-search-agent--信息检索器)
  - [5. Visualization Agent — 可视化器](#5-visualization-agent--可视化器)
  - [6. Report Agent — 报告撰写器](#6-report-agent--报告撰写器)
  - [7. Quality Review Agent — 质量审核器](#7-quality-review-agent--质量审核器)
  - [8. Note Agent — 状态记录器](#8-note-agent--状态记录器)
  - [9. Refiner Agent — 报告润色器](#9-refiner-agent--报告润色器)
- [工作流图](#工作流图)
- [完整工具调用链路演示](#完整工具调用链路演示)
- [结构化输出与失败处理](#结构化输出与失败处理)
- [安全机制](#安全机制)
- [配置说明](#配置说明)
- [技术栈](#技术栈)

---

## 快速开始

### 前置条件

- Python 3.10+
- Conda（可选，用于隔离代码执行环境）
- Chrome 浏览器（用于 Google 搜索工具）

### 安装

```bash
# 克隆项目
git clone <your-repo-url>
cd DATAGEN-main

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ".env Example" .env
# 编辑 .env，至少填入一个 LLM API Key（推荐 DeepSeek）
```

### 配置环境变量

编辑 `.env` 文件，关键配置项：

```ini
# 数据存储路径（必填）
WORKING_DIRECTORY = ./data/

# LLM API 密钥（至少需要一个）
# DeepSeek：将密钥填入 OPENAI_API_KEY
OPENAI_API_KEY = your-deepseek-api-key

# 可选：Conda 环境名称
CONDA_ENV = datagen
```

### 命令行运行

```bash
python main.py
```

### Streamlit Web UI 运行

```bash
streamlit run frontend/streamlit_app.py
```

在浏览器中打开后，选择数据文件，输入分析目标，点击"开始分析"即可。

### 自定义配置

- **Agent 模型**：编辑 `config/agent_models.yaml`
- **Agent 提示词**：编辑对应 Agent 的 `config/agents/<agent_name>/AGENT.md`
- **Agent 工具**：编辑对应 Agent 的 `config/agents/<agent_name>/config.yaml`
- **资源限制**：编辑 `config/tool_limits.yaml`
- **MCP 服务器**：编辑 `config/agents/<agent_name>/config.yaml` 中的 `mcp_servers`

---

## 项目结构

```
DATAGEN-main/
├── main.py                          # CLI 入口
├── .env Example                     # 环境变量模板
├── config/
│   ├── agent_models.yaml            # 各 Agent 的 LLM 模型配置
│   ├── tool_limits.yaml             # 代码执行的资源限制
│   └── agents/
│       ├── _shared/rules.md         # 全局规则（语言偏好等）
│       ├── hypothesis_agent/        # 假设生成 Agent
│       │   ├── AGENT.md             #   系统提示词
│       │   └── config.yaml          #   工具/技能/MCP 配置
│       ├── process_agent/           # 流程调度 Agent
│       ├── code_agent/              # 代码执行 Agent
│       ├── search_agent/            # 信息检索 Agent
│       ├── visualization_agent/     # 可视化 Agent
│       ├── report_agent/            # 报告撰写 Agent
│       ├── quality_review_agent/    # 质量审核 Agent
│       ├── note_agent/              # 状态记录 Agent
│       └── refiner_agent/           # 报告润色 Agent
├── frontend/
│   └── streamlit_app.py            # Streamlit Web UI
├── src/
│   ├── config.py                    # 全局配置管理
│   ├── logger.py                    # 日志系统
│   ├── system.py                    # MultiAgentSystem 编排器
│   ├── agents/
│   │   ├── base.py                  # BaseAgent 抽象基类
│   │   ├── factory.py               # AgentFactory
│   │   └── [9个Agent实现文件].py
│   ├── core/
│   │   ├── state.py                 # State Pydantic 模型
│   │   ├── workflow.py              # LangGraph 工作流图构建
│   │   ├── node.py                  # Agent 节点 + 结构化输出解析
│   │   ├── router.py                # 3个条件路由器
│   │   ├── schemas.py               # ArtifactSchema
│   │   ├── state_updater.py         # StateUpdater 协议
│   │   ├── agent_config_loader.py   # 渐进式配置加载
│   │   ├── language_models.py       # LLM 模型管理器
│   │   └── mcp_manager.py           # MCP 协议管理器
│   ├── tools/
│   │   ├── basetool.py              # execute_code/command/list_dir
│   │   ├── FileEdit.py              # 文件读写与文档管理
│   │   ├── internet.py              # Google搜索+网页抓取
│   │   ├── security.py              # 安全扫描+资源限制
│   │   ├── validators.py            # 路径/内容验证器
│   │   ├── factory.py               # 工具注册表
│   │   ├── tool_config.py           # 工具配置加载
│   │   ├── skills.py                # 技能查找工具
│   │   └── mcp_tools.py             # MCP 工具适配器
│   └── llm/
│       ├── base.py                  # LLM Provider 抽象基类
│       ├── factory.py               # Provider 工厂（7种后端）
│       └── [openai/anthropic/google/deepseek/...].py
└── data/                            # 数据与运行输出目录
```

---

## 架构概览

```
┌──────────────┐    ┌─────────────────────────────────────┐
│  用户输入     │───▶│  LangGraph 工作流（StateGraph）       │
│  (CSV数据 +   │    │                                     │
│   分析目标)   │    │  9个Agent节点 + 2个人机交互节点       │
└──────────────┘    │  + 3个条件路由器 + 循环控制           │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌──────────────┐              ┌──────────────────┐
            │  共享 State   │              │  工具系统 (12个)   │
            │  (Pydantic)   │◀─────────────│  execute_code     │
            │  - 消息历史    │   调用工具    │  create_document  │
            │  - 产物字典    │              │  google_search    │
            │  - 流程控制    │              │  scrape_webpages  │
            │  - 修订计数    │              │  wikipedia/arxiv  │
            └──────────────┘              │  ...              │
                    │                      └──────────────────┘
                    ▼
            ┌──────────────┐
            │   输出产物     │
            │  - 研究报告.md │
            │  - 图表.png    │
            │  - 代码.py     │
            │  - 数据.csv    │
            └──────────────┘
```

**核心设计理念**：每个智能体（Agent）是一个独立的 LLM 角色，拥有专属的系统提示词、工具集和结构化输出格式。共享的 `State` 对象作为"黑板"，所有智能体往上面读写信息，由路由器和修订循环控制整体流程。

---

## 智能体说明

### 1. Hypothesis Agent — 假设生成器

| 属性 | 值 |
|---|---|
| **角色定位** | 数据分析的"头脑风暴者" |
| **核心职责** | 读取 CSV 数据，生成可验证的研究假设 |
| **输入** | 用户的分析请求 + 数据文件的列名/样本 |
| **输出** | 一段研究假设文本（存入 `State.hypothesis`） |
| **工具集** | `collect_data`（读取CSV）、`google_search`、`scrape_webpages`、`wikipedia`、`arxiv`、`list_directory` |
| **结构化输出** | 无（纯文本假设） |

**工作方式**：用户提出分析需求后，Hypothesis Agent 首先读取数据文件，了解字段含义和分布，然后结合外部搜索（Google、维基百科、ArXiv）生成有针对性的研究假设。例如，对于销售数据，它可能提出"是否存在季节性销售模式？""客户RFM分群是否与复购率相关？"等假设。

---

### 2. Process Agent — 流程调度器

| 属性 | 值 |
|---|---|
| **角色定位** | 项目"总指挥"，负责分解任务和分配工作 |
| **核心职责** | 将研究假设拆解为子任务，决定下一步该调用哪个 Agent |
| **输入** | 当前状态（假设、已完成任务、历史消息） |
| **输出** | `ProcessRouteSchema`（下一步节点 + 详细指令 + 待办列表） |
| **工具集** | 无（纯推理决策角色） |
| **结构化输出** | `ProcessRouteSchema` |

**ProcessRouteSchema 结构**：

```python
class ProcessRouteSchema(BaseModel):
    next_workflow_step: Literal["FINISH", "Visualization", "Search", "Coder", "Report"]
    current_instruction: str   # 给下一个Agent的详细任务指令
    todo_list: List[str]       # 当前项目待办清单
```

**工作方式**：Process Agent 不执行任何工具，它像一个项目经理——审视当前进度，决定"现在应该做数据可视化"还是"应该搜索外部资料"，然后将具体任务指令传递给下一个 Agent。当所有子任务完成后，它发出 `FINISH` 信号，流程进入报告润色阶段。

---

### 3. Code Agent — 代码执行器

| 属性 | 值 |
|---|---|
| **角色定位** | Python 数据处理与机器学习专家 |
| **核心职责** | 编写并执行数据处理/分析/建模代码 |
| **输入** | Process Agent 分配的任务指令 |
| **输出** | `ArtifactSchema`（代码摘要 + 产物文件路径） |
| **工具集** | `execute_code`、`read_document`、`execute_command`、`list_directory` |
| **结构化输出** | `ArtifactSchema` |

**ArtifactSchema 结构**：

```python
class ArtifactSchema(BaseModel):
    summary: str                        # "完成了RFM客户分群，发现高价值客户占比15%"
    artifacts: Dict[str, str]           # {"output/rfm_result.csv": "客户分群结果数据"}
```

**代码执行安全链路**（详见[安全机制](#安全机制)）：
1. LLM 生成代码 → 2. 正则+AST 安全扫描 → 3. 资源限制器封装 → 4. 在 Conda 环境中执行 → 5. 输出截断

---

### 4. Search Agent — 信息检索器

| 属性 | 值 |
|---|---|
| **角色定位** | 外部知识与信息的"研究员" |
| **核心职责** | 通过多源搜索引擎获取与假设相关的背景资料和数据 |
| **输入** | Process Agent 分配的搜索任务 |
| **输出** | `ArtifactSchema`（搜索结果摘要 + 保存的文档路径） |
| **工具集** | `create_document`、`read_document`、`collect_data`、`google_search`、`scrape_webpages`、`wikipedia`、`arxiv`、`list_directory` |
| **结构化输出** | `ArtifactSchema` |

**搜索工具链**：
- `google_search`：Selenium 无头浏览器模拟 Google 搜索，BeautifulSoup 解析结果
- `scrape_webpages`：优先使用 FireCrawl API，不可用时降级为 WebBaseLoader
- `wikipedia`：通过 langchain_community 查询维基百科
- `arxiv`：搜索 ArXiv 学术论文

---

### 5. Visualization Agent — 可视化器

| 属性 | 值 |
|---|---|
| **角色定位** | 数据可视化与图表制作专家 |
| **核心职责** | 根据分析结果创建 matplotlib/seaborn/plotly 图表 |
| **输入** | Process Agent 分配的可视化任务 |
| **输出** | `ArtifactSchema`（图表摘要 + 图表文件路径） |
| **工具集** | `execute_code`、`read_document`、`execute_command`、`list_directory` |
| **结构化输出** | `ArtifactSchema` |

---

### 6. Report Agent — 报告撰写器

| 属性 | 值 |
|---|---|
| **角色定位** | 中文科研报告撰写专家 |
| **核心职责** | 汇总所有分析产物，用中文撰写结构完整的研究报告 |
| **输入** | 所有前面的分析产物（搜索结果、代码输出、图表） |
| **输出** | `ArtifactSchema`（报告章节摘要 + 报告文件路径） |
| **工具集** | `create_document`、`read_document`、`edit_document`、`list_directory` |
| **结构化输出** | `ArtifactSchema` |

---

### 7. Quality Review Agent — 质量审核器

| 属性 | 值 |
|---|---|
| **角色定位** | 产出的"质检员" |
| **核心职责** | 审查上一个 Agent 的输出质量，决定是否需要修订 |
| **输入** | 任意工作 Agent（Code/Search/Vis/Report）的输出 |
| **输出** | `QualityOutput`（是否需要修订 + 具体反馈） |
| **工具集** | `create_document`、`read_document`、`edit_document`、`list_directory` |
| **结构化输出** | `QualityOutput` |

**QualityOutput 结构**：

```python
class QualityOutput(BaseModel):
    needs_revision: bool   # True = 需要返工
    feedback: str          # "图表的X轴标签缺失，请补充；回归分析的R²值未报告"
```

**修订循环控制**（详见[结构化输出与失败处理](#结构化输出与失败处理)）：
- `needs_revision=True` → 路由回原 Agent 修改（最多 3 次）
- `needs_revision=False` → 通过，进入 NoteTaker
- 超过 3 次修订仍不合格 → 强制推进（防止死循环）

---

### 8. Note Agent — 状态记录器

| 属性 | 值 |
|---|---|
| **角色定位** | 研究过程的"档案管理员" |
| **核心职责** | 汇总所有 Agent 的产物，更新全局 State |
| **输入** | 当前完整的 State（消息历史、各产物字典） |
| **输出** | `NoteOutput`（覆盖所有 State 字段） |
| **工具集** | `read_document`、`list_directory` |
| **结构化输出** | `NoteOutput` |

**NoteOutput 结构**：

```python
class NoteOutput(BaseModel):
    messages: List[Any]            # 裁剪/整理后的消息历史
    hypothesis: str                # 更新后的研究假设
    current_instruction: str       # 更新后的当前指令
    next_workflow_step: str        # 更新后的下一步
    search_artifacts: str          # 搜索产物归档
    data_viz_artifacts: str        # 可视化产物归档
    code_artifacts: str            # 代码产物归档
    report_artifacts: str          # 报告产物归档
    quality_feedback: str          # 质量反馈
    needs_revision: bool           # 修订标记
```

**上下文窗口管理**：当消息历史超过 6 条时，Note Agent 采用"保留首尾、裁剪中间"的策略（保留前 2 条 + 后 2 条，中间部分交给 Note Agent 做摘要），防止超过 LLM 上下文窗口限制。

---

### 9. Refiner Agent — 报告润色器

| 属性 | 值 |
|---|---|
| **角色定位** | 报告的"精修编辑" |
| **核心职责** | 收集所有 `.md` 文件，整合润色为最终报告 |
| **输入** | 工作目录下所有 Markdown 文件内容 |
| **输出** | `ArtifactSchema`（润色后的报告） |
| **工具集** | `create_document`、`read_document`、`edit_document`、`wikipedia`、`google_search`、`scrape_webpages`、`arxiv`、`list_directory` |
| **结构化输出** | `ArtifactSchema` |

---

## 工作流图

```
                            ┌───────────┐
                            │   START   │
                            └─────┬─────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │   Hypothesis   │  ← 生成研究假设
                         └───────┬────────┘
                                 │
                                 ▼
                         ┌──────────────┐
                  ┌──────│ HumanChoice  │──────┐
                  │ 重新 │  (自动跳过)   │ 继续 │
                  │ 生成 └──────────────┘      │
                  │          │                │
                  ▼          │                ▼
          ┌──────────┐      │        ┌───────────┐
          │Hypothesis│◄─────┘        │  Process  │  ← 任务分解+路由
          └──────────┘               └─────┬─────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │       │             │             │       │
                    ▼       ▼             ▼             ▼       ▼
              ┌──────┐ ┌──────┐   ┌────────────┐ ┌──────┐ ┌──────┐
              │Coder │ │Search│   │Visualization│ │Report│ │Refiner│
              └──┬───┘ └──┬───┘   └──────┬─────┘ └──┬───┘ └──┬───┘
                 │        │              │          │        │
                 └────────┴──────────────┴──────────┘        │
                              │                              │
                              ▼                              │
                     ┌────────────────┐                      │
                     │ QualityReview  │                      │
                     └───────┬────────┘                      │
                             │                               │
                  ┌──────────┴──────────┐                    │
                  │ needs_revision?      │                    │
                  │ (最多3次)             │                    │
                  └──────────┬──────────┘                    │
                       是    │    否                         │
                  ┌──────────┘    └──────────┐               │
                  ▼                          ▼               │
          ┌──────────────┐           ┌────────────┐         │
          │回到原Agent修改│           │ NoteTaker  │         │
          └──────────────┘           └──────┬─────┘         │
                                           │               │
                                           ▼               │
                                    ┌───────────┐          │
                                    │  Process  │◄─────────┘
                                    └─────┬─────┘  (FINISH)
                                          │
                                          ▼
                                   ┌────────────┐
                                   │  Refiner   │ ← 润色最终报告
                                   └──────┬─────┘
                                          │
                                          ▼
                                   ┌────────────┐
                                   │HumanReview │ ← 自动结束
                                   └──────┬─────┘
                                    否    │    是
                               ┌──────────┘    └──────────┐
                               ▼                          ▼
                        ┌──────────┐                 ┌────────┐
                        │ Process  │                 │  END   │
                        └──────────┘                 └────────┘
```

**流程说明**：
1. **Hypothesis → HumanChoice**：生成假设后，用户可选择"重新生成"或"继续"
2. **Process → {Coder, Search, Visualization, Report}**：Process Agent 按任务需要路由到具体执行 Agent
3. **执行 Agent → QualityReview**：每个执行 Agent 完成后必须经过质量审核
4. **QualityReview 修订循环**：不合格则返回修改（最多 3 次），合格则进入 NoteTaker 归档
5. **NoteTaker → Process**：归档后回到 Process，开始下一个子任务
6. **Process → Refiner**：所有任务完成时发出 FINISH
7. **HumanReview → END**：最终审核通过后结束

**安全保护**：
- `step_count > 20` 时强制进入 Refiner（防止无限循环）
- `revision_count > 3` 时强制进入 NoteTaker（防止质量审核死循环）
- 所有异常被捕获并转为 `AIMessage`，不会导致流程崩溃

---

## 完整工具调用链路演示

以下演示一次完整的工具调用链路：**从用户输入到 Code Agent 执行代码的端到端过程**。

### 场景设定

用户输入：
> "分析 OnlineSalesData.csv，找出影响销售额的关键因素"

### 链路追踪

```
步骤1: Hypothesis Agent 被调用
│
├─ 工具调用: collect_data(file_path="data/OnlineSalesData.csv")
│  ├─ 内部: PathValidator 验证路径安全性
│  ├─ 内部: 尝试 utf-8 → gbk → latin-1 编码读取
│  └─ 返回: DataFrame 的前5行 + 列信息
│
├─ 工具调用: google_search(query="OnlineSalesData 销售数据分析方法")
│  ├─ 内部: Selenium Chrome 无头浏览器启动
│  ├─ 内部: 执行搜索 → 解析搜索结果 → 提取标题+URL+摘要
│  └─ 返回: 搜索结果列表
│
└─ 输出: "假设：客户年龄、购买时段、产品类别是影响销售额的关键因素"
   → 写入 State.hypothesis

────────────────────────────────────────────────────────

步骤2: HumanChoice (AUTO_MODE 自动跳过)
└─ 注入 HumanMessage("继续执行研究流程")
   → State.current_instruction = "继续执行研究流程"

────────────────────────────────────────────────────────

步骤3: Process Agent 被调用
│
├─ (无工具调用 — 纯推理角色)
│
└─ 结构化输出 (ProcessRouteSchema):
   {
     "next_workflow_step": "Coder",
     "current_instruction": "编写Python代码对OnlineSalesData.csv进行多元回归分析，
                            以年龄、购买时段、产品类别为自变量，销售额为因变量",
     "todo_list": [
       "1. 数据清洗与预处理",
       "2. 多元回归分析",
       "3. 可视化关键因素",
       "4. 撰写分析报告"
     ]
   }
   → process_router 读取 next_workflow_step → 路由到 "Coder"

────────────────────────────────────────────────────────

步骤4: Code Agent 被调用
│
├─ 工具调用: read_document(file_path="data/OnlineSalesData.csv")
│  ├─ 内部: PathValidator 验证路径
│  ├─ 内部: 检查文件大小 (max 5MB)
│  └─ 返回: 文件内容
│
├─ 工具调用: execute_code(code="""
│       import pandas as pd
│       import statsmodels.api as sm
│
│       df = pd.read_csv('data/OnlineSalesData.csv')
│       df = df.dropna()
│       X = df[['Age', 'PurchaseHour', 'ProductCategory']]
│       X = pd.get_dummies(X, columns=['ProductCategory'], drop_first=True)
│       y = df['SalesAmount']
│       X = sm.add_constant(X)
│       model = sm.OLS(y, X).fit()
│       print(model.summary())
│   """)
│  │
│  │  ┌── 安全扫描阶段 ──────────────────────────┐
│  │  │ 1. 正则扫描: 检测 os.system, subprocess, │
│  │  │    eval, exec, __import__, shutil.rmtree  │
│  │  │ 2. AST 扫描: ast.parse() 遍历 AST 节点   │
│  │  │    - 检查 Call→Name 是否为危险内置函数    │
│  │  │    - 检查 Import/ImportFrom 是否为风险模块│
│  │  │    - 检查 os.system / shutil.rmtree 调用  │
│  │  │ → ScanResult(is_safe=True, violations=[]) │
│  │  └──────────────────────────────────────────┘
│  │
│  │  ┌── 资源限制器 ───────────────────────────┐
│  │  │ - timeout: 根据 tool_limits.yaml 配置    │
│  │  │ - 进程监控: 多线程读取 stdout/stderr     │
│  │  │ - 进度超时: N 秒无输出则 kill            │
│  │  │ - 内存限制: Linux 下 setrlimit           │
│  │  │ - 输出截断: max_output_chars 50000       │
│  │  └──────────────────────────────────────────┘
│  │
│  │  ┌── 执行阶段 ─────────────────────────────┐
│  │  │ 1. 将代码写入临时 .py 文件               │
│  │  │ 2. subprocess.Popen 在 conda 环境中执行  │
│  │  │ 3. 多线程实时读取 stdout/stderr          │
│  │  │ 4. 等待进程结束或触发超时                │
│  │  └──────────────────────────────────────────┘
│  │
│  └─ 返回: stdout 输出 (回归结果摘要)
│
├─ 工具调用: create_document(
│       points=["回归分析结果", "关键因素: 年龄(p<0.001), 产品类别(p<0.01)"],
│       file_path="output/regression_analysis.md"
│   )
│  ├─ 内部: ContentValidator 检查内容
│  │  - 检测 TODO/FIXME/TBD/HACK 标记
│  │  - 检测 API 密钥/密码泄露
│  │  - 文件大小限制检查
│  └─ 返回: 文件保存成功
│
└─ 结构化输出 (ArtifactSchema):
   {
     "summary": "多元回归显示年龄(p<0.001)和产品类别(p<0.01)是销售额的显著预测因子",
     "artifacts": {
       "output/regression_analysis.md": "回归分析详细结果",
       "output/model_results.csv": "模型系数表"
     }
   }
   → State.code_artifacts 更新

────────────────────────────────────────────────────────

步骤5: QualityReview Agent 被调用
│
└─ 结构化输出 (QualityOutput):
   {
     "needs_revision": false,
     "feedback": ""
   }
   → QualityReview_router: needs_revision=false → "NoteTaker"

────────────────────────────────────────────────────────

步骤6: NoteTaker (Note Agent) 被调用
│
├─ 工具调用: read_document(所有产物文件)
├─ 工具调用: list_directory(工作目录)
│
└─ 结构化输出 (NoteOutput):
   {
     "messages": [...],
     "current_instruction": "撰写分析报告",
     "next_workflow_step": "Report",
     "code_artifacts": "output/regression_analysis.md: 回归分析详细结果",
     ...
   }
   → 回到 Process Agent，进入下一轮任务
```

---

## 结构化输出与失败处理

### 什么是结构化输出？

DATAGEN 中 6 个 Agent 使用 **Pydantic 模型** 来约束 LLM 的输出格式。LLM 必须返回符合 JSON Schema 的结构化数据，而不是自由文本。

| Agent | Schema | 关键字段 |
|---|---|---|
| Process | `ProcessRouteSchema` | `next_workflow_step`, `current_instruction`, `todo_list` |
| Code | `ArtifactSchema` | `summary`, `artifacts` |
| Search | `ArtifactSchema` | `summary`, `artifacts` |
| Visualization | `ArtifactSchema` | `summary`, `artifacts` |
| Report | `ArtifactSchema` | `summary`, `artifacts` |
| QualityReview | `QualityOutput` | `needs_revision`, `feedback` |
| Note | `NoteOutput` | `messages`, `hypothesis`, 所有 artifacts 字段 |
| Refiner | `ArtifactSchema` | `summary`, `artifacts` |

### 结构化输出解析流程

`get_structured_output()` 函数采用 **4 层降级策略** 来提取结构化数据：

```
                    ┌──────────────────────────┐
                    │ Agent 调用返回 result     │
                    └───────────┬──────────────┘
                                │
                    ┌───────────▼──────────────┐
                    │ 第1层: result["structured │
                    │ _response"] 是否存在？    │
                    └───────────┬──────────────┘
                          是    │    否
                    ┌──────────┘    └──────────┐
                    ▼                          ▼
              ┌──────────┐           ┌──────────────────┐
              │ 直接返回  │           │ 第2层: result 自身 │
              └──────────┘           │ 是否是 Pydantic?   │
                                     │ (有 .dict() 或     │
                                     │  .model_dump())    │
                                     └────────┬─────────┘
                                        是    │    否
                                  ┌──────────┘    └──────────┐
                                  ▼                          ▼
                            ┌──────────┐           ┌──────────────────┐
                            │ 直接返回  │           │ 第3层: 从最后一条  │
                            └──────────┘           │ 消息内容中提取 JSON │
                                                   └────────┬─────────┘
                                                      成功   │   失败
                                                ┌──────────┘    └──────────┐
                                                ▼                          ▼
                                          ┌──────────┐           ┌──────────┐
                                          │ 返回 dict │           │ 返回 None │
                                          └──────────┘           └──────────┘
```

#### 第3层 JSON 提取的细节

当 LLM 返回的是嵌在文本中的 JSON 时，`extract_json_from_text()` 会尝试两种策略：

```python
# 策略A: 匹配 ```json ... ``` 代码块
json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)

# 策略B: 找到第一个 { 和最后一个 } 之间的内容
start_idx = text.find('{')
end_idx = text.rfind('}')
# 然后尝试 json.loads(text[start_idx:end_idx+1])
```

### 失败处理的完整链路

当结构化输出解析**完全失败**（`get_structured_output()` 返回 `None`）时，系统不会崩溃，而是采用以下降级策略：

#### 场景1: 普通 Agent (agent_node) 的结构化输出失败

```
agent_node() 调用 agent.invoke(state)
  │
  ├─ get_structured_output(result, agent) → None (解析失败)
  │
  ├─ 回退路径:
  │   │
  │   ├─ 尝试从 result["messages"][-1] 获取原始 AIMessage
  │   │  → 将整个消息内容作为字符串输出
  │   │
  │   └─ 如果消息列表中也没有 → 直接 str(result) 作为输出
  │
  ├─ 创建 AIMessage(content=原始字符串, name=agent_name)
  │
  └─ 流程继续，不会中断
     (但下游 Agent 收到的可能是非结构化的文本)
```

**关键代码**（`node.py:130-138`）：
```python
if output:
    content = safe_get_content(output, ["task", "feedback", "summary", "current_instruction"])
    ai_message = AIMessage(content=content, name=name)
else:
    # 回退：解析失败时使用原始消息
    if isinstance(result, dict) and "messages" in result:
        ai_message = result["messages"][-1]
        output = ai_message.content
    else:
        output = str(result)
        ai_message = AIMessage(content=output, name=name)
```

#### 场景2: Note Agent 的结构化输出失败

Note Agent 的失败影响最大（因为它要更新整个 State），所以有专门的错误处理：

```
note_agent_node() 调用 agent.invoke(invoke_state)
  │
  ├─ get_structured_output(result, agent) → None
  │
  ├─ 日志记录: ERROR "Note agent note_agent failed to return
  │              structured response. Result: {result[:500]}"
  │
  └─ _create_error_state():
     │
     ├─ 保留当前 State 的全部内容
     ├─ 追加错误 AIMessage: "Error: Agent note_agent failed to
     │   return structured response. Raw: {raw_content[:200]}"
     └─ 流程继续，不会中断
```

#### 场景3: QualityReview Agent 收到非结构化字符串

`QualityReviewAgent.get_state_updates()` 设计了针对字符串输入的**启发式降级**：

```python
if isinstance(output, str):
    logger.warning(f"QualityReviewAgent received string instead of QualityOutput: {output[:100]}...")
    # 启发式判断: 如果输出中包含修改相关关键词，假定需要修订
    needs_revision = any(kw in output.lower()
                         for kw in ["revision", "improve", "fix", "correct", "change"])
    feedback = output
```

#### 场景4: Agent 调用本身抛出异常

```python
except Exception as e:
    logger.error(f"Error in {name}: {str(e)}", exc_info=True)
    # 将异常转换为 AIMessage，流程继续
    return {
        "messages": current_messages + [
            AIMessage(content=f"Error: {str(e)}", name=name)
        ],
        "last_active_agent": name
    }
```

### 失败处理的设计原则

| 原则 | 说明 |
|---|---|
| **永不崩溃** | 任何解析失败都被捕获，不会导致工作流中断 |
| **优雅降级** | 结构化输出 → 原始消息 → 字符串，逐层回退 |
| **信息保留** | 失败时的原始输出始终被保存在消息历史中 |
| **日志可见** | 所有失败路径都有 WARNING/ERROR 级别日志 |
| **流程推进** | 即使单个 Agent 失败，工作流也会继续（由修订循环和安全计数器兜底） |

### 防止级联失败的保护机制

```
保护1: 修订计数器 (revision_count ≤ 3)
  └─ 防止 QualityReview 和 Agent 之间的无限修订循环

保护2: 步骤计数器 (step_count ≤ 20)
  └─ 防止整体工作流的无限循环

保护3: 异常捕获 (try/except 包裹所有 agent_node)
  └─ 单个 Agent 的崩溃不会拖垮整条流水线

保护4: 上下文裁剪 (Note Agent 的首尾保留策略)
  └─ 防止消息历史超出 LLM 上下文窗口
```

---

## 安全机制

DATAGEN 在执行 LLM 生成的代码前，实施了多层安全防护：

### 代码安全扫描 (`SecurityScanner`)

**第一层：正则模式匹配**（快速阻断已知危险模式）

```python
blocked_patterns = [
    "os.system", "subprocess.call", "subprocess.run",
    "subprocess.Popen", "shutil.rmtree", "eval(", "exec(",
    "__import__"
]
```

**第二层：AST 静态分析**（精确检测实际调用）

- 检测危险内置函数调用：`eval()`, `exec()`, `compile()`, `__import__()`
- 检测风险模块导入：`os`, `subprocess`, `shutil`, `socket`, `ctypes`
- 检测风险属性访问：`os.system()`, `shutil.rmtree()`
- 语法错误不阻断（留待运行时处理）

### 资源限制 (`ResourceLimiter`)

| 限制类型 | 说明 |
|---|---|
| **固定超时** | 代码运行超过 N 秒后强制 `kill` |
| **进度超时** | N 秒内无 stdout 输出则终止（防止死循环占着进程） |
| **内存限制** | Linux 下通过 `resource.setrlimit(RLIMIT_AS)` 限制 |
| **输出截断** | stdout 超过 `max_output_chars`(默认50000) 时截断 |

### 路径与内容验证

| 验证器 | 功能 |
|---|---|
| **PathValidator** | 阻止访问 `/etc`, `/sys`, `/proc`, `~/.ssh` 等敏感路径；限制文件扩展名白名单 |
| **ContentValidator** | 检测文件大小限制；检测 `TODO`/`FIXME`/`TBD`/`HACK` 占位符；检测 API 密钥泄露 |

---

## 配置说明

### Agent 配置的双层结构

每个 Agent 有两层配置：

```
config/agents/code_agent/
├── AGENT.md          # 系统提示词（YAML 头 + Markdown 正文）
└── config.yaml       # 工具、技能、规则、MCP 服务器配置
```

#### AGENT.md 示例

```markdown
---
name: code-agent
description: 数据分析与处理的Python编程专家。
use_complete_prompt: true
---

你是一位精通数据处理与分析的 Python 编程专家...

**输出格式：**
你必须输出一个遵循 `ArtifactSchema` 结构的 JSON 对象：
- `summary`：对所编写、执行的代码及获得的结果的简要总结。
- `artifacts`：一个字典，键为文件绝对路径，值为内容描述。
```

#### config.yaml 示例

```yaml
tools:
  - execute_code
  - read_document
skills:
  - pandas-cheat-sheet
rules:
  - _shared/rules.md
mcp_servers: []
```

### 工具配置的加载优先级

```
config.yaml 中显式配置了 tools (即使是空列表)
  → 使用 config.yaml 中的工具列表
  → 不加载硬编码回退工具

config.yaml 中没有 tools 字段
  → 使用 Agent 子类的 _get_tools() 硬编码回退

额外追加:
  + skills 配置的技能工具
  + mcp_servers 配置的 MCP 工具
```

---

## 技术栈

| 层级 | 技术 |
|---|---|
| **工作流编排** | LangGraph (StateGraph + 条件路由 + 检查点) |
| **LLM 框架** | LangChain (create_agent + 工具绑定) |
| **结构化输出** | Pydantic (response_format) |
| **代码安全** | AST 静态分析 + 正则扫描 + 资源限制 |
| **前端 UI** | Streamlit |
| **MCP 协议** | Model Context Protocol (stdio 通信) |
| **LLM 后端** | 支持 7 种: DeepSeek / OpenAI / Anthropic / Google / Ollama / Azure / Groq |
