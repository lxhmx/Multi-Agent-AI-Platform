"""
数据库 Schema 工具
获取数据库表结构信息
"""

from langchain_core.tools import tool

from common.vanna_instance import get_vanna_instance


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
