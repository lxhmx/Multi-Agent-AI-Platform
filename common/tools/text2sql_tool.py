"""
Text2SQL 工具
将用户自然语言问题转换为 SQL 并执行查询
"""

import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

import pandas as pd
import mysql.connector
from langchain_core.tools import tool

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
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
        
        # 1. 生成 SQL（允许 LLM 查看数据以生成更准确的 SQL）
        sql = vn.generate_sql(question, allow_llm_to_see_data=True)
        
        if not sql or not sql.strip():
            return {
                "success": False,
                "error": "无法根据问题生成 SQL，可能是问题描述不够清晰或数据库中没有相关表"
            }
        
        # 清理 SQL：移除 intermediate_sql 等前缀和注释
        sql_clean = sql.strip()
        
        # 移除注释行和 intermediate_sql 标记
        lines = sql_clean.split('\n')
        sql_lines = []
        for line in lines:
            stripped = line.strip().lower()
            # 跳过注释行
            if stripped.startswith('--') or stripped.startswith('#'):
                continue
            # 跳过 intermediate_sql 标记行
            if stripped == 'intermediate_sql':
                continue
            sql_lines.append(line)
        sql_clean = '\n'.join(sql_lines).strip()
        
        sql_upper = sql_clean.upper()
        if not sql_upper.startswith('SELECT'):
            return {
                "success": False,
                "error": "只支持查询操作，不支持数据修改"
            }
        
        # 2. 执行 SQL
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql_clean)
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
            "sql": sql_clean,
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
