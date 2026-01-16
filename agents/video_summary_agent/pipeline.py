"""
视频处理管道

链式执行视频处理流程
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, AsyncGenerator

from agents.video_summary_agent.tools.platform_detector import PlatformDetector
from agents.video_summary_agent.tools.video_downloader import VideoDownloader
from agents.video_summary_agent.tools.video_analyzer import VideoAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """管道执行结果"""
    success: bool = False
    platform: str = ""              # 平台英文名称
    platform_display: str = ""      # 平台显示名称
    original_url: str = ""          # 原始URL
    real_url: str = ""              # 真实视频URL
    local_path: str = ""            # 本地视频路径
    summary: str = ""               # 视频总结（Markdown格式）
    title: str = ""                 # 视频标题
    author: str = ""                # 作者
    video_id: str = ""              # 视频ID
    error: Optional[str] = None     # 错误信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据


class VideoPipeline:
    """
    视频处理管道
    
    链式执行：平台识别 → 获取真实URL → 下载视频 → 分析内容
    
    支持的步骤:
    - detect: 平台识别
    - fetch: 获取真实URL
    - download: 下载视频
    - analyze: 分析内容
    """
    
    ALL_STEPS = ["detect", "fetch", "download", "analyze"]
    
    def __init__(self):
        self.detector = PlatformDetector()
        self.downloader = VideoDownloader()
        self.analyzer = VideoAnalyzer()
    
    async def run(
        self, 
        url: str, 
        steps: list = None
    ) -> PipelineResult:
        """
        执行管道
        
        Args:
            url: 视频页面URL
            steps: 要执行的步骤列表，默认执行全部
            
        Returns:
            PipelineResult: 执行结果
        """
        steps = steps or self.ALL_STEPS
        result = PipelineResult(original_url=url)
        
        try:
            # Step 1: 平台识别
            if "detect" in steps:
                platform = self.detector.detect(url)
                if not platform:
                    result.error = f"不支持的平台，目前支持: {', '.join(self.detector.get_supported_platforms())}"
                    return result
                
                result.platform = platform.name
                result.platform_display = platform.display_name
                logger.info(f"[Pipeline] 识别到平台: {platform.display_name}")
            
            # Step 2: 获取真实URL
            if "fetch" in steps:
                platform = self.detector.detect(url)
                video_info = await platform.get_video_info(url)
                
                if not video_info.real_url:
                    result.error = "无法获取视频真实地址"
                    return result
                
                result.real_url = video_info.real_url
                result.title = video_info.title
                result.author = video_info.author
                result.video_id = video_info.video_id
                logger.info(f"[Pipeline] 获取到视频: {video_info.title or video_info.video_id}")
            
            # Step 3: 下载视频
            if "download" in steps:
                local_path = await self.downloader.download(
                    url=result.real_url,
                    platform=result.platform,
                    video_id=result.video_id,
                    title=result.title,
                )
                result.local_path = local_path
                
                # 验证视频文件是否存在
                import os
                if not os.path.exists(local_path):
                    result.error = f"视频下载失败：文件未保存到 {local_path}"
                    return result
                
                file_size = os.path.getsize(local_path)
                if file_size == 0:
                    result.error = "视频下载失败：文件大小为0"
                    return result
                
                logger.info(f"[Pipeline] 视频已下载: {local_path}, 大小: {file_size / 1024 / 1024:.2f}MB")
            
            # Step 4: 分析视频
            if "analyze" in steps:
                # 验证视频文件存在才能进入分析步骤
                import os
                if not result.local_path or not os.path.exists(result.local_path):
                    result.error = "无法分析视频：视频文件不存在"
                    return result
                
                summary = await self.analyzer.analyze(result.local_path)
                result.summary = summary
                logger.info(f"[Pipeline] 分析完成")
            
            result.success = True
            return result
            
        except Exception as e:
            logger.error(f"[Pipeline] 执行失败: {e}")
            result.error = str(e)
            return result
    
    async def run_stream(
        self, 
        url: str, 
        steps: list = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行管道，实时输出进度
        
        Args:
            url: 视频页面URL
            steps: 要执行的步骤列表
            
        Yields:
            str: 进度信息和结果
        """
        steps = steps or self.ALL_STEPS
        result = PipelineResult(original_url=url)
        
        try:
            # Step 1: 平台识别
            if "detect" in steps:
                yield "🔍 正在识别视频平台...\n\n"
                
                platform = self.detector.detect(url)
                if not platform:
                    supported = ', '.join(self.detector.get_supported_platforms())
                    yield f"❌ 不支持的平台\n\n目前支持: {supported}\n"
                    return
                
                result.platform = platform.name
                result.platform_display = platform.display_name
                yield f"✅ 识别到平台: **{platform.display_name}**\n\n"
            
            # Step 2: 获取真实URL
            if "fetch" in steps:
                yield "🔗 正在获取视频地址...\n\n"
                
                platform = self.detector.detect(url)
                video_info = await platform.get_video_info(url)
                
                if not video_info.real_url:
                    yield "❌ 无法获取视频真实地址\n"
                    return
                
                result.real_url = video_info.real_url
                result.title = video_info.title
                result.author = video_info.author
                result.video_id = video_info.video_id
                
                info_text = ""
                if video_info.title:
                    info_text += f"📺 标题: {video_info.title}\n"
                if video_info.author:
                    info_text += f"👤 作者: {video_info.author}\n"
                if info_text:
                    yield f"✅ 获取视频信息成功\n\n{info_text}\n"
                else:
                    yield "✅ 获取视频地址成功\n\n"
            
            # Step 3: 下载视频
            if "download" in steps:
                yield "⬇️ 正在下载视频...\n\n"
                
                local_path = await self.downloader.download(
                    url=result.real_url,
                    platform=result.platform,
                    video_id=result.video_id,
                    title=result.title,
                )
                result.local_path = local_path
                
                # 验证视频文件是否存在
                import os
                if not os.path.exists(local_path):
                    yield f"❌ 视频下载失败：文件未保存到 `{local_path}`\n"
                    return
                
                file_size = os.path.getsize(local_path)
                if file_size == 0:
                    yield f"❌ 视频下载失败：文件大小为0\n"
                    return
                
                yield f"✅ 视频下载完成\n\n📁 保存路径: `{local_path}`\n📊 文件大小: {file_size / 1024 / 1024:.2f}MB\n\n"
            
            # Step 4: 分析视频
            if "analyze" in steps:
                # 再次验证视频文件存在才能进入分析步骤
                import os
                if not result.local_path or not os.path.exists(result.local_path):
                    yield "❌ 无法分析视频：视频文件不存在\n"
                    return
                
                yield "🤖 正在分析视频内容，请稍候...\n\n"
                
                summary = await self.analyzer.analyze(result.local_path)
                result.summary = summary
                
                yield "✅ 分析完成\n\n"
                yield "---\n\n"
                yield summary
            
            result.success = True
            
            # 存储结果到metadata供后续使用
            yield f"\n\n[PIPELINE_RESULT:{result.local_path}]"
            
        except Exception as e:
            logger.error(f"[Pipeline] 执行失败: {e}")
            yield f"\n\n❌ 处理失败: {str(e)}\n"
