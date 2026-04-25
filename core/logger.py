import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 日志颜色（控制台）
class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[32;1m"
    reset = "\x1b[0m"
    format_str = "%(asctime)s | %(levelname)-7s | %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# 文件格式（不带颜色）
class FileFormatter(logging.Formatter):
    format_str = "%(asctime)s | %(levelname)-7s | %(message)s"
    def __init__(self):
        super().__init__(self.format_str, datefmt="%Y-%m-%d %H:%M:%S")

# 获取日志
def get_logger(name="agent"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # 避免重复

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColorFormatter())

    # 文件输出
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    file_handler = RotatingFileHandler(
        f"logs/agent-{datetime.now().strftime('%Y%m%d')}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FileFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

# 全局单例日志
logger = get_logger()