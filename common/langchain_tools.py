"""
LangChain Tools 定义
将 Vanna Text2SQL 和数据库查询封装为可被 Agent 调用的工具
"""

import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

import pandas as pd
import mysql.connector
from langchain_core.tools import tool

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance
from common.conn_mysql import get_mysql_connection


def convert_value(obj):
    """处理数据库返回值中的特殊类型"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    return obj


@tool
def text2sql_query(question: str) -> dict:
    """
    根据用户的自然语言问题查询数据库。
    
    这个工具会：
    1. 将用户问题转换为 SQL 语句
    2. 执行 SQL 查询
    3. 返回查询结果摘要
    
    适用场景：
    - 用户询问数据相关问题，如"查询所有设备"、"统计数量"、"查找某条记录"等
    - 需要从数据库获取信息来回答用户问题
    
    Args:
        question: 用户的自然语言问题
    
    Returns:
        dict: 包含查询结果的字典，包括：
            - success: 是否成功
            - sql: 生成的 SQL 语句
            - row_count: 结果行数
            - columns: 列名列表
            - data_preview: 数据预览（前 10 行的 markdown 表格）
            - error: 错误信息（如果失败）
    """
    try:
        vn = get_vanna_instance()
        
        # 1. 生成 SQL
        sql = vn.generate_sql(question)
        
        if not sql or not sql.strip():
            return {
                "success": False,
                "error": "无法根据问题生成 SQL，可能是问题描述不够清晰或数据库中没有相关表"
            }
        
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith('SELECT'):
            return {
                "success": False,
                "error": "只支持查询操作，不支持数据修改"
            }
        
        # 2. 执行 SQL
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 3. 处理结果
        converted_results = []
        for row in results:
            converted_row = {k: convert_value(v) for k, v in row.items()}
            converted_results.append(converted_row)
        
        df = pd.DataFrame(converted_results) if converted_results else pd.DataFrame()
        
        # 4. 生成数据预览
        row_count = len(df)
        columns = list(df.columns) if not df.empty else []
        
        if df.empty:
            data_preview = "查询结果为空"
        elif row_count <= 10:
            data_preview = df.to_markdown(index=False)
        else:
            data_preview = df.head(10).to_markdown(index=False)
            data_preview += f"\n\n... 共 {row_count} 条记录"
        
        return {
            "success": True,
            "sql": sql,
            "row_count": row_count,
            "columns": columns,
            "data_preview": data_preview
        }
        
    except mysql.connector.Error as db_error:
        return {
            "success": False,
            "error": f"数据库查询错误: {str(db_error)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"执行出错: {str(e)}"
        }


@tool
def get_database_schema() -> str:
    """
    获取数据库的表结构信息。
    
    当用户询问"有哪些表"、"数据库结构是什么"等问题时使用。
    
    Returns:
        str: 数据库表结构的描述
    """
    try:
        vn = get_vanna_instance()
        # 获取训练过的 DDL 信息
        training_data = vn.get_training_data()
        
        ddl_list = [item for item in training_data if item.get('training_data_type') == 'ddl']
        
        if not ddl_list:
            return "暂无数据库结构信息，请先进行知识训练。"
        
        schema_info = "数据库包含以下表：\n\n"
        for item in ddl_list[:10]:  # 最多显示 10 个
            schema_info += f"```sql\n{item.get('content', '')}\n```\n\n"
        
        return schema_info
        
    except Exception as e:
        return f"获取数据库结构失败: {str(e)}"


# 导出所有工具列表，供 Agent 使用
ALL_TOOLS = [text2sql_query, get_database_schema]
