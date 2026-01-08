"""
动态可视化图表智能体
负责数据查询并生成可视化图表
"""

from typing import AsyncGenerator, Optional, List

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage

from agents.base import BaseAgent
from agents.chart_agent.prompts import SYSTEM_PROMPT, ROUTING_KEYWORDS
from agents.chart_agent.tools import ALL_TOOLS
from core.llm import get_llm
from core.memory import AgentMemory


class ChartAgent(BaseAgent):
    """
    动态可视化图表智能体
    
    负责：
    - 理解用户数据查询需求
    - 生成 SQL 并执行查询
    - 选择合适的图表类型
    - 返回可视化图表数据
    """
    
    name = "chart_agent"
    description = "动态可视化图表Agent，可以查询数据并生成EChart图表"
    
    def __init__(self):
        self._agent = None
        self._memory = AgentMemory(max_rounds=10)
    
    def get_tools(self) -> List[BaseTool]:
        """返回图表相关的工具"""
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
            str: 完整回答（JSON 格式，包含图表数据）
        """
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
        """
        流式执行智能体
        """
        agent = self._get_agent()
        
        messages = self._memory.get_messages(session_id)
        messages.append(HumanMessage(content=question))
        
        full_output = ""
        chart_data_sent = False
        
        try:
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2"
            ):
                event_name = event.get("event", "")
                
                # 调试：打印所有事件类型
                if "tool" in event_name.lower():
                    print(f"[ChartAgent] 事件: {event_name}, data keys: {event.get('data', {}).keys()}")
                
                # 捕获工具调用的输出 - 尝试多种事件名
                if event_name == "on_tool_end":
                    tool_output = event.get("data", {}).get("output", "")
                    # 处理不同类型的输出
                    if hasattr(tool_output, 'content'):
                        tool_output = tool_output.content
                    elif not isinstance(tool_output, str):
                        tool_output = str(tool_output)
                    
                    print(f"[ChartAgent] 工具输出类型: {type(tool_output)}, 内容: {tool_output[:100]}...")
                    
                    if "[CHART:" in tool_output:
                        yield tool_output
                        chart_data_sent = True
                        print(f"[ChartAgent] 发送图表数据标记 ✓")
                        continue
                
                if event_name == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, 'content') and chunk.content:
                        full_output += chunk.content
                        yield chunk.content
            
            if not full_output and not chart_data_sent:
                full_output = "抱歉，我无法处理您的问题。"
                yield full_output
            
            self._memory.add_message(session_id, question, full_output)
                
        except Exception as e:
            print(f"[ChartAgent] 流式处理异常: {e}")
            import traceback
            traceback.print_exc()
            error_msg = "抱歉，处理您的问题时出现错误。"
            yield error_msg
            self._memory.add_message(session_id, question, error_msg)
    
    def can_handle(self, question: str) -> float:
        """
        判断是否适合处理该问题
        
        图表/可视化相关问题返回高置信度
        
        Args:
            question: 用户问题
        
        Returns:
            float: 0-1 的置信度分数
        """
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question)
        score = matched / len(ROUTING_KEYWORDS)
        
        return min(0.3 + score * 2, 1.0)
    
    def clear_memory(self, session_id: str) -> None:
        """清除指定会话的记忆"""
        self._memory.clear(session_id)
