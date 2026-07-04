# DATAGEN 线上部署教学指南

## 一、你现在要做什么

```
本地写好代码 → 推到 GitHub → 自动部署到 Hugging Face Spaces
                                  ↓
                    面试官打开网址 → 直接看到你的 Streamlit 页面
                    输入分析需求 → 点"开始分析" → 拿到报告和图表
```

整条链路里，你只需要做一件事：**把代码推到 GitHub**。剩下的自动完成。

---

## 二、概念扫盲：Hugging Face Spaces 是什么

### 它和你理解的"租服务器"区别在哪

| | 租服务器 + 域名 | Hugging Face Spaces |
|------|----------------|-------------------|
| 你拿到的是什么 | 一台裸的 Linux 机器（Ubuntu/CentOS），你自己装 Python、pip、Nginx | 一个已经配好 Python + Streamlit 的"应用容器" |
| 部署方式 | SSH 登录 → git pull → pip install → 手动启动 → 配 Nginx | 代码推到 GitHub → 自动 pip install → 自动启动 |
| HTTPS | 自己搞 Let's Encrypt，三个月续一次 | **自动配好**，`https://你的用户名-hf.space` |
| 进程挂掉 | 你不会收到通知，网站悄无声息下线 | **自动重启** |
| 成本 | 几十～几百块/月 | **0 元** |
| 运维工作 | 全是你的（更新系统、看日志、打补丁） | **零运维** |

Hugging Face Spaces 做的事本质上就是"别人替你干了运维的活"。你不用管 Python 版本、不用管 Nginx、不用管进程守护、不用管 SSL 证书——平台全包了。

### 面试官打开网址之后发生了什么

```
面试官浏览器 → https://xxx.hf.space
                  ↓
            HF 的 Nginx 接收请求
                  ↓
            转发给后台的 Streamlit 进程
                  ↓
            Streamlit 渲染 app.py → frontend/streamlit_app.py
                  ↓
            面试官看到页面 → 可以上传自己的 CSV/Excel，也可以用预设的示例数据
                  ↓
            输入分析需求（一句话："分析这个文件，出报告和图表"）
                  ↓
            点"开始分析"
                  ↓
            Streamlit 进程调用 DeepSeek API
                  ↓
            代码执行、图表生成、报告输出
                  ↓
            Agent 协作流程和关键结果实时展示在面试官浏览器里
```

面试官不需要安装 Python、不需要 pip install、不需要配置任何东西——他只需要一个浏览器。**他还可以上传自己的 CSV 或 Excel 文件来测试**，不用局限于你预设的数据。

---

## 三、运行环境是你必须知道的

### 你的本地环境 vs 线上环境

