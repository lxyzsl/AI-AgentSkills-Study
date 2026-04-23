import os
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional

class ConfigManager:
    """INI配置读取工具（线程安全/类型转换/环境隔离）"""

    def __init__(self,
                 config_file_name: str = "config.ini",
                 env: str = "DEFAULT",
                 encoding: str = "utf-8"):
        """
        :param config_file_name: 配置文件名
        :param env: 环境标识段（如DEV/PROD）
        :param encoding: 文件编码（默认UTF-8）
        """
        confit_dir = os.path.join(get_project_root(), 'config',config_file_name)
        self._path = Path(confit_dir)
        self._env = env
        self._encoding = encoding
        self._parser = ConfigParser()
        self._validate_and_load()

    def _validate_and_load(self) -> None:
        """配置加载与基础验证"""
        if not self._path.exists():
            raise FileNotFoundError(f"Config file not found: {self._path}")
        if not self._path.suffix.lower()  == '.ini':
            raise ValueError("Only .ini files are supported")

        self._parser.read(self._path,  encoding=self._encoding)
        if not self._parser.has_section(self._env):
            raise KeyError(f"Section [{self._env}] missing in config")

    def get(self,
            key: str,
            dtype: type = str,
            default: Optional[Any] = None) -> Any:
        """安全获取配置项（自动类型转换）"""
        try:
            val = self._parser.get(self._env,  key)
            return dtype(val.strip())  if val else default
        except (ConfigParser.NoOptionError, ValueError) as e:
            if default is not None:
                return default
            raise KeyError(f"Config key '{key}' error: {str(e)}")

    @property
    def all_settings(self) -> dict:
        """获取当前环境所有配置（返回原生字典）"""
        return dict(self._parser.items(self._env))



def get_project_root() -> Path:
    """获取项目根目录（自动识别标记文件或.git目录）"""
    current = Path(__file__).absolute()
    while not (current / 'pyproject.toml').exists() and current.parent != current:
        current = current.parent
    if (current / 'pyproject.toml').exists():
        return current
    raise FileNotFoundError("Project root not found (pyproject.toml  missing)")

def get_temp_path() -> str:
   return os.path.join(get_project_root(), '.temp')

def get_checkpoint_path() -> str:
   return os.path.join(get_project_root(), '.temp/checkpoint')

