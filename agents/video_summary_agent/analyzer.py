"""
视频分析器
调用阿里云百炼 Qwen-VL 多模态模型分析视频内容
"""

import os
import logging
from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI

from config import DASHSCOPE_API_KEY, VIDEO_MODEL
from agents.video_summary_agent.prompts import VIDEO_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """视频内容分析器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fps: float = 1.0
    ):
        """
        初始化分析器
        
        Args:
            api_key: 百炼 API Key，默认从配置文件获取
            model: 模型名称，默认从配置文件获取
            fps: 视频抽帧频率（每秒抽取帧数），默认 1
        """
        self.api_key = api_key or DASHSCOPE_API_KEY or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("未配置 DASHSCOPE_API_KEY")
        
        self.model = model or VIDEO_MODEL
        self.fps = fps
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    
    async def analyze(self, video_url: str, prompt: Optional[str] = None) -> str:
        """
        分析视频内容
        
        Args:
            video_url: 视频的公网 URL
            prompt: 自定义提示词，默认使用 VIDEO_ANALYSIS_PROMPT
        
        Returns:
            str: Markdown 格式的分析结果
        """
        prompt = prompt or VIDEO_ANALYSIS_PROMPT
        
        logger.info(f"[VideoAnalyzer] 开始分析视频: {video_url}")
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "video_url",
                                "video_url": {"url": video_url},
                                "fps": self.fps
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            result = completion.choices[0].message.content
            logger.info(f"[VideoAnalyzer] 分析完成，结果长度: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"[VideoAnalyzer] 分析失败: {e}")
            raise AnalyzeError(f"视频分析失败: {e}")
    
    async def analyze_stream(
        self,
        video_url: str,
        prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式分析视频内容
        
        Args:
            video_url: 视频的公网 URL
            prompt: 自定义提示词
        
        Yields:
            str: 流式输出的文本片段
        """
        prompt = prompt or VIDEO_ANALYSIS_PROMPT
        
        logger.info(f"[VideoAnalyzer] 开始流式分析视频: {video_url}")
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "video_url",
                                "video_url": {"url": video_url},
                                "fps": self.fps
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"[VideoAnalyzer] 流式分析失败: {e}")
            raise AnalyzeError(f"视频分析失败: {e}")


class AnalyzeError(Exception):
    """分析错误"""
    pass
