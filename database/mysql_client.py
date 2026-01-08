"""
MySQL 数据库客户端
提供通用的数据库查询功能
"""

import pymysql
from typing import List, Dict, Tuple, Optional, Any
from config import DB_CONFIG


class MySQLClient:
    """MySQL 数据库客户端"""
    
    def __init__(self, db_config: Dict = None):
        """
        初始化 MySQL 客户端
        
        Args:
            db_config: 数据库配置，默认使用 config.py 中的配置
        """
        self.db_config = db_config or DB_CONFIG
        self.conn = None
        self._connect()
    
    def _connect(self):
        """建立数据库连接"""
        self.conn = pymysql.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            user=self.db_config['user'],
            password=self.db_config['password'],
            database=self.db_config['database'],
            charset=self.db_config.get('charset', 'utf8mb4'),
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        执行查询 SQL
        
        Args:
            sql: SQL 语句
            params: 参数元组
        
        Returns:
            List[Dict]: 查询结果列表
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except pymysql.Error as e:
            # 连接断开时重连
            if e.args[0] in (2006, 2013):
                self._connect()
                with self.conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    return cursor.fetchall()
            raise
    
    def execute_query_with_columns(self, sql: str, params: tuple = None) -> Tuple[List[Dict], List[str]]:
        """
        执行查询 SQL 并返回列名
        
        Args:
            sql: SQL 语句
            params: 参数元组
        
        Returns:
            Tuple[List[Dict], List[str]]: (查询结果列表, 列名列表)
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                data = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return data, columns
        except pymysql.Error as e:
            if e.args[0] in (2006, 2013):
                self._connect()
                with self.conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    data = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    return data, columns
            raise
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新 SQL (INSERT/UPDATE/DELETE)
        
        Args:
            sql: SQL 语句
            params: 参数元组
        
        Returns:
            int: 影响的行数
        """
        try:
            with self.conn.cursor() as cursor:
                affected = cursor.execute(sql, params)
                self.conn.commit()
                return affected
        except pymysql.Error as e:
            self.conn.rollback()
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
