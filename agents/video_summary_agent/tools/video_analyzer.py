"""
视频分析器

调用多模态大模型分析视频内容
"""

import os
import logging
from typing import Optional
from openai import OpenAI

from config import DASHSCOPE_API_KEY, VIDEO_MODEL, VANNA_API_BASE, VIDEO_BASE_URL
from agents.video_summary_agent.prompts import VIDEO_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    视频分析器
    
    使用阿里云百炼的多模态模型（qwen-vl系列）分析视频内容
    通过视频URL方式调用，需要视频可通过HTTP访问
    """
    
    def __init__(
        self, 
        api_key: str = None, 
        model: str = None,
        base_url: str = None,
        video_base_url: str = None
    ):
        """
        初始化分析器
        
        Args:
            api_key: API密钥，默认使用配置
            model: 模型名称，默认使用配置中的VIDEO_MODEL
            base_url: API地址
            video_base_url: 视频访问基础URL
        """
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.model = model or VIDEO_MODEL
        self.base_url = base_url or VANNA_API_BASE
        self.video_base_url = video_base_url or VIDEO_BASE_URL
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
    
    def _get_video_url(self, video_path: str) -> str:
        """
        将本地视频路径转换为可访问的URL
        
        Args:
            video_path: 本地视频路径，如 /opt/app/video/douyin_xxx.mp4
            
        Returns:
            str: 视频URL，如 http://111.229.42.23/videos/douyin_xxx.mp4
        """
        filename = os.path.basename(video_path)
        return f"{self.video_base_url}/{filename}"
    
    async def analyze(
        self, 
        video_path: str, 
        prompt: str = None
    ) -> str:
        """
        分析视频内容
        
        Args:
            video_path: 本地视频文件路径
            prompt: 分析提示词，默认使用VIDEO_ANALYSIS_PROMPT
            
        Returns:
            str: 视频内容总结（Markdown格式）
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 转换为可访问的URL
        video_url = self._get_video_url(video_path)
        logger.info(f"[VideoAnalyzer] 视频URL: {video_url}")
        
        return await self.analyze_from_url(video_url, prompt)
    
    async def analyze_from_url(
        self, 
        video_url: str, 
        prompt: str = None
    ) -> str:
        """
        从URL分析视频
        
        Args:
            video_url: 视频URL
            prompt: 分析提示词
            
        Returns:
            str: 视频内容总结
        """
        prompt = prompt or VIDEO_ANALYSIS_PROMPT
        
        logger.info(f"[VideoAnalyzer] 开始分析视频: {video_url}")
        logger.info(f"[VideoAnalyzer] 使用模型: {self.model}")
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video_url",
                            "video_url": {"url": video_url}
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096,
            )
            
            result = response.choices[0].message.content
            logger.info(f"[VideoAnalyzer] 分析完成，结果长度: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"[VideoAnalyzer] 分析失败: {e}")
            raise
