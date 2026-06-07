# 技能配置指南

本文档说明如何创建和使用代理技能。

## 概述

技能是可复用的知识模块，为代理提供特定领域的专业知识。技能采用**渐进式披露**机制：代理最初只看到描述，仅在需要时才加载完整内容。

---

## 目录结构

所有技能存储在 `config/skills/` 中：

```
config/skills/
└── {skill-name}/
    └── SKILL.md       # 技能定义文件（必填）
```

---

## SKILL.md 格式

### 基本结构

```markdown
---
name: skill-name
description: 简要描述技能功能及使用时机
---

# 技能标题

## 指令
[代理应遵循的步骤]

## 最佳实践
[推荐的方法]

## 示例
[具体的使用示例]
```

### 字段要求

| 字段 | 要求 | 描述 |
|-------|-------------|-------------|
| `name` | 必填，最长 64 字符 | 小写字母、数字、连字符 |
| `description` | 必填，最长 1024 字符 | 描述功能及触发条件 |

---

## 创建技能教程

### 示例：数据验证技能

1. 创建目录：
```bash
mkdir -p config/skills/data-validation
```

2. 创建 `config/skills/data-validation/SKILL.md`：

```markdown
---
name: data-validation
description: 验证数据集的完整性和一致性。在检查数据质量、识别缺失值或验证数据类型时使用。
---

# 数据验证

## 验证步骤

1. **完整性检查**
   - 识别缺失值（`df.isnull().sum()`）
   - 计算缺失率

2. **一致性检查**
   - 验证数据类型
   - 检查值域范围

3. **唯一性检查**
   - 识别重复记录
   - 验证主键唯一性

## 示例代码

\`\`\`python
import pandas as pd

def validate_dataset(df: pd.DataFrame) -> dict:
    return {
        "missing": df.isnull().sum().to_dict(),
        "duplicates": df.duplicated().sum(),
        "dtypes": df.dtypes.to_dict()
    }
\`\`\`
```

---

## 使用技能

### 在代理 config.yaml 中引用

```yaml
skills:
  - data-validation
```

### 工作原理

1. **第一级（系统启动时）**：代理仅知道技能的 `name` 和 `description`
2. **第二级（需要时）**：代理调用 `lookup_skill("data-validation")` 获取完整内容

这种设计避免了不必要的上下文窗口消耗。

---

## 进阶：多文件技能

技能可以包含多个文件：

```
config/skills/advanced-skill/
├── SKILL.md           # 主指令文件
├── REFERENCE.md       # 详细参考
└── scripts/
    └── helper.py      # 辅助脚本
```

在 `SKILL.md` 中引用其他文件：
```markdown
详细的 API 参考，请参见 [REFERENCE.md](REFERENCE.md)。
```

---

## 相关文档
- [快速入门](QUICKSTART.md)
- [代理配置参考](AGENT_CONFIG.md)