| | 你本地 | Hugging Face Spaces |
|------|------|-------------------|
| 操作系统 | **Windows** | **Linux**（通常是 Ubuntu） |
| Python 版本 | 你装的那个 | 3.10（可指定） |
| 文件系统 | `D:\Agent\DATAGEN-main\data\` | `/home/user/app/data/` |
| ChromeDriver | `./chromedriver/` | **没有 GUI，不能用 Selenium** |
| 中文字体 | 系统自带 SimHei | **没有中文字体！** |
| 环境变量 | `.env` 文件 | HF Spaces 的 Settings → Secrets |
| 启动命令 | `streamlit run frontend/streamlit_app.py` | 平台自动检测 Streamlit 并启动 |

### ⚠️ 这意味着你需要改代码

你的项目目前是为 Windows 写的。部署到 Linux 上，有三个必改项：

---

## 四、部署前必须修改的代码

### 修改 1：中文字体（⭐⭐⭐ 最重要）

Agent 生成的分析脚本里会写 `plt.rcParams['font.sans-serif'] = ['SimHei']`，但 `SimHei` 是 Windows 专有字体，Linux 上没有，图表里的中文会变成方框。

**解决方案分两步**：

**① 线上装字体**（已完成）：`packages.txt` 里声明了 `fonts-wqy-microhei`（文泉驿微米黑），部署时自动安装。

**② 让脚本找到字体**（可选优化）：在 `basetool.py` 的 `execute_code` 里，写脚本前自动在代码头部注入一行字体回退逻辑，确保 `SimHei` 找不到时自动用文泉驿。这一步在本地 Windows 测试时不影响——因为 `SimHei` 存在，不会被覆盖。

### 修改 2：ChromeDriver / Selenium

你项目里有 `search_agent` 和 `internet.py`，依赖 Selenium + ChromeDriver。**Linux 服务器没有桌面环境，Chrome 跑不起来。**

**解决方案**：要么让 `search_agent` 禁用 Selenium 降级（只用 requests 做网页抓取），要么在 `searcher_agent` 的 `config.yaml` 里把 `scrape_webpages` 从工具列表里移除。我们之前已经把 search_agent 的工具精简到了只剩 `collect_data`，这个问题实际上已经不存在了——但如果面试官跑完整流程时碰到了，记得检查 search_agent 的工具列表。

### 修改 3：路径分隔符

Windows 用 `\`，Linux 用 `/`。你的代码里已经用了 `os.path.join()` 和 `os.path.normpath()`，这几本兼容了。但如果有硬编码的路径（比如 `'data\\OnlineSalesData.csv'`），需要全部改成 `os.path.join('data', 'OnlineSalesData.csv')`。

### 修改 4：Streamlit 的 MONKEY_PATCH

你 `streamlit_app.py` 里有一段 monkey-patch：

```python
node_module.human_choice_node = _auto_choice
node_module.human_review_node = _auto_review
workflow_module.human_choice_node = _auto_choice
workflow_module.human_review_node = _auto_review
```

这个逻辑在 Streamlit Cloud / HF Spaces 上没有问题，保留即可。它做的事情是让 Streamlit 启动后自动跳过人工交互节点——跟我们的 `AUTO_MODE` 环境变量效果一样，但方式不同。

---

## 五、部署文件清单

部署到 Hugging Face Spaces 需要项目根目录下有以下文件：

```
DATAGEN/
├── app.py                   # 【新增】HF 入口文件，转发到 frontend/
├── frontend/
│   └── streamlit_app.py     # Streamlit 页面（含文件上传 + Agent 流程展示）
├── src/                     # 后端代码（Agent、工具、工作流）
├── config/                  # Agent 配置（AGENT.md、config.yaml）
├── data/
│   └── OnlineSalesData.csv  # 示例数据（面试官可以直接用这个测）
├── requirements.txt         # Python 依赖（已补全 matplotlib、streamlit 等）
├── packages.txt             # 【新增】Linux 系统包（中文字体）
├── .gitignore               # 已配置：排除 .env、生成文件，保留示例 CSV
└── README.md                # 项目说明 + 线上 Demo 链接
```

### `packages.txt`（新建）

这个文件告诉 HF Spaces 在 pip install 之前，先用 apt-get 装哪些系统包。

```
fonts-wqy-microhei
```

就一行。`fonts-wqy-microhei` 是 Linux 下的文泉驿微米黑，支持中文图表渲染。

### `app.py`（新建，重要）

HF Spaces 要求 Streamlit 入口文件在项目根目录。我们实际的 Streamlit 代码在 `frontend/streamlit_app.py`，所以创建了 `app.py` 做转发：

```python
import sys, os, runpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
runpy.run_path(os.path.join("frontend", "streamlit_app.py"))
```

### `.gitignore`（已更新）

```
.env          ← API key 绝对不能泄露
*.log
.venv/
data/*.png    ← 运行时生成的图表不提交
data/*.md     ← 运行时生成的报告不提交
data/run_*/   ← 运行时目录不提交
!data/OnlineSalesData.csv  ← 但保留示例数据文件
```

---

## 六、API Key 怎么处理（关键）

1. **本地**：API key 在 `.env` 里，不推上 GitHub
2. **线上**：在 Hugging Face Space 的 Settings → Repository Secrets 里添加

```
Key:   OPENAI_API_KEY
Value: <YOUR_API_KEY_HERE>
```

这样 `load_dotenv()` 读不到 `.env`（因为没推上去），但 HF 会自动把 Secret 注入为环境变量，代码里的 `os.getenv('OPENAI_API_KEY')` 能读到。

面试官看不到你的 API key。

---

## 七、完整操作步骤

### Step 1：确保项目在 GitHub 上

```bash
cd D:\Agent\DATAGEN-main
git add .
git commit -m "ready for online deployment"
git push origin main
```

### Step 2：创建 Hugging Face Space

1. 打开 https://huggingface.co/new-space
2. Owner：你的用户名
3. Space name：`datagen`（网址会变成 `https://你的用户名-datagen.hf.space`）
4. SDK：选 **Streamlit**
5. Hardware：**CPU（免费）**
6. 点 Create Space

### Step 3：关联 GitHub 仓库

创建 Space 后，HF 会给你一个空的 Git 仓库地址。你有两种方式把代码传上去：

**方式 A（推荐）**：在 HF Space 的 Settings 里，关联你的 GitHub 仓库。之后每次 `git push` 到 GitHub，HF 自动同步 + 重新部署。

**方式 B**：把 HF Space 当作第二个 Git remote，手动推：
```bash
git remote add hf https://huggingface.co/spaces/你的用户名/datagen
git push hf main
```

### Step 4：配 API Key

在 Space 的 Settings → Secrets 里添加 `OPENAI_API_KEY`。

### Step 5：等待自动部署

推完代码后，HF 会自动：
1. `apt-get install` → 装 `packages.txt` 里声明的中文字体
2. `pip install -r requirements.txt` → 装 Python 依赖（matplotlib、streamlit、pandas 等）
3. 检测到根目录的 `app.py` → 启动 Streamlit

