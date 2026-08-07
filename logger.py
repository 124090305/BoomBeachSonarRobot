from __future__ import annotations

import logging

import config


_LOGGING_READY = False


class GuiLogFormatter(logging.Formatter):
    """GUI 日志窗口使用的简洁格式。"""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )


def _normalize_level(
    level: str | int,
) -> int:
    """把配置中的日志等级转换成 logging 使用的整数。"""
    if isinstance(level, int):
        return level

    normalized = level.upper().strip()
    value = logging.getLevelName(normalized)

    if not isinstance(value, int):
        raise ValueError(
            f"不支持的日志等级：{level}"
        )

    return value


def setup_logging(
    level: str | int | None = None,
) -> None:
    """初始化控制台和文件日志。"""
    global _LOGGING_READY

    log_level = _normalize_level(
        level or config.LOG_LEVEL
    )

    root_logger = logging.getLogger()

    if _LOGGING_READY:
        root_logger.setLevel(log_level)

        for handler in root_logger.handlers:
            handler.setLevel(log_level)

        return

    config.ensure_directories()

    root_logger.setLevel(log_level)

    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        console_formatter
    )

    file_handler = logging.FileHandler(
        config.LOG_FILE,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        file_formatter
    )

    root_logger.addHandler(
        console_handler
    )
    root_logger.addHandler(
        file_handler
    )

    _LOGGING_READY = True


def get_logger(
    name: str,
) -> logging.Logger:
    """获取项目 logger。"""
    setup_logging()

    return logging.getLogger(
        name
    )


def attach_log_handler(
    handler: logging.Handler,
    level: str | int | None = None,
) -> None:
    """把额外日志处理器接到项目日志上，例如 GUI。"""
    setup_logging()

    log_level = _normalize_level(
        level or config.LOG_LEVEL
    )

    handler.setLevel(
        log_level
    )

    if handler.formatter is None:
        handler.setFormatter(
            GuiLogFormatter()
        )

    root_logger = logging.getLogger()

    if handler not in root_logger.handlers:
        root_logger.addHandler(
            handler
        )


def detach_log_handler(
    handler: logging.Handler,
) -> None:
    """移除额外日志处理器。"""
    root_logger = logging.getLogger()

    if handler in root_logger.handlers:
        root_logger.removeHandler(
            handler
        )

    handler.close()