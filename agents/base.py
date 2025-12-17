"""
智能体基类
所有智能体必须继承此类并实现抽象方法
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, List, Any
from langchain_core.tools import BaseTool


class BaseAgent(ABC):
    """
    智能体基类
    
    每个智能体需要实现：
    - name: 唯一标识符
    - description: 描述信息
    - get_tools(): 返回工具列表
    - get_system_prompt(): 返回系统提示词
    - run_stream(): 流式执行
    """
    
    name: str = "base_agent"
    description: str = "基础智能体"
    
    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """
        返回该智能体的工具列表
        
        Returns:
            List[BaseTool]: LangChain 工具列表
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        返回系统提示词
        
        Returns:
            str: 系统提示词
        """
        pass
    
    @abstractmethod
    async def run_stream(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体
        
        Args:
            question: 用户问题
            session_id: 会话 ID（用于记忆管理）
        
        Yields:
            str: 流式输出的文本片段
        """
        pass
    
    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """
        同步执行智能体（可选实现）
        
        Args:
            question: 用户问题
            session_id: 会话 ID
        
        Returns:
            str: 完整回答
        """
        raise NotImplementedError(f"{self.name} 未实现同步执行方法")
    
    def can_handle(self, question: str) -> float:
        """
        判断该智能体是否适合处理这个问题
        
        用于智能体路由，返回 0-1 的置信度分数
        子类可重写此方法实现更精确的路由
        
        Args:
            question: 用户问题
        
        Returns:
            float: 0-1 的置信度分数
        """
        return 0.5
    
    def clear_memory(self, session_id: str) -> None:
        """
        清除指定会话的记忆
        
        Args:
            session_id: 会话 ID
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"
