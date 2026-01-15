"""
日志配置 - 按天分割日志文件
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "/app/logs"

def setup_logger(name: str = "app") -> logging.Logger:
    """配置日志器，按天分割"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 按天分割，保留30天
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, f"{name}.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 默认 logger
logger = setup_logger()
