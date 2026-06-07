# 代理配置参考

本文档详细说明所有代理配置选项。

## 目录结构

每个代理的配置位于 `config/agents/{agent_name}/`：

```
config/agents/{agent_name}/
├── AGENT.md       # 系统提示词（必填）
└── config.yaml    # 能力配置（必填）
```

---

## AGENT.md 格式

### YAML 前置元数据（Frontmatter）

| 字段 | 类型 | 必填 | 描述 |
|-------|------|----------|-------------|
| `name` | string | ✅ | 唯一的代理标识符（小写字母 + 连字符） |
| `description` | string | ✅ | 代理功能的简要描述 |
| `version` | string | ❌ | 语义版本号（默认：1.0.0） |
| `use_complete_prompt` | boolean | ❌ | 如果为 `true`，则使用完整提示模式 |

### 示例

```markdown
---
name: code-agent
description: 数据分析代码编写与执行的 Python 专家
version: 1.2.0
---

# 代码代理

你是一位精通数据处理的 Python 程序员...
```

---

## config.yaml 格式

### 完整结构

```yaml
# 工具列表（字符串数组）
tools:
  - execute_code
  - read_document

# 技能引用（来自 config/skills/）
skills:
  - data-validation

# 规则文件路径
rules: _shared/rules.md

# MCP 服务器列表
mcp_servers:
  - filesystem
  - web-search
```

### 字段说明

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `tools` | List[str] | 可用工具名称（参见 [工具配置](TOOL_CONFIG.md)） |
| `skills` | List[str] | 引用的技能名称（参见 [技能配置](SKILL_CONFIG.md)） |
| `rules` | str | 规则文件路径（相对于 `config/agents/`） |
| `mcp_servers` | List[str] | 启用的 MCP 服务器名称 |

---

## 加载机制

### 渐进式披露

系统采用三级加载策略来优化上下文窗口的使用：

```
┌─────────────────────────────────────────────────────────────┐
│  第一级：元数据                                              │
│  ─────────────────────────────────────────────────────────  │
│  • 系统启动时加载                                            │
│  • 仅包含名称、描述                                          │
│  • 非常轻量（约 100 tokens）                                 │
└─────────────────────────────────────────────────────────────┘
          │
          ▼ （代理被触发时）
┌─────────────────────────────────────────────────────────────┐
│  第二级：指令                                                │
│  ─────────────────────────────────────────────────────────  │
│  • 完整的系统提示词（AGENT.md 内容）                          │
│  • 自动注入的全局规则                                        │
└─────────────────────────────────────────────────────────────┘
          │
          ▼ （代理调用 lookup_skill 时）
┌─────────────────────────────────────────────────────────────┐
│  第三级：资源                                                │
│  ─────────────────────────────────────────────────────────  │
│  • 完整的 SKILL.md 内容                                      │
│  • MCP 服务器资源                                            │
│  • 外部文件                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 状态扩展（高级）

代理可以通过实现 `StateUpdater` 协议来自定义其输出如何更新工作流状态。

### 实现自定义状态更新

在你的代理类中重写 `get_state_updates()`：

```python
from src.agents.base import BaseAgent

class MyCustomAgent(BaseAgent):
    def get_state_updates(self, state, output):
        """定义自定义状态字段映射。"""
        return {
            "my_custom_field": output.some_value,
            "another_field": output.other_value,
        }
```

### 内置状态字段

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `step_count` | int | 每次代理执行时自动递增 |
| `completed_tasks` | List[str] | 自动跟踪已完成的指令 |
| `revision_count` | int | 跟踪连续的修订请求 |
| `quality_feedback` | Optional[str] | 审查通过后清空 |

---

## 相关文档
- [快速入门](QUICKSTART.md)
- [工具配置](TOOL_CONFIG.md)
- [技能配置](SKILL_CONFIG.md)
- [MCP 配置](MCP_CONFIG.md)
