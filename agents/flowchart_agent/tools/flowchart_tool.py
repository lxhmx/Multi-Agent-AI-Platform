"""
流程图工具 - 从 MCP Server 动态生成 LangChain Tools

自动发现 MCP 服务器提供的工具，并生成对应的 LangChain Tool。
无需手动维护工具定义，MCP 服务端新增工具后自动可用。

Requirements: 1.2, 4.2, 6.1
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import Field, create_model

from agents.flowchart_agent.mcp_client import MCPTool, get_mcp_client_sync

logger = logging.getLogger(__name__)

# 缓存已生成的工具
_cached_tools: Optional[List[BaseTool]] = None


def _json_schema_to_pydantic_field(name: str, schema: Dict[str, Any], required: bool) -> tuple:
    """将 JSON Schema 字段转换为 Pydantic Field"""
    json_type = schema.get("type", "string")
    description = schema.get("description", "")
    default_value = schema.get("default")
    
    if isinstance(json_type, list):
        json_type = next((t for t in json_type if t != "null"), "string")
    
    type_map = {
        "string": str, "integer": int, "number": float,
        "boolean": bool, "array": list, "object": dict,
    }
    py_type = type_map.get(json_type, str)
    
    if required:
        return (py_type, Field(..., description=description))
    if default_value is None:
        return (Optional[py_type], Field(default=None, description=description))
    if isinstance(default_value, (list, dict)) and not default_value:
        factory = list if isinstance(default_value, list) else dict
        return (py_type, Field(default_factory=factory, description=description))
    return (py_type, Field(default=default_value, description=description))


def _create_input_model(tool_name: str, input_schema: Dict[str, Any]) -> type:
    """根据 MCP 工具的 inputSchema 创建 Pydantic 模型"""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    
    if not properties:
        return create_model(f"{tool_name}Input")
    
    fields = {}
    for prop_name, prop_schema in properties.items():
        try:
            fields[prop_name] = _json_schema_to_pydantic_field(
                prop_name, prop_schema, prop_name in required
            )
        except Exception:
            fields[prop_name] = (Optional[str], Field(default=None, description=""))
    
    return create_model(f"{tool_name}Input", **fields)


def _create_tool_func(mcp_tool: MCPTool) -> Callable:
    """为 MCP 工具创建调用函数"""
    tool_name = mcp_tool.name
    
    def tool_func(**kwargs) -> Dict[str, Any]:
        """动态生成的 MCP 工具调用函数"""
        try:
            # 获取全局 MCP 客户端单例（app.py 启动时已初始化）
            client = get_mcp_client_sync()
            if client is None:
                return {
                    "success": False,
                    "error": "MCP 客户端未初始化",
                    "message": "请确保应用已正确启动"
                }
            
            # 使用同步方法调用工具
            result = client.call_tool_sync(tool_name, kwargs)
            
            if result.success:
                return {
                    "success": True,
                    "data": result.data,
                    "message": f"工具 {tool_name} 执行成功"
                }
            return {
                "success": False,
                "error": result.error,
                "message": f"工具 {tool_name} 执行失败"
            }
        except Exception as e:
            logger.error(f"[MCPTool] {tool_name} 调用异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"工具 {tool_name} 调用异常"
            }
    
    return tool_func


def _mcp_tool_to_langchain(mcp_tool: MCPTool) -> BaseTool:
    """将 MCP 工具转换为 LangChain Tool"""
    input_model = _create_input_model(mcp_tool.name, mcp_tool.input_schema)
    func = _create_tool_func(mcp_tool)
    tool_name = mcp_tool.name.replace("-", "_")
    
    return StructuredTool.from_function(
        func=func,
        name=tool_name,
        description=mcp_tool.description or f"MCP 工具: {mcp_tool.name}",
        args_schema=input_model,
        return_direct=False
    )


def discover_and_create_tools() -> List[BaseTool]:
    """发现 MCP 工具并创建对应的 LangChain Tools"""
    global _cached_tools
    
    if _cached_tools is not None:
        return _cached_tools
    
    tools = []
    
    try:
        # 获取全局 MCP 客户端（app.py 启动时已初始化并加载工具列表）
        client = get_mcp_client_sync()
        if client is None:
            logger.error("[MCPTool] MCP 客户端未初始化")
            return tools
        
        mcp_tools = client.tools or []
        
        for mcp_tool in mcp_tools:
            try:
                lc_tool = _mcp_tool_to_langchain(mcp_tool)
                tools.append(lc_tool)
                logger.info(f"[MCPTool] 已创建工具: {lc_tool.name}")
            except Exception as e:
                logger.warning(f"[MCPTool] 创建工具 {mcp_tool.name} 失败: {e}")
        
        logger.info(f"[MCPTool] 共发现并创建 {len(tools)} 个工具")
        _cached_tools = tools
        
    except Exception as e:
        logger.error(f"[MCPTool] 工具发现异常: {e}")
    
    return tools


def get_tools() -> List[BaseTool]:
    """获取所有可用的流程图工具"""
    return discover_and_create_tools()


def refresh_tools() -> List[BaseTool]:
    """刷新工具列表（清除缓存并重新发现）"""
    global _cached_tools
    _cached_tools = None
    return discover_and_create_tools()


def cleanup():
    """清理 MCP 连接（由 app.py 调用）"""
    pass  # MCP 客户端由 app.py 管理
