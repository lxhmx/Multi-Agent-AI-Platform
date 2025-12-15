"""
LangChain Tools 工具集
将各种工具封装为可被 Agent 调用的模块
"""

from common.tools.text2sql_tool import text2sql_query
from common.tools.schema_tool import get_database_schema
from common.tools.equipment_tool import get_equipment_property

# 导出所有工具列表，供 Agent 使用
ALL_TOOLS = [text2sql_query, get_database_schema, get_equipment_property]
