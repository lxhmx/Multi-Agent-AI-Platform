"""
智能体统一路由 API
提供统一的智能体调用入口，支持自动路由和指定智能体
"""

import json
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import AgentRegistry
from common.dependencies import get_current_user

router = APIRouter(prefix="/api/agent", tags=["智能体"])


class AgentRequest(BaseModel):
    """智能体请求模型"""
    question: str
    session_id: Optional[str] = None
    agent_name: Optional[str] = None  # 可选指定智能体，不指定则自动路由


class AgentInfo(BaseModel):
    """智能体信息模型"""
    name: str
    description: str


@router.post("/chat")
async def chat_with_agent(req: AgentRequest, user=Depends(get_current_user)):
    """
    与智能体对话（流式输出）
    
    - 如果指定 agent_name，则使用指定的智能体
    - 如果不指定，则根据问题自动路由到最合适的智能体
    """
    question = req.question.strip()
    
    if not question:
        async def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    # 获取智能体
    if req.agent_name:
        agent = AgentRegistry.get(req.agent_name)
        if not agent:
            raise HTTPException(
                status_code=404, 
                detail=f"智能体 '{req.agent_name}' 不存在"
            )
    else:
        agent = AgentRegistry.route(question)
    
    async def generate():
        try:
            print(f"\n[Agent Router] 用户问题: {question}")
            print(f"[Agent Router] 使用智能体: {agent.name}")
            print(f"[Agent Router] Session ID: {req.session_id}")
            
            # 流式输出
            async for chunk in agent.run_stream(question, req.session_id):
                yield f"event: answer\ndata: {chunk}\n\n"
            
            # 发送完成信号
            done_data = json.dumps({
                'success': True,
                'agent': agent.name,
                'user_id': user["id"]
            })
            yield f"event: done\ndata: {done_data}\n\n"
            
        except Exception as e:
            print(f"[Agent Router] 异常: {traceback.format_exc()}")
            error_data = json.dumps({
                'message': '处理您的问题时出现错误，请稍后重试。'
            }, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@router.get("/list")
async def list_agents(user=Depends(get_current_user)):
    """
    列出所有可用的智能体
    """
    agents = AgentRegistry.get_all()
    return {
        "agents": [
            AgentInfo(name=a.name, description=a.description)
            for a in agents.values()
        ]
    }


@router.post("/clear-memory")
async def clear_agent_memory(
    agent_name: str,
    session_id: str,
    user=Depends(get_current_user)
):
    """
    清除指定智能体的会话记忆
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"智能体 '{agent_name}' 不存在"
        )
    
    agent.clear_memory(session_id)
    return {"success": True, "message": f"已清除 {agent_name} 的会话记忆"}
