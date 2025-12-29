"""
流程图智能体

负责解析用户的自然语言描述并调用 Draw.io MCP 生成流程图。
继承自 BaseAgent，遵循现有的智能体框架模式。

Requirements: 5.1, 5.2, 5.3, 6.4
"""

from typing import AsyncGenerator, Optional, List
import logging

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage

from agents.base import BaseAgent
from agents.flowchart_agent.prompts import SYSTEM_PROMPT, ROUTING_KEYWORDS, detect_diagram_type
from agents.flowchart_agent.tools import get_tools
from core.llm import get_llm
from core.memory import AgentMemory

logger = logging.getLogger(__name__)


class FlowchartAgent(BaseAgent):
    """
    流程图智能体
    
    负责：
    - 解析用户的自然语言描述
    - 调用 Draw.io MCP 生成流程图
    - 支持流程图的创建、修改和导出
    
    Requirements: 5.1, 5.2
    """
    
    name = "flowchart"
    description = "流程图智能体，可以根据自然语言描述生成流程图、序列图、组织架构图等"
    
    def __init__(self):
        self._agent = None
        self._memory = AgentMemory(max_rounds=10)
    
    def get_tools(self) -> List[BaseTool]:
        """
        返回流程图相关的工具
        
        从 MCP Server 动态发现并返回可用工具。
        
        Returns:
            List[BaseTool]: 从 MCP 动态生成的工具列表
        """
        return get_tools()
    
    def get_system_prompt(self) -> str:
        """
        返回系统提示词
        
        Returns:
            str: 流程图生成的系统提示词
        """
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
            output = "抱歉，我无法处理您的流程图请求。"
        
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
            
        Requirements: 5.2
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
                full_output = "抱歉，我无法处理您的流程图请求。"
                yield full_output
            
            # 保存到历史
            self._memory.add_message(session_id, question, full_output)
                
        except Exception as e:
            logger.error(f"[FlowchartAgent] 流式处理异常: {e}")
            error_msg = "抱歉，处理您的流程图请求时出现错误。"
            yield error_msg
            self._memory.add_message(session_id, question, error_msg)

    def can_handle(self, question: str) -> float:
        """
        判断是否适合处理该问题
        
        流程图相关问题返回高置信度。
        使用关键词匹配来计算置信度分数。
        
        Args:
            question: 用户问题
        
        Returns:
            float: 0-1 的置信度分数
            - 包含流程图关键词时返回 > 0.5
            - 不包含关键词时返回 <= 0.5
            
        Requirements: 5.3
        """
        question_lower = question.lower()
        
        # 计算关键词匹配数量
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question_lower)
        
        if matched == 0:
            # 没有匹配任何关键词，返回低置信度
            return 0.3
        
        # 基础分 0.6（确保 > 0.5），每匹配一个关键词增加分数
        # 最高 1.0
        score = 0.6 + (matched * 0.1)
        return min(score, 1.0)
    
    def clear_memory(self, session_id: str) -> None:
        """
        清除指定会话的记忆
        
        Args:
            session_id: 会话 ID
        """
        self._memory.clear(session_id)
    
    def get_default_diagram_type(self, description: str) -> str:
        """
        获取默认的图表类型
        
        当用户未指定图表类型时，根据描述检测或返回默认值 "flowchart"
        
        Args:
            description: 用户的描述
        
        Returns:
            str: 图表类型，默认为 "flowchart"
            
        Requirements: 6.4
        """
        return detect_diagram_type(description)
