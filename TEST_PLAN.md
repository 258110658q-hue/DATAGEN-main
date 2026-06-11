# DATAGEN 项目测试方案

> **版本**: 1.0 | **日期**: 2026-06-10 | **测试框架**: pytest 9.0.3+

---

## 目录

1. [项目概述与测试挑战](#1-项目概述与测试挑战)
2. [测试分层策略](#2-测试分层策略)
3. [第一层：单元测试（免 LLM）](#3-第一层单元测试免-llm)
4. [第二层：集成测试（Mock LLM）](#4-第二层集成测试mock-llm)
5. [第三层：端到端测试](#5-第三层端到端测试)
6. [Mock 与 Fixture 基础设施](#6-mock-与-fixture-基础设施)
7. [测试数据管理](#7-测试数据管理)
8. [CI/CD 集成](#8-cicd-集成)
9. [实施路线图](#9-实施路线图)
10. [附录：覆盖率目标](#10-附录覆盖率目标)

---

## 1. 项目概述与测试挑战

### 1.1 项目架构回顾

DATAGEN 是一个基于多智能体的 AI 数据分析平台，核心组件：

```
main.py  →  MultiAgentSystem  →  WorkflowManager (LangGraph StateGraph)
                                      │
                    ┌─────────────────┼──────────────────┐
                    ▼                  ▼                   ▼
             AgentFactory        LanguageModelMgr     MCPManager
                    │                  │                   │
            9个专业Agent ←─── LLM Providers ───→ MCP Servers
                    │          (8种后端)          (3个server)
                    ▼
              ToolFactory
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    安全模块    文件工具    网络工具
```

### 1.2 核心测试挑战

| 挑战 | 说明 | 对策 |
|------|------|------|
| **LLM 强依赖** | 9 个 Agent 全部依赖 LLM 推理 | 全部通过 FakeListChatModel / MagicMock 模拟 |
| **MCP 异步连接** | MCP Server 需要后台 asyncio 事件循环 | conftest 中统一管理，测试前后启停 |
| **代码执行安全** | Agent 可执行任意 Python 代码 | 沙箱化 + ResourceLimiter + 独立 temp 目录 |
| **网络依赖** | Google 搜索、FireCrawl、Wikipedia、arXiv | 全部 mock，不发起真实网络请求 |
| **LangGraph 状态流** | 复杂的条件路由（11节点 + 3条件边） | 逐节点单元测试 + 快照对比 |
| **配置层级多** | YAML/ENV/MD frontmatter 三层配置 | 每种配置路径独立测试 |
| **平台差异** | Security 模块部分功能仅 Linux | 条件跳过 + CI 矩阵 |

### 1.3 测试原则

1. **无 LLM 无网络**：所有单元/集成测试不应调用真实 LLM API 或发起网络请求
2. **快速反馈**：单元测试 < 5s 全量跑完，集成测试 < 60s
3. **隔离性**：每个测试独立创建 temp 目录，不影响项目文件
4. **可重复性**：固定随机种子，消除不确定性
5. **中文兼容**：所有测试覆盖中文路径/内容/编码场景

---

## 2. 测试分层策略

```
         ┌───────────────────────────┐
         │  E2E Tests (5-10 个)      │  ← 真实 LLM（可选），全流程
         │  完整工作流验证            │     运行时间: 分钟级
         ├───────────────────────────┤
         │  Integration Tests (30-50) │  ← Mock LLM，多模块协作
         │  Agent创建、图构建、节点交互│     运行时间: < 60s
         ├───────────────────────────┤
         │  Unit Tests (80-120 个)    │  ← 零外部依赖，纯逻辑
         │  所有独立可测模块           │     运行时间: < 5s
         └───────────────────────────┘
```

**比例目标**: 单元测试 60% | 集成测试 30% | E2E 10%

---

## 3. 第一层：单元测试（免 LLM）

### 3.1 模块清单与优先级

#### P0 — 安全关键（必须覆盖）

| 模块 | 文件 | 测试文件 | 预估用例数 |
|------|------|----------|-----------|
| 安全扫描器 | `src/tools/security.py` | `tests/unit/test_security.py` | 15-20 |
| 路径校验器 | `src/tools/validators.py` | `tests/unit/test_validators.py` | 12-15 |
| 内容校验器 | `src/tools/validators.py` | `tests/unit/test_content_validator.py` | 10-12 |
| 工具配置 | `src/tools/tool_config.py` | `tests/unit/test_tool_config.py` | 8-10 |

#### P1 — 核心逻辑

| 模块 | 文件 | 测试文件 | 预估用例数 |
|------|------|----------|-----------|
| State 模型 | `src/core/state.py` | `tests/unit/test_state.py` | 8-10 |
| Schema 校验 | `src/core/schemas.py` | `tests/unit/test_schemas.py` | 6-8 |
| 路由器 | `src/core/router.py` | `tests/unit/test_router.py` | 15-20 |
| 模型配置 | `src/config.py` | `tests/unit/test_config.py` | 8-10 |
| Agent 配置加载 | `src/core/agent_config_loader.py` | `tests/unit/test_agent_config.py` | 15-20 |

#### P2 — 工具与工厂

| 模块 | 文件 | 测试文件 | 预估用例数 |
|------|------|----------|-----------|
| LLM 工厂 | `src/llm/factory.py` | `tests/unit/test_llm_factory.py` | 5-8 |
| 工具工厂 | `src/tools/factory.py` | `tests/unit/test_tool_factory.py` | 6-8 |
| Agent 工厂 | `src/agents/factory.py` | `tests/unit/test_agent_factory.py` | 5-8 |
| Logger | `src/logger.py` | `tests/unit/test_logger.py` | 5-6 |

### 3.2 详细测试用例

#### 3.2.1 SecurityScanner (`tests/unit/test_security.py`)

```python
class TestSecurityScanner:
    """安全扫描器单元测试"""

    # --- 危险内置函数检测 ---
    def test_detect_eval(self):
        """检测 eval() 调用"""

    def test_detect_exec(self):
        """检测 exec() 调用"""

    def test_detect_compile(self):
        """检测 compile() 调用"""

    def test_detect_import_builtin(self):
        """检测 __import__() 调用"""

    # --- 模式匹配检测 ---
    def test_detect_os_system(self):
        """检测 os.system()"""

    def test_detect_subprocess_run(self):
        """检测 subprocess.run()"""

    def test_detect_subprocess_popen(self):
        """检测 subprocess.Popen()"""

    def test_detect_shutil_rmtree(self):
        """检测 shutil.rmtree()"""

    # --- 风险导入警告 ---
    def test_warn_os_import(self):
        """import os 触发警告"""

    def test_warn_subprocess_import(self):
        """import subprocess 触发警告"""

    def test_warn_socket_import(self):
        """import socket 触发警告"""

    def test_warn_ctypes_import(self):
        """import ctypes 触发警告"""

    def test_warn_from_import_risky(self):
        """from os import path 触发警告"""

    # --- 边界情况 ---
    def test_safe_code_passes(self):
        """正常代码（pandas, numpy等）通过检查"""

    def test_empty_code(self):
        """空代码通过检查"""

    def test_syntax_error_handles_gracefully(self):
        """语法错误不阻断扫描"""

    def test_commented_dangerous_code(self):
        """注释中的危险代码应被检测（模式匹配）"""

    # --- AST 精确检测 ---
    def test_variable_named_eval_not_detected(self):
        """变量名 eval 不作为函数调用处理"""

    def test_string_containing_os_system(self):
        """字符串中的'os.system'仍在模式匹配层被检测"""
```

#### 3.2.2 PathValidator (`tests/unit/test_validators.py`)

```python
class TestPathValidator:
    """路径校验器单元测试"""

    def test_allowed_path_passes(self):
        """合法路径（/tmp/test.py）通过"""

    def test_blocked_etc_path_rejected(self):
        """禁止访问 /etc"""

    def test_blocked_sys_path_rejected(self):
        """禁止访问 /sys"""

    def test_blocked_proc_path_rejected(self):
        """禁止访问 /proc"""

    def test_blocked_root_path_rejected(self):
        """禁止访问 /root"""

    def test_blocked_ssh_path_rejected(self):
        """禁止访问 ~/.ssh"""

    def test_blocked_var_log_path_rejected(self):
        """禁止访问 /var/log"""

    def test_allowed_extensions_pass(self):
        """白名单扩展名（.py/.md/.csv/.json等）全部通过"""

    def test_blocked_extension_rejected(self):
        """.exe/.sh/.bat 等黑名单扩展名被拒绝"""

    def test_no_extension_allowed(self):
        """无扩展名文件允许"""

    def test_nonexistent_file_skips_size_check(self):
        """不存在的文件跳过大小检查"""

    def test_file_too_large_rejected(self):
        """超过 5MB 的文件被拒绝"""

    def test_validate_read_combines_all_checks(self):
        """validate_read 执行全部三项检查"""

    def test_validate_write_combines_path_and_ext(self):
        """validate_write 执行路径+扩展名检查（不检查大小）"""

    def test_unicode_path(self):
        """中文路径名处理正确"""

    def test_path_traversal_rejected(self):
        """../../../etc/passwd 被规范化后拦截"""
```

#### 3.2.3 ContentValidator (`tests/unit/test_content_validator.py`)

```python
class TestContentValidator:
    """内容校验器单元测试"""

    # --- 大小限制 ---
    def test_content_too_large_rejected(self):
        """超过 10MB 的内容被拒绝"""

    def test_content_within_limit_passes(self):
        """正常大小内容通过"""

    # --- 不完整标记 ---
    def test_todo_marker_warns(self):
        """包含 TODO 触发警告"""

    def test_fixme_marker_warns(self):
        """包含 FIXME 触发警告"""

    def test_xxx_marker_warns(self):
        """包含 XXX 触发警告"""

    def test_chinese_todo_warns(self):
        """包含中文（待补）触发警告"""

    # --- 敏感数据 ---
    def test_openai_api_key_detected(self):
        """检测到 sk-xxx 格式的 OpenAI Key"""

    def test_aws_access_key_detected(self):
        """检测到 AKIAxxx 格式的 AWS Key"""

    def test_hardcoded_password_detected(self):
        """检测到 password='xxx' 赋值"""

    def test_potential_api_hash_detected(self):
        """检测到 32 位 hex 字符串"""

    # --- 边界情况 ---
    def test_empty_content_warns(self):
        """空内容触发警告"""

    def test_very_short_content_warns(self):
        """极短内容（<10 字符）触发警告"""

    def test_validation_disabled_skips_checks(self):
        """enable_write_validation=False 时跳过非大小校验"""

    def test_validate_and_log_returns_formatted_message(self):
        """校验并返回格式化结果字符串"""
```

#### 3.2.4 Router (`tests/unit/test_router.py`)

```python
class TestHypothesisRouter:
    """假设路由测试"""

    def test_continue_to_process_when_instruction_matches(self):
        """current_instruction 为 '继续执行研究流程' → Process"""

    def test_continue_to_process_when_english_instruction(self):
        """current_instruction 为 'Continue the research process' → Process"""

    def test_routes_to_hypothesis_otherwise(self):
        """其他任何指令 → Hypothesis"""

    def test_missing_instruction_defaults_to_hypothesis(self):
        """缺少 current_instruction → Hypothesis"""

    def test_works_with_dict_state(self):
        """兼容 dict 类型的 state"""

    def test_works_with_pydantic_state(self):
        """兼容 Pydantic 类型的 state"""


class TestQualityReviewRouter:
    """质量评审路由测试"""

    def test_no_revision_routes_to_note_taker(self):
        """needs_revision=False → NoteTaker"""

    def test_revision_routes_back_to_code_agent(self):
        """code_agent 需要修订 → Coder"""

    def test_revision_routes_back_to_search_agent(self):
        """search_agent 需要修订 → Search"""

    def test_revision_routes_back_to_visualization_agent(self):
        """visualization_agent 需要修订 → Visualization"""

    def test_revision_routes_back_to_report_agent(self):
        """report_agent 需要修订 → Report"""

    def test_max_revisions_exceeded_falls_back_to_note_taker(self):
        """revision_count > 3 → NoteTaker"""

    def test_insufficient_messages_defaults_to_note_taker(self):
        """消息数 < 2 → NoteTaker"""

    def test_unknown_previous_node_defaults_to_note_taker(self):
        """未知的前一个节点 → NoteTaker"""


class TestProcessRouter:
    """流程路由测试"""

    @pytest.mark.parametrize("step", ["Coder", "Search", "Visualization", "Report"])
    def test_valid_step_routes_correctly(self, step):
        """有效步骤路由到对应节点"""

    def test_finish_routes_to_refiner(self):
        """FINISH → Refiner"""

    def test_step_count_too_high_forces_finish(self):
        """step_count > 20 且无效步骤 → Refiner"""

    def test_invalid_step_defaults_to_process(self):
        """无效步骤→ Process"""

    def test_empty_step_defaults_to_process(self):
        """空步骤→ Process"""
```

#### 3.2.5 State Model (`tests/unit/test_state.py`)

```python
class TestStateModel:
    """状态模型测试"""

    def test_default_values(self):
        """所有字段有正确的默认值"""

    def test_create_initial_state(self):
        """create_initial_state 创建正确的初始状态 dict"""

    def test_messages_use_add_messages_reducer(self):
        """消息字段使用 add_messages 归并器"""

    def test_artifact_dicts_start_empty(self):
        """search/code/viz/report_artifacts 初始为空 dict"""

    def test_extra_fields_ignored(self):
        """extra='ignore' 忽略多余字段"""

    def test_validate_assignment_enabled(self):
        """赋值时触发校验"""

    def test_state_serialization(self):
        """State 可序列化为 JSON 兼容格式"""


class TestArtifactSchema:
    """ArtifactSchema 测试"""

    def test_valid_schema(self):
        """合法输入通过校验"""

    def test_missing_artifacts_defaults_to_empty_dict(self):
        """不提供 artifacts 默认为空 dict"""

    def test_summary_is_required(self):
        """缺少 summary 字段触发 ValidationError"""
```

#### 3.2.6 AgentConfigLoader (`tests/unit/test_agent_config.py`)

```python
class TestAgentConfigLoader:
    """Agent 配置加载器测试"""

    # --- Frontmatter 解析 ---
    def test_extract_valid_frontmatter(self):
        """正确解析 YAML frontmatter"""

    def test_no_frontmatter_returns_none(self):
        """无 frontmatter 返回 None"""

    def test_invalid_yaml_frontmatter_returns_none(self):
        """无效 YAML 返回 None"""

    # --- Agent 发现 ---
    def test_discover_all_agents(self):
        """扫描并发现全部 9 个 Agent 目录"""

    def test_ignore_underscore_directories(self):
        """忽略 _shared 等以 _ 开头的目录"""

    # --- 元数据加载 ---
    def test_load_metadata_caches_result(self):
        """二次调用使用缓存"""

    def test_load_metadata_file_not_found(self):
        """AGENT.md 不存在抛出 FileNotFoundError"""

    # --- 系统提示词加载 ---
    def test_load_system_prompt_strips_frontmatter(self):
        """系统提示词不包含 YAML frontmatter"""

    def test_load_system_prompt_applies_rules(self):
        """系统提示词包含 always_on 规则"""

    def test_load_system_prompt_applies_skills(self):
        """系统提示词包含技能简介"""

    def test_use_complete_prompt_prefix(self):
        """use_complete_prompt=True 时添加 SYSTEM_PROMPT: 前缀"""

    # --- 技能/Rules 加载 ---
    def test_load_skills_by_name(self):
        """根据 skill 名称加载 SKILL.md"""

    def test_skill_not_found_warns(self):
        """技能文件不存在时记录警告"""

    def test_load_rules_by_path(self):
        """根据规则路径加载 .md 文件"""

    def test_rules_sorted_by_priority(self):
        """规则按 priority 降序排列"""

    def test_shared_rules_with_underscore_prefix(self):
        """_shared/rules.md 路径解析正确"""

    # --- MCP 配置 ---
    def test_load_mcp_config_merges_defaults(self):
        """defaults + agent-specific MCP servers 合并正确"""

    def test_env_var_expansion(self):
        """${VAR_NAME} 格式环境变量被替换"""

    # --- config.yaml 解析 ---
    def test_per_agent_config_yaml(self):
        """解析 agent 目录下的 config.yaml"""

    def test_missing_config_yaml_uses_defaults(self):
        """config.yaml 不存在时使用空默认值"""
```

#### 3.2.7 ToolConfig (`tests/unit/test_tool_config.py`)

```python
class TestToolConfig:
    """工具配置测试"""

    def test_load_from_yaml(self):
        """从 tool_limits.yaml 正确加载"""

    def test_default_values_when_no_file(self):
        """配置文件缺失时使用默认值"""

    def test_execution_limits_defaults(self):
        """执行限制默认值正确"""

    def test_file_operation_limits_defaults(self):
        """文件操作限制默认值正确"""

    def test_custom_blocked_patterns(self):
        """自定义危险模式列表被正确加载"""

    def test_custom_allowed_extensions(self):
        """自定义允许扩展名列表被正确加载"""

    def test_to_dict_roundtrip(self):
        """to_dict() 输出可重建等价配置"""

    def test_global_singleton_initialized(self):
        """TOOL_CONFIG 全局单例正确初始化"""
```

#### 3.2.8 LLM Provider 工厂 (`tests/unit/test_llm_factory.py`)

```python
class TestProviderFactory:
    """LLM Provider 工厂测试"""

    @pytest.mark.parametrize("provider", [
        "openai", "anthropic", "google", "deepseek", "ollama", "groq", "azure"
    ])
    def test_get_known_provider(self, provider):
        """所有已知 provider 返回正确的 ChatModel 类"""

    def test_unknown_provider_raises(self):
        """未知 provider 抛出异常"""

    def test_lazy_import_does_not_load_all(self):
        """只 import 请求的 provider，不全部加载"""
```

---

## 4. 第二层：集成测试（Mock LLM）

### 4.1 Mock LLM 策略

使用 LangChain 的 `FakeListChatModel` 或自定义 mock：

```python
# conftest.py — 核心 mock fixture
@pytest.fixture
def mock_chat_model():
    """返回可控响应的 FakeListChatModel"""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    def _make(responses: list[str]):
        return FakeListChatModel(
            responses=responses,
            sleep=0,  # 无延迟
        )
    return _make
```

对于结构化输出的 Agent（如 ProcessAgent 输出 JSON Schema），mock 必须返回合法的 JSON：

```python
@pytest.fixture
def mock_structured_llm():
    """Mock ProcessAgent 的结构化输出"""
    def _make(route: str, instruction: str):
        return FakeListChatModel(responses=[
            json.dumps({
                "next_workflow_step": route,
                "current_instruction": instruction,
                "todo_list": [instruction]
            })
        ])
    return _make
```

### 4.2 集成测试用例

#### 4.2.1 Agent 创建与工具加载 (`tests/integration/test_agent_creation.py`)

```python
class TestAgentCreation:
    """Agent 创建集成测试"""

    @pytest.mark.parametrize("agent_name", [
        "hypothesis_agent", "process_agent", "code_agent",
        "search_agent", "visualization_agent", "report_agent",
        "quality_review_agent", "note_agent", "refiner_agent"
    ])
    def test_agent_initialization(self, agent_name, mock_chat_model):
        """所有 9 个 Agent 可成功初始化"""

    @pytest.mark.parametrize("agent_name,tool_names", [
        ("code_agent", ["execute_code", "execute_command", "read_document", "list_directory"]),
        ("search_agent", ["wikipedia", "arxiv", "google_search", "scrape_webpages", "read_document", "write_document"]),
        ("report_agent", ["create_document", "read_document", "edit_document", "list_directory"]),
        ("visualization_agent", ["execute_code", "execute_command", "read_document", "list_directory"]),
        ("refiner_agent", ["create_document", "read_document", "edit_document", "wikipedia", "google_search", "scrape_webpages"]),
        ("hypothesis_agent", ["wikipedia", "arxiv", "google_search", "scrape_webpages"]),
        ("process_agent", []),  # 纯路由，无工具
        ("quality_review_agent", []),
        ("note_agent", []),
    ])
    def test_agent_tools_loaded(self, agent_name, tool_names, mock_chat_model):
        """每个 Agent 加载了正确的工具集"""

    def test_agent_system_prompt_contains_keywords(self, mock_chat_model):
        """系统提示词包含预期关键词（如角色定义）"""

    def test_agent_with_invalid_name_raises(self):
        """不存在的 Agent 名称抛出异常"""
```

#### 4.2.2 Workflow 图构建 (`tests/integration/test_workflow_graph.py`)

```python
class TestWorkflowGraph:
    """LangGraph 工作流集成测试"""

    def test_graph_has_all_11_nodes(self, workflow_manager):
        """图中包含全部 11 个节点"""

    def test_graph_entry_point_is_hypothesis(self, workflow_manager):
        """入口为 Hypothesis 节点"""

    def test_conditional_edges_registered(self, workflow_manager):
        """三条条件边已注册"""

    def test_graph_compiles_without_error(self, workflow_manager):
        """图可成功编译"""

    def test_graph_has_memory_checkpointer(self, workflow_manager):
        """图使用 MemorySaver 作为 checkpointer"""
```

#### 4.2.3 节点函数测试 (`tests/integration/test_nodes.py`)

```python
class TestAgentNode:
    """agent_node 通用节点函数测试"""

    def test_extracts_structured_output_from_ai_message(self):
        """从 AIMessage 中提取结构化 JSON"""

    def test_merges_agent_artifacts_into_state(self):
        """Agent 产物正确合并到状态"""

    def test_increments_step_count(self):
        """每次调用 step_count +1"""

    def test_appends_completed_task(self):
        """完成任务追加到 completed_tasks"""

    def test_handles_malformed_ai_output_gracefully(self):
        """JSON 解析失败时优雅降级"""

    def test_conversation_summary_applied_for_large_context(self):
        """上下文过大时应用摘要策略"""


class TestHumanChoiceNode:
    """HumanChoice 节点测试"""

    def test_auto_mode_returns_continue(self):
        """auto_mode=True 时自动继续"""

    def test_sets_current_instruction(self):
        """正确设置 current_instruction"""


class TestQualityReviewLoop:
    """质量评审循环集成测试"""

    def test_single_revision_then_pass(self):
        """一次修订后通过 → NoteTaker"""

    def test_three_revisions_then_pass(self):
        """三次修订后通过"""

    def test_exceed_max_revisions_forces_next(self):
        """超过 3 次修订强制进入 NoteTaker"""

    def test_revision_count_resets_after_pass(self):
        """通过后 revision_count 重置"""
```

#### 4.2.4 MCP Manager (`tests/integration/test_mcp_manager.py`)

```python
class TestMCPManager:
    """MCP Manager 集成测试"""

    @pytest.mark.asyncio
    async def test_connect_to_mock_server(self, mock_mcp_server):
        """连接到模拟 MCP Server"""

    @pytest.mark.asyncio
    async def test_discover_tools_from_mock_server(self, mock_mcp_server):
        """从模拟 Server 发现工具列表"""

    @pytest.mark.asyncio
    async def test_call_tool_via_mcp(self, mock_mcp_server):
        """通过 MCP 调用工具"""

    @pytest.mark.asyncio
    async def test_mcp_tool_adapter_wraps_correctly(self, mock_mcp_server):
        """MCPToolAdapter 正确包装为 LangChain Tool"""

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self):
        """MCP 连接失败时优雅处理"""

    def test_get_tools_for_agent_filters_by_config(self):
        """按 Agent 配置过滤 MCP 工具"""
```

#### 4.2.5 工具集成测试 (`tests/integration/test_tools_integration.py`)

```python
class TestCodeExecutionIntegration:
    """代码执行集成测试"""

    def test_execute_safe_python_code(self, temp_workspace):
        """在临时目录执行安全的 Python 代码"""

    def test_dangerous_code_blocked_by_security_scanner(self, temp_workspace):
        """危险代码被安全扫描器阻止"""

    def test_execution_timeout_kills_process(self, temp_workspace):
        """超时后进程被终止"""

    def test_progress_timeout_kills_idle_process(self, temp_workspace):
        """无输出超时后进程被终止"""

    def test_output_truncation(self, temp_workspace):
        """超过 max_output_chars 的输出被截断"""

    def test_conda_env_activation(self, temp_workspace):
        """conda 环境激活后执行代码"""


class TestFileOperationsIntegration:
    """文件操作集成测试"""

    def test_collect_data_csv(self, temp_workspace, sample_csv):
        """collect_data 正确读取 CSV"""

    def test_collect_data_multi_encoding(self, temp_workspace):
        """collect_data 自动检测编码（UTF-8/GBK/UTF-16）"""

    def test_create_and_read_document(self, temp_workspace):
        """创建并读取文档"""

    def test_edit_document_line_insertion(self, temp_workspace):
        """edit_document 行级插入"""

    def test_write_to_blocked_path_rejected(self, temp_workspace):
        """写入被保护路径被拒绝"""

    def test_read_too_large_file_rejected(self, temp_workspace):
        """读取过大文件被拒绝"""


class TestInternetTools:
    """网络工具集成测试（全 Mock）"""

    def test_google_search_mocked(self, mock_selenium):
        """Google 搜索返回模拟结果"""

    def test_scrape_webpages_mocked(self, mock_firecrawl):
        """网页抓取返回模拟内容"""

    def test_scrape_webpages_fallback_to_web_base_loader(self, mock_requests):
        """FireCrawl 失败时回退到 WebBaseLoader"""

    def test_wikipedia_search_mocked(self, mock_wikipedia):
        """Wikipedia 搜索返回模拟页面"""

    def test_arxiv_search_mocked(self, mock_arxiv):
        """arXiv 搜索返回模拟论文"""
```

---

## 5. 第三层：端到端测试

### 5.1 轻量级 E2E（Mock LLM，`tests/e2e/test_workflow_e2e_mock.py`）

```python
class TestFullWorkflowE2E:
    """全流程端到端测试（Mock LLM）"""

    def test_complete_analysis_pipeline(self, mock_all_agents):
        """
        完整流程：
        Hypothesis → HumanChoice → Process → Coder → QualityReview(通过) →
        NoteTaker → Process → Search → QualityReview(修订×1) → NoteTaker →
        Process → FINISH → Refiner → HumanReview → END
        """

    def test_hypothesis_regeneration_loop(self, mock_all_agents):
        """Hypothesis 多次生成直到用户满意"""

    def test_max_revision_exceeded_scenario(self, mock_all_agents):
        """修订超过 3 次后自动推进"""

    def test_step_count_overflow_protection(self, mock_all_agents):
        """step_count > 20 时强制结束"""

    def test_empty_state_recovery(self, mock_all_agents):
        """空/损坏状态下的恢复"""
```

### 5.2 真实 LLM E2E（可选，`tests/e2e/test_workflow_e2e_live.py`）

```python
@pytest.mark.slow
@pytest.mark.live_llm
class TestLiveWorkflowE2E:
    """全流程端到端测试（真实 LLM，仅手动触发）"""

    def test_mini_analysis_with_real_llm(self, temp_data_dir):
        """用小数据集和单一 LLM 运行完整分析"""

    def test_multi_turn_conversation(self, temp_data_dir):
        """验证多轮对话上下文保持"""
```

运行方式：
```bash
# Mock E2E — CI 中每次运行
pytest tests/e2e/test_workflow_e2e_mock.py -v

# 真实 LLM E2E — 仅手动触发
pytest tests/e2e/test_workflow_e2e_live.py -v -m "live_llm" --run-slow
```

---

## 6. Mock 与 Fixture 基础设施

### 6.1 核心 Fixtures（`tests/conftest.py`）

```python
# ===== 路径/环境 Fixtures =====

@pytest.fixture
def project_root():
    """返回项目根目录的绝对路径"""
    return Path(__file__).parent.parent

@pytest.fixture
def temp_workspace(tmp_path):
    """隔离的临时工作目录，预置 data/ 结构"""
    (tmp_path / "data").mkdir()
    (tmp_path / "output").mkdir()
    return tmp_path

@pytest.fixture
def sample_csv(temp_workspace):
    """创建示例 CSV 文件"""
    path = temp_workspace / "data" / "test.csv"
    path.write_text("col1,col2\n1,2\n3,4\n", encoding="utf-8")
    return path

@pytest.fixture
def sample_config_dir(tmp_path):
    """创建模拟的 config/ 目录结构"""
    # 创建 _shared/rules.md, agents/*/AGENT.md + config.yaml 等
    return tmp_path

# ===== LLM Mock Fixtures =====

@pytest.fixture
def mock_chat_model():
    """FakeListChatModel 工厂"""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    def _make(responses: list[str]):
        return FakeListChatModel(responses=responses, sleep=0)
    return _make

@pytest.fixture
def mock_language_model_manager(monkeypatch):
    """替换 LanguageModelManager 为 mock"""

@pytest.fixture
def mock_all_agents(monkeypatch):
    """替换全部 9 个 Agent 为 mock 版本（用于 E2E）"""

# ===== 网络 Mock Fixtures =====

@pytest.fixture
def mock_selenium(monkeypatch):
    """Mock Selenium WebDriver"""

@pytest.fixture
def mock_firecrawl(monkeypatch):
    """Mock FireCrawlLoader"""

@pytest.fixture
def mock_wikipedia(monkeypatch):
    """Mock wikipedia 库"""

@pytest.fixture
def mock_arxiv(monkeypatch):
    """Mock arxiv 库"""

# ===== MCP Mock Fixtures =====

@pytest.fixture
def mock_mcp_server():
    """启动模拟 MCP Server 并返回连接信息"""

@pytest.fixture
def mock_mcp_manager(monkeypatch):
    """替换 MCPManager 为 mock"""

# ===== 配置 Fixtures =====

@pytest.fixture
def mock_env_vars(monkeypatch):
    """设置测试用环境变量"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("CONFIG_DIRECTORY", "tests/fixtures/config")
    monkeypatch.setenv("WORKING_DIRECTORY", "tests/fixtures/data")

# ===== pytest 配置 =====

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: 慢速测试（默认跳过）")
    config.addinivalue_line("markers", "live_llm: 需要真实 LLM API 的测试")
    config.addinivalue_line("markers", "network: 需要网络连接的测试")

def pytest_collection_modifyitems(config, items):
    """默认跳过 slow 和 live_llm 标记的测试"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="需要 --run-slow 选项")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
```

### 6.2 测试目录结构

```
tests/
├── __init__.py
├── conftest.py                          # 全局 fixtures
├── pytest.ini                           # pytest 配置
│
├── fixtures/                            # 测试用静态数据
│   ├── config/                          # 模拟 config 目录
│   │   ├── agent_models.yaml
│   │   ├── mcp.yaml
│   │   ├── tool_limits.yaml
│   │   └── agents/
│   │       ├── _shared/rules.md
│   │       ├── code_agent/AGENT.md + config.yaml
│   │       ├── process_agent/AGENT.md + config.yaml
│   │       ├── ... (所有 9 个 Agent)
│   │       └── skills/
│   │           └── example_skill/SKILL.md
│   └── data/                            # 测试数据集
│       ├── tiny.csv                     # 3 行 × 3 列的微型 CSV
│       ├── small_online_sales.csv       # 100 行销售数据
│       ├── bad_encoding_gbk.csv         # GBK 编码的 CSV
│       └── malformed.csv                # 格式错误的 CSV
│
├── unit/                                # 单元测试
│   ├── __init__.py
│   ├── test_security.py                 # SecurityScanner + ResourceLimiter
│   ├── test_validators.py               # PathValidator
│   ├── test_content_validator.py        # ContentValidator
│   ├── test_tool_config.py              # ToolConfig
│   ├── test_state.py                    # State + create_initial_state
│   ├── test_schemas.py                  # ArtifactSchema + 其他 schema
│   ├── test_router.py                   # 3 个路由函数
│   ├── test_config.py                   # AgentModelsConfig
│   ├── test_agent_config.py             # AgentConfigLoader
│   ├── test_llm_factory.py              # ProviderFactory
│   ├── test_tool_factory.py             # ToolFactory
│   ├── test_agent_factory.py            # AgentFactory
│   ├── test_logger.py                   # Logger 设置
│   └── test_node_utils.py               # 节点辅助函数
│
├── integration/                         # 集成测试
│   ├── __init__.py
│   ├── test_agent_creation.py           # Agent 初始化 + 工具加载
│   ├── test_workflow_graph.py           # Workflow 图构建 + 编译
│   ├── test_nodes.py                    # 节点函数 + 状态转换
│   ├── test_mcp_manager.py              # MCP 连接 + 工具发现
│   ├── test_tools_integration.py        # 工具执行 + 文件操作
│   └── test_skills.py                   # LookupSkill + skill 加载
│
└── e2e/                                 # 端到端测试
    ├── __init__.py
    ├── test_workflow_e2e_mock.py         # Mock LLM 全流程
    └── test_workflow_e2e_live.py         # 真实 LLM（手动触发）
```

---

## 7. 测试数据管理

### 7.1 静态测试数据 (`tests/fixtures/data/`)

| 文件 | 用途 | 大小 |
|------|------|------|
| `tiny.csv` | 基础文件读取测试 | ~50B |
| `small_online_sales.csv` | 集成测试用销售数据 | ~10KB |
| `bad_encoding_gbk.csv` | 非 UTF-8 编码兼容性 | ~200B |
| `malformed.csv` | 错误格式处理 | ~100B |
| `empty.csv` | 空文件边界情况 | 0B |
| `large.csv` | 大文件截断测试 | ~6MB |

### 7.2 动态测试数据

```python
# conftest.py
@pytest.fixture
def generate_csv(tmp_path):
    """动态生成指定行数的 CSV"""
    def _make(rows: int, cols: int = 3):
        import pandas as pd
        import numpy as np
        df = pd.DataFrame(
            np.random.randn(rows, cols),
            columns=[f"col_{i}" for i in range(cols)]
        )
        path = tmp_path / f"gen_{rows}x{cols}.csv"
        df.to_csv(path, index=False)
        return path
    return _make
```

### 7.3 Agent 响应 Gold 文件（用于快照测试）

```
tests/fixtures/golden/
├── process_agent_routes.json       # 预期路由决策
├── quality_review_decisions.json   # 预期质量评审结果
├── hypothesis_samples.json         # 预期假设格式
└── artifact_schema_samples.json    # 预期产物格式
```

---

## 8. CI/CD 集成

### 8.1 GitHub Actions 工作流

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-and-integration:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-mock pytest-cov
      - name: Run unit tests
        run: pytest tests/unit/ -v --tb=short --cov=src --cov-report=xml
      - name: Run integration tests
        run: pytest tests/integration/ -v --tb=short
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  e2e-mock:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-mock
      - name: Run E2E (mock)
        run: pytest tests/e2e/test_workflow_e2e_mock.py -v

  security-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security-focused tests
        run: |
          pip install pytest
          pytest tests/unit/test_security.py tests/unit/test_validators.py -v
```

### 8.2 Pre-commit 钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: unit-tests
        name: Run unit tests
        entry: pytest tests/unit/ -x --tb=short
        language: system
        pass_filenames: false
        stages: [pre-commit]
```

### 8.3 tox 配置（可选多环境本地测试）

```ini
# tox.ini
[tox]
envlist = py311, py312, py313

[testenv]
deps =
    -r requirements.txt
    pytest
    pytest-asyncio
    pytest-mock
    pytest-cov
commands =
    pytest tests/unit/ {posargs}
    pytest tests/integration/ {posargs}
```

---

## 9. 实施路线图

### Phase 1：基础重建（第 1-2 天） ⭐ 最高优先级

恢复并增强之前存在过的测试（参考 `tests/__pycache__/` 中的 `.pyc` 文件）：

| 任务 | 产出 | 预估工作量 |
|------|------|-----------|
| 搭建测试基础设施 | `tests/conftest.py`, `tests/pytest.ini`, `tests/fixtures/` | 3h |
| 恢复 `test_security.py` | SecurityScanner 全覆盖 | 2h |
| 恢复 `test_validators.py` | PathValidator + ContentValidator 全覆盖 | 2h |
| 恢复 `test_config.py` | AgentModelsConfig 测试 | 1h |
| 恢复 `test_schemas.py` | ArtifactSchema 校验测试 | 1h |
| 恢复 `test_state.py` | State 模型测试 | 1.5h |
| 恢复 `test_router.py` | 3 个路由函数全覆盖 | 2.5h |
| 恢复 `test_llm_factory.py` | ProviderFactory 测试 | 1h |
| 恢复 `test_agent_config.py` | AgentConfigLoader 测试 | 3h |

### Phase 2：核心补齐（第 3-4 天）

| 任务 | 产出 | 预估工作量 |
|------|------|-----------|
| `test_tool_config.py` | ToolConfig 加载/默认值/单例 | 1.5h |
| `test_tool_factory.py` | ToolFactory 注册/获取/MCP 工具 | 1.5h |
| `test_agent_factory.py` | AgentFactory 映射/未知名称 | 1h |
| `test_logger.py` | 日志设置/Unicode 安全/过滤器 | 1h |
| `test_content_validator.py` | ContentValidator 补充 | 1.5h |
| `test_node_utils.py` | get_state_attr 等辅助函数 | 1h |

### Phase 3：集成测试（第 5-7 天）

| 任务 | 产出 | 预估工作量 |
|------|------|-----------|
| Agent 创建集成测试 | 9 Agent 初始化 + 工具加载验证 | 4h |
| Workflow 图构建测试 | 11 节点 + 3 条件边验证 | 3h |
| 节点函数集成测试 | agent_node + 状态转换 | 4h |
| MCP Manager 集成测试 | Mock MCP server + 工具适配 | 3h |
| 工具集成测试 | 代码执行 + 文件操作 + 网络工具 mock | 4h |
| Skills/Rules 集成测试 | 渐进式披露加载流程 | 2h |

### Phase 4：E2E + CI（第 8-10 天）

| 任务 | 产出 | 预估工作量 |
|------|------|-----------|
| Mock LLM E2E 测试 | 完整工作流验证 | 5h |
| 真实 LLM E2E 测试 | 手动触发用 | 3h |
| GitHub Actions CI 配置 | 多平台多版本矩阵 | 3h |
| pre-commit 钩子 | 提交前自动跑单测 | 1h |
| 覆盖率报告集成 | Codecov / Coveralls | 1h |

### Phase 5：持续维护

- 每个新功能/修改同步更新测试
- 每周手动运行一次 `live_llm` E2E
- 覆盖率低于 80% 时增加测试

---

## 10. 附录：覆盖率目标

| 模块 | 行覆盖率目标 | 分支覆盖率目标 |
|------|------------|--------------|
| `src/tools/security.py` | > 95% | > 90% |
| `src/tools/validators.py` | > 95% | > 90% |
| `src/tools/tool_config.py` | > 90% | > 85% |
| `src/core/router.py` | > 95% | > 90% |
| `src/core/state.py` | > 90% | > 80% |
| `src/core/schemas.py` | > 90% | - |
| `src/core/agent_config_loader.py` | > 90% | > 85% |
| `src/config.py` | > 85% | > 80% |
| `src/llm/factory.py` | > 85% | > 80% |
| `src/tools/factory.py` | > 80% | > 75% |
| `src/agents/factory.py` | > 85% | > 80% |
| `src/logger.py` | > 80% | - |
| `src/core/workflow.py` | > 75% | > 65% |
| `src/core/node.py` | > 70% | > 60% |
| `src/core/mcp_manager.py` | > 70% | > 60% |
| `src/tools/basetool.py` | > 75% | > 65% |
| `src/tools/FileEdit.py` | > 70% | > 60% |
| `src/tools/internet.py` | > 60% | > 50% |
| `src/system.py` | > 65% | > 55% |
| `src/agents/*.py` (9个) | > 60% | > 50% |

**项目总体目标**: 行覆盖率 > 80%，分支覆盖率 > 70%

---

## 快速开始

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-mock pytest-cov

# 运行全部单元测试
pytest tests/unit/ -v

# 运行安全相关测试
pytest tests/unit/test_security.py tests/unit/test_validators.py -v

# 运行集成测试
pytest tests/integration/ -v

# 运行 E2E (mock)
pytest tests/e2e/test_workflow_e2e_mock.py -v

# 生成覆盖率报告
pytest tests/unit/ tests/integration/ --cov=src --cov-report=html

# 运行全部测试（跳过慢测试）
pytest tests/ -v

# 运行全部（包括真实 LLM）
pytest tests/ -v --run-slow
```

---

> 📋 **下一步**: 从 Phase 1 的 `tests/conftest.py` 和 `tests/fixtures/` 开始搭建基础设施，然后按优先级逐个恢复单元测试。
