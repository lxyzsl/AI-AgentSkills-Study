import re
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

"""
数据结构：Skill（元数据+指令）

Level 1：元数据（Metadata）常驻
    来源：SKILL.md 头部 YAML frontmatter
    内容：name, description, version, tags, allowed-tools
    时机：启动时全量加载（~100 token/skill）
    作用：让 Agent 知道 “我有什么技能”
Level 2：指令（Instructions）按需加载
    来源：SKILL.md 正文（Markdown）
    时机：匹配到任务时才加载（<5000 token）
    作用：详细步骤、SOP、示例
Level 3：资源（Resources）
    来源：scripts/, references/, assets/
    时机：执行中按需加载 / 调用
    作用：代码、模板、参考文档
"""
@dataclass
class Skill:
    # Level 1:Metadata(常驻)
    name:str
    description:str
    version:str = "1.0.0"
    tags:list[str] = None
    allowed_tools:list[str] = None
    author:str = None
    # 新增：Anthropic 要求的元数据
    input_schema: dict = None  # 脚本入参Schema（JSON Schema）
    output_schema: dict = None  # 脚本出参Schema
    execution_constraints: dict = None  # 执行约束：{"timeout":30, "max_memory_mb":512}
    permission_level: str = "basic"  # 权限等级：basic/admin/system
    # Level 2:Instructions（按需加载）
    instructions:str = ""
    # 路径
    skill_dir:Path = None
    md_path:Path = None
    # 状态
    is_loaded:bool = False
    loaded_at:float = 0.0

    @classmethod
    def from_skill_md(cls,md_path:Path) -> "Skill":
        """
        从SKILL.md解析（YAML frontmatter + Markdown）
        :param md_path:MD文件路径
        :return: 返回一个Skill对象，加引号是因为类还没定义完，提前标注（前向引用）
        """
        with open(md_path,"r",encoding="utf-8") as f:
            content = f.read()

        # 拆分 --- 分隔的 YAML 于正文
        match = re.search(r"^---\n(.*?)\n---\n(.*)$",content,re.DOTALL)
        if not match:
            raise ValueError(f"{md_path} 缺少 YAML frontmatter")
        # YAML内容
        yaml_meta = match.group(1)
        # MD正文
        instructions = match.group(2)

        # 安全解析 YAML
        meta = yaml.safe_load(yaml_meta)

        return cls(
            name=meta["name"],
            description=meta["description"],
            version=meta.get("version","1.0.0"),
            tags=meta.get("tags",[]),
            allowed_tools=meta.get("allowed-tools",[]),
            author=meta.get("author",""),
            input_schema=meta.get("input-schema", {}),
            output_schema=meta.get("output-schema", {}),
            execution_constraints=meta.get("execution-constraints", {"timeout": 30, "max_memory_mb": 512}),
            permission_level=meta.get("permission-level", "basic"),
            instructions=instructions,
            skill_dir=md_path.parent,
            md_path=md_path,
        )

    def load_instructions(self):
        """主动加载完整指令（Level 2）"""
        if not self.is_loaded:
            with open(self.md_path,"r",encoding="utf-8") as f:
                content = f.read()
                # 读取MD正文
                match = re.match(r"^---\n.*?\n---\n(.*)$", content, re.DOTALL)
                # 去掉首尾空白、换行、空格。如果匹配失败，赋值空字符串
                self.instructions = match.group(1).strip() if match else ""
            self.is_loaded = True
            self.loaded_at = time.time()

    def unload(self):
        """卸载（节省内存）"""
        self.instructions = ""
        self.is_loaded = False


    @property
    def metadata_prompt(self)->str:
        """
        生成 Level 1 元数据提示（极小 token）
        skill名称，skill描述，skill标签
        """
        return (
            f"- {self.name}: {self.description}\n"
            f"  Tags: {'，'.join(self.tags)}\n"
        )


    @property
    def full_prompt(self)->str:
        """生成 Level 1+2 完整提示（触发后使用）"""
        self.load_instructions()
        return f"""
=== Skill Name: {self.name} ===
description: {self.description}
version: {self.version}
tags: {'，'.join(self.tags)}

{self.instructions}
"""
