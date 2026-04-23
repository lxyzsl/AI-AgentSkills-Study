"""
生成系统提示（渐进式）
"""
from core.agent_skills.skill import Skill
from core.agent_skills.skills_manager import SkillsManager


class PromptEngine:
    @staticmethod
    def base_system_prompt(manager:SkillsManager)->str:
        """基础提示：仅所有技能元数据（Level 1）"""
        skills_list = manager.list_metadata()
        return f"""
你是一个具备专业技能的 AI Agent。
可用技能（仅名称与描述）：
{skills_list}

规则：
1. 用户需求匹配技能时，必须先加载该技能
2. 加载格式：[LOAD_SKILL] 技能名
3. 如需执行脚本，使用：[RUN_SCRIPT] 技能名 脚本名 参数...
4. 只回答有用信息，保持简洁
"""

    @staticmethod
    def with_loaded_skill(base_prompt:str,skill:Skill)->str:
        """加入已加载技能的完整指令（Level 1+2）"""
        return f"{base_prompt}\n\n=== 已加载技能 ===\n{skill.full_prompt}"