"""
视频平台基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class VideoInfo:
    """视频信息"""
    real_url: str           # 真实视频URL
    title: str = ""         # 视频标题
    author: str = ""        # 作者
    video_id: str = ""      # 视频ID
    cover_url: str = ""     # 封面URL
    duration: int = 0       # 时长（秒）


class BasePlatform(ABC):
    """
    视频平台基类
    
    每个平台需要实现：
    - name: 平台英文名称（用于文件命名）
    - display_name: 平台显示名称
    - patterns: URL匹配正则列表
    - get_video_info(): 获取视频信息
    """
    
    name: str = "base"
    display_name: str = "基础平台"
    patterns: List[str] = []
    
    def match(self, url: str) -> bool:
        """检查URL是否匹配该平台"""
        for pattern in self.patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        return None
    
    @abstractmethod
    async def get_video_info(self, page_url: str, page=None) -> VideoInfo:
        """
        获取视频真实地址和信息
        
        Args:
            page_url: 浏览器地址栏复制的URL
            page: Playwright page对象（可选，用于复用）
            
        Returns:
            VideoInfo: 视频信息
        """
        pass
