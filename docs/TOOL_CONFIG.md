# 工具配置指南

本文档说明如何为代理配置工具。

## 概述

工具是允许代理与外部世界交互的能力。所有工具均由 `ToolFactory` 集中管理。

---

## 可用工具

### 核心工具

| 工具名称 | 描述 | 使用场景 |
|-----------|-------------|----------|
| `execute_code` | 执行 Python 代码 | 数据处理、分析 |
| `execute_command` | 执行 Shell 命令 | 系统操作 |
| `list_directory` | 列出目录内容 | 文件探索 |

### 文件操作工具

| 工具名称 | 描述 | 使用场景 |
|-----------|-------------|----------|
| `read_document` | 读取文件内容 | 读取数据、报告 |
| `create_document` | 创建新文件 | 生成报告 |
| `edit_document` | 编辑现有文件 | 修改内容 |
| `collect_data` | 收集数据 | 数据聚合 |

### 研究工具

| 工具名称 | 描述 | 使用场景 |
|-----------|-------------|----------|
| `wikipedia` | 查询维基百科 | 背景知识 |
| `arxiv` | 查询 arXiv 论文 | 学术研究 |
| `google_search` | Google 搜索 | 网络信息 |
| `scrape_webpages` | 网页抓取 | 网页内容提取 |

### 系统工具

| 工具名称 | 描述 | 使用场景 |
|-----------|-------------|----------|
| `lookup_skill` | 查询技能内容 | 配置技能后自动添加 |

---

## 安全与资源限制

### 配置文件

工具限制在 `config/tool_limits.yaml` 中配置：

```yaml
# 执行限制
execution:
  timeout_seconds: 60              # 固定超时（null = 无限制）
  max_memory_mb: 512               # 内存限制（仅 Linux）
  max_output_chars: 50000          # 截断输出
  progress_timeout_seconds: 300    # 用于 ML/DL 任务

# 文件操作限制
file_operations:
  max_read_bytes: 5242880          # 5MB
  max_read_lines: 10000
  max_write_bytes: 10485760        # 10MB
  allowed_extensions: [.py, .md, .txt, .csv, .json]
  blocked_paths: [/etc, /sys, ~/.ssh]

# 全局开关
enable_security_scan: true
enable_write_validation: true
```

### execute_code 参数

```python
execute_code(
    input_code="...",
    codefile_name="code.py",
    timeout=60,              # 固定超时（秒）
    memory_mb=512,           # 内存限制（仅 Linux）
    progress_timeout=300     # 仅当无输出时才超时
)
```

| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `timeout` | `int \| None` | N 秒后强制终止 |
| `memory_mb` | `int \| None` | 内存限制（MB，仅 Linux） |
| `progress_timeout` | `int \| None` | 仅当 N 秒内无 stdout 输出时才超时 |

> **提示**：对于 ML/DL 训练，使用 `progress_timeout` 而非 `timeout`，以允许打印进度信息的长时运行任务。

### 安全特性

| 特性 | 描述 |
|---------|-------------|
| **代码扫描** | AST 分析阻止危险模式（`eval`、`os.system` 等） |
| **路径验证** | 阻止访问敏感路径（`/etc`、`~/.ssh`） |
| **内容验证** | 对不完整标记（TODO、FIXME）发出警告 |
| **大小限制** | 防止读取/写入过大的文件 |

### 默认拦截模式

```
os.system、subprocess.call、subprocess.run、subprocess.Popen、
shutil.rmtree、eval(、exec(、__import__
```

---

## 代理配置

### 在 config.yaml 中指定

```yaml
tools:
  - execute_code
  - read_document
  - wikipedia
```

### 配置示例

#### 代码代理
```yaml
tools:
  - execute_code
  - execute_command
  - read_document
  - list_directory
```

#### 搜索代理
```yaml
tools:
  - read_document
  - wikipedia
  - arxiv
  - google_search
  - scrape_webpages
  - list_directory
```

#### 报告代理
```yaml
tools:
  - create_document
  - read_document
  - edit_document
  - list_directory
```

---

## 自定义工具

### 向 ToolFactory 添加新工具

1. 在 `src/tools/` 中创建工具函数
2. 在 `src/tools/factory.py` 中注册：

```python
from .my_tools import my_custom_tool

class ToolFactory:
    _registry = {
        # ... 已有工具 ...
        "my_custom_tool": my_custom_tool,
    }
```

3. 在代理的 `config.yaml` 中引用：
```yaml
tools:
  - my_custom_tool
```

---

## 编程方式访问

```python
from src.tools.factory import ToolFactory

# 获取当前配置
config = ToolFactory.get_config()

# 仅获取限制
limits = ToolFactory.get_limits()
print(limits["execution"]["timeout_seconds"])
```

---

## 回退机制

如果 `config.yaml` 中未定义 `tools`，系统将回退到代理类的 `_get_tools()` 方法。

---

## 相关文档
- [快速入门](QUICKSTART.md)
- [代理配置参考](AGENT_CONFIG.md)
