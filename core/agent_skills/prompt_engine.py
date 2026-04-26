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
1. 匹配技能时必须先加载，执行脚本前必须确认技能已加载；
2. 指令必须输出 JSON 格式，示例：
   - 加载技能：{{"command": "LOAD_SKILL", "skill_name": "xxx"}}
   - 执行脚本：{{"command": "RUN_SCRIPT", "skill_name": "xxx", "script_name": "xxx", "args": ["x1", "x2"]}}
3. 只返回 JSON 指令或有用回答，禁止多余文本；
4. 执行脚本前需校验技能的 allowed_tools 权限。
"""



    @staticmethod
    def with_loaded_skill(base_prompt:str,skill:Skill)->str:
        """加入已加载技能的完整指令（Level 1+2）"""
        return f"{base_prompt}\n\n=== 已加载技能 ===\n{skill.full_prompt}"