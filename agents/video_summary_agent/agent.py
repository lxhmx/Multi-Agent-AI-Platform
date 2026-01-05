"""
视频总结智能体

根据用户提供的视频URL，自动识别平台、下载视频、分析内容并生成总结
"""

import re
import logging
from typing import AsyncGenerator, Optional, List

from langchain_core.tools import BaseTool

from agents.base import BaseAgent
from agents.video_summary_agent.prompts import ROUTING_KEYWORDS
from agents.video_summary_agent.pipeline import VideoPipeline, PipelineResult
from core.memory import AgentMemory

logger = logging.getLogger(__name__)


# 系统提示词
SYSTEM_PROMPT = """你是一个视频内容分析助手，可以帮助用户：
1. 分析来自抖音、B站、小红书、视频号等平台的视频内容
2. 生成视频内容的详细总结
3. 提取视频中的关键信息

当用户提供视频链接时，你会自动：
- 识别视频平台
- 获取视频真实地址
- 下载视频到本地
- 使用多模态AI分析视频内容
- 生成结构化的内容总结

支持的平台：抖音、B站(Bilibili)、小红书、微信视频号

请直接提供视频链接，我会为你分析视频内容。"""


class VideoSummaryAgent(BaseAgent):
    """
    视频总结智能体
    
    工作流程：
    1. 接收用户提供的视频URL
    2. 自动识别平台（抖音/B站/小红书/视频号）
    3. 使用Playwright获取视频真实地址
    4. 下载视频到本地
    5. 调用多模态模型分析视频内容
    6. 返回结构化的视频总结
    """
    
    name = "video_summary"
    description = "视频总结智能体，可以分析抖音、B站、小红书、视频号等平台的视频内容"
    
    # URL匹配正则
    URL_PATTERN = re.compile(
        r'https?://(?:www\.)?'
        r'(?:douyin\.com|v\.douyin\.com|'
        r'bilibili\.com|b23\.tv|'
        r'xiaohongshu\.com|xhslink\.com|'
        r'channels\.weixin\.qq\.com|finder\.video\.qq\.com)'
        r'[^\s]*',
        re.IGNORECASE
    )
    
    def __init__(self):
        self._memory = AgentMemory(max_rounds=10)
        self._pipeline = None
        self._last_result: Optional[PipelineResult] = None
    
    def _get_pipeline(self) -> VideoPipeline:
        """获取Pipeline实例（懒加载）"""
        if self._pipeline is None:
            self._pipeline = VideoPipeline()
        return self._pipeline
    
    def get_tools(self) -> List[BaseTool]:
        """返回工具列表（当前实现不使用LangChain工具）"""
        return []
    
    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        return SYSTEM_PROMPT
    
    def _extract_url(self, text: str) -> Optional[str]:
        """从文本中提取视频URL"""
        match = self.URL_PATTERN.search(text)
        if match:
            return match.group(0)
        return None
    
    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """同步执行（不推荐，请使用run_stream）"""
        import asyncio
        result = []
        async def collect():
            async for chunk in self.run_stream(question, session_id):
                result.append(chunk)
        asyncio.run(collect())
        return "".join(result)
    
    async def run_stream(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体
        
        Args:
            question: 用户输入（包含视频URL）
            session_id: 会话ID
            
        Yields:
            str: 流式输出的文本片段
        """
        session_id = session_id or "default"
        full_output = ""
        
        try:
            # 提取URL
            url = self._extract_url(question)
            
            if not url:
                msg = "请提供视频链接，支持以下平台：\n\n"
                msg += "- 🎵 抖音: `https://www.douyin.com/video/xxx`\n"
                msg += "- 📺 B站: `https://www.bilibili.com/video/BVxxx`\n"
                msg += "- 📕 小红书: `https://www.xiaohongshu.com/explore/xxx`\n"
                msg += "- 📱 视频号: `https://channels.weixin.qq.com/xxx`\n"
                yield msg
                return
            
            yield f"📎 检测到视频链接: `{url}`\n\n"
            
            # 执行Pipeline
            pipeline = self._get_pipeline()
            
            async for chunk in pipeline.run_stream(url):
                # 过滤掉内部标记
                if chunk.startswith("[PIPELINE_RESULT:"):
                    # 提取结果路径，存储供后续使用
                    path = chunk.replace("[PIPELINE_RESULT:", "").replace("]", "")
                    self._last_result = PipelineResult(
                        success=True,
                        local_path=path,
                        original_url=url
                    )
                else:
                    full_output += chunk
                    yield chunk
            
            # 保存到记忆
            self._memory.add_message(session_id, question, full_output)
            
        except Exception as e:
            logger.error(f"[VideoSummaryAgent] 执行异常: {e}", exc_info=True)
            error_msg = f"\n\n❌ 处理视频时出现错误: {str(e)}\n\n"
            error_msg += "**可能的原因：**\n"
            error_msg += "- 视频链接无效或已失效\n"
            error_msg += "- 网络连接问题\n"
            error_msg += "- 平台限制访问\n\n"
            error_msg += "请检查链接后重试。"
            yield error_msg
    
    def can_handle(self, question: str) -> float:
        """判断是否适合处理该问题"""
        question_lower = question.lower()
        
        # 如果包含视频URL，高优先级
        if self._extract_url(question):
            return 0.95
        
        # 检查关键词匹配
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question_lower)
        
        if matched == 0:
            return 0.2
        
        return min(0.5 + (matched * 0.1), 0.9)
    
    def clear_memory(self, session_id: str) -> None:
        """清除指定会话的记忆"""
        self._memory.clear(session_id)
    
    def get_last_result(self) -> Optional[PipelineResult]:
        """
        获取上次执行的结果
        
        用于后续功能（如自动发布）获取视频路径和总结内容
        """
        return self._last_result
