"""
流程图智能体的工具集

从 MCP Server 动态发现并生成 LangChain Tools。
无需手动维护工具定义，MCP 服务端新增工具后自动可用。
"""

from agents.flowchart_agent.tools.flowchart_tool import (
    get_tools,
    refresh_tools,
    cleanup,
    discover_and_create_tools,
)


def get_all_tools():
    """
    获取所有可用的流程图工具（懒加载）
    
    Returns:
        List[BaseTool]: LangChain 工具列表
    """
    return get_tools()


# 为了兼容现有代码，提供 ALL_TOOLS
# 注意：这是一个函数调用，会触发 MCP 工具发现
ALL_TOOLS = property(lambda self: get_tools())


__all__ = [
    "get_tools",
    "get_all_tools", 
    "refresh_tools",
    "cleanup",
    "discover_and_create_tools",
]
