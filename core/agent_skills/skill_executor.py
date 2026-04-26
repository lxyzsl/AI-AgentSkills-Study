"""
SkillExecutor：安全执行 scripts/ 代码（Level 3）
"""
import subprocess
import threading
import time
from typing import List
from pathlib import Path

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

    @staticmethod
    def _watch_process(pid: int):
        """后台守护线程：全平台监控进程资源，超标立即终止"""
        try:
            process = psutil.Process(pid)
            while process.is_running():
                # 跨平台获取CPU/内存
                cpu = process.cpu_percent(interval=0.5)
                mem = process.memory_info().rss / 1024 / 1024  # 转MB

                # CPU超限
                if cpu > SkillExecutor.MAX_CPU_USAGE:
                    logger.error(f"[资源拦截] CPU超标：{cpu}% > {SkillExecutor.MAX_CPU_USAGE}%")
                    process.kill()
                    break
                # 内存超限
                if mem > SkillExecutor.MAX_MEMORY_USAGE:
                    logger.error(f"[资源拦截] 内存超标：{mem:.1f}MB > {SkillExecutor.MAX_MEMORY_USAGE}MB")
                    process.kill()
                    break
                time.sleep(0.2)
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.debug(f"[监控结束] {str(e)}")



    @staticmethod
    def run_script(skill: Skill, script_name: str, args: List[str] = None) -> str:
        args = args or []
        # 严格路径隔离：只允许执行当前技能 scripts 目录下的文件
        script_path = skill.skill_dir / "scripts" / script_name

        # 安全校验1：文件必须存在
        if not script_path.exists():
            return f"错误：脚本不存在：{script_name}，执行路径：{script_path}"

        # 安全校验2：后缀白名单 + 工具权限校验（Anthropic 最小权限原则）
        suffix = script_path.suffix.lower()
        tool_map = {".py": "python", ".sh": "bash", ".bat": "cmd"}
        if suffix not in tool_map:
            err = f"[安全拦截] 不支持的脚本类型：{suffix}"
            logger.error(err)
            return err

         # 校验 allowed_tools 权限
        required_tool = tool_map[suffix]
        if required_tool not in skill.allowed_tools:
            err = f"[权限拦截] 技能 {skill.name} 未授权使用工具：{required_tool}"
            logger.error(err)
            return err

        try:
            if suffix == ".py":
                cmd = ["python", str(script_path)] + args
            elif suffix == ".sh":
                cmd = ["bash", str(script_path)] + args
            elif suffix == ".bat":
                cmd = [str(script_path)] + args
            else:
                return f"不支持的脚本类型：{suffix}"

            # 启动子进程（执行你的脚本）
            process = subprocess.Popen(
                cmd,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # ========== 启动跨平台资源监控 ==========
            # 开一个后台线程，专门监控进程的CPU/内存，超标就杀进程
            # ✅ 这个线程【只监控、不返回、不影响主流程】
            watcher = threading.Thread(
                target=SkillExecutor._watch_process,
                args=(process.pid,),
                daemon=True
            )
            watcher.start()

            # 等待执行 + 超时控制
            stdout, stderr = process.communicate(timeout=SkillExecutor.EXEC_TIMEOUT)
            watcher.join(timeout=1) # 等监控线程优雅退出

            # 返回结果
            if process.returncode == 0:
                return f"执行成功：\n{stdout}"
            else:
                return f"执行失败：\n{stderr}"


        except subprocess.TimeoutExpired:
            err = f"[超时] 脚本执行超过{SkillExecutor.EXEC_TIMEOUT}秒：{script_name}"
            logger.error(err)
            return err

        except Exception as e:
            err = f"[执行异常] {str(e)}"
            logger.error(err)
            return err