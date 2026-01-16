"""
视频下载器

下载视频到本地目录
"""

import os
import re
import logging
import hashlib
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Awaitable
import aiohttp
import asyncio

from config import VIDEO_OUTPUT_DIR

logger = logging.getLogger(__name__)


# 进度回调类型: (downloaded_bytes, total_bytes, percentage) -> None
ProgressCallback = Callable[[int, int, float], Awaitable[None]]


def _get_output_dir() -> str:
    """获取输出目录，Windows下使用项目目录"""
    if platform.system() == "Windows":
        # Windows测试环境使用项目下的test_downloads目录
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "test_downloads")
    return VIDEO_OUTPUT_DIR


class VideoDownloader:
    """
    视频下载器
    
    负责将视频从URL下载到本地目录
    文件命名格式: {platform}_{video_id}_{timestamp}.mp4
    """
    
    def __init__(self, output_dir: str = None):
        """
        初始化下载器
        
        Args:
            output_dir: 输出目录，默认使用配置中的VIDEO_OUTPUT_DIR
        """
        self.output_dir = output_dir or _get_output_dir()
        # 确保目录存在
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(
        self, 
        platform: str, 
        video_id: str = "", 
        title: str = ""
    ) -> str:
        """
        生成文件名
        
        格式: {platform}_{video_id或hash}_{timestamp}.mp4
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 如果有video_id就用，否则用标题hash
        if video_id:
            safe_id = re.sub(r'[^\w\-]', '', video_id)[:32]
        elif title:
            safe_id = hashlib.md5(title.encode()).hexdigest()[:8]
        else:
            safe_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        
        filename = f"{platform}_{safe_id}_{timestamp}.mp4"
        return filename
    
    async def download(
        self,
        url: str,
        platform: str,
        video_id: str = "",
        title: str = "",
        headers: dict = None,
        progress_callback: ProgressCallback = None
    ) -> str:
        """
        下载视频
        
        Args:
            url: 视频真实URL
            platform: 平台英文名称
            video_id: 视频ID
            title: 视频标题
            headers: 请求头
            progress_callback: 进度回调函数，参数为 (已下载字节, 总字节, 百分比)
            
        Returns:
            str: 本地文件路径
        """
        filename = self._generate_filename(platform, video_id, title)
        filepath = os.path.join(self.output_dir, filename)
        
        # 默认请求头
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self._get_referer(platform),
        }
        if headers:
            default_headers.update(headers)
        
        logger.info(f"[VideoDownloader] 开始下载: {url[:100]}...")
        logger.info(f"[VideoDownloader] 保存到: {filepath}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=default_headers,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"下载失败，状态码: {response.status}")
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    last_callback_progress = -1  # 用于控制回调频率
                    
                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                # 每1%或每MB回调一次，避免过于频繁
                                current_progress = int(progress)
                                if progress_callback and current_progress > last_callback_progress:
                                    last_callback_progress = current_progress
                                    await progress_callback(downloaded, total_size, progress)
                                if downloaded % (1024 * 1024) < 8192:  # 每MB打印一次
                                    logger.info(f"[VideoDownloader] 下载进度: {progress:.1f}%")
                            elif progress_callback and downloaded % (512 * 1024) < 8192:
                                # 如果没有content-length，每512KB回调一次
                                await progress_callback(downloaded, 0, 0)
            
            # 验证文件是否下载成功
            if not os.path.exists(filepath):
                raise Exception(f"下载失败：文件未保存到 {filepath}")
            
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                os.remove(filepath)
                raise Exception("下载失败：文件大小为0")
            
            logger.info(f"[VideoDownloader] 下载完成: {filepath}, 大小: {file_size / 1024 / 1024:.2f}MB")
            return filepath
            
        except asyncio.TimeoutError:
            logger.error("[VideoDownloader] 下载超时")
            raise Exception("视频下载超时，请稍后重试")
        except Exception as e:
            logger.error(f"[VideoDownloader] 下载失败: {e}")
            # 清理不完整的文件
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
    
    def _get_referer(self, platform: str) -> str:
        """根据平台获取Referer"""
        referers = {
            "douyin": "https://www.douyin.com/",
            "bilibili": "https://www.bilibili.com/",
            "xiaohongshu": "https://www.xiaohongshu.com/",
            "weixin_video": "https://channels.weixin.qq.com/",
        }
        return referers.get(platform, "")
