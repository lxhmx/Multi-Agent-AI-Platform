"""
抖音平台适配器
"""

import re
import logging
from typing import Optional

from agents.video_summary_agent.platforms.base import BasePlatform, VideoInfo

logger = logging.getLogger(__name__)


class DouyinPlatform(BasePlatform):
    """抖音平台"""
    
    name = "douyin"
    display_name = "抖音"
    patterns = [
        r"douyin\.com/video/(\d+)",
        r"douyin\.com/user/.*?/(\d+)",
        r"v\.douyin\.com/\w+",
    ]
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """提取抖音视频ID"""
        # 从 /video/xxx 格式提取
        match = re.search(r"douyin\.com/video/(\d+)", url)
        if match:
            return match.group(1)
        # 从URL路径最后部分提取
        match = re.search(r"/(\d{15,})(?:\?|$)", url)
        if match:
            return match.group(1)
        return None
    
    async def get_video_info(self, page_url: str, page=None) -> VideoInfo:
        """
        获取抖音视频真实地址
        
        通过Playwright访问页面，拦截网络请求获取视频URL
        使用视频ID过滤匹配目标视频
        """
        from playwright.async_api import async_playwright
        
        video_url = ""
        title = ""
        author = ""
        video_id = self.extract_video_id(page_url) or ""
        
        logger.info(f"[Douyin] 目标视频ID: {video_id}")
        
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
            
            # 存储拦截到的视频URL
            captured_urls = []
            
            async def handle_response(response):
                url = response.url
                content_type = response.headers.get("content-type", "")
                # 匹配抖音视频CDN特征
                if any(x in url for x in ['douyinvod', 'v26-web', 'v3-web', 'v9-web']):
                    if 'video' in content_type or 'octet-stream' in content_type:
                        captured_urls.append(url)
                        logger.info(f"[Douyin] 捕获视频URL: {url[:80]}...")
            
            page.on("response", handle_response)
            
            # 访问页面
            logger.info(f"[Douyin] 访问: {page_url}")
            await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            
            # 等待视频加载
            await page.wait_for_timeout(5000)
            
            # 尝试点击播放按钮
            try:
                play_btn = await page.query_selector('[class*="play"], [class*="Play"]')
                if play_btn:
                    await play_btn.click()
                    await page.wait_for_timeout(2000)
            except Exception:
                pass
            
            # 尝试获取标题
            try:
                title_el = await page.query_selector('[class*="title"], [class*="desc"], h1')
                if title_el:
                    title = await title_el.inner_text()
            except Exception as e:
                logger.warning(f"获取标题失败: {e}")
            
            # 尝试获取作者
            try:
                author_el = await page.query_selector('[data-e2e="video-author-name"]')
                if author_el:
                    author = await author_el.inner_text()
            except Exception as e:
                logger.warning(f"获取作者失败: {e}")
            
            # 方法1: 从video标签获取当前播放的视频
            video_el = await page.query_selector('video[src]')
            if video_el:
                src = await video_el.get_attribute('src')
                if src and src.startswith('http') and 'douyinvod' in src:
                    video_url = src
                    logger.info("[Douyin] 从video标签获取成功")
            
            # 方法2: 从捕获的请求中获取（取第一个，通常是当前视频）
            if not video_url and captured_urls:
                video_url = captured_urls[0]
                logger.info("[Douyin] 从网络请求捕获成功")
            
            # 方法3: 从页面脚本中正则匹配（带视频ID过滤）
            if not video_url and video_id:
                content = await page.content()
                # 优先匹配包含视频ID的URL
                patterns = [
                    rf'(https?://[^"\']+douyinvod[^"\']*{video_id}[^"\']*)',
                    r'(https?://[^"\']+douyinvod[^"\']+)',
                ]
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        video_url = match.group(1).replace("\\u002F", "/")
                        logger.info(f"[Douyin] 正则匹配成功")
                        break
            
            if video_url:
                logger.info(f"[Douyin] 获取到视频URL: {video_url[:100]}...")
            else:
                logger.warning("[Douyin] 未找到视频地址")
            
        except Exception as e:
            logger.error(f"[Douyin] 获取视频信息失败: {e}")
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
