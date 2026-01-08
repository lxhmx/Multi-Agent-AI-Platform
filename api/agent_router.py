"""
智能体统一路由 API
提供统一的智能体调用入口，支持自动路由和指定智能体

SSE Event Types:
- answer: 文本回答片段
- answer_base64: Base64 编码的文本（包含换行符时使用）
- image: Base64 编码的图片数据
- image_meta: 图片元信息 JSON (包含 diagram_id, title, format, xml)
- done: 完成信号 (包含 success: bool, message: str, agent: str, user_id: int)
- error: 错误信息 (包含 message: str)

前端处理示例:
```javascript
eventSource.addEventListener('image', (event) => {
    const imageBase64 = event.data;
    const imgSrc = `data:image/png;base64,${imageBase64}`;
    // 显示图片
});

eventSource.addEventListener('image_meta', (event) => {
    const meta = JSON.parse(atob(event.data));
    // meta.diagram_id, meta.title, meta.format, meta.xml
});
```
"""

import json
import traceback
import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import AgentRegistry
from common.dependencies import get_current_user

router = APIRouter(prefix="/api/agent", tags=["智能体"])


def _encode_image_meta(meta: dict) -> str:
    """
    编码图片元信息为 Base64 格式
    """
    json_str = json.dumps(meta, ensure_ascii=False)
    return base64.b64encode(json_str.encode('utf-8')).decode('ascii')


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
            
            # 收集完整响应
            full_response = ""
            # 用于累积可能被分割的特殊标记
            buffer = ""
            
            # 流式输出
            async for chunk in agent.run_stream(question, req.session_id):
                # 累积到 buffer
                buffer += chunk
                
                # 检查是否是图片数据
                if buffer.startswith("[IMAGE:") and buffer.endswith("]"):
                    # 提取图片 Base64 数据
                    image_base64 = buffer[7:-1]
                    yield f"event: image\ndata: {image_base64}\n\n"
                    print(f"[Agent Router] 发送图片数据，大小: {len(image_base64)} chars")
                    buffer = ""
                    continue
                
                # 检查是否是图片元信息
                if buffer.startswith("[IMAGE_META:") and buffer.endswith("]"):
                    # 提取元信息 JSON
                    meta_json = buffer[12:-1]
                    encoded_meta = base64.b64encode(meta_json.encode('utf-8')).decode('ascii')
                    yield f"event: image_meta\ndata: {encoded_meta}\n\n"
                    print(f"[Agent Router] 发送图片元信息")
                    buffer = ""
                    continue
                
                # 检查是否包含完整的图表数据
                if "[CHART:" in buffer and buffer.count("[CHART:") == buffer.count("]") - buffer.count("\\]"):
                    # 找到完整的 [CHART:...] 标记
                    start_idx = buffer.find("[CHART:")
                    # 找到匹配的结束 ]
                    depth = 0
                    end_idx = -1
                    for i in range(start_idx + 7, len(buffer)):
                        if buffer[i] == '{':
                            depth += 1
                        elif buffer[i] == '}':
                            depth -= 1
                        elif buffer[i] == ']' and depth == 0:
                            end_idx = i
                            break
                    
                    if end_idx > start_idx:
                        # 发送图表前的文本
                        before_chart = buffer[:start_idx]
                        if before_chart.strip():
                            full_response += before_chart
                            if '\n' in before_chart:
                                encoded_chunk = base64.b64encode(before_chart.encode('utf-8')).decode('ascii')
                                yield f"event: answer_base64\ndata: {encoded_chunk}\n\n"
                            else:
                                yield f"event: answer\ndata: {before_chart}\n\n"
                        
                        # 提取并发送图表数据
                        chart_json = buffer[start_idx + 7:end_idx]
                        encoded_chart = base64.b64encode(chart_json.encode('utf-8')).decode('ascii')
                        yield f"event: chart\ndata: {encoded_chart}\n\n"
                        print(f"[Agent Router] 发送图表数据，大小: {len(chart_json)} chars")
                        
                        # 处理图表后的文本
                        buffer = buffer[end_idx + 1:]
                        continue
                
                # 如果 buffer 开始看起来像特殊标记，继续累积
                if buffer.startswith("[IMAGE") or buffer.startswith("[CHART") or buffer.startswith("["):
                    if len(buffer) < 50000:  # 防止无限累积
                        continue
                
                # 正常文本，直接输出
                full_response += buffer
                
                # SSE data 字段不能包含换行符
                if '\n' in buffer:
                    encoded_chunk = base64.b64encode(buffer.encode('utf-8')).decode('ascii')
                    yield f"event: answer_base64\ndata: {encoded_chunk}\n\n"
                else:
                    yield f"event: answer\ndata: {buffer}\n\n"
                
                buffer = ""
            
            # 处理剩余的 buffer
            if buffer:
                # 最后检查一次是否是图表数据
                if "[CHART:" in buffer:
                    start_idx = buffer.find("[CHART:")
                    end_idx = buffer.rfind("]")
                    if end_idx > start_idx:
                        before_chart = buffer[:start_idx]
                        if before_chart.strip():
                            full_response += before_chart
                            encoded_chunk = base64.b64encode(before_chart.encode('utf-8')).decode('ascii')
                            yield f"event: answer_base64\ndata: {encoded_chunk}\n\n"
                        
                        chart_json = buffer[start_idx + 7:end_idx]
                        encoded_chart = base64.b64encode(chart_json.encode('utf-8')).decode('ascii')
                        yield f"event: chart\ndata: {encoded_chart}\n\n"
                        print(f"[Agent Router] 发送图表数据（最终）")
                        
                        after_chart = buffer[end_idx + 1:]
                        if after_chart.strip():
                            full_response += after_chart
                            encoded_chunk = base64.b64encode(after_chart.encode('utf-8')).decode('ascii')
                            yield f"event: answer_base64\ndata: {encoded_chunk}\n\n"
                else:
                    full_response += buffer
                    if '\n' in buffer:
                        encoded_chunk = base64.b64encode(buffer.encode('utf-8')).decode('ascii')
                        yield f"event: answer_base64\ndata: {encoded_chunk}\n\n"
                    else:
                        yield f"event: answer\ndata: {buffer}\n\n"
            
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
