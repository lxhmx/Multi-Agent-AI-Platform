"""
LLM 工厂模块
统一管理大语言模型实例
"""

from typing import Optional
from langchain_openai import ChatOpenAI

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import API_KEY, VANNA_MODEL, VANNA_API_BASE


# LLM 实例缓存
_llm_cache = {}


def get_llm(
    streaming: bool = False,
    temperature: float = 0.7,
    model: Optional[str] = None,
) -> ChatOpenAI:
    """
    获取 LLM 实例
    
    Args:
        streaming: 是否启用流式输出
        temperature: 温度参数
        model: 模型名称（默认使用配置文件中的模型）
    
    Returns:
        ChatOpenAI: LangChain ChatOpenAI 实例
    """
    model = model or VANNA_MODEL
    cache_key = f"{model}_{streaming}_{temperature}"
    
    if cache_key not in _llm_cache:
        _llm_cache[cache_key] = ChatOpenAI(
            model=model,
            openai_api_key=API_KEY,
            openai_api_base=VANNA_API_BASE,
            streaming=streaming,
            temperature=temperature,
        )
    
    return _llm_cache[cache_key]


def clear_llm_cache():
    """清除 LLM 缓存"""
    global _llm_cache
    _llm_cache = {}
