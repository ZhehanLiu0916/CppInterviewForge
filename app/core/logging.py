import sys
import logging
from pathlib import Path

from loguru import logger

# 移除默认sink
logger.remove()

# 控制台输出
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# 文件输出
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger.add(
    log_dir / "app.log",
    rotation="50 MB",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)


def setup_logging():
    """初始化日志（兼容FastAPI）。"""
    import logging as standard_logging

    class InterceptHandler(standard_logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = standard_logging.currentframe(), 2
            while frame and frame.f_code.co_filename == standard_logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    standard_logging.basicConfig(handlers=[InterceptHandler()], level=0)
    return logger
