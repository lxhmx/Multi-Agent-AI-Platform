"""
Vanna Text2SQL 统一启动入口 (FastAPI 版本)
整合所有 API 路由到一个服务，支持真正的异步流式输出

项目结构：
- api/ask_api_fastapi.py         - 问答接口
- api/data_manage_api_fastapi.py - 数据管理接口
- api/upload_api_fastapi.py      - 上传接口
- api/train_api_fastapi.py       - 训练接口
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入各个模块的路由器
from api.auth_api import router as auth_router
from api.ask_api import router as ask_router
from api.data_manage_api import router as data_manage_router
from api.upload_api import router as upload_router
from api.train_api import router as train_router
from api.session_api import router as session_router
from api.agent_router import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    from api.data_manage_api import init_table
    init_table()
    
    # 预启动 Draw.io MCP 服务器（避免首次请求时延迟）
    mcp_client = None
    try:
        from agents.flowchart_agent.mcp_client import get_mcp_client
        mcp_client = await get_mcp_client()
        if await mcp_client.start():
            response = await mcp_client.initialize()
            if response.success:
                # 预加载工具列表
                await mcp_client.list_tools()
                print(f"[MCP] Draw.io MCP 服务器已启动，发现 {len(mcp_client.tools)} 个工具")
            else:
                print(f"[MCP] MCP 初始化失败: {response.error}")
        else:
            print("[MCP] Draw.io MCP 服务器启动失败")
            print("[MCP] 流程图功能将在首次使用时尝试连接")
    except Exception as e:
        print(f"[MCP] Draw.io MCP 服务器启动失败: {e}")
        print("[MCP] 流程图功能将在首次使用时尝试连接")
    
    print("=" * 60)
    print("Vanna Text2SQL API 服务 (FastAPI)")
    print("=" * 60)
    
    yield
    
    # 关闭时清理 MCP 连接
    try:
        if mcp_client:
            await mcp_client.stop()
            print("[MCP] Draw.io MCP 服务器已关闭")
    except Exception as e:
        print(f"[MCP] 关闭 MCP 服务器时出错: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title="Vanna Text2SQL API",
    description="自然语言查询数据库服务",
    version="2.0.0",
    lifespan=lifespan
)

# 启用 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
app.include_router(auth_router)          # 鉴权接口
app.include_router(ask_router)           # 问答接口（保留向后兼容）
app.include_router(data_manage_router)   # 数据管理接口
app.include_router(upload_router)        # 上传接口
app.include_router(train_router)         # 训练接口
app.include_router(session_router)       # 会话管理接口
app.include_router(agent_router)         # 智能体统一入口（新）


# ==================== 健康检查 ====================

@app.get("/api/health", tags=["其他"])
async def health():
    """健康检查"""
    return {"status": "ok", "service": "vanna-api-fastapi"}


# ==================== 启动入口 ====================

if __name__ == '__main__':
    print("\n可用接口:")
    print("  训练接口:")
    print("    POST /api/train-sql         - 训练 SQL 文件")
    print("    POST /api/train-document    - 训练文档文件")
    print("    POST /api/train-manual      - 手动输入训练")
    print("    POST /api/upload            - 上传训练文件")
    print("\n  数据管理接口:")
    print("    GET  /api/data-manage/stats    - 获取统计数据")
    print("    GET  /api/data-manage/activity - 获取活跃度")
    print("    GET  /api/data-manage/files    - 获取文件列表")
    print("    DELETE /api/data-manage/files  - 删除文件记录")
    print("\n  查询接口:")
    print("    POST /api/query             - 自然语言查询")
    print("    POST /api/query-stream      - 流式查询")
    print("    POST /api/query-agent       - Agent 模式查询（真正流式）")
    print("\n  智能体接口（新）:")
    print("    POST /api/agent/chat        - 智能体对话（支持自动路由）")
    print("    GET  /api/agent/list        - 列出所有智能体")
    print("\n  其他:")
    print("    GET  /api/health            - 健康检查")
    print("\n" + "=" * 60)
    
    uvicorn.run(app, host='0.0.0.0', port=5000)