大约 2-3 分钟后，你的 Space 状态变成 **Running**。

### Step 6：把网址发给面试官

网址是 `https://你的用户名-datagen.hf.space`。面试官打开浏览器就能看到你的 Streamlit 界面。

---

## 八、面试官看到什么

面试官打开链接 → 看到的是这个页面：

```
┌──────────────────────────────────────────────────────┐
│  📊 DATAGEN — 多 Agent 智能数据分析                    │
│  基于 LangGraph 的 9 Agent 协作系统 | 模型: DeepSeek   │
├───────────────────────┬──────────────────────────────┤
│ 📤 上传数据文件         │ 📝 分析任务                    │
│ [拖拽 CSV 或 Excel]   │ "请分析 OnlineSalesData.csv,    │
│ 支持 csv/xlsx/xls     │  进行数据清洗、描述性统计、... ] │
│                       │                              │
│ 📁 可用数据文件         │      [▶ 开始分析]              │
│ 📄 OnlineSalesData.csv │                              │
│ （或面试官自己上传的）   │                              │
└───────────────────────┴──────────────────────────────┘
```

面试官有两个选择：
- **直接跑**：用你预设的 `OnlineSalesData.csv`，点"开始分析"
- **上传自己的数据**：拖一个 CSV 或 Excel 文件，系统自动识别格式，然后用它分析

点"开始分析" → 等 2-3 分钟 → 看到：

```
🤖 Agent 协作流程
  ✅ 假设生成
  ✅ 流程调度
  ✅ 代码执行
  ✅ 图表生成
  ✅ 质量审查
  ✅ 报告精炼

📋 关键输出
  [展开查看每个 Agent 的分析结果...]

📁 本次输出
  📄 analysis_report.md
  📄 sales_dashboard.png
```

---

## 九、常见的坑

| 问题 | 原因 | 怎么修 |
|------|------|--------|
| 部署后打不开 | requirements.txt 缺了某个包 | 看 HF 的构建日志（Build Log），找 `ModuleNotFoundError` |
| 中文图表乱码 | Linux 没装中文字体 | 确认 `packages.txt` 有 `fonts-wqy-microhei` |
| 分析跑到一半报错 | 某个 Agent 调用了 Windows 专用命令 | 看 HF 的运行日志（App Log），定位具体行的错误 |
| API 调用失败 | API key 没配 | 确认 Settings → Secrets 里有 `OPENAI_API_KEY` |
| 页面能打开但按钮点了没反应 | 某个 import 在 import 阶段就挂了 | 看 HF 的运行日志，通常第一行就是报错 |

---

## 十、常见疑问

### Q：HF Spaces 免费版会不会很慢？
A：首次启动需要 2-3 分钟装依赖。之后每次访问如果 Space 在 sleep 状态，需要十几秒唤醒。唤醒后速度正常。如果长期没人访问会自动 sleep，但下一个请求会自动唤醒——不需要你手动操作。

### Q：我的 DeepSeek key 安全吗？
A：HF Secrets 加密存储，面试官看不到。每次 API 调用走你的余额，24 小时持续有人访问也不会烧很多钱——DeepSeek 的 API 极便宜，几十次完整分析也就几毛钱。

### Q：面试官能下载我的代码吗？
A：HF Spaces 是公开的，代码可见（跟 GitHub 公开仓库一样）。这对面试是好事——面试官可以同时看你的编排逻辑和线上效果。

### Q：如果我本地改了代码，线上会自动更新吗？
A：用了 GitHub 关联就会。你 `git push` → GitHub → HF 检测到更新 → 自动重新部署。整个流程不到 5 分钟。

### Q：面试官能上传自己的文件吗？
A：能。侧边栏有上传组件，支持 CSV 和 Excel（.xlsx/.xls）。面试官拖一个文件上去，系统自动识别格式——`.xlsx` 用 `pd.read_excel()`，`.csv` 用 `pd.read_csv()`。上传后文件名出现在可用文件列表里，直接在分析任务里引用即可。

### Q：预设的示例数据够用吗？
A：`OnlineSalesData.csv` 包含 35 条销售记录（日期、销售额、利润、客户数、区域、产品类别、促销活动），足以展示完整的数据清洗 → 统计 → 趋势 → 建模 → 报告的全流程。面试官如果用这个预设数据测试，不需要上传任何东西。

---

## 十一、你以为很复杂，实际上很简单

```
你做的事：                      平台做的事：
─────────                      ─────────
写代码                         装系统
推到 GitHub                    装 Python
                               装依赖
                               配 HTTPS
                               启动进程
                               监控进程
                               自动重启
                               自动唤醒
```

你就正常写代码 → `git push`，剩下的都是自动的。
