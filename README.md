# DATAGEN（前身 AI-Data-Analysis-MultiAgent）

![DATAGEN Banner](./docs/DATAGEN.jpg "DATAGEN Banner")

## 关于 DATAGEN
DATAGEN 是一个富有力量感的品牌名称，代表着我们利用人工智能技术进行数据生成和分析的愿景。名称由 "DATA" 和 "GEN"（生成）组合而成，完美体现了本项目的核心功能——通过多代理系统实现自动化的数据分析和研究。

![系统架构](./docs/Architecture.png)

## 概述

DATAGEN 是一个先进的 AI 驱动的数据分析与研究平台，利用多个专业化代理来简化数据分析、可视化和报告生成等任务。我们的平台采用 LangChain、OpenAI 的 GPT 模型和 LangGraph 等前沿技术来处理复杂的研究流程，整合多种 AI 架构以实现最佳性能。

## 核心特性

### 智能分析核心
- **高级假设引擎**
  - AI 驱动的研究假设生成与验证
  - 自动化的研究方向优化
  - 实时的假设精炼
- **企业级数据处理**
  - 强大的数据清洗与转换
  - 可扩展的分析流水线
  - 自动化的质量保证
- **动态可视化套件**
  - 交互式数据可视化
  - 自定义报告生成
  - 自动化的洞察提取

### 先进的技术架构
- **多代理智能**
  - 针对不同任务的专业化代理
  - 智能任务分配
  - 实时协调与优化
- **智能记忆管理**
  - 最先进的笔记代理
  - 高效的上下文保留系统
  - 无缝的工作流集成
- **自适应处理流水线**
  - 动态工作流调整
  - 自动化的资源优化
  - 实时性能监控

## DATAGEN 的独特优势

DATAGEN 通过其创新的多代理架构和智能自动化能力，彻底改变了数据分析的方式：

1. **先进的多代理系统**
   - 专业化代理协同工作
   - 智能任务分配与协调
   - 实时适应复杂的分析需求

2. **智能上下文管理**
   - 开创性的笔记代理用于状态跟踪
   - 高效的内存利用和上下文保留
   - 跨分析阶段的无缝集成

3. **企业级性能**
   - 稳健且可扩展的架构
   - 一致且可靠的结果
   - 生产就绪的实现

## 系统要求

- Python 3.10 或更高版本

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/starpig1129/DATAGEN.git
```
2. 创建并激活 Conda 虚拟环境：
```bash
conda create -n datagen python=3.10
conda activate datagen
```
3. 安装依赖：
```bash
pip install -r requirements.txt
```
4. 配置环境变量：
**将 `.env Example` 重命名为 `.env` 并填写所有值**
```sh
# 数据存储路径（必填）
# 同时供 filesystem MCP 服务器使用
WORKING_DIRECTORY = ./data/

# 配置目录路径（可选）
# 所有配置文件（agent_models.yaml、agents/、mcp.yaml）均相对于此目录。
# 默认为 config/
# 使用 'config_local' 进行本地开发以避免 Git 跟踪（已在 .gitignore 中）
CONFIG_DIRECTORY = config

# Conda 环境名称（必填）
CONDA_ENV = datagen

# ChromeDriver 可执行文件路径（必填）
CHROMEDRIVER_PATH = ./chromedriver-linux64/chromedriver

# Firecrawl API 密钥（可选）
# 注意：如果缺少此密钥，查询能力可能会降低
FIRECRAWL_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# OpenAI API 密钥（可选）
OPENAI_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Anthropic API 密钥（可选）
ANTHROPIC_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Google API 密钥（可选）
GOOGLE_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# LangChain API 密钥（可选）
# 用于监控处理过程
LANGCHAIN_TRACING_V2 = true
LANGCHAIN_PROJECT = "Multi-agent-DataAnalysis"
LANGCHAIN_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# MCP（模型上下文协议）设置（可选）
# Tavily API 密钥用于 web-search MCP 服务器
TAVILY_API_KEY = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# GitHub token 用于 github MCP 服务器
GITHUB_TOKEN = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

## 使用方式

### 使用 Python 脚本

你可以使用 main.py 运行系统：

1. 将数据文件（例如 YourDataName.csv）放入 data 目录

2. 修改 main.py 中 main() 函数的 user_input 变量：
```python
user_input = '''
datapath:YourDataName.csv
使用机器学习进行数据分析，并撰写完整的图表报告
'''
```

3. 运行脚本：
```bash
python main.py
```

## 主要组件

