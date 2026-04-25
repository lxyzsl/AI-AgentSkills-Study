"""
LLM 基类继承（LangChain 标准架构）
"""
import re
from pathlib import Path
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage

from core.agent_skills.prompt_engine import PromptEngine
from core.agent_skills.skill import Skill
from core.agent_skills.skill_executor import SkillExecutor
from core.agent_skills.skills_manager import SkillsManager
from core.logger import logger, timer


class AgentSkillsLLM:
    def __init__(self, llm: BaseChatModel, skill_manager: SkillsManager,debug=False):
        self.llm = llm
        self.skill_manager = skill_manager
        self.executor = SkillExecutor()
        self.base_prompt = PromptEngine.base_system_prompt(self.skill_manager)
        self.loaded_skill: Optional[Skill] = None
        self.debug = debug

    @staticmethod
    def parse_command(text: str):
        load_match = re.search(r"\[LOAD_SKILL\]\s*(.+)", text)
        run_match = re.search(r"\[RUN_SCRIPT\]\s*(\S+)\s*(\S+)\s*(.*)", text)
        cmd = {
            "LOAD_SKILL": load_match.group(1) if load_match else None,
            "RUN": {
                "skill": run_match.group(1) if run_match else None,
                "script": run_match.group(2) if run_match else None,
                "args": run_match.group(3).split() if run_match else []
            }
        }
        if cmd["RUN"]["script"]:
            cmd["RUN"]["script"] = AgentSkillsLLM.get_last_path_part(cmd["RUN"]["script"])
        logger.info(f"cmd:{str(cmd)}")
        return cmd

    @staticmethod
    def get_last_path_part(s: str) -> str:
        """
        /a/b/c/SKILL.md -> SKILL.md
        ./skills/chat -> chat
        D:\\tools\\app.exe -> app.exe
        普通文本 -> 普通文本
        """
        # 先判断是否疑似路径：包含 / 或 \
        if "/" in s or "\\" in s:
            return Path(s).name  # 只保留最后一段
        return s

    @timer(name="Agent 完整对话流程")
    def chat(self, user_input: str) -> str:
        if self.debug:
            logger.info(f"用户输入：{user_input}")


        messages = [
            SystemMessage(content=self.base_prompt),
            HumanMessage(content=user_input)
        ]
        if self.debug:
            logger.info("\n[日志] 第一轮 LLM 调用（仅元数据）")
            for message in messages:
                logger.info(message.pretty_repr())
        first_reply = self.llm.invoke(messages).content
        if self.debug:
            logger.info(f"[LLM 第一轮回复] {first_reply}")
        cmd = self.parse_command(first_reply)
        if self.debug:
            logger.info(f"[解析命令] {cmd}")
        # 2. 渐进式加载技能（Level 2）
        if cmd["LOAD_SKILL"]:
            skill_name = cmd["LOAD_SKILL"]
            if self.debug:
                logger.info(f"\n[日志] 开始加载技能：{skill_name}")
            self.loaded_skill = self.skill_manager.load_skill(skill_name)

            # 空值保护：技能不存在
            if not self.loaded_skill:
                return f"❌ 技能 {skill_name} 不存在"
            if self.debug:
                logger.info(f"[日志] 技能加载成功：{self.loaded_skill.name}")

            # 注入完整技能指令，重新调用LLM
            system = PromptEngine.with_loaded_skill(self.base_prompt, self.loaded_skill)
            messages = [SystemMessage(content=system), HumanMessage(content=user_input)]
            if self.debug:
                logger.info("\n[日志] 第二轮 LLM 调用（技能已加载）")
                for message in messages:
                    logger.info(message.pretty_repr())
            second_reply = self.llm.invoke(messages).content
            if self.debug:
                logger.info(f"[LLM 第二轮回复] {second_reply}")

            cmd = AgentSkillsLLM.parse_command(second_reply)
            if self.debug:
                logger.info(f"[解析新命令] {cmd}")
            final_reply = second_reply
        else:
            # 无需加载技能，直接返回
            final_reply = first_reply

        # 3. 执行脚本（Level 3）✅ 修复：使用最新解析的命令
        run = cmd["RUN"]
        if run["skill"] and run["script"] and self.loaded_skill:
            # 安全校验：执行的技能必须是当前加载的技能
            if run["skill"] != self.loaded_skill.name:
                return "❌ 安全校验失败：只能执行当前已加载的技能"

            if self.debug:
                logger.info(f"\n[日志] 执行脚本：{run['script']} 参数：{run['args']}")
            exec_result = self.executor.run_script(self.loaded_skill, run["script"], run["args"])
            if self.debug:
                logger.info(f"[脚本执行结果] {exec_result}")
            # 让LLM基于执行结果生成最终回答（优化体验）
            final_reply = f"✅ 执行完成\n{exec_result}"
        if self.debug:
            logger.info(f"[最终回复] {final_reply}")
        return final_reply