"""
视频内容总结智能体

支持从抖音、B站等平台下载视频，并使用多模态大模型分析视频内容，
生成结构化的 Markdown 摘要。
"""

import re
import logging
from typing import AsyncGenerator, Optional, List

from langchain_core.tools import BaseTool

from agents.base import BaseAgent
from agents.video_summary_agent.prompts import ROUTING_KEYWORDS
from agents.video_summary_agent.downloader import VideoDownloader, DownloadError
from agents.video_summary_agent.analyzer import VideoAnalyzer, AnalyzeError

logger = logging.getLogger(__name__)


class VideoSummaryAgent(BaseAgent):
    """
    视频内容总结智能体
    
    工作流程：
    1. 从用户输入中提取视频链接
    2. 使用 yt-dlp 下载视频到服务器
    3. 调用百炼 Qwen-VL 多模态模型分析视频
    4. 返回结构化的 Markdown 摘要
    """
    
    name = "video_summary"
    description = "视频内容总结智能体，可以下载并分析抖音、B站等平台的视频内容"
    
    def __init__(self):
        self._downloader: Optional[VideoDownloader] = None
        self._analyzer: Optional[VideoAnalyzer] = None
    
    def _get_downloader(self) -> VideoDownloader:
        """获取下载器实例（懒加载）"""
        if self._downloader is None:
            self._downloader = VideoDownloader()
        return self._downloader
    
    def _get_analyzer(self) -> VideoAnalyzer:
        """获取分析器实例（懒加载）"""
        if self._analyzer is None:
            self._analyzer = VideoAnalyzer()
        return self._analyzer
    
    def get_tools(self) -> List[BaseTool]:
        """返回工具列表（当前实现不使用 LangChain 工具）"""
        return []
    
    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        return "你是一个视频内容分析助手，可以帮助用户下载和分析视频内容。"
    
    async def run_stream(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体
        
        Yields:
            str: 流式输出的文本片段
        """
        # 提取视频链接
        video_url = self._extract_video_url(question)
        
        if not video_url:
            yield "❌ 未检测到有效的视频链接。\n\n"
            yield "请提供视频链接，支持以下平台：\n"
            yield "- 抖音（douyin.com）\n"
            yield "- B站（bilibili.com）\n"
            yield "- YouTube（youtube.com）\n"
            yield "- 其他 yt-dlp 支持的平台\n\n"
            yield "示例：`请帮我总结这个视频 https://www.douyin.com/video/xxx`"
            return
        
        yield f"🔗 检测到视频链接: {video_url}\n\n"
        
        # Step 1: 下载视频
        yield "📥 **Step 1/2: 正在下载视频...**\n\n"
        
        try:
            downloader = self._get_downloader()
            video_info = await downloader.download(video_url)
            
            yield f"✅ 下载完成！\n"
            yield f"- 标题: {video_info.title}\n"
            if video_info.duration:
                yield f"- 时长: {self._format_duration(video_info.duration)}\n"
            yield f"- 大小: {self._format_size(video_info.file_size)}\n"
            yield f"- 下载地址: {video_info.public_url}\n\n"
            
        except DownloadError as e:
            yield f"❌ 下载失败: {e}\n\n"
            yield "可能的原因：\n"
            yield "- 视频链接无效或已失效\n"
            yield "- 视频需要登录才能访问\n"
            yield "- 网络连接问题\n"
            return
        
        # Step 2: 分析视频
        yield "🤖 **Step 2/2: 正在分析视频内容...**\n\n"
        yield "（使用 Qwen-VL 多模态大模型，可能需要 1-2 分钟）\n\n"
        yield "---\n\n"
        
        try:
            analyzer = self._get_analyzer()
            async for chunk in analyzer.analyze_stream(video_info.public_url):
                yield chunk
            
            yield "\n\n---\n\n"
            yield "✅ **分析完成！**\n\n"
            yield f"📥 [点击下载视频]({video_info.public_url})"
            
        except AnalyzeError as e:
            yield f"\n\n❌ 分析失败: {e}\n\n"
            yield f"视频已下载成功，您可以直接下载: {video_info.public_url}"
    
    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """同步执行（不推荐，请使用 run_stream）"""
        import asyncio
        result = []
        async def collect():
            async for chunk in self.run_stream(question, session_id):
                result.append(chunk)
        asyncio.run(collect())
        return "".join(result)
    
    def _extract_video_url(self, text: str) -> Optional[str]:
        """从文本中提取视频链接"""
        # 匹配常见视频平台链接
        patterns = [
            r'https?://[^\s]*douyin\.com[^\s]*',
            r'https?://[^\s]*bilibili\.com[^\s]*',
            r'https?://[^\s]*youtube\.com[^\s]*',
            r'https?://[^\s]*youtu\.be[^\s]*',
            r'https?://[^\s]*tiktok\.com[^\s]*',
            r'https?://v\.douyin\.com/[^\s]*',
            r'https?://b23\.tv/[^\s]*',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0).rstrip('，。！？,.')
        
        return None
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长"""
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}小时{minutes}分{secs}秒"
        elif minutes > 0:
            return f"{minutes}分{secs}秒"
        else:
            return f"{secs}秒"
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def can_handle(self, question: str) -> float:
        """判断是否适合处理该问题"""
        question_lower = question.lower()
        
        # 检查是否包含视频链接
        if self._extract_video_url(question):
            return 0.95
        
        # 检查关键词
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question_lower)
        
        if matched == 0:
            return 0.1
        
        return min(0.5 + (matched * 0.1), 0.9)
    
    def clear_memory(self, session_id: str) -> None:
        """清除会话记忆（当前实现无状态）"""
        pass
