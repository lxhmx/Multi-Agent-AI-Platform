"""
知识库检索工具
从 Vanna 训练的文档中检索相关知识
"""

from langchain_core.tools import tool
from common.vanna_instance import get_vanna_instance


@tool
def search_knowledge(query: str) -> dict:
    """
    从知识库中搜索相关文档内容。
    
    这个工具会：
    1. 在已训练的文档知识库中进行语义搜索
    2. 返回与问题最相关的文档片段
    
    适用场景：
    - 用户询问业务知识、流程说明、视频总结等非数据库查询问题
    - 需要查找之前上传的文档内容
    - 回答关于特定主题的知识性问题
    
    Args:
        query: 用户的问题或搜索关键词
    
    Returns:
        dict: 包含搜索结果的字典，包括：
            - success: 是否成功
            - documents: 相关文档列表
            - count: 找到的文档数量
            - error: 错误信息（如果失败）
    """
    try:
        vn = get_vanna_instance()
        
        # 使用 Vanna 的文档检索功能
        # ChromaDB_VectorStore 提供了 get_related_documentation 方法
        related_docs = vn.get_related_documentation(query)
        
        if not related_docs:
            return {
                "success": True,
                "documents": [],
                "count": 0,
                "message": "未找到相关文档，知识库中可能没有相关内容"
            }
        
        # 处理返回结果
        documents = []
        for doc in related_docs:
            if isinstance(doc, str):
                documents.append(doc)
            elif isinstance(doc, dict):
                content = doc.get('content', doc.get('document', str(doc)))
                documents.append(content)
            else:
                documents.append(str(doc))
        
        return {
            "success": True,
            "documents": documents,
            "count": len(documents)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"知识库检索出错: {str(e)}",
            "documents": [],
            "count": 0
        }
