"""支持渐进式披露的Agent配置加载器。

本模块根据Claude Agent Skills规范实现了智能的Agent配置加载器。它支持：
- Agent定义的YAML frontmatter + Markdown格式
- 渐进式披露（Level 1：元数据，Level 2：指令，Level 3：资源）
- Skills和Rules集成
- 每个Agent的MCP server配置

示例：
    loader = AgentConfigLoader()

    # Level 1：发现Agent（轻量级）
    agents = loader.discover_agents()

    # Level 2：在需要时加载完整的系统提示词
    prompt = loader.load_system_prompt("process_agent")

    # Level 3：加载skills和MCP配置
    skills = loader.load_skills("process_agent")
    mcp_config = loader.load_mcp_config("process_agent")
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..logger import setup_logger


logger = setup_logger()


@dataclass
class AgentMetadata:
    """从YAML frontmatter中提取的Agent元数据（Level 1）。

    Attributes:
        name: Agent的唯一标识符（小写加连字符）。
        description: Agent用途的简要说明。
        version: 语义化版本字符串。
        model: 模型配置字典。
        skills: 要从共享skills/文件夹加载的技能名称列表。
        rules: 规则文件路径（字符串）或路径列表。
        mcp_servers: 要启用的MCP server名称列表。
        use_complete_prompt: 如果为True，将markdown内容用作完整的系统提示词。
    """
    name: str
    description: str
    version: str = "1.0.0"
    model: Dict[str, Any] = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    rules: Any = ""  # 可以是str或List[str]
    mcp_servers: List[str] = field(default_factory=list)
    use_complete_prompt: bool = False


@dataclass
class SkillConfig:
    """来自SKILL.md文件的技能配置。

    Attributes:
        name: 技能的唯一标识符。
        description: 用于发现和触发的简要说明。
        content: 技能的完整markdown内容。
        path: 技能文件的绝对路径。
    """
    name: str
    description: str
    content: str
    path: Path


@dataclass
class RuleConfig:
    """来自规则markdown文件的规则配置。

    Attributes:
        trigger: 规则何时生效（'always_on'、'on_demand'、'context_match'）。
        priority: 规则应用的优先级（数值越大越先应用）。
        context_patterns: 用于context_match触发器的模式。
        content: 规则的完整markdown内容。
        path: 规则文件的绝对路径。
    """
    trigger: str = "always_on"
    priority: int = 100
    context_patterns: List[str] = field(default_factory=list)
    content: str = ""
    path: Optional[Path] = None


class AgentConfigLoader:
    """支持渐进式披露的智能Agent配置加载器。

    此加载器实现了三级加载策略：
    - Level 1：元数据（始终加载，轻量级）
    - Level 2：指令/系统提示词（在Agent被触发时加载）
    - Level 3：Skills、Rules、MCP配置（按需加载）

    Attributes:
        config_root: Agent配置的根目录。
    """

    # 从markdown中提取YAML frontmatter的正则表达式
    FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n",
        re.DOTALL
    )

    def __init__(
        self,
        config_root: str | Path | None = None,
        mcp_config_path: str | Path | None = None
    ) -> None:
        """初始化Agent配置加载器。

        Args:
            config_root: 包含Agent配置的根目录。
            mcp_config_path: MCP server配置文件的路径。
        """
        # 从环境变量加载基础配置目录
        config_dir = os.getenv('CONFIG_DIRECTORY', 'config')

        # 如果未提供则相对于config_dir设置默认值
        if config_root is None:
            config_root = os.path.join(config_dir, "agents")
        if mcp_config_path is None:
            mcp_config_path = os.path.join(config_dir, "mcp.yaml")

        self.config_root = Path(config_root)
        self.mcp_config_path = Path(mcp_config_path)
        self._metadata_cache: Dict[str, AgentMetadata] = {}
        self._mcp_config: Optional[Dict[str, Any]] = None

    def discover_agents(self) -> List[str]:
        """发现所有可用的Agent（Level 1）。

        扫描config_root目录，查找包含AGENT.md文件的Agent子目录。

        Returns:
            Agent名称列表（目录名）。
        """
        agents = []
        if not self.config_root.exists():
            logger.warning(f"Agent配置根目录不存在: {self.config_root}")
            return agents

        for item in self.config_root.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                agent_md = item / "AGENT.md"
                if agent_md.exists():
                    agents.append(item.name)

        logger.info(f"发现{len(agents)}个Agent: {agents}")
        return agents

    def load_metadata(self, agent_name: str) -> AgentMetadata:
        """从YAML frontmatter加载Agent元数据（Level 1）。

        Args:
            agent_name: Agent的名称（目录名）。

        Returns:
            包含frontmatter数据的AgentMetadata数据类。

        Raises:
            FileNotFoundError: 如果AGENT.md不存在。
            ValueError: 如果frontmatter缺失或无效。
        """
        if agent_name in self._metadata_cache:
            return self._metadata_cache[agent_name]

        agent_md_path = self.config_root / agent_name / "AGENT.md"
        if not agent_md_path.exists():
            raise FileNotFoundError(f"Agent配置未找到: {agent_md_path}")

        content = agent_md_path.read_text(encoding="utf-8")
        frontmatter = self._extract_frontmatter(content)

        if not frontmatter:
            raise ValueError(f"在{agent_md_path}中未找到frontmatter")

        # 从agent_config.yaml获取扩展配置
        ext_config = self._get_agent_extended_config(agent_name)

        metadata = AgentMetadata(
            name=frontmatter.get("name", agent_name),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            model=frontmatter.get("model", {}),
            # 从agent_config.yaml读取skills/rules/mcp，而非frontmatter
            skills=ext_config.get("skills", []),
            tools=ext_config.get("tools", []),
            rules=ext_config.get("rules", []),
            mcp_servers=ext_config.get("mcp_servers", []),
            use_complete_prompt=frontmatter.get("use_complete_prompt", False),
        )

        self._metadata_cache[agent_name] = metadata
        return metadata

    def load_system_prompt(self, agent_name: str) -> str:
        """从AGENT.md加载完整的系统提示词（Level 2）。

        提取frontmatter之后的markdown内容作为系统提示词。

        Args:
            agent_name: Agent的名称。

        Returns:
            系统提示词字符串（markdown内容）。

        Raises:
            FileNotFoundError: 如果AGENT.md不存在。
        """
        agent_md_path = self.config_root / agent_name / "AGENT.md"
        if not agent_md_path.exists():
            raise FileNotFoundError(f"Agent配置未找到: {agent_md_path}")

        content = agent_md_path.read_text(encoding="utf-8")

        # 移除frontmatter以获取提示词内容
        match = self.FRONTMATTER_PATTERN.match(content)
        if match:
            prompt = content[match.end():].strip()
        else:
            prompt = content.strip()

        # 加载并应用rules
        rules_content = self._load_rules_content(agent_name)
        if rules_content:
            prompt = f"{prompt}\n\n{rules_content}"

        # 加载并应用skills
        skills_content = self._load_skills_content(agent_name)
        if skills_content:
            prompt = f"{prompt}\n\n{skills_content}"

        metadata = self.load_metadata(agent_name)
        if metadata.use_complete_prompt:
            return f"SYSTEM_PROMPT:{prompt}"

        return prompt

    def load_skills(self, agent_name: str) -> List[SkillConfig]:
        """加载Agent特定的skills（Level 3）。

        Args:
            agent_name: Agent的名称。

        Returns:
            SkillConfig对象列表。
        """
        metadata = self.load_metadata(agent_name)
        skills = []
        # skills文件夹位于config/skills/（与agents/同级）
        skills_dir = self.config_root.parent / "skills"

        for skill_name in metadata.skills:
            # skills按名称引用，存储在共享skills/文件夹中
            skill_path = skills_dir / skill_name / "SKILL.md"
            if skill_path.exists():
                skill = self._parse_skill_file(skill_path)
                if skill:
                    skills.append(skill)
            else:
                logger.warning(f"技能未找到: {skill_name}")

        return skills

    def get_skill_content(self, skill_name: str) -> Optional[str]:
        """获取技能文件的完整内容（Level 2）。

        Args:
            skill_name: 技能的名称。

        Returns:
            SKILL.md文件的内容，如果未找到则返回None。
        """
        # skills文件夹位于config/skills/（与agents/同级）
        skills_dir = self.config_root.parent / "skills"
        skill_path = skills_dir / skill_name / "SKILL.md"

        if not skill_path.exists():
            logger.warning(f"技能文件未找到: {skill_path}")
            return None

        return skill_path.read_text(encoding="utf-8")

    def load_rules(self, agent_name: str) -> List[RuleConfig]:
        """加载Agent适用的rules（Level 3）。

        Args:
            agent_name: Agent的名称。

        Returns:
            RuleConfig对象列表，按优先级降序排列。
        """
        metadata = self.load_metadata(agent_name)
        rules = []

        # rules现在是一个单一的文件路径（字符串），而非列表
        rule_path = metadata.rules
        if not rule_path:
            return rules

        # 处理为字符串（单个文件）或向后兼容的列表
        if isinstance(rule_path, str):
            rule_paths = [rule_path]
        else:
            rule_paths = rule_path

        for rp in rule_paths:
            # 以下划线开头的路径相对于config_root（共享的）
            if rp.startswith("_"):
                full_path = (self.config_root / rp).resolve()
            else:
                agent_dir = self.config_root / agent_name
                full_path = (agent_dir / rp).resolve()

            if full_path.exists():
                rule = self._parse_rule_file(full_path)
                if rule:
                    rules.append(rule)
            else:
                logger.warning(f"规则文件未找到: {full_path}")

        # 按优先级排序（数值大的优先）
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules

    def load_mcp_config(self, agent_name: str) -> Dict[str, Any]:
        """加载Agent的MCP server配置（Level 3）。

        将默认MCP servers与Agent特定的覆盖项合并。

        Args:
            agent_name: Agent的名称。

        Returns:
            包含'servers'键的字典，值为已启用的server配置。
        """
        if self._mcp_config is None:
            self._mcp_config = self._load_mcp_config_file()

        metadata = self.load_metadata(agent_name)
        all_servers = self._mcp_config.get("servers", {})
        defaults = self._mcp_config.get("defaults", [])

        # 将默认servers与Agent特定的servers合并
        enabled_servers = set(defaults) | set(metadata.mcp_servers)

        result = {
            "servers": {
                name: config
                for name, config in all_servers.items()
                if name in enabled_servers
            }
        }

        return result

    def get_model_config(self, agent_name: str) -> Dict[str, Any]:
        """从Agent元数据中获取模型配置。

        Args:
            agent_name: Agent的名称。

        Returns:
            包含provider和model配置的字典。
        """
        metadata = self.load_metadata(agent_name)
        return metadata.model

    def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """从markdown内容中提取YAML frontmatter。

        Args:
            content: 完整的markdown文件内容。

        Returns:
            解析后的YAML字典，如果没有frontmatter则返回None。
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return None

        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            logger.error(f"解析frontmatter失败: {e}")
            return None

    def _parse_skill_file(self, path: Path) -> Optional[SkillConfig]:
        """将SKILL.md文件解析为SkillConfig。

        Args:
            path: 技能文件的路径。

        Returns:
            SkillConfig，如果解析失败则返回None。
        """
        content = path.read_text(encoding="utf-8")
        frontmatter = self._extract_frontmatter(content)

        if not frontmatter:
            logger.warning(f"技能文件中没有frontmatter: {path}")
            return None

        return SkillConfig(
            name=frontmatter.get("name", path.stem),
            description=frontmatter.get("description", ""),
            content=content,
            path=path,
        )

    def _parse_rule_file(self, path: Path) -> Optional[RuleConfig]:
        """将规则markdown文件解析为RuleConfig。

        Args:
            path: 规则文件的路径。

        Returns:
            RuleConfig，如果解析失败则返回None。
        """
        content = path.read_text(encoding="utf-8")
        frontmatter = self._extract_frontmatter(content)

        if not frontmatter:
            # 没有frontmatter的规则默认为always_on
            return RuleConfig(
                trigger="always_on",
                priority=100,
                content=content,
                path=path,
            )

        # 从内容中移除frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        rule_content = content[match.end():].strip() if match else content

        return RuleConfig(
            trigger=frontmatter.get("trigger", "always_on"),
            priority=frontmatter.get("priority", 100),
            context_patterns=frontmatter.get("context_patterns", []),
            content=rule_content,
            path=path,
        )

    def _load_rules_content(self, agent_name: str) -> str:
        """加载并合并Agent的规则内容。

        Args:
            agent_name: Agent的名称。

        Returns:
            合并后的规则内容字符串。
        """
        rules = self.load_rules(agent_name)
        active_rules = [r for r in rules if r.trigger == "always_on"]

        if not active_rules:
            return ""

        sections = ["## Applied Rules"]
        for rule in active_rules:
            sections.append(rule.content)

        return "\n\n".join(sections)

    def _load_skills_content(self, agent_name: str) -> str:
        """加载并合并Agent的技能内容。

        Args:
            agent_name: Agent的名称。

        Returns:
            合并后的技能内容字符串。
        """
        skills = self.load_skills(agent_name)

        if not skills:
            return ""

        sections = ["## Available Skills"]
        for skill in skills:
            sections.append(f"### {skill.name}\n{skill.description}")

        return "\n\n".join(sections)

    def _load_mcp_config_file(self) -> Dict[str, Any]:
        """从YAML文件加载MCP配置。

        Returns:
            MCP配置字典。
        """
        if not self.mcp_config_path.exists():
            logger.warning(f"MCP配置未找到: {self.mcp_config_path}")
            return {"servers": {}, "defaults": []}

        try:
            content = self.mcp_config_path.read_text(encoding="utf-8")
            config = yaml.safe_load(content)

            # 展开配置中的环境变量
            return self._expand_env_vars(config)
        except yaml.YAMLError as e:
            logger.error(f"解析MCP配置失败: {e}")
            return {"servers": {}, "defaults": []}

    def _expand_env_vars(self, obj: Any) -> Any:
        """递归展开配置中的环境变量。

        支持${VAR_NAME}语法。

        Args:
            obj: 配置对象（dict、list或string）。

        Returns:
            环境变量已展开的对象。
        """
        if isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # 匹配${VAR_NAME}模式
            pattern = re.compile(r"\$\{([^}]+)\}")
            def replace(match: re.Match) -> str:
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))
            return pattern.sub(replace, obj)
        return obj

    def _load_per_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """从config.yaml加载每个Agent的配置。

        Args:
            agent_name: Agent的名称。

        Returns:
            Agent配置字典。
        """
        config_path = self.config_root / agent_name / "config.yaml"
        if not config_path.exists():
            logger.debug(f"Agent没有config.yaml: {agent_name}")
            return {"skills": [], "tools": [], "rules": [], "mcp_servers": []}

        try:
            content = config_path.read_text(encoding="utf-8")
            config = yaml.safe_load(content) or {}
            return {
                "skills": config.get("skills", []),
                "tools": config.get("tools", []),
                "rules": config.get("rules", []),
                "mcp_servers": config.get("mcp_servers", []),
            }
        except yaml.YAMLError as e:
            logger.error(f"解析{agent_name}的config.yaml失败: {e}")
            return {"skills": [], "tools": [], "rules": [], "mcp_servers": []}

    def _get_agent_extended_config(self, agent_name: str) -> Dict[str, Any]:
        """获取Agent的扩展配置（skills/rules/mcp）。

        从Agent自身的config.yaml文件中读取。

        Args:
            agent_name: Agent的名称。

        Returns:
            包含skills、rules和mcp_servers的字典。
        """
        return self._load_per_agent_config(agent_name)



# 用于全局访问的单例实例
_default_loader: Optional[AgentConfigLoader] = None


def get_agent_config_loader() -> AgentConfigLoader:
    """获取默认的AgentConfigLoader单例。

    Returns:
        AgentConfigLoader实例。
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = AgentConfigLoader()
    return _default_loader
