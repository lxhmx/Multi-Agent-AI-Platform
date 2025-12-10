"""
MySQL 数据库连接模块
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_CONFIG
import mysql.connector


def get_mysql_connection():
    """获取 MySQL 数据库连接"""
    host_port = DB_CONFIG['host'].split(':')
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 3306
    
    return mysql.connector.connect(
        host=host,
        port=port,
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset=DB_CONFIG['charset']
    )
