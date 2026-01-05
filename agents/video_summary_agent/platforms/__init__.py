"""
视频平台适配器模块
"""

from agents.video_summary_agent.platforms.base import BasePlatform
from agents.video_summary_agent.platforms.douyin import DouyinPlatform
from agents.video_summary_agent.platforms.bilibili import BilibiliPlatform
from agents.video_summary_agent.platforms.xiaohongshu import XiaohongshuPlatform
from agents.video_summary_agent.platforms.weixin_video import WeixinVideoPlatform

__all__ = [
    "BasePlatform",
    "DouyinPlatform",
    "BilibiliPlatform",
    "XiaohongshuPlatform",
    "WeixinVideoPlatform",
]
