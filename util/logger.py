import logging
import sys
import os
from logging.handlers import RotatingFileHandler


def setup_logger(config=None):
    """
    设置logger，支持配置化

    Args:
        config: Config对象，包含日志配置
    """
    logger = logging.getLogger("auto_maker")

    # 如果没有配置，使用默认值
    if config is None:
        # 延迟导入避免循环依赖
        try:
            from config.config import C

            config = C
        except:
            # 如果配置还未加载，使用默认设置
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            return logger

    # 设置日志级别
    log_level = getattr(config, "LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 清除现有handlers（避免重复）
    logger.handlers.clear()

    # 创建formatter
    log_format = getattr(
        config, "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    formatter = logging.Formatter(log_format)

    # 1. 控制台输出
    console_enabled = getattr(config, "LOG_CONSOLE_ENABLED", True)
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_level = getattr(config, "LOG_CONSOLE_LEVEL", "INFO")
        console_handler.setLevel(getattr(logging, console_level, logging.INFO))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 2. 文件输出
    file_enabled = getattr(config, "LOG_FILE_ENABLED", False)
    if file_enabled:
        file_path = getattr(config, "LOG_FILE_PATH", "logs/auto_maker.log")

        # 确保日志目录存在
        log_dir = os.path.dirname(file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        max_bytes = getattr(config, "LOG_FILE_MAX_BYTES", 10485760)
        backup_count = getattr(config, "LOG_FILE_BACKUP_COUNT", 5)

        file_handler = RotatingFileHandler(
            file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_level = getattr(config, "LOG_FILE_LEVEL", "DEBUG")
        file_handler.setLevel(getattr(logging, file_level, logging.DEBUG))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 初始化logger
logger = setup_logger()


def _traceback_and_raise_impl(e):
    """打印堆栈并重新抛出异常"""
    logger.exception(str(e))
    raise e


# 动态绑定方法
logger.traceback_and_raise = _traceback_and_raise_impl


def reload_logger():
    """重新加载logger配置（在Config加载后调用）"""
    global logger
    from config.config import C

    logger = setup_logger(C)
    logger.traceback_and_raise = _traceback_and_raise_impl
    return logger
