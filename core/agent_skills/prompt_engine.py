"""
生成系统提示（渐进式）
"""
import json

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
1. 优先使用技能，若无匹配技能但存在合适的工具，则输出工具调用指令。
2. 指令必须输出 JSON 格式：
   - 加载技能：{{"command": "LOAD_SKILL", "skill_name": "xxx"}}
   - 执行脚本：{{"command": "RUN_SCRIPT", "skill_name": "xxx", "script_name": "xxx", "args": ["x1"]}}
   - 调用工具：{{"command": "USE_TOOL", "tool_name": "xxx", "tool_args": {{...}}}}
3. 只返回 JSON 指令或有用回答，禁止多余文本；
4. 执行脚本前需校验技能的 allowed_tools 权限；
"""



    @staticmethod
    def with_loaded_skill(base_prompt:str,skill:Skill)->str:
        """加入已加载技能的完整指令（Level 1+2）"""
        return f"{base_prompt}\n\n=== 已加载技能 ===\n{skill.full_prompt}"