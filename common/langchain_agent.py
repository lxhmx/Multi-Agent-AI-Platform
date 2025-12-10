"""
LangChain Agent
使用 Tools 和 Memory 的智能代理，可以自动决定何时调用数据库查询工具
"""

import sys
from pathlib import Path
from typing import Generator
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import API_KEY, VANNA_MODEL, VANNA_API_BASE
from common.langchain_tools import ALL_TOOLS

# Agent 实例缓存
_agent_graph = None

# 会话记忆（按 session_id 分隔）
_agent_memory = {}

# 最大记忆轮数
MAX_MEMORY_ROUNDS = 10

# 系统提示词
AGENT_SYSTEM_PROMPT = """你是一个智能数据分析助手，可以帮助用户查询和分析数据库中的数据。

你的能力：
1. 理解用户的自然语言问题
2. 使用 text2sql_query 工具查询数据库
3. 使用 get_database_schema 工具了解数据库结构
4. 根据查询结果给出清晰、友好的回答

回答要求：
1. 用自然、易懂的中文回答
2. 不要向用户展示 SQL 语句等技术细节
3. 如果数据量大，给出关键统计信息
4. 回答要简洁明了，控制在 200 字以内
5. 如果无法回答，礼貌地说明原因
"""


def get_agent_graph():
    """
    获取 Agent Graph（单例）
    使用 langgraph 的 create_react_agent
    """
    global _agent_graph
    
    if _agent_graph is None:
        # 创建 LLM
        llm = ChatOpenAI(
            model=VANNA_MODEL,
            openai_api_key=API_KEY,
            openai_api_base=VANNA_API_BASE,
            streaming=True,
        )
        
        # 使用 langgraph 创建 ReAct Agent
        _agent_graph = create_react_agent(
            model=llm,
            tools=ALL_TOOLS,
            prompt=AGENT_SYSTEM_PROMPT,  # 系统提示词
        )
    
    return _agent_graph


def get_chat_history(session_id: str) -> list:
    """获取会话历史"""
    return _agent_memory.get(session_id, [])


def add_to_history(session_id: str, user_input: str, ai_output: str):
    """添加对话到历史"""
    if session_id not in _agent_memory:
        _agent_memory[session_id] = []
    
    _agent_memory[session_id].append(HumanMessage(content=user_input))
    _agent_memory[session_id].append(AIMessage(content=ai_output))
    
    # 限制长度
    max_messages = MAX_MEMORY_ROUNDS * 2
    if len(_agent_memory[session_id]) > max_messages:
        _agent_memory[session_id] = _agent_memory[session_id][-max_messages:]


def clear_history(session_id: str):
    """清除会话历史"""
    if session_id in _agent_memory:
        del _agent_memory[session_id]


def run_agent(question: str, session_id: str = None) -> str:
    """
    运行 Agent 处理用户问题（非流式）
    
    Args:
        question: 用户问题
        session_id: 会话 ID
    
    Returns:
        str: Agent 的回答
    """
    agent = get_agent_graph()
    
    # 构建消息列表（包含历史）
    messages = []
    if session_id:
        messages.extend(get_chat_history(session_id))
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
    if session_id:
        add_to_history(session_id, question, output)
    
    return output


def run_agent_stream(question: str, session_id: str = None) -> Generator[str, None, None]:
    """
    运行 Agent 处理用户问题（流式输出）
    
    Args:
        question: 用户问题
        session_id: 会话 ID
    
    Yields:
        str: 每个 token
    """
    agent = get_agent_graph()
    
    # 构建消息列表（包含历史）
    messages = []
    if session_id:
        messages.extend(get_chat_history(session_id))
    messages.append(HumanMessage(content=question))
    
    full_output = ""
    
    # 流式调用 Agent
    for event in agent.stream({"messages": messages}, stream_mode="messages"):
        # event 是 (message, metadata) 元组
        if isinstance(event, tuple) and len(event) >= 1:
            msg = event[0]
            # 只输出 AI 消息的内容
            if isinstance(msg, AIMessage) and msg.content:
                full_output += msg.content
                yield msg.content
    
    # 保存到历史
    if session_id and full_output:
        add_to_history(session_id, question, full_output)
