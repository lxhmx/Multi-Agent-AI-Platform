"""
视频下载器
使用 yt-dlp 下载抖音、B站等平台视频
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

from config import VIDEO_OUTPUT_DIR, VIDEO_BASE_URL

logger = logging.getLogger(__name__)

# 平台域名到 cookies 文件名的映射
PLATFORM_COOKIES_MAP = {
    "douyin.com": "douyin_cookies.txt",
    "v.douyin.com": "douyin_cookies.txt",
    "xiaohongshu.com": "xiaohongshu_cookies.txt",
    "xhslink.com": "xiaohongshu_cookies.txt",
    "bilibili.com": "bilibili_cookies.txt",
    "b23.tv": "bilibili_cookies.txt",
    "weixin.qq.com": "weixin_cookies.txt",  # 视频号
    "youtube.com": "youtube_cookies.txt",
    "youtu.be": "youtube_cookies.txt",
    "tiktok.com": "tiktok_cookies.txt",
}

# 支持从浏览器直接读取 cookies 的浏览器列表
SUPPORTED_BROWSERS = ['chrome', 'firefox', 'edge', 'safari', 'opera', 'brave', 'chromium', 'vivaldi']


@dataclass
class VideoInfo:
    """视频信息"""
    video_id: str
    title: str
    duration: Optional[int]  # 秒
    local_path: str
    public_url: str
    file_size: int  # 字节


class VideoDownloader:
    """视频下载器"""
    
    def __init__(
        self,
        output_dir: Optional[str] = None,
        base_url: Optional[str] = None,
        cookies_dir: Optional[str] = None,
        cookies_from_browser: Optional[str] = None  # 新增：从浏览器读取 cookies
    ):
        self.output_dir = Path(output_dir or VIDEO_OUTPUT_DIR)
        self.base_url = (base_url or VIDEO_BASE_URL).rstrip("/")
        # cookies 文件存放目录
        self.cookies_dir = Path(cookies_dir or VIDEO_OUTPUT_DIR) / "cookies"
        # 从浏览器读取 cookies（如 'chrome', 'firefox', 'edge' 等）
        self.cookies_from_browser = cookies_from_browser
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cookies_file(self, url: str) -> Optional[str]:
        """根据 URL 获取对应平台的 cookies 文件路径"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 移除 www. 前缀进行匹配
            domain_clean = domain.replace("www.", "")
            
            for platform_domain, cookies_filename in PLATFORM_COOKIES_MAP.items():
                if platform_domain in domain or domain_clean in platform_domain:
                    cookies_path = self.cookies_dir / cookies_filename
                    if cookies_path.exists():
                        logger.info(f"[VideoDownloader] 使用 cookies: {cookies_path}")
                        return str(cookies_path)
                    else:
                        logger.warning(f"[VideoDownloader] cookies 文件不存在: {cookies_path}")
            
            return None
        except Exception as e:
            logger.error(f"[VideoDownloader] 解析 URL 失败: {e}")
            return None
    
    async def download(self, url: str) -> VideoInfo:
        """
        下载视频
        
        Args:
            url: 视频链接（支持抖音、B站、YouTube等）
        
        Returns:
            VideoInfo: 视频信息
        
        Raises:
            DownloadError: 下载失败
        """
        import asyncio
        
        # 在线程池中执行同步下载
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._download_sync, url)
    
    def _get_http_headers(self, url: str) -> dict:
        """根据 URL 获取对应平台的 HTTP headers"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # B站特殊处理
        if 'bilibili.com' in domain or 'b23.tv' in domain:
            headers['Referer'] = 'https://www.bilibili.com/'
            headers['Origin'] = 'https://www.bilibili.com'
        # 抖音特殊处理
        elif 'douyin.com' in domain:
            headers['Referer'] = 'https://www.douyin.com/'
        # 小红书特殊处理
        elif 'xiaohongshu.com' in domain or 'xhslink.com' in domain:
            headers['Referer'] = 'https://www.xiaohongshu.com/'
        
        return headers
    
    def _download_sync(self, url: str) -> VideoInfo:
        """同步下载视频"""
        try:
            import yt_dlp
        except ImportError:
            raise DownloadError("yt-dlp 未安装，请运行: pip install yt-dlp")
        
        video_id = str(uuid.uuid4())[:8]
        filename = f"{video_id}.mp4"
        output_path = self.output_dir / filename
        
        # 构建 yt-dlp 选项
        ydl_opts = {
            'outtmpl': str(output_path),
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # 根据平台设置 headers
            'http_headers': self._get_http_headers(url),
            # 重试设置
            'retries': 3,
            'fragment_retries': 3,
            # 网络超时
            'socket_timeout': 30,
        }
        
        # 优先使用浏览器 cookies（推荐方式）
        if self.cookies_from_browser and self.cookies_from_browser in SUPPORTED_BROWSERS:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
            logger.info(f"[VideoDownloader] 使用浏览器 cookies: {self.cookies_from_browser}")
        else:
            # 回退到 cookies 文件
            cookies_file = self._get_cookies_file(url)
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
        
        # B站特殊处理
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if 'bilibili.com' in domain or 'b23.tv' in domain:
            # 使用正确的 extractor_args 格式
            ydl_opts['extractor_args'] = {'BiliBili': ['prefer_formats=dash-flv']}
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"[VideoDownloader] 开始下载: {url}")
                info = ydl.extract_info(url, download=True)
                
                # 获取实际文件路径（可能被重命名）
                actual_path = output_path
                if not actual_path.exists():
                    # 尝试查找下载的文件
                    for f in self.output_dir.glob(f"{video_id}.*"):
                        actual_path = f
                        break
                
                if not actual_path.exists():
                    raise DownloadError("下载完成但找不到文件")
                
                file_size = actual_path.stat().st_size
                
                logger.info(f"[VideoDownloader] 下载完成: {actual_path}, 大小: {file_size}")
                
                return VideoInfo(
                    video_id=video_id,
                    title=info.get("title", "未知标题"),
                    duration=info.get("duration"),
                    local_path=str(actual_path),
                    public_url=f"{self.base_url}/{actual_path.name}",
                    file_size=file_size,
                )
                
        except Exception as e:
            logger.error(f"[VideoDownloader] 下载失败: {e}")
            # 清理可能的残留文件
            if output_path.exists():
                output_path.unlink()
            raise DownloadError(f"下载失败: {e}")
    
    def delete(self, video_id: str) -> bool:
        """删除视频文件"""
        for f in self.output_dir.glob(f"{video_id}.*"):
            try:
                f.unlink()
                logger.info(f"[VideoDownloader] 已删除: {f}")
                return True
            except Exception as e:
                logger.error(f"[VideoDownloader] 删除失败: {e}")
        return False


class DownloadError(Exception):
    """下载错误"""
    pass
