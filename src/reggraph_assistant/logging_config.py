"""统一日志配置

提供结构化日志支持，便于生产环境调试和监控
"""
import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    format_json: bool = False,
) -> None:
    """配置应用日志

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: 日志文件路径（可选）
        format_json: 是否使用JSON格式（生产环境推荐）
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 日志格式
    if format_json:
        # 生产环境：结构化JSON格式
        log_format = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    else:
        # 开发环境：可读格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True,
    )

    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """获取logger实例

    Args:
        name: logger名称（通常使用 __name__）

    Returns:
        配置好的logger实例
    """
    return logging.getLogger(name)
