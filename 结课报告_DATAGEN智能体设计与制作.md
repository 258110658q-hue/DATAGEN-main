# AI智能体设计与制作实践 —— 结课报告

**课程名称**：AI智能体设计与制作实践

**项目名称**：DATAGEN — 基于多智能体协作的自动化数据分析与研究平台

**姓名**：[请填写你的姓名]

**学号**：[请填写你的学号]

**日期**：2026年6月4日

---

## 目录

1. [设计该智能体的初衷与解决的问题](#一设计该智能体的初衷与解决的问题)
2. [智能体的创建步骤与设置过程](#二智能体的创建步骤与设置过程)
3. [智能体的功能、用途与使用场景](#三智能体的功能用途与使用场景)
4. [实践收获与总结](#四实践收获与总结)

---

## 一、设计该智能体的初衷与解决的问题

### 1.1 设计背景与初衷

在当今数据驱动的时代，数据分析已成为各行各业不可或缺的核心能力。然而，传统的数据分析流程存在以下痛点：

- **流程繁琐**：一次完整的数据分析需要经历"数据清洗 → 探索性分析 → 假设提出 → 统计建模 → 可视化 → 报告撰写"等多个环节，每个环节都需要不同的专业知识和工具，单靠一人难以高质量完成全流程。
- **门槛较高**：有效的数据分析不仅需要编程能力（Python/R），还需要统计学知识、机器学习理论、可视化设计能力以及学术写作能力——这些技能的组合对非专业人员构成了巨大障碍。
- **效率低下**：传统方式下，分析师需要在 Jupyter Notebook、Excel、可视化工具、Word 文档之间反复切换，上下文切换成本极高。
- **质量不稳定**：人工分析容易遗漏关键变量、忽略重要的统计检验、或在不经意间引入偏见，分析质量高度依赖个人经验。

正是基于以上观察，我设计了 **DATAGEN**——一个基于多智能体协作架构的自动化数据分析平台。核心理念是：**将数据分析全流程中的每个专业环节交给专门的 AI Agent 负责，通过 Agent 之间的智能协作，实现从"原始数据"到"分析报告"的端到端自动化。**

取名 DATAGEN，意为 "Data Generation"——不仅是数据的生成，更是数据洞察的生成。

### 1.2 解决的核心问题

DATAGEN 智能体系统针对性地解决了以下问题：

| 痛点 | DATAGEN 的解决方案 |
|------|-------------------|
| 分析流程碎片化 | 9 个专业 Agent 通过 LangGraph 工作流无缝协作，一个输入即可驱动全流程 |
| 专业技能门槛高 | 每个 Agent 内置专业知识（统计、ML、可视化、学术写作），用户只需用自然语言描述需求 |
| 质量控制缺失 | 内置 `quality_review_agent`，自动审查每个环节的输出，最多 3 次修订循环 |
| 上下文管理混乱 | `note_agent` 自动压缩长对话历史，优化 token 使用，保证长流程不丢失关键信息 |
| 工具生态割裂 | 统一工具系统集成代码执行、网页搜索、文件操作、MCP 外部服务器 |
| 模型选择受限 | 支持 7 种 LLM 提供商（OpenAI、Anthropic、Google、DeepSeek、Ollama、Groq、Azure），可按需为每个 Agent 配置不同模型 |

---

## 二、智能体的创建步骤与设置过程

### 2.1 整体架构设计

在开始编码之前，我首先进行了系统架构的顶层设计。DATAGEN 采用**多智能体协作架构**，核心设计原则包括：

1. **专业化分工**：每个 Agent 只负责一个明确的子任务（假设生成、代码编写、可视化、报告撰写等），遵循单一职责原则。
2. **工作流编排**：使用 LangGraph 状态图（StateGraph）定义 Agent 之间的协作流程和路由规则。
3. **共享状态**：所有 Agent 通过 Pydantic 定义的统一 State 对象共享上下文，包括消息历史、任务列表、产出物等。
4. **渐进式配置**：受 Claude Agent Skills 规范启发，采用三级加载策略优化上下文窗口使用。

**系统架构如下图所示：**

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入 (自然语言)                        │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph 工作流引擎                           │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │Hypothesis│──▶│HumanChoice│──▶│ Process  │──▶│ Coder/Search │ │
│  │  Agent   │   │   Node   │   │  Agent   │   │ /Viz/Report  │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────┘ │
│                                                       ▼         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │  END     │◀──│HumanReview│◀──│ Refiner  │◀──│QualityReview │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 创建步骤详解

#### 第一步：环境搭建

首先创建 Python 虚拟环境并安装核心依赖：

```bash
# 创建 Conda 虚拟环境
conda create -n datagen python=3.10
conda activate datagen

# 安装核心依赖
pip install -r requirements.txt
```

核心依赖包括：
- **LangChain 1.0.x + LangGraph 1.0.x**：Agent 框架和工作流编排
- **Pandas 2.3.3**：数据处理
- **Pydantic**：状态模型定义
- **PyYAML**：配置文件解析
- **Selenium + BeautifulSoup4**：网页搜索与抓取
- **MCP（Model Context Protocol）**：外部工具服务器集成

#### 第二步：配置环境变量

在 `.env` 文件中配置以下关键参数：

```ini
# 工作目录（数据文件存放路径）
WORKING_DIRECTORY = ./data/

# 配置目录
CONFIG_DIRECTORY = config

# Conda 环境名称
CONDA_ENV = datagen

# LLM API 密钥（按需配置）
OPENAI_API_KEY = sk-xxx
ANTHROPIC_API_KEY = sk-ant-xxx
GOOGLE_API_KEY = xxx

# MCP 工具密钥
TAVILY_API_KEY = tvly-xxx
GITHUB_TOKEN = github_pat_xxx
```

#### 第三步：设计 Agent 系统

这是最核心的环节——创建 9 个专业 Agent 并定义各自的职责：

**（1）Agent 基类设计（`src/agents/base.py`）**

所有 Agent 继承自 `BaseAgent` 抽象基类，统一封装了：
- LLM 模型绑定（通过 `language_models.py` 分配）
- 工具注册（通过 `ToolFactory` 动态加载）
- 系统提示词注入（通过 `AgentConfigLoader` 渐进式加载）
- MCP 工具适配

```python
class BaseAgent(ABC):
    def __init__(self, name, llm, tools, system_prompt, ...):
        self.name = name
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        # 创建 LangChain ReAct Agent
        self.agent = self._create_agent()

    @abstractmethod
    def process(self, state: State) -> dict:
        """每个 Agent 必须实现的核心处理逻辑"""
        pass
```

**（2）9 个专业 Agent 的职责划分**

| 序号 | Agent 名称 | 类名 | 核心职责 | 配置文件 |
|------|-----------|------|---------|---------|
| 1 | `hypothesis_agent` | `HypothesisAgent` | 分析数据，提出研究假设并验证可行性 | `config/agents/hypothesis_agent/AGENT.md` |
| 2 | `process_agent` | `ProcessAgent` | 研究主管：管理 todo_list，决定下一步由哪个 Agent 执行 | `config/agents/process_agent/AGENT.md` |
| 3 | `code_agent` | `CodeAgent` | 编写和执行 Python 数据分析代码 | `config/agents/code_agent/AGENT.md` |
| 4 | `search_agent` | `SearchAgent` | 文献检索（Wikipedia、arXiv）和网络搜索 | `config/agents/search_agent/AGENT.md` |
| 5 | `visualization_agent` | `VisualizationAgent` | 创建数据可视化图表 | `config/agents/visualization_agent/AGENT.md` |
| 6 | `report_agent` | `ReportAgent` | 撰写结构化研究报告（中文输出） | `config/agents/report_agent/AGENT.md` |
| 7 | `quality_review_agent` | `QualityReviewAgent` | 审查输出质量，判断是否需要修订 | `config/agents/quality_review_agent/AGENT.md` |
| 8 | `note_agent` | `NoteAgent` | 记录研究过程，压缩上下文窗口 | `config/agents/note_agent/AGENT.md` |
| 9 | `refiner_agent` | `RefinerAgent` | 润色和优化最终报告 | `config/agents/refiner_agent/AGENT.md` |

**（3）Agent 配置示例（以 `process_agent` 为例）**

每个 Agent 的 AGENT.md 文件使用 YAML frontmatter + Markdown 格式：

```markdown
---
name: process-agent
description: 研究主管，负责监督和协调综合性数据分析项目。
use_complete_prompt: true
---

你是一位研究主管，负责监督和协调一个综合性的数据分析项目。

**你的核心职责：**
管理 `todo_list` 并引导团队完成研究流程。

**管理待办事项列表：**
- **初始化：** 开始时，将用户的需求分解为具体步骤列表
- **更新：** 每个步骤完成后，从列表中移除已完成的任务
- **选择：** 始终选择 `todo_list` 中最优先的一项作为 `current_instruction`

**路由指南：**
- **Visualization：** 用于绘图、图表和图形
- **Search：** 用于文献综述、数据收集或事实核查
- **Coder：** 用于数据处理、清洗和统计分析脚本
- **Report：** 用于撰写最终论文的各个章节
- **FINISH：** 仅当 `todo_list` 为空且最终报告已完成时使用
```

#### 第四步：搭建工作流（LangGraph StateGraph）

工作流是 DATAGEN 的"骨架"。我使用 LangGraph 的 StateGraph 来定义 9 个 Agent 之间的协作流程：

```python
class WorkflowManager:
    def setup_workflow(self):
        # 1. 创建状态图
        self.workflow = StateGraph(State)

        # 2. 注册所有 Agent 节点
        self.workflow.add_node("Hypothesis", hypothesis_action)
        self.workflow.add_node("Process", process_action)
        self.workflow.add_node("Coder", coder_action)
        self.workflow.add_node("Search", search_action)
        self.workflow.add_node("Visualization", viz_action)
        self.workflow.add_node("Report", report_action)
        self.workflow.add_node("QualityReview", qr_action)
        self.workflow.add_node("NoteTaker", note_action)
        self.workflow.add_node("Refiner", refiner_action)

        # 3. 定义流程边和条件路由
        self.workflow.add_edge(START, "Hypothesis")
        self.workflow.add_edge("Hypothesis", "HumanChoice")
        self.workflow.add_conditional_edges("HumanChoice", hypothesis_router, ...)
        self.workflow.add_conditional_edges("Process", process_router, ...)
        # ... 更多路由规则

        # 4. 编译为可执行图
        self.graph = self.workflow.compile()
```

**工作流执行顺序：**

```
START → Hypothesis（生成假设）→ HumanChoice（人工确认）
    → Process（任务调度）→ Coder/Search/Visualization/Report（执行具体任务）
    → QualityReview（质量审查）→ NoteTaker（记录笔记）→ Process（循环）
    → Refiner（润色报告）→ HumanReview（人工审核）→ END
```

关键设计亮点：
- **条件路由**：`process_router` 根据 `next_workflow_step` 字段动态决定任务分发目标
- **质量闭环**：`QualityReview_router` 判断输出是否合格，不合格则回退重做（最多 3 次）
- **人工节点**：在关键决策点（假设确认、最终审核）设置人工交互节点，保证人类对分析方向的控制权

#### 第五步：实现工具系统

为了让 Agent 能够真正"做事"而不仅仅"说话"，我实现了一套完整的工具系统：

**（1）代码执行工具**：Agent 可以编写并安全执行 Python 代码，支持超时控制、内存限制和 AST 安全扫描。

```python
# 安全机制示例（src/tools/security.py）
FORBIDDEN_FUNCTIONS = ['eval', 'exec', 'os.system', 'subprocess.run', ...]
FORBIDDEN_PATHS = ['/etc', '/sys', '/proc', '/root', '~/.ssh', ...]
```

**（2）文件操作工具**：支持 CSV 数据读取（多编码自动检测）、Markdown 文档创建/读取/编辑。

**（3）网络搜索工具**：集成 Google 搜索（Selenium 无头浏览器）、Wikipedia API、arXiv API、FireCrawl 网页抓取。

**（4）MCP 集成工具**：通过 Model Context Protocol 接入外部工具服务器（文件系统访问、Tavily 网络搜索、GitHub 仓库操作），并通过 `MCPToolAdapter` 包装为 LangChain 原生工具。

#### 第六步：LLM 多提供商支持

实现了 `ProviderFactory` 工厂模式，支持 7 种 LLM 后端的懒加载：

```python
# src/llm/factory.py
class ProviderFactory:
    _providers = {
        'openai': (ChatOpenAI, 'langchain-openai'),
        'anthropic': (ChatAnthropic, 'langchain-anthropic'),
        'google': (ChatGoogleGenerativeAI, 'langchain-google-genai'),
        'deepseek': (ChatOpenAI, 'langchain-openai'),  # OpenAI 兼容
        'ollama': (ChatOllama, 'langchain-ollama'),
        'groq': (ChatGroq, 'langchain-groq'),
        'azure': (AzureChatOpenAI, 'langchain-openai'),
    }
```

通过 `config/agent_models.yaml` 可为每个 Agent 独立指定使用的 LLM 模型和参数：

```yaml
agents:
  code_agent:
    provider: deepseek
    model_config:
      model: deepseek-chat
      temperature: 1.0
  report_agent:
    provider: anthropic
    model_config:
      model: claude-sonnet-4-20250514
      temperature: 0.7
```

#### 第七步：全局规则注入

在 `config/agents/_shared/rules.md` 中定义全局规则，所有 Agent 自动继承：

- 代码注释和文档字符串使用英文，用户输出使用简体中文
- 所有函数签名包含类型提示
- 使用 Google 风格的文档字符串
- 随机算法必须锁定随机种子以保证可复现性
- 不允许静默失败

#### 第八步：前端界面（可选）

使用 Streamlit 构建 Web UI（`frontend/streamlit_app.py`），提供：
- 自然语言输入分析任务
- 实时显示 Agent 协作流程
- 展示关键输出和生成文件
- 每次运行创建独立输出目录

### 2.3 设置过程总结

整个智能体的创建遵循了"架构设计 → 环境搭建 → Agent 设计 → 工作流编排 → 工具集成 → 前端封装"的完整流程，体现了软件工程中的**分层架构**和**关注点分离**原则。

---

## 三、智能体的功能、用途与使用场景

### 3.1 核心功能总览

DATAGEN 提供以下 8 大核心功能：

| 功能模块 | 负责 Agent | 详细说明 |
|----------|-----------|---------|
| **自动假设生成** | `hypothesis_agent` | 分析上传的数据集，自动生成可验证的研究假设，附文献支撑 |
| **智能任务调度** | `process_agent` | 将用户需求分解为 todo_list，动态分配给最合适的 Agent |
| **代码自动生成与执行** | `code_agent` | 编写 Python 代码进行数据清洗、统计分析、机器学习建模，经安全扫描后执行 |
| **文献与网络搜索** | `search_agent` | 自动搜索 Wikipedia、arXiv、Google，获取领域知识和参考文献 |
| **数据可视化** | `visualization_agent` | 生成 matplotlib/seaborn 图表，自动嵌入报告 |
| **报告自动撰写** | `report_agent` | 撰写结构化中文研究报告（引言→方法论→结果→讨论→结论） |
| **质量自动审查** | `quality_review_agent` | 审查每个环节输出，判断是否需要修订（最多 3 次循环） |
| **上下文智能管理** | `note_agent` | 压缩长对话历史，优化 token 使用，保证长流程不丢失关键信息 |

### 3.2 工作流详解

DATAGEN 的完整工作流包含 6 个阶段：

```
阶段 1：假设提出
  用户上传数据 + 输入分析需求
  → hypothesis_agent 分析数据，提出研究假设
  → 人工确认或要求重新生成

阶段 2：任务规划
  process_agent 将研究目标分解为具体任务列表（todo_list）
  → 按优先级逐一分配

阶段 3：并行执行
  code_agent 编写并执行数据分析代码
  search_agent 搜索相关文献和数据
  visualization_agent 创建可视化图表
  report_agent 撰写报告各章节

阶段 4：质量审查
  quality_review_agent 审查每个输出
  → 不合格：返回重做（最多 3 次）
  → 合格：继续下一任务

阶段 5：笔记记录
  note_agent 压缩上下文，记录当前进度
  → 返回阶段 2，继续下一个任务

阶段 6：润色与交付
  refiner_agent 润色最终报告
  → 人工审核，确认是否还需修改
  → 完成，生成最终报告
```

### 3.3 典型使用场景

#### 场景一：学术研究数据分析

**用户**：研究生/科研人员

**需求**：对实验数据进行统计分析，生成可用于论文的研究报告

**操作步骤**：
1. 将实验数据（CSV 格式）放入 `data/` 目录
2. 在 `main.py` 中编写：
   ```python
   user_input = '''
   datapath:experiment_data.csv
   请对实验数据进行全面的统计分析，包括描述性统计、假设检验、
   相关性分析和回归分析，并生成包含图表的完整研究报告
   '''
   ```
3. 运行 `python main.py`
4. 在交互提示中确认假设方向
5. 等待自动生成包含 SPSS 风格统计表和可视化图表的报告

**输出**：一份结构完整的学术研究报告（.md 格式），包含引言、方法论、结果分析和讨论章节。

#### 场景二：商业销售数据分析

**用户**：企业数据分析师/业务人员

**需求**：分析销售数据，发现趋势和异常，辅助商业决策

**操作步骤**：
1. 上传销售数据（项目内置 `OnlineSalesData.csv` 作为示例）
2. 输入分析需求："分析销售趋势，识别影响销售额的关键因素，使用机器学习预测下季度销售"
3. 系统自动完成：数据清洗 → 趋势可视化 → 特征重要性分析（随机森林）→ 预测建模 → 报告生成

**输出**：包含销售趋势折线图、热力图、特征重要性条形图和预测结果的综合分析报告。

#### 场景三：教育教学演示

**用户**：教师/学生

**需求**：在课堂上演示 AI 驱动的数据分析流程

**操作步骤**：
1. 使用 Streamlit Web UI 启动：`streamlit run frontend/streamlit_app.py`
2. 在浏览器中直接输入分析任务
3. 实时观察 9 个 Agent 如何协作完成分析
4. 查看每个 Agent 的输出和最终报告

**输出**：可用于教学展示的完整分析过程和结果。

#### 场景四：快速数据探索

**用户**：任何需要快速理解数据集的用户

**需求**：对陌生数据集进行快速探索和初步分析

**操作步骤**：
1. 将数据集放入 `data/` 目录
2. 输入："请对这个数据集进行探索性数据分析（EDA），包括数据概况、缺失值分析、分布分析和关键变量关系"
3. 系统自动生成 EDA 报告

**输出**：包含数据摘要、缺失值热力图、分布直方图、相关性矩阵的 EDA 报告。

### 3.4 关键特性

1. **多模型混合配置**：可为不同 Agent 选择不同 LLM——例如代码生成用 Claude（编程能力强），报告撰写用 DeepSeek（性价比高），搜索用 Gemini（搜索能力强）。

2. **安全执行环境**：Agent 生成的代码经过 AST 静态分析扫描，禁止危险函数调用（eval、exec、os.system 等），限制文件访问路径，设定执行超时和内存上限。

3. **渐进式配置系统**：受 Claude Agent Skills 启发，Agent 配置采用三级加载——启动时仅加载元数据（~100 tokens），触发时加载完整提示词，按需加载技能和 MCP 资源，最大化节省上下文窗口。

4. **人机协作**：在关键决策点（假设确认、最终审核）保留人工介入通道，保证 AI 分析不偏离用户意图。

---

## 四、实践收获与总结

### 4.1 技术收获

通过本次 DATAGEN 智能体的设计与制作，我在以下方面获得了显著的提升：

#### （1）多智能体架构设计能力

深入理解了多 Agent 系统的核心设计模式：
- **专业化分工**：将复杂任务拆解为多个专业化子任务，每个 Agent 聚焦单一职责，降低单个 Agent 的复杂度。
- **工作流编排**：掌握 LangGraph StateGraph 的使用，包括节点注册、条件路由、状态管理和检查点（Checkpoint）机制。
- **共享状态管理**：使用 Pydantic BaseModel 定义类型安全的状态对象，所有 Agent 通过统一的状态接口通信，避免了信息孤岛。

#### （2）大语言模型应用开发

- 掌握了 LangChain 框架的 ReAct Agent 模式（Reasoning + Acting）
- 理解了系统提示词（System Prompt）对 Agent 行为的关键影响
- 学会了通过 `temperature`、`max_iterations` 等参数调优 Agent 表现
- 实践了多模型混合配置策略——不同任务选用最适合的 LLM

#### （3）工具系统与安全机制

- 实现了工具的动态注册和加载（ToolFactory 模式）
- 集成了 MCP（Model Context Protocol）协议，将外部工具服务器包装为 LangChain 原生工具
- 设计了多层安全机制：AST 静态代码分析、路径白名单、内容验证器、资源限制器

#### （4）软件工程实践

- 实践了工厂模式（AgentFactory、ProviderFactory）、单例模式（MCPManager）、策略模式（路由函数）等设计模式
- 应用了渐进式披露（Progressive Disclosure）的配置管理理念
- 编写了清晰的文档注释和类型提示

### 4.2 关键挑战与解决方案

| 挑战 | 解决方案 |
|------|---------|
| **上下文窗口溢出**：长分析流程中消息历史不断膨胀，超出 LLM 上下文限制 | 设计 `note_agent` 自动压缩历史消息，保留关键信息的同时释放上下文空间 |
| **Agent 输出质量不稳定**：单次生成的结果可能包含错误或不完整 | 引入 `quality_review_agent` 审查机制 + 最多 3 次修订循环，形成质量闭环 |
| **代码执行安全性**：Agent 生成的代码可能包含危险操作 | 实现 AST 静态分析器 + 正则模式检测，阻止 eval/exec/os.system 等危险调用 |
| **工具调用兼容性**：不同来源的工具（内置/MCP/LangChain）接口不统一 | 通过 `MCPToolAdapter` 将 MCP 工具包装为 LangChain 标准 BaseTool |
| **多 LLM 提供商管理**：不同 Agent 可能需要不同模型 | 设计 `ProviderFactory` 懒加载工厂 + `agent_models.yaml` 配置，支持按 Agent 独立指定模型 |

### 4.3 心得体会

1. **"分而治之"是复杂系统设计的核心原则**。面对数据分析这样一个包含多个专业环节的复杂任务，将其拆解为 9 个专业化 Agent 是成功的关键。每个 Agent 只需做好一件事，整体系统却能完成远超个体能力的工作。

2. **质量闭环比单次生成更重要**。在实际使用中，我发现 Agent 的第一次输出往往不是最优的。引入"生成→审查→修订"的质量闭环后，最终输出的质量有了显著提升。这让我深刻理解了迭代优化的重要性。

3. **人机协作是 AI 系统的必要设计**。虽然 DATAGEN 追求全流程自动化，但我在关键决策点保留了人工交互节点（假设确认、最终审核）。实践证明，这种设计既保证了效率，又让用户保持对分析方向的控制。

4. **安全机制需要从设计之初就考虑**。当 Agent 能够编写和执行代码时，安全问题就不能是"事后补救"。DATAGEN 的 AST 扫描器、路径白名单和资源限制器是在设计阶段就规划好的，这避免了潜在的安全风险。

5. **好的配置系统是 Agent 可维护性的基础**。受 Claude Agent Skills 规范启发，我实现了渐进式披露的配置架构。这让 Agent 的行为调整不再需要修改代码，只需编辑 YAML 和 Markdown 配置文件即可。

### 4.4 未来展望

DATAGEN 仍有很大的改进空间，后续我计划从以下方向继续优化：

1. **提升 Agent 推理深度**：引入 Chain-of-Thought 和 Tree-of-Thoughts 等推理策略，增强 Agent 在复杂分析任务中的推理能力。
2. **支持更多数据格式**：目前主要支持 CSV，未来计划支持 Excel、JSON、SQL 数据库等更多数据源。
3. **增加协作模式**：支持多个用户同时参与分析，Agent 充当"分析主持人"角色。
4. **优化运行效率**：通过并行 Agent 执行和缓存机制，缩短整体分析时间。
5. **增强可视化交互性**：使用 Plotly 等交互式可视化库替代静态图表，让报告更加生动。

### 4.5 总结

通过本次"AI智能体设计与制作实践"课程，我完成了 DATAGEN——一个基于多智能体协作的自动化数据分析平台。该项目从零开始，经历了需求分析、架构设计、Agent 开发、工作流编排、工具集成、安全机制设计和前端封装等完整的软件工程流程。

DATAGEN 目前包含 **9 个专业化 Agent**，支持 **7 种 LLM 提供商**，集成了 **10+ 种工具**，能够实现从"原始数据"到"分析报告"的端到端自动化。它不仅在技术上是一个完整的多智能体系统，在实践上也切实解决了数据分析流程繁琐、门槛高、效率低的痛点。

这次实践让我深刻体会到：**AI 智能体的真正价值不在于单个模型的能力，而在于如何将多个专业能力有机组合，形成一个能够解决真实问题的协作系统。** 这一认知将指导我在 AI 领域的后续学习和探索。

---

> **附录**：DATAGEN 项目源代码可在 GitHub 查看：[https://github.com/starpig1129/DATAGEN](https://github.com/starpig1129/DATAGEN)

---

*本报告由 [你的姓名] 撰写，作为 AI智能体设计与制作实践 课程的结课作业。*
