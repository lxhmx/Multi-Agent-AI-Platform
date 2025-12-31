"""
流程图导出服务

调用 draw-image-export2 服务将 mxGraphModel XML 转换为图片。
"""

import logging
import aiohttp
from typing import Optional

from config import EXPORT_SERVER_URL

logger = logging.getLogger(__name__)


class DiagramExporter:
    """
    图表导出器
    
    调用 draw-image-export2 服务将 XML 转换为图片。
    """
    
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or EXPORT_SERVER_URL
    
    async def export_to_image(
        self,
        xml: str,
        format: str = "png",
        bg: str = "#ffffff",
        scale: float = 1.5,
        border: int = 10
    ) -> bytes:
        """
        将 mxGraphModel XML 转换为图片
        
        Args:
            xml: mxGraphModel XML 内容
            format: 输出格式 (png, jpg, svg, pdf)
            bg: 背景颜色
            scale: 缩放比例
            border: 边框大小
        
        Returns:
            bytes: 图片二进制数据
        
        Raises:
            ExportError: 导出失败时抛出
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "xml": xml,
                    "format": format,
                    "bg": bg,
                    "scale": str(scale),
                    "border": str(border)
                }
                
                logger.info(f"[Exporter] 调用导出服务: {self.server_url}")
                logger.debug(f"[Exporter] XML 长度: {len(xml)}")
                
                async with session.post(
                    self.server_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Exporter] 导出失败: {response.status} - {error_text}")
                        raise ExportError(f"导出服务返回错误: {response.status}")
                    
                    image_bytes = await response.read()
                    logger.info(f"[Exporter] 导出成功，图片大小: {len(image_bytes)} bytes")
                    return image_bytes
                    
        except aiohttp.ClientError as e:
            logger.error(f"[Exporter] 网络错误: {e}")
            raise ExportError(f"无法连接导出服务: {e}")
        except Exception as e:
            logger.error(f"[Exporter] 导出异常: {e}")
            raise ExportError(f"导出失败: {e}")
    
    def export_to_image_sync(
        self,
        xml: str,
        format: str = "png",
        bg: str = "#ffffff",
        scale: float = 1.5,
        border: int = 10
    ) -> bytes:
        """
        同步版本的导出方法
        
        使用 requests 库进行同步调用。
        """
        import requests
        
        try:
            data = {
                "xml": xml,
                "format": format,
                "bg": bg,
                "scale": str(scale),
                "border": str(border)
            }
            
            logger.info(f"[Exporter] 同步调用导出服务: {self.server_url}")
            
            response = requests.post(
                self.server_url,
                data=data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"[Exporter] 导出失败: {response.status_code} - {response.text}")
                raise ExportError(f"导出服务返回错误: {response.status_code}")
            
            logger.info(f"[Exporter] 导出成功，图片大小: {len(response.content)} bytes")
            return response.content
            
        except requests.RequestException as e:
            logger.error(f"[Exporter] 网络错误: {e}")
            raise ExportError(f"无法连接导出服务: {e}")


class ExportError(Exception):
    """导出错误"""
    pass


# 全局单例
_exporter: Optional[DiagramExporter] = None


def get_exporter() -> DiagramExporter:
    """获取导出器单例"""
    global _exporter
    if _exporter is None:
        _exporter = DiagramExporter()
    return _exporter
