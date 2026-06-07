# MCP 配置指南

本文档说明如何配置模型上下文协议（MCP）服务。

## 概述

MCP（模型上下文协议）是一种标准化协议，允许代理安全地与外部系统交互，例如：
- 文件系统操作
- GitHub 仓库访问
- 网络搜索
- 数据库查询

---

## 准备工作

### 必需依赖

```bash
pip install mcp>=1.0.0
```

### Node.js

MCP 服务器通常是 Node.js 包。请确保已安装 Node.js 18+（推荐 Node.js 20+）。

```bash
node --version  # 应为 v18+（推荐 v20+）
```

---

## 环境变量

在 `.env` 文件中配置以下内容：

| 变量 | 必填 | 描述 |
|----------|----------|-------------|
| `WORKING_DIRECTORY` | ✅ | filesystem MCP 服务器使用的数据目录 |
| `TAVILY_API_KEY` | ❌ | web-search MCP 服务器的 API 密钥 |
| `GITHUB_TOKEN` | ❌ | github MCP 服务器的个人访问令牌 |

`.env` 示例：

```sh
# 数据存储路径（同时供 filesystem MCP 服务器使用）
WORKING_DIRECTORY = ./data/

# MCP（模型上下文协议）设置（可选）
# Tavily API 密钥用于 web-search MCP 服务器
TAVILY_API_KEY = 你的_tavily_api_密钥
# GitHub token 用于 github MCP 服务器
GITHUB_TOKEN = 你的_github_令牌
```

---

## 全局配置

### 文件位置

MCP 服务在 `config/mcp.yaml` 中统一定义：

```yaml
servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "${WORKING_DIRECTORY}"]
    description: 用于数据文件的本地文件系统访问
	    
  web-search:
    command: npx
    args: ["-y", "@anthropic/mcp-server-web-search"]
    env:
      TAVILY_API_KEY: ${TAVILY_API_KEY}
    description: 网络搜索能力
	    
  github:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: ${GITHUB_TOKEN}
    description: GitHub 仓库访问

defaults:
  - filesystem   # 默认对所有代理启用
```

### 配置结构

| 字段 | 描述 |
|-------|-------------|
| `servers` | 所有可用的 MCP 服务定义 |
| `servers.{name}.command` | 启动服务的命令 |
| `servers.{name}.args` | 命令参数 |
| `servers.{name}.env` | 环境变量 |
| `servers.{name}.description` | 人类可读的描述 |
| `defaults` | 默认对所有代理启用的服务 |

---

## 代理专属配置

### 在 config.yaml 中启用

除了全局的 `defaults` 外，每个代理还可以启用额外的服务：

```yaml
# config/agents/search_agent/config.yaml
mcp_servers:
  - filesystem
  - web-search
```

### 最终结果

代理的已启用服务 = `defaults` ∪ 代理专属的 `mcp_servers`

---

## 可用工具

### Filesystem 服务器

`filesystem` MCP 服务器提供 14 个工具：

| 工具 | 描述 |
|------|-------------|
| `read_file` | 将文件内容读取为文本 |
| `read_text_file` | 支持编码的文件读取 |
| `read_media_file` | 将图片/音频读取为 base64 |
| `read_multiple_files` | 同时读取多个文件 |
| `write_file` | 创建或覆盖文件 |
| `edit_file` | 对文本文件进行基于行的编辑 |
| `create_directory` | 创建目录 |
| `list_directory` | 列出目录内容 |
| `list_directory_with_sizes` | 列出目录内容及文件大小 |
| `directory_tree` | 以 JSON 格式递归展示目录树 |
| `move_file` | 移动或重命名文件 |
| `search_files` | 按模式搜索文件 |
| `get_file_info` | 获取文件元数据 |
| `file_exists` | 检查文件是否存在 |

> [!NOTE]
> 文件系统访问仅限于 `${WORKING_DIRECTORY}`。

### Web Search 服务器

需要 `TAVILY_API_KEY`。提供网络搜索能力。

### GitHub 服务器

需要 `GITHUB_TOKEN`。提供对仓库、Issue 和 Pull Request 的访问。

---

## 编程方式使用

```python
import asyncio
from src.core.mcp_manager import get_mcp_manager

async def use_mcp():
    manager = get_mcp_manager()
    
    # 从服务器发现工具
    tools = await manager.discover_tools("filesystem")
    
    # 调用工具
    result = await manager.call_tool(
        "filesystem",
        "read_file",
        {"path": "data/sample.csv"}
    )
    
    # 清理
    await manager.close_all()

asyncio.run(use_mcp())
```

---

## 安全注意事项

> [!WARNING]
> MCP 服务拥有强大的系统访问能力。请确保：
> - 仅启用必要的服务
> - 安全存储 API 令牌
> - 通过 `WORKING_DIRECTORY` 限制文件系统访问范围

---

## 相关文档
- [快速入门](QUICKSTART.md)
- [代理配置参考](AGENT_CONFIG.md)
- [工具配置](TOOL_CONFIG.md)
