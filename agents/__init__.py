"""
智能体注册表
管理所有智能体实例，提供路由和调用能力
"""

from typing import Dict, Type, Optional
from agents.base import BaseAgent


class AgentRegistry:
    """智能体注册表 - 管理所有智能体实例"""
    
    _agents: Dict[str, "BaseAgent"] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, agent_class: Type["BaseAgent"]) -> Type["BaseAgent"]:
        """注册智能体（装饰器方式）"""
        agent = agent_class()
        cls._agents[agent.name] = agent
        return agent_class
    
    @classmethod
    def get(cls, name: str) -> Optional["BaseAgent"]:
        """获取指定智能体"""
        cls._ensure_initialized()
        return cls._agents.get(name)
    
    @classmethod
    def get_all(cls) -> Dict[str, "BaseAgent"]:
        """获取所有智能体"""
        cls._ensure_initialized()
        return cls._agents
    
    @classmethod
    def route(cls, question: str) -> "BaseAgent":
        """根据问题自动路由到最合适的智能体"""
        cls._ensure_initialized()
        
        best_agent = None
        best_score = 0
        
        for agent in cls._agents.values():
            score = agent.can_handle(question)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        # 默认返回数据分析智能体
        return best_agent or cls._agents.get("data_analyst")
    
    @classmethod
    def _ensure_initialized(cls):
        """确保智能体已初始化"""
        if not cls._initialized:
            cls._init_agents()
            cls._initialized = True
    
    @classmethod
    def _init_agents(cls):
        """初始化所有智能体"""
        # 延迟导入避免循环依赖
        from agents.data_analyst_agent import DataAnalystAgent
        from agents.flowchart_agent import FlowchartAgent
        from agents.browser_agent import BrowserAgent
        from agents.server_monitor_agent import ServerMonitorAgent
        from agents.video_summary_agent import VideoSummaryAgent
        
        if "data_analyst" not in cls._agents:
            cls.register(DataAnalystAgent)
        
        if "flowchart" not in cls._agents:
            cls.register(FlowchartAgent)
        
        if "browser" not in cls._agents:
            cls.register(BrowserAgent)
        
        if "server_monitor" not in cls._agents:
            cls.register(ServerMonitorAgent)
        
        if "video_summary" not in cls._agents:
            cls.register(VideoSummaryAgent)


# 便捷函数
def get_agent(name: str) -> Optional["BaseAgent"]:
    """获取指定智能体"""
    return AgentRegistry.get(name)


def route_agent(question: str) -> "BaseAgent":
    """根据问题路由到合适的智能体"""
    return AgentRegistry.route(question)
