"""
B站平台适配器
"""

import re
import logging
from typing import Optional

from agents.video_summary_agent.platforms.base import BasePlatform, VideoInfo

logger = logging.getLogger(__name__)


class BilibiliPlatform(BasePlatform):
    """B站平台"""
    
    name = "bilibili"
    display_name = "B站"
    patterns = [
        r"bilibili\.com/video/(BV\w+)",
        r"bilibili\.com/video/(av\d+)",
        r"b23\.tv/\w+",
    ]
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """提取B站视频ID（BV号或av号）"""
        match = re.search(r"bilibili\.com/video/(BV\w+|av\d+)", url)
        if match:
            return match.group(1)
        return None
    
    async def get_video_info(self, page_url: str, page=None) -> VideoInfo:
        """
        获取B站视频真实地址
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
                # B站视频CDN特征
                if "bilivideo" in url or ".m4s" in url or "upos-sz" in url:
                    captured_urls.append(url)
            
            page.on("response", handle_response)
            
            await page.goto(page_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 获取标题
            try:
                title_el = await page.query_selector("h1.video-title")
                if title_el:
                    title = await title_el.inner_text()
            except Exception as e:
                logger.warning(f"获取标题失败: {e}")
            
            # 获取作者
            try:
                author_el = await page.query_selector(".up-name")
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
                # 选择视频流（非音频）
                for url in captured_urls:
                    if "video" in url.lower() or ".m4s" in url:
                        video_url = url
                        break
                if not video_url:
                    video_url = captured_urls[0]
            
            logger.info(f"[Bilibili] 获取到视频URL: {video_url[:100] if video_url else 'None'}...")
            
        except Exception as e:
            logger.error(f"[Bilibili] 获取视频信息失败: {e}")
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
