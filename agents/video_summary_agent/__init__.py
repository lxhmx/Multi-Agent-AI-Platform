"""
视频内容总结智能体

支持平台：抖音、B站、小红书、视频号
功能：自动识别平台 → 获取真实URL → 下载视频 → AI分析总结
"""

from agents.video_summary_agent.agent import VideoSummaryAgent
from agents.video_summary_agent.pipeline import VideoPipeline, PipelineResult

__all__ = [
    "VideoSummaryAgent",
    "VideoPipeline",
    "PipelineResult",
]
