"""
平台识别器

根据URL自动识别视频平台
"""

import logging
from typing import Optional, List, Type

from agents.video_summary_agent.platforms.base import BasePlatform
from agents.video_summary_agent.platforms.douyin import DouyinPlatform
from agents.video_summary_agent.platforms.bilibili import BilibiliPlatform
from agents.video_summary_agent.platforms.xiaohongshu import XiaohongshuPlatform
from agents.video_summary_agent.platforms.weixin_video import WeixinVideoPlatform

logger = logging.getLogger(__name__)


class PlatformDetector:
    """
    平台识别器
    
    根据URL自动识别是哪个视频平台，返回对应的平台适配器
    """
    
    # 注册的平台列表
    _platforms: List[Type[BasePlatform]] = [
        DouyinPlatform,
        BilibiliPlatform,
        XiaohongshuPlatform,
        WeixinVideoPlatform,
    ]
    
    @classmethod
    def detect(cls, url: str) -> Optional[BasePlatform]:
        """
        识别URL对应的平台
        
        Args:
            url: 视频页面URL
            
        Returns:
            BasePlatform: 平台适配器实例，未识别返回None
        """
        for platform_cls in cls._platforms:
            platform = platform_cls()
            if platform.match(url):
                logger.info(f"[PlatformDetector] 识别到平台: {platform.display_name}")
                return platform
        
        logger.warning(f"[PlatformDetector] 未识别的URL: {url}")
        return None
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """获取支持的平台列表"""
        return [p().display_name for p in cls._platforms]
