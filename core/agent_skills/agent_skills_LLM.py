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
from core.builtin_tools import get_tool
from core.logger import logger, timer


class AgentSkillsLLM:
    def __init__(self, llm: BaseChatModel, skill_manager: SkillsManager,debug=False):
        self.llm = llm
        self.skill_manager = skill_manager
        self.executor = SkillExecutor()
        self.base_prompt = PromptEngine.base_system_prompt(self.skill_manager)
        self.loaded_skill: Optional[Skill] = None
        self.debug = debug

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """执行内置工具并返回结果"""
        tool = get_tool(tool_name)
        if not tool:
            return f"❌ 未知工具：{tool_name}"
        # 后续可加入权限等级校验
        try:
            result = tool.handler(**tool_args)
            return str(result)
        except Exception as e:
            return f"❌ 工具执行异常：{str(e)}"

    # 2. 重构 parse_command 方法（解析 JSON 指令）
    @staticmethod
    def parse_command(text: str):
        import json
        # 提取文本中的 JSON 片段
        default_return = {
            "command": None,
            "skill_name": None,
            "script_name": None,
            "args": [],
            "tool_name": None,
            "tool_args": [],
        }
        json_match = re.search(r"\{[\s\S]*\}", text)
        if not json_match:
            return default_return
        try:
            cmd = json.loads(json_match.group())
            script_name = None
            tool_name = None
            if cmd.get("script_name") is not None:
                script_name = AgentSkillsLLM.get_last_path_part(cmd.get("script_name"))
            if cmd.get("tool_name") is not None:
                tool_name = AgentSkillsLLM.get_last_path_part(cmd.get("tool_name"))
            return {
                "command": cmd.get("command"),
                "skill_name": cmd.get("skill_name"),
                "script_name": script_name,
                "args": cmd.get("args", []),
                "tool_name": tool_name,
                "tool_args": cmd.get("tool_args", []),
            }
        except json.JSONDecodeError:
            logger.error("LLM 输出的指令 JSON 格式错误")
            return default_return

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
        if cmd["command"] == 'LOAD_SKILL':
            skill_name = cmd["skill_name"]
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
        if cmd["skill_name"] and cmd["script_name"] and self.loaded_skill:
            # 安全校验：执行的技能必须是当前加载的技能
            if cmd["skill_name"] != self.loaded_skill.name:
                return "❌ 安全校验失败：只能执行当前已加载的技能"

            if self.debug:
                logger.info(f"\n[日志] 执行脚本：{cmd['script_name']} 参数：{cmd['args']}")
            exec_result = self.executor.run_script(self.loaded_skill, cmd["script_name"], cmd["args"])
            if self.debug:
                logger.info(f"[脚本执行结果] {exec_result}")
            # 让LLM基于执行结果生成最终回答（优化体验）
            final_reply = f"✅ 执行完成\n{exec_result}"
        if self.debug:
            logger.info(f"[最终回复] {final_reply}")
        return final_reply

    # @timer(name="Agent 完整对话流程")
    # def chat(self, user_input: str) -> str:
    #     if self.debug:
    #         logger.info(f"用户输入：{user_input}")
    #
    #     messages = [
    #         SystemMessage(content=self.base_prompt),
    #         HumanMessage(content=user_input)
    #     ]
    #
    #     # 🔁 多轮循环：支持连续 Skill 加载 + 工具调用
    #     MAX_TURNS = 5
    #     for turn in range(MAX_TURNS):
    #         if self.debug:
    #             logger.info(f"\n[日志] 第 {turn + 1} 轮 LLM 调用")
    #         reply = self.llm.invoke(messages).content
    #         if self.debug:
    #             logger.info(f"[LLM 回复] {reply}")
    #
    #         cmd = self.parse_command(reply)
    #         if self.debug:
    #             logger.info(f"[解析命令] {cmd}")
    #
    #         # ---- 处理 LOAD_SKILL ----
    #         if cmd["command"] == "LOAD_SKILL":
    #             skill_name = cmd["skill_name"]
    #             self.loaded_skill = self.skill_manager.load_skill(skill_name)
    #             if not self.loaded_skill:
    #                 return f"❌ 技能 {skill_name} 不存在"
    #             # 注入技能指令，继续下一轮
    #             system = PromptEngine.with_loaded_skill(self.base_prompt, self.loaded_skill)
    #             messages = [SystemMessage(content=system), HumanMessage(content=user_input)]
    #             continue
    #
    #         # ---- 处理 RUN_SCRIPT ----
    #         if cmd["command"] == "RUN_SCRIPT" and self.loaded_skill:
    #             if cmd["skill_name"] != self.loaded_skill.name:
    #                 return "❌ 安全校验失败：只能执行当前已加载的技能"
    #             exec_result = self.executor.run_script(
    #                 self.loaded_skill, cmd["script_name"], cmd["args"]
    #             )
    #             # 将执行结果反馈给 LLM 以生成最终回答
    #             feedback = f"脚本执行结果：\n{exec_result}\n请根据此结果回答用户。"
    #             messages.append(HumanMessage(content=feedback))
    #             continue
    #
    #         # ---- 处理 USE_TOOL ----
    #         if cmd["command"] == "USE_TOOL":
    #             tool_name = cmd.get("tool_name")
    #             tool_args = cmd.get("tool_args", {})
    #             if not tool_name:
    #                 return "❌ 工具调用缺少 tool_name"
    #             tool_result = self._execute_tool(tool_name, tool_args)
    #             # 将工具结果反馈给 LLM
    #             feedback = f"工具 [{tool_name}] 返回结果：\n{tool_result}\n请根据此结果回答用户。"
    #             messages.append(HumanMessage(content=feedback))
    #             continue
    #
    #         # ---- 无命令，直接返回文本 ----
    #         return reply
    #
    #     return "❌ 达到最大对话轮次，请简化你的请求。"