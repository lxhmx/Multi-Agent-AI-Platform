"""
微信视频号平台适配器
"""

import re
import logging
from typing import Optional

from agents.video_summary_agent.platforms.base import BasePlatform, VideoInfo

logger = logging.getLogger(__name__)


class WeixinVideoPlatform(BasePlatform):
    """微信视频号平台"""
    
    name = "weixin_video"
    display_name = "视频号"
    patterns = [
        r"channels\.weixin\.qq\.com/",
        r"finder\.video\.qq\.com/",
    ]
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """提取视频号ID"""
        # 视频号URL结构较复杂，尝试提取feed_id
        match = re.search(r"feed_id=(\w+)", url)
        if match:
            return match.group(1)
        return None
    
    async def get_video_info(self, page_url: str, page=None) -> VideoInfo:
        """
        获取视频号视频真实地址
        """
        from playwright.async_api import async_playwright
        
        video_url = ""
        title = ""
        author = ""
        video_id = self.extract_video_id(page_url) or ""
        
        own_browser = page is None
        playwright = None
        browser = None
        
        try:
            if own_browser:
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
            
            captured_urls = []
            
            async def handle_response(response):
                url = response.url
                content_type = response.headers.get("content-type", "")
                # 视频号CDN特征
                if "video" in content_type or ".mp4" in url or "finder.video" in url:
                    captured_urls.append(url)
            
            page.on("response", handle_response)
            
            await page.goto(page_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(5000)  # 视频号加载较慢
            
            # 获取标题
            try:
                title_el = await page.query_selector(".feed-desc")
                if title_el:
                    title = await title_el.inner_text()
            except Exception as e:
                logger.warning(f"获取标题失败: {e}")
            
            # 获取作者
            try:
                author_el = await page.query_selector(".finder-nickname")
                if author_el:
                    author = await author_el.inner_text()
            except Exception as e:
                logger.warning(f"获取作者失败: {e}")
            
            # 尝试从video标签获取
            if not captured_urls:
                try:
                    video_el = await page.query_selector("video")
                    if video_el:
                        src = await video_el.get_attribute("src")
                        if src:
                            captured_urls.append(src)
                except Exception:
                    pass
            
            if captured_urls:
                video_url = captured_urls[-1]
            
            logger.info(f"[WeixinVideo] 获取到视频URL: {video_url[:100] if video_url else 'None'}...")
            
        except Exception as e:
            logger.error(f"[WeixinVideo] 获取视频信息失败: {e}")
            raise
        finally:
            if own_browser:
                if browser:
                    await browser.close()
                if playwright:
                    await playwright.stop()
        
        return VideoInfo(
            real_url=video_url,
            title=title.strip() if title else "",
            author=author.strip() if author else "",
            video_id=video_id,
        )
