"""
SkillExecutor：安全执行 scripts/ 代码（Level 3）
"""
import subprocess
from typing import List

from core.agent_skills.skill import Skill


class SkillExecutor:
    @staticmethod
    def run_script(skill:Skill,script_name:str,args:List[str] = None)->str:
        """安全运行 scripts/ 下的 .py/.sh"""
        args = args or []
        # 提示词里已经家了"scripts"路径,所里拼接处级省略
        script_path = skill.skill_dir / "scripts" / script_name
        if not script_path.exists():
            return f"错误：脚本不存在：{script_name}，执行路径：{script_path}"
        try:
            if script_path.suffix == ".py":
                cmd = ["python", str(script_path)] + args
            elif script_path.suffix == ".sh":
                cmd = ["bash", str(script_path)] + args
            else:
                return f"不支持：{script_path.suffix}"

            result = subprocess.run(
                cmd,
                encoding='utf-8',
                capture_output=True,# 捕获 输出 + 错误
                text=True,# 输出转字符串（不是二进制）
                timeout=30
            )
            return result.stdout if result.returncode == 0 else result.stderr
        except subprocess.TimeoutExpired:
            return "错误:执行超时（30秒）"
        except Exception as e:
            return f"错误：{str(e)}"