- `hypothesis_agent`：生成研究假设
- `process_agent`：监督整个研究流程
- `visualization_agent`：创建数据可视化
- `code_agent`：编写数据分析代码
- `searcher_agent`：进行文献和网络搜索
- `report_agent`：撰写研究报告
- `quality_review_agent`：执行质量审查
- `note_agent`：记录研究过程

## 工作流

系统使用 LangGraph 创建状态图来管理整个研究流程。工作流包括以下步骤：

1. 假设生成
2. 人工选择（继续或重新生成假设）
3. 处理（包括数据分析、可视化、搜索和报告撰写）
4. 质量审查
5. 根据需要修订

### 代理模型配置

用户可以通过编辑 `agent_models.yaml` 文件（位于你的 `CONFIG_DIRECTORY` 中）来自定义每个代理的语言模型提供商和模型配置。这使得只需指向不同的配置文件夹即可实现无缝的环境切换（开发/生产）。

以下是 `agent_models.yaml` 的示例结构：

```yaml
agents:
  hypothesis_agent:
    provider: openai
    model_config:
      model: gpt-5-nano
      temperature: 1.0
  note_agent:
    provider: google
    model_config:
      model: gemini-2.5-pro
      temperature: 1.0
  code_agent:
    provider: anthropic
    model_config:
      model: claude-haiku-4-5
      temperature: 1.0
```

- **provider**：指定要使用的语言模型提供商（例如 openai、google、anthropic、ollama、groq）
- **model_config**：包含模型特定的配置参数
  - `model`：要使用的具体模型名称
  - `temperature`：控制模型输出的随机性（范围：0.0-2.0）

## 高级配置系统

DATAGEN 实现了强大的**渐进式披露**架构用于代理配置，灵感来自 [Claude Agent Skills](https://platform.claude.com/docs/agents-and-tools/agent-skills/overview)。

### 文档

| 指南 | 描述 |
|-------|-------------|
| [系统架构](docs/SYSTEM_ARCHITECTURE.md) | 高层次概述与核心概念 |
| [快速入门](docs/QUICKSTART.md) | 5 分钟内创建新代理 |
| [代理配置参考](docs/AGENT_CONFIG.md) | AGENT.md 与 config.yaml 完整参考 |
| [工具配置](docs/TOOL_CONFIG.md) | 可用工具与自定义工具创建 |
| [技能配置](docs/SKILL_CONFIG.md) | 创建和使用可复用知识模块 |
| [MCP 配置](docs/MCP_CONFIG.md) | 模型上下文协议服务器设置 |

### 核心特性
- **统一配置根目录**：所有核心设置通过 `CONFIG_DIRECTORY` 环境变量管理。
- **基于技能的架构**：可复用的技能存储在 `skills/` 中（位于配置根目录下）
- **动态工具加载**：通过 `ToolFactory` 在 `config.yaml` 中配置工具
- **模型上下文协议（MCP）**：外部服务器集成（文件系统、GitHub、网络搜索）
- **渐进式披露**：三级加载策略优化上下文窗口使用

## 注意事项

- 确保你有足够的 API 配额，系统将会发起多次 API 调用。
- 根据任务复杂度，系统可能需要一些时间来完成整个研究流程。
- **警告**：代理系统可能会修改正在分析的数据。强烈建议在使用本系统之前备份数据。

## 当前问题与解决方案
1. 笔记代理效率提升
2. 整体运行时间优化
3. 精炼代理需要进一步改进

## 贡献

欢迎提交 Pull Request。对于重大更改，请先创建 Issue 讨论你希望修改的内容。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=starpig1129/DATAGEN&type=Date)](https://star-history.com/#starpig1129/DATAGEN&Date)

## 其他项目
以下是我其他一些值得关注的项目：

### PheroPath
PheroPath 是一个基于文件系统的信息素通信协议，允许代理和人类在文件上留下不可见的"信息素"（信号）。它能够在不修改文件内容本身的情况下传达上下文、风险（DANGER）或状态（TODO、SAFE），促进更好的多代理协作。
- GitHub: [PheroPath](https://github.com/starpig1129/PheroPath)

### PigPig：先进的多模态 LLM Discord 机器人
一个基于多模态大语言模型（LLM）的强大 Discord 机器人，旨在通过自然语言与用户交互。
它结合了先进的 AI 能力与实用功能，为 Discord 社区提供丰富的体验。
- GitHub: [ai-discord-bot-PigPig](https://github.com/starpig1129/ai-discord-bot-PigPig)
