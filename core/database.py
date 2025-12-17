"""
数据库连接模块
提供 MySQL 数据库连接
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import mysql.connector


def get_mysql_connection():
    """
    获取 MySQL 数据库连接
    
    Returns:
        mysql.connector.connection: MySQL 连接对象
    """
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci'
    )
