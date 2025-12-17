"""
数据分析智能体的工具集
"""

from agents.data_analyst_agent.tools.text2sql_tool import text2sql_query
from agents.data_analyst_agent.tools.schema_tool import get_database_schema
from agents.data_analyst_agent.tools.equipment_tool import get_equipment_property

# 导出所有工具列表
ALL_TOOLS = [text2sql_query, get_database_schema, get_equipment_property]

__all__ = ["ALL_TOOLS", "text2sql_query", "get_database_schema", "get_equipment_property"]
