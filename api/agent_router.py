"""
智能体统一路由 API
提供统一的智能体调用入口，支持自动路由和指定智能体

SSE Event Types:
- answer: 文本回答片段
- flowchart: 流程图数据 (包含 svg_content, diagram_id, title)
- done: 完成信号 (包含 success: bool, message: str, agent: str, user_id: int)
- error: 错误信息 (包含 message: str)

前端处理示例:
```javascript
eventSource.addEventListener('done', (event) => {
    const data = JSON.parse(event.data);
    if (data.success) {
        // 任务成功
        showNotification('success', data.message || '任务执行完成');
    } else {
        // 任务失败
        showNotification('error', data.message || '任务执行失败');
    }
});

eventSource.addEventListener('error', (event) => {
    const data = JSON.parse(event.data);
    showNotification('error', data.message);
});
```
"""

import json
import traceback
import base64
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import AgentRegistry
from common.dependencies import get_current_user

router = APIRouter(prefix="/api/agent", tags=["智能体"])


def _encode_flowchart_data(svg_content: str, diagram_id: str, title: str) -> str:
    """
    编码流程图数据为 Base64 格式（支持 UTF-8 中文）
    
    Args:
        svg_content: SVG 内容
        diagram_id: 图表 ID
        title: 图表标题
    
    Returns:
        str: Base64 编码的 JSON 字符串
    """
    data = {
        "svg_content": svg_content,
        "diagram_id": diagram_id,
        "title": title
    }
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.b64encode(json_str.encode('utf-8')).decode('ascii')


def _extract_flowchart_from_response(text: str) -> Optional[dict]:
    """
    从响应文本中提取流程图数据
    
    检测响应中是否包含流程图工具调用结果，
    如果包含则提取 svg_content, diagram_id, title
    
    Args:
        text: 响应文本
    
    Returns:
        dict: 流程图数据，如果没有则返回 None
    """
    # 检查是否包含流程图相关的 JSON 数据
    # 工具返回的格式通常包含 svg_content 字段
    try:
        # 尝试查找 JSON 格式的流程图数据
        # 模式1: 直接的 JSON 对象
        json_pattern = r'\{[^{}]*"svg_content"[^{}]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if data.get("svg_content") and data.get("success", True):
                    return {
                        "svg_content": data.get("svg_content", ""),
                        "diagram_id": data.get("diagram_id", ""),
                        "title": data.get("title", "")
                    }
            except json.JSONDecodeError:
                continue
        
        return None
    except Exception:
        return None


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
    
    # 调试日志：打印接收到的参数
    print(f"\n[Agent Router] 接收请求:")
    print(f"  - question: {question}")
    print(f"  - agent_name: {req.agent_name} (type: {type(req.agent_name)})")
    print(f"  - session_id: {req.session_id}")
    
    if not question:
        async def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    # 获取智能体
    if req.agent_name:
        print(f"[Agent Router] 使用指定智能体: {req.agent_name}")
        agent = AgentRegistry.get(req.agent_name)
        if not agent:
            raise HTTPException(
                status_code=404, 
                detail=f"智能体 '{req.agent_name}' 不存在"
            )
    else:
        print(f"[Agent Router] 自动路由...")
        agent = AgentRegistry.route(question)
        print(f"[Agent Router] 路由结果: {agent.name}")
    
    async def generate():
        try:
            print(f"\n[Agent Router] 用户问题: {question}")
            print(f"[Agent Router] 使用智能体: {agent.name}")
            print(f"[Agent Router] Session ID: {req.session_id}")
            
            # 收集完整响应用于检测流程图数据
            full_response = ""
            flowchart_sent = False
            
            # 流式输出
            async for chunk in agent.run_stream(question, req.session_id):
                full_response += chunk
                # SSE data 字段不能包含换行符，需要对每行单独发送或编码
                # 方案：将包含换行的内容用 Base64 编码
                if '\n' in chunk:
                    encoded_chunk = base64.b64encode(chunk.encode('utf-8')).decode('ascii')
                    yield f"event: answer_base64\ndata: {encoded_chunk}\n\n"
                else:
                    yield f"event: answer\ndata: {chunk}\n\n"
                
                # 检查是否有流程图数据（在流式过程中检测）
                if not flowchart_sent and agent.name == "flowchart":
                    flowchart_data = _extract_flowchart_from_response(full_response)
                    if flowchart_data and flowchart_data.get("svg_content"):
                        # 发送流程图事件
                        encoded_data = _encode_flowchart_data(
                            flowchart_data["svg_content"],
                            flowchart_data["diagram_id"],
                            flowchart_data["title"]
                        )
                        yield f"event: flowchart\ndata: {encoded_data}\n\n"
                        flowchart_sent = True
                        print(f"[Agent Router] 发送流程图数据: diagram_id={flowchart_data['diagram_id']}")
            
            # 发送完成信号
            done_data = json.dumps({
                'success': True,
                'agent': agent.name,
                'user_id': user["id"]
            }, ensure_ascii=False)
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
