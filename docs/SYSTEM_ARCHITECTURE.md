# 系统架构概述

本文档提供 DATAGEN 系统架构的高层次概述。

## 文档索引

| 文档 | 描述 |
|----------|-------------|
| [快速入门](QUICKSTART.md) | 5 分钟内配置一个代理 |
| [代理配置](AGENT_CONFIG.md) | AGENT.md 与 config.yaml 完整参考 |
| [工具配置](TOOL_CONFIG.md) | 可用工具与自定义工具指南 |
| [技能配置](SKILL_CONFIG.md) | 创建和使用可复用知识模块 |
| [MCP 配置](MCP_CONFIG.md) | 模型上下文协议服务器设置 |

---

## 核心概念

### 渐进式披露

DATAGEN 采用三级加载策略来优化上下文窗口的使用：

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   第一级：元数据                   ← 启动时加载（约 100 tokens）   │
│   ─────────────────                                             │
│   • 代理名称、描述                                               │
│   • 可用技能列表（仅名称）                                        │
│                                                                 │
│             ▼                                                   │
│                                                                 │
│   第二级：指令                     ← 代理触发时加载                │
│   ─────────────────                                             │
│   • 完整的 AGENT.md 内容                                         │
│   • 自动注入的全局规则                                           │
│                                                                 │
│             ▼                                                   │
│                                                                 │
│   第三级：资源                     ← 按需加载（通过 lookup_skill）  │
│   ─────────────────                                             │
│   • 完整的 SKILL.md 内容                                         │
│   • MCP 服务器资源                                               │
│   • 外部文件                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 设计理念

此架构的灵感来自 [Claude Agent Skills](https://platform.claude.com/docs/agents-and-tools/agent-skills/overview)，确保：

1. **最小的启动成本**：启动时仅加载轻量级元数据
2. **按需加载**：详细指令仅在需要时进入上下文窗口
3. **可组合性**：技能可以在多个代理间共享

---

## 目录结构

```plaintext
config/
├── agent_models.yaml          # LLM 提供商和模型设置
├── mcp.yaml                   # MCP 服务器全局配置
│
├── skills/                    # 共享技能仓库
│   └── {skill-name}/
│       └── SKILL.md
│
└── agents/                    # 代理专属配置
    ├── _shared/
    │   └── rules.md           # 全局规则（自动注入）
    │
    └── {agent_name}/
        ├── AGENT.md           # 系统提示词
        └── config.yaml        # 工具、技能、MCP 设置
```

---

## 核心模块

| 模块 | 路径 | 职责 |
|--------|------|----------------|
| AgentConfigLoader | `src/core/agent_config_loader.py` | 以渐进式披露方式加载代理配置 |
| ToolFactory | `src/tools/factory.py` | 工具注册与动态加载 |
| MCPManager | `src/core/mcp_manager.py` | MCP 服务器生命周期管理 |
| BaseAgent | `src/agents/base.py` | 集成配置的代理基类 |
| State | `src/core/state.py` | 基于 Pydantic 的工作流状态，含语义化字段 |
| StateUpdater | `src/core/state_updater.py` | 解耦代理状态更新逻辑的协议 |
| agent_node | `src/core/node.py` | 处理代理动作并更新状态 |

---

## 后续步骤

- 👉 [快速入门](QUICKSTART.md) - 开始配置你的第一个代理
