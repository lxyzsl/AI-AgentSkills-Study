"""
启动扫描（bootstrap）、缓存、检索
"""
import time
from pathlib import Path
from typing import Dict, Optional, List

from core.agent_skills.skill import Skill


class SkillsManager:
    def __init__(self,skills_root:str='./skills',ttl:int = 3600,debug=False):
        self.skills_root = Path(skills_root)
        self.ttl = ttl # 缓存有效期（秒）
        self.skills:Dict[str,Skill] = {} # name -> Skill
        self.debug = debug
        self.bootstrap() # 启动时扫描所有技能（仅元数据）

    def bootstrap(self):
        """启动加载：扫描所有 SKILL.md， 仅加载元数据（Level 1）"""
        self.skills.clear()
        # 从skills_root开始，递归查找所有名称为SKILL.md的文件
        for md_path in  self.skills_root.rglob("**/SKILL.md"):
            try:
                skill = Skill.from_skill_md(md_path)
                self.skills[skill.name] = skill
                if self.debug:
                    print(f"[Bootstrap] 发现技能：{skill.name}")
            except Exception as e:
                print(f"[Bootstrap] 加载失败 {md_path}: {e}")


    def get(self,skill_name:str) -> Optional[Skill]:
        """获取技能（过期自动清理）"""
        skill = self.skills.get(skill_name)
        if skill and skill.is_loaded and time.time() - skill.loaded_at > self.ttl:
            skill.unload()
        return skill

    def list_all(self)->List[Skill]:
        """所有技能（元数据）"""
        return list(self.skills.values())

    def list_metadata(self) -> str:
        return "\n".join(s.metadata_prompt for s in self.list_all())
    def search(self,query:str,limit:int = 5) -> List[Skill]:
        """关键词匹配技能，最多匹配5个"""
        query = query.lower()
        matches = []
        for s in self.skills.values():
            if (
                    (query in s.name.lower())
                    or (query in s.description.lower())
                    or (query in t.lower() for t in s.tags)
            ):
                matches.append(s)
        return matches[:limit]

    def load_skill(self,skill_name:str) -> Optional[Skill]:
        """触发加载完整节能 （Level 2）"""
        skill = self.get(skill_name)
        if skill:
            skill.load_instructions()
        return skill

    def unload_all(self):
        for s in self.skills.values():
            s.unload()