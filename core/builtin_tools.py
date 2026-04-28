"""
内置工具注册中心（常驻、原子能力）
"""
import subprocess
import shlex
from typing import Dict, Any
from core.logger import logger

class BuiltinTool:
    def __init__(self, name: str, description: str, parameters: dict, handler, permission: str = "basic"):
        self.name = name
        self.description = description
        self.parameters = parameters        # JSON Schema 参数定义
        self.handler = handler              # 可调用对象
        self.permission = permission        # basic / admin / system

# 工具注册表（全局单例，启动时初始化）
_registry: Dict[str, BuiltinTool] = {}

def register(tool: BuiltinTool):
    _registry[tool.name] = tool

def get_tool(name: str) -> BuiltinTool:
    return _registry.get(name)

def list_tools() -> Dict[str, BuiltinTool]:
    return _registry.copy()

# ---------- 预置工具 ----------
def terminal_handler(command: str, timeout: int = 30) -> str:
    """安全执行 shell 命令并返回输出（白名单 + 沙箱建议）"""
    # 此处仅示例，实际必须加命令白名单、沙箱、权限确认
    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)

def file_read_handler(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return str(e)

# 注册工具
register(BuiltinTool(
    name="terminal",
    description="执行一条 shell 命令并返回输出，需要 admin 权限",
    parameters={
        "command": {"type": "string", "description": "要执行的命令"}
    },
    handler=terminal_handler,
    permission="admin"
))

register(BuiltinTool(
    name="file_read",
    description="读取指定文件内容",
    parameters={
        "path": {"type": "string", "description": "文件路径（相对于项目根或绝对路径）"}
    },
    handler=file_read_handler,
    permission="basic"
))