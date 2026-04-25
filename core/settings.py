import configparser
import os

SETTINGS_PATH = "config.ini"

config = configparser.ConfigParser()
config.read(SETTINGS_PATH, encoding="utf-8")

# 全局开关
ENABLE_PERF_COUNTER = config.getboolean("settings", "enable_perf_counter", fallback=True)
LOG_LEVEL = config.get("settings", "log_level", fallback="INFO")
