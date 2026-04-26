import logging
import sys
import os
import time
from logging.handlers import RotatingFileHandler
from datetime import datetime

from core.config_manager import get_project_root
from core.settings import ENABLE_PERF_COUNTER, LOG_LEVEL

# 颜色
class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    green = "\x1b[32;1m"
    reset = "\x1b[0m"
    fmt = "%(asctime)s | %(levelname)-7s | %(message)s"

    FORMATS = {
        logging.DEBUG: grey + fmt + reset,
        logging.INFO: green + fmt + reset,
        logging.WARNING: yellow + fmt + reset,
        logging.ERROR: red + fmt + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

class FileFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

def get_logger(name="agent"):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.handlers.clear()

    # 控制台
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(ColorFormatter())

    # 文件
    if not os.path.exists("logs"):
        os.makedirs("logs")

    fh = RotatingFileHandler(
        f"{get_project_root()}/logs/agent-{datetime.now().strftime('%Y%m%d')}.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8"
    )
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(FileFormatter())

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

logger = get_logger()

# ======================
# 耗时统计工具
# ======================
def timer(name="任务"):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not ENABLE_PERF_COUNTER:
                return func(*args, **kwargs)

            start = time.time()
            logger.info(f"【耗时】开始 → {name}")
            try:
                return func(*args, **kwargs)
            finally:
                cost = round((time.time() - start) * 1000, 2)
                logger.info(f"【耗时】结束 → {name} | 耗时 {cost} ms")
        return wrapper
    return decorator