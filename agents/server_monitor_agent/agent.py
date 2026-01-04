"""
服务器监控智能体
负责监控服务器状态、资源使用情况、告警检测
"""

from typing import AsyncGenerator, Optional, List

from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage

from agents.base import BaseAgent
from agents.server_monitor_agent.prompts import SYSTEM_PROMPT, ROUTING_KEYWORDS
from agents.server_monitor_agent.tools import ALL_TOOLS
from agents.server_monitor_agent.ssh_manager import get_server_list
from core.llm import get_llm
from core.memory import AgentMemory


class ServerMonitorAgent(BaseAgent):
    """
    服务器监控智能体
    
    负责：
    - 监控服务器 CPU、内存、磁盘使用情况
    - 检查系统负载和进程状态
    - 告警检测和通知
    """
    
    name = "server_monitor"
    description = "服务器监控Agent，可以查看服务器状态、资源使用情况、检测告警"
    
    def __init__(self):
        self._agent = None
        self._memory = AgentMemory(max_rounds=10)
    
    def get_tools(self) -> List[BaseTool]:
        """返回服务器监控相关的工具"""
        return ALL_TOOLS
    
    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        server_list = get_server_list()
        return SYSTEM_PROMPT.format(server_list=server_list)
    
    def _get_agent(self):
        """获取或创建 Agent 实例（懒加载）"""
        if self._agent is None:
            from langchain.agents import create_agent
            
            llm = get_llm(streaming=True)
            self._agent = create_agent(
                llm,
                tools=self.get_tools(),
                system_prompt=self.get_system_prompt(),
            )
        return self._agent
    
    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """同步执行智能体"""
        agent = self._get_agent()
        
        messages = self._memory.get_messages(session_id)
        messages.append(HumanMessage(content=question))
        
        result = agent.invoke({"messages": messages})
        
        output = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                output = msg.content
                break
        
        if not output:
            output = "抱歉，我无法处理您的问题。"
        
        self._memory.add_message(session_id, question, output)
        return output
    
    async def run_stream(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式执行智能体"""
        agent = self._get_agent()
        
        messages = self._memory.get_messages(session_id)
        messages.append(HumanMessage(content=question))
        
        full_output = ""
        
        try:
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2"
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, 'content') and chunk.content:
                        full_output += chunk.content
                        yield chunk.content
            
            if not full_output:
                full_output = "抱歉，我无法处理您的问题。"
                yield full_output
            
            self._memory.add_message(session_id, question, full_output)
                
        except Exception as e:
            print(f"[ServerMonitorAgent] 流式处理异常: {e}")
            error_msg = "抱歉，处理您的问题时出现错误。"
            yield error_msg
            self._memory.add_message(session_id, question, error_msg)
    
    def can_handle(self, question: str) -> float:
        """判断是否适合处理该问题"""
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question.lower())
        score = matched / len(ROUTING_KEYWORDS)
        return min(0.3 + score * 2, 1.0)
    
    def clear_memory(self, session_id: str) -> None:
        """清除指定会话的记忆"""
        self._memory.clear(session_id)
