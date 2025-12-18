"""
数据分析智能体
负责数据库查询、数据分析、统计等任务
"""

from typing import AsyncGenerator, Optional, List

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage

from agents.base import BaseAgent
from agents.data_analyst_agent.prompts import SYSTEM_PROMPT, ROUTING_KEYWORDS
from agents.data_analyst_agent.tools import ALL_TOOLS
from core.llm import get_llm
from core.memory import AgentMemory


class DataAnalystAgent(BaseAgent):
    """
    数据分析智能体
    
    负责：
    - 数据库查询（Text2SQL）
    - 数据统计分析
    - 设备实时数据查询
    """
    
    name = "data_analyst"
    description = "数据分析Agent，可以查询数据库、分析数据、获取设备实时信息"
    
    def __init__(self):
        self._agent = None
        self._memory = AgentMemory(max_rounds=10)
    
    def get_tools(self) -> List[BaseTool]:
        """返回数据分析相关的工具"""
        return ALL_TOOLS
    
    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        return SYSTEM_PROMPT
    
    def _get_agent(self):
        """获取或创建 Agent 实例（懒加载）"""
        if self._agent is None:
            llm = get_llm(streaming=True)
            self._agent = create_agent(
                llm,
                tools=self.get_tools(),
                system_prompt=self.get_system_prompt(),
            )
        return self._agent
    
    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """
        同步执行智能体
        
        Args:
            question: 用户问题
            session_id: 会话 ID
        
        Returns:
            str: 完整回答
        """
        agent = self._get_agent()
        
        # 构建消息列表（包含历史）
        messages = self._memory.get_messages(session_id)
        messages.append(HumanMessage(content=question))
        
        # 调用 Agent
        result = agent.invoke({"messages": messages})
        
        # 提取最后一条 AI 消息
        output = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                output = msg.content
                break
        
        if not output:
            output = "抱歉，我无法处理您的问题。"
        
        # 保存到历史
        self._memory.add_message(session_id, question, output)
        
        return output
    
    async def run_stream(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体
        
        Args:
            question: 用户问题
            session_id: 会话 ID
        
        Yields:
            str: 流式输出的文本片段
        """
        agent = self._get_agent()
        
        # 构建消息列表（包含历史）
        messages = self._memory.get_messages(session_id)
        messages.append(HumanMessage(content=question))
        
        # 收集完整输出用于保存历史
        full_output = ""
        
        try:
            # 使用 astream_events 实现真正的流式输出
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2"
            ):
                # 只处理 LLM 流式输出事件
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if hasattr(chunk, 'content') and chunk.content:
                        full_output += chunk.content
                        yield chunk.content
            
            # 如果没有输出，返回默认消息
            if not full_output:
                full_output = "抱歉，我无法处理您的问题。"
                yield full_output
            
            # 保存到历史
            self._memory.add_message(session_id, question, full_output)
                
        except Exception as e:
            print(f"[DataAnalystAgent] 流式处理异常: {e}")
            error_msg = "抱歉，处理您的问题时出现错误。"
            yield error_msg
            self._memory.add_message(session_id, question, error_msg)
    
    def can_handle(self, question: str) -> float:
        """
        判断是否适合处理该问题
        
        数据相关问题返回高置信度
        
        Args:
            question: 用户问题
        
        Returns:
            float: 0-1 的置信度分数
        """
        # 计算关键词匹配度
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question)
        score = matched / len(ROUTING_KEYWORDS)
        
        # 基础分 0.3，最高 1.0
        return min(0.3 + score * 2, 1.0)
    
    def clear_memory(self, session_id: str) -> None:
        """清除指定会话的记忆"""
        self._memory.clear(session_id)
