# 快速入门

本指南帮助你快速配置 DATAGEN 的代理系统。

## 准备工作
- 完成基础安装（参见 [README.md](../README.md#安装)）
- 确保 `.env` 文件已正确配置

---

## 教程 1：配置已有代理

全部 9 个已有代理均支持外部配置。你可以在不修改代码的情况下改变它们的行为。

### 第一步：修改系统提示词

编辑 `config/agents/{agent_name}/AGENT.md`：

```markdown
---
name: code-agent
description: 编写和执行数据分析代码的 Python 专家
version: 1.0.0
---

# 代码代理

你是一位精通数据处理的 Python 程序员...

## 自定义指令
[在此添加你的自定义指令]
```

### 第二步：修改可用工具

编辑 `config/agents/{agent_name}/config.yaml`：

```yaml
tools:
  - execute_code
  - read_document
  - wikipedia        # 添加研究工具
  - arxiv
```

### 第三步：验证更改

重启系统，代理将使用新的配置：
```bash
python main.py
```

---

## 教程 2：更改 LLM 模型

编辑 `config/agent_models.yaml` 来更改代理的模型：

```yaml
agents:
  code_agent:
    provider: anthropic      # openai、google、anthropic、ollama
    model_config:
      model: claude-sonnet-4-20250514
      temperature: 0.7
```

支持的提供商：
- `openai` - GPT 系列
- `google` - Gemini 系列
- `anthropic` - Claude 系列
- `ollama` - 本地模型

---

## 教程 3：添加全局规则

编辑 `config/agents/_shared/rules.md`。所有代理将自动遵循这些规则：

```markdown
# 全局规则

## 输出格式
- 所有代码必须包含类型提示
- 使用 Google 风格的文档字符串

## 安全指南
- 不执行文件删除操作
- 敏感数据必须脱敏处理
```

---

## 可用代理

| 代理 | 配置路径 | 职责 |
|-------|-------------|----------------|
| `hypothesis_agent` | `config/agents/hypothesis_agent/` | 生成研究假设 |
| `process_agent` | `config/agents/process_agent/` | 监督整体工作流 |
| `code_agent` | `config/agents/code_agent/` | 编写分析代码 |
| `search_agent` | `config/agents/search_agent/` | 文献和网络搜索 |
| `visualization_agent` | `config/agents/visualization_agent/` | 数据可视化 |
| `report_agent` | `config/agents/report_agent/` | 撰写报告 |
| `quality_review_agent` | `config/agents/quality_review_agent/` | 质量审查 |
| `note_agent` | `config/agents/note_agent/` | 记录研究过程 |
| `refiner_agent` | `config/agents/refiner_agent/` | 润色最终报告 |

---

## 后续步骤
- [代理配置参考](AGENT_CONFIG.md) - 完整的配置选项
- [工具配置](TOOL_CONFIG.md) - 可用工具列表
- [技能配置](SKILL_CONFIG.md) - 创建可复用知识模块
