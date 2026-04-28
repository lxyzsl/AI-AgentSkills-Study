"""
SkillExecutor：安全执行 scripts/ 代码（Level 3）
"""
import os
import subprocess
import threading
import time
from typing import List, Dict

import psutil

from core.agent_skills.skill import Skill
from core.logger import logger


class SkillExecutor:
    """
    系统通用技能执行器（Windows/Linux/macOS）
    符合 Anthropic 标准：路径隔离 + 权限校验 + 超时 + CPU/内存硬限制
    无系统专属依赖，零兼容问题
     """

    # ======================
    # 全局资源限制（可自定义）
    # ======================
    MAX_CPU_USAGE = 50  # 单脚本最大CPU占用（%）
    MAX_MEMORY_USAGE = 256  # 单脚本最大内存（MB）
    EXEC_TIMEOUT = 30  # 全局超时时间（秒）
    MAX_OUTPUT_LINES = 100
    MAX_OUTPUT_CHARS = 8192

    @staticmethod
    def _truncate(text: str,max_len=2000) -> str:
        """安全截断输出，防 Context 爆炸"""
        if not text: return ""
        lines = text.splitlines()
        if len(lines) > SkillExecutor.MAX_OUTPUT_LINES:
            head = "\n".join(lines[:30])
            tail = "\n".join(lines[-20:])
            text = f"{head}\n... (截断 {len(lines) - 50} 行) ...\n{tail}"
        if len(text) > SkillExecutor.MAX_OUTPUT_CHARS:
            text = text[:SkillExecutor.MAX_OUTPUT_CHARS] + "\n... (输出已截断)"
        return text.strip() if len(text) <= max_len else text[:max_len] + "...(truncated)"

    # @staticmethod
    # def _watch_process(pid: int):
    #     """后台守护线程：全平台监控进程资源，超标立即终止"""
    #     try:
    #         process = psutil.Process(pid)
    #         while process.is_running():
    #             # 跨平台获取CPU/内存
    #             cpu = process.cpu_percent(interval=0.5)
    #             mem = process.memory_info().rss / 1024 / 1024  # 转MB
    #
    #             # CPU超限
    #             if cpu > SkillExecutor.MAX_CPU_USAGE:
    #                 logger.error(f"[资源拦截] CPU超标：{cpu}% > {SkillExecutor.MAX_CPU_USAGE}%")
    #                 process.kill()
    #                 break
    #             # 内存超限
    #             if mem > SkillExecutor.MAX_MEMORY_USAGE:
    #                 logger.error(f"[资源拦截] 内存超标：{mem:.1f}MB > {SkillExecutor.MAX_MEMORY_USAGE}MB")
    #                 process.kill()
    #                 break
    #             time.sleep(0.2)
    #     except psutil.NoSuchProcess:
    #         pass
    #     except Exception as e:
    #         logger.debug(f"[监控结束] {str(e)}")

    @staticmethod
    def _watch_process(pid: int, kill_flag: Dict[str, bool]):
        try:
            proc = psutil.Process(pid)
            proc.cpu_percent(interval=None)  # 基线

            while proc.is_running() and not kill_flag["checked"]:
                cpu = proc.cpu_percent(interval=0.2)
                mem = proc.memory_info().rss / 1024 / 1024

                if cpu > SkillExecutor.MAX_CPU_USAGE:
                    kill_flag["reason"] = "CPU超限"
                    proc.terminate()  # ✅ 温和终止，让 communicate 返回
                    break
                if mem > SkillExecutor.MAX_MEMORY_USAGE:
                    kill_flag["reason"] = "内存超限"
                    proc.terminate()
                    break

        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.debug(f"[监控异常] {e}")
        finally:
            kill_flag["checked"] = True

    @staticmethod
    def run_script(skill: Skill, script_name: str, args: List[str] = None) -> str:
        args = args or []
        script_path = skill.skill_dir / "scripts" / script_name

        if not script_path.exists():
            return f"❌ 脚本不存在: {script_name}"

        suffix = script_path.suffix.lower()
        tool_map = {".py": "python", ".sh": "bash", ".bat": "cmd"}
        if suffix not in tool_map:
            return f"🚫 不支持的脚本类型: {suffix}"

        required_tool = tool_map[suffix]
        if required_tool not in skill.allowed_tools:
            return f"🔒 权限拦截: 未授权使用 {required_tool}"

        # 构建执行环境
        cwd = skill.skill_dir / "scripts"
        env = os.environ.copy()
        env["AGENT_SANDBOX"] = "1"
        env["PATH"] = os.pathsep.join([str(cwd), env.get("PATH", "")])  # 隔离系统路径


        cmd = {
            ".py": ["python", "-u", str(script_name)] + args,
            ".sh": ["bash", str(script_name)] + args,
            ".bat": ["cmd", "/c", str(script_name)] + args
        }[suffix]



        # Windows隐藏控制台窗口
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        process = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=creation_flags,encoding="utf-8",
        )

        kill_flag = {"checked": False, "reason": ""}
        watcher = threading.Thread(target=SkillExecutor._watch_process, args=(process.pid, kill_flag), daemon=True)
        watcher.start()

        try:
            stdout, stderr = process.communicate(timeout=SkillExecutor.EXEC_TIMEOUT)
        except subprocess.TimeoutExpired:
            kill_flag["reason"] = "执行超时"
            process.kill()  # 超时直接强杀
            stdout, stderr = process.communicate()  # 回收僵尸

        # 等待监控线程优雅退出（最多1秒）
        watcher.join(timeout=1)

        # 统一根据 reason 返回信息
        if kill_flag["reason"]:
            return f"[{kill_flag['reason']}] 脚本已终止"

        # 处理资源拦截导致的非正常退出
        if process.returncode and process.returncode < 0:
            return f"💥 [强制终止] {kill_flag.get('reason', '未知资源异常')}"

        if process.returncode == 0:
            return f"✅ 执行成功:\n{SkillExecutor._truncate(stdout)}"
        else:
            return f"❌ 执行失败:\n{SkillExecutor._truncate(stderr)}"

    # @staticmethod
    # def run_script(skill: Skill, script_name: str, args: List[str] = None) -> str:
    #     args = args or []
    #     # 严格路径隔离：只允许执行当前技能 scripts 目录下的文件
    #     script_path = skill.skill_dir / "scripts" / script_name
    #
    #     # 安全校验1：文件必须存在
    #     if not script_path.exists():
    #         return f"错误：脚本不存在：{script_name}，执行路径：{script_path}"
    #
    #     # 安全校验2：后缀白名单 + 工具权限校验（Anthropic 最小权限原则）
    #     suffix = script_path.suffix.lower()
    #     tool_map = {".py": "python", ".sh": "bash", ".bat": "cmd"}
    #     if suffix not in tool_map:
    #         err = f"[安全拦截] 不支持的脚本类型：{suffix}"
    #         logger.error(err)
    #         return err
    #
    #      # 校验 allowed_tools 权限
    #     required_tool = tool_map[suffix]
    #     if required_tool not in skill.allowed_tools:
    #         err = f"[权限拦截] 技能 {skill.name} 未授权使用工具：{required_tool}"
    #         logger.error(err)
    #         return err
    #
    #     try:
    #         if suffix == ".py":
    #             cmd = ["python", str(script_path)] + args
    #         elif suffix == ".sh":
    #             cmd = ["bash", str(script_path)] + args
    #         elif suffix == ".bat":
    #             cmd = [str(script_path)] + args
    #         else:
    #             return f"不支持的脚本类型：{suffix}"
    #
    #         # 启动子进程（执行你的脚本）
    #         process = subprocess.Popen(
    #             cmd,
    #             encoding="utf-8",
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.PIPE,
    #             text=True
    #         )
    #
    #         # ========== 启动跨平台资源监控 ==========
    #         # 开一个后台线程，专门监控进程的CPU/内存，超标就杀进程
    #         # ✅ 这个线程【只监控、不返回、不影响主流程】
    #         watcher = threading.Thread(
    #             target=SkillExecutor._watch_process,
    #             args=(process.pid,),
    #             daemon=True
    #         )
    #         watcher.start()
    #
    #         # 等待执行 + 超时控制
    #         stdout, stderr = process.communicate(timeout=SkillExecutor.EXEC_TIMEOUT)
    #         watcher.join(timeout=1) # 等监控线程优雅退出
    #
    #         # 返回结果
    #         if process.returncode == 0:
    #             return f"执行成功：\n{stdout}"
    #         else:
    #             return f"执行失败：\n{stderr}"
    #
    #
    #     except subprocess.TimeoutExpired:
    #         err = f"[超时] 脚本执行超过{SkillExecutor.EXEC_TIMEOUT}秒：{script_name}"
    #         logger.error(err)
    #         return err
    #
    #     except Exception as e:
    #         err = f"[执行异常] {str(e)}"
    #         logger.error(err)
    #         return err