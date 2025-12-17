"""
会话记忆管理模块
管理智能体的对话历史
"""

from typing import Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class AgentMemory:
    """
    智能体会话记忆管理
    
    按 session_id 分隔存储对话历史
    """
    
    def __init__(self, max_rounds: int = 10):
        """
        初始化记忆管理器
        
        Args:
            max_rounds: 最大保留对话轮数
        """
        self._memory: Dict[str, List[BaseMessage]] = {}
        self.max_rounds = max_rounds
    
    def get_messages(self, session_id: Optional[str]) -> List[BaseMessage]:
        """
        获取会话历史消息
        
        Args:
            session_id: 会话 ID
        
        Returns:
            List[BaseMessage]: 消息列表
        """
        if not session_id:
            return []
        return self._memory.get(session_id, []).copy()
    
    def add_message(
        self, 
        session_id: Optional[str], 
        user_input: str, 
        ai_output: str
    ) -> None:
        """
        添加一轮对话到历史
        
        Args:
            session_id: 会话 ID
            user_input: 用户输入
            ai_output: AI 输出
        """
        if not session_id:
            return
        
        if session_id not in self._memory:
            self._memory[session_id] = []
        
        self._memory[session_id].append(HumanMessage(content=user_input))
        self._memory[session_id].append(AIMessage(content=ai_output))
        
        # 限制长度
        max_messages = self.max_rounds * 2
        if len(self._memory[session_id]) > max_messages:
            self._memory[session_id] = self._memory[session_id][-max_messages:]
    
    def clear(self, session_id: str) -> None:
        """
        清除指定会话的历史
        
        Args:
            session_id: 会话 ID
        """
        if session_id in self._memory:
            del self._memory[session_id]
    
    def clear_all(self) -> None:
        """清除所有会话历史"""
        self._memory.clear()
