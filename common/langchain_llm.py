"""
LangChain LLM 实例
用于替代 Vanna 的 submit_prompt_stream，提供更灵活的 LLM 调用能力
支持会话记忆（Memory）
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from config import API_KEY, VANNA_MODEL, VANNA_API_BASE

# 单例模式存储 LLM 实例
_llm_instance = None

# 会话记忆存储（按 session_id 分隔）
# 结构: { session_id: [Message, Message, ...] }
_conversation_memory = {}

# 最大记忆轮数（防止 token 过多）
MAX_MEMORY_ROUNDS = 10


def get_langchain_llm():
    """
    获取 LangChain LLM 单例实例
    使用与 Vanna 相同的 DeepSeek 配置
    """
    global _llm_instance
    
    if _llm_instance is None:
        _llm_instance = ChatOpenAI(
            model=VANNA_MODEL,
            openai_api_key=API_KEY,
            openai_api_base=VANNA_API_BASE,
            streaming=True,  # 启用流式输出
        )
    
    return _llm_instance


def get_conversation_history(session_id: str) -> list:
    """
    获取指定会话的历史记录
    """
    return _conversation_memory.get(session_id, [])


def add_to_memory(session_id: str, user_message: str, ai_message: str):
    """
    将一轮对话添加到记忆中
    """
    if session_id not in _conversation_memory:
        _conversation_memory[session_id] = []
    
    _conversation_memory[session_id].append(HumanMessage(content=user_message))
    _conversation_memory[session_id].append(AIMessage(content=ai_message))
    
    # 限制记忆长度（保留最近 N 轮，每轮 2 条消息）
    max_messages = MAX_MEMORY_ROUNDS * 2
    if len(_conversation_memory[session_id]) > max_messages:
        _conversation_memory[session_id] = _conversation_memory[session_id][-max_messages:]


def clear_memory(session_id: str):
    """
    清除指定会话的记忆
    """
    if session_id in _conversation_memory:
        del _conversation_memory[session_id]


def stream_chat_response(system_prompt: str, user_prompt: str, session_id: str = None):
    """
    流式生成聊天回复（支持会话记忆）
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        session_id: 会话 ID（可选，传入则启用记忆）
    
    Yields:
        str: 每个 token/chunk 的内容
    """
    llm = get_langchain_llm()
    
    # 构建消息列表
    messages = [SystemMessage(content=system_prompt)]
    
    # 如果有 session_id，加入历史对话
    if session_id:
        history = get_conversation_history(session_id)
        messages.extend(history)
    
    # 添加当前用户消息
    messages.append(HumanMessage(content=user_prompt))
    
    # 流式调用，同时收集完整回复
    full_response = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            full_response += chunk.content
            yield chunk.content
    
    # 如果有 session_id，保存这轮对话到记忆
    if session_id and full_response:
        add_to_memory(session_id, user_prompt, full_response)
