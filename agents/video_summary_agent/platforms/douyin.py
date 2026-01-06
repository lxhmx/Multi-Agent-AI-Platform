"""
抖音平台适配器
"""

import re
import os
import logging
from typing import Optional

from agents.video_summary_agent.platforms.base import BasePlatform, VideoInfo

logger = logging.getLogger(__name__)


def parse_netscape_cookies(cookie_file: str) -> list:
    """解析 Netscape 格式 cookies 为 Playwright 格式"""
    cookies = []
    
    with open(cookie_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookie = {
                        "name": parts[5],
                        "value": parts[6],
                        "domain": parts[0],
                        "path": parts[2],
                        "secure": parts[3].lower() == "true",
                        "httpOnly": False,
                    }
                    try:
                        expires = int(parts[4])
                        if expires > 0:
                            cookie["expires"] = expires
                    except:
                        pass
                    
                    cookies.append(cookie)
    
    return cookies


class DouyinPlatform(BasePlatform):
    """抖音平台"""
    
    name = "douyin"
    display_name = "抖音"
    patterns = [
        r"douyin\.com/video/(\d+)",
        r"douyin\.com/user/.*?/(\d+)",
        r"v\.douyin\.com/\w+",
        r"douyin\.com/.*[?&]modal_id=(\d+)",  # 支持精选/搜索页面的 modal_id 参数
    ]
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """提取抖音视频ID"""
        # 从 /video/xxx 格式提取
        match = re.search(r"douyin\.com/video/(\d+)", url)
        if match:
            return match.group(1)
        
        # 从 modal_id 参数提取（精选/搜索页面）
        match = re.search(r"[?&]modal_id=(\d+)", url)
        if match:
            return match.group(1)
        
        # 从URL路径最后部分提取
        match = re.search(r"/(\d{15,})(?:\?|$)", url)
        if match:
            return match.group(1)
        return None
    
    def normalize_url(self, url: str) -> str:
        """
        将各种抖音链接格式统一转换为标准的视频页面URL
        
        支持的输入格式:
        - https://www.douyin.com/jingxuan/search/xxx?modal_id=123456
        - https://www.douyin.com/search/xxx?modal_id=123456
        - https://www.douyin.com/user/xxx?modal_id=123456
        - https://www.douyin.com/video/123456
        - https://v.douyin.com/xxx (短链接)
        
        输出格式:
        - https://www.douyin.com/video/123456
        """
        video_id = self.extract_video_id(url)
        if video_id:
            # 如果已经是标准格式，直接返回
            if f"/video/{video_id}" in url:
                return url.split('?')[0]  # 去掉查询参数
            # 转换为标准格式
            normalized = f"https://www.douyin.com/video/{video_id}"
            logger.info(f"[Douyin] URL标准化: {url[:50]}... -> {normalized}")
            return normalized
        # 无法提取ID时返回原URL
        return url
    
    async def get_video_info(self, page_url: str, page=None) -> VideoInfo:
        """
        获取抖音视频真实地址
        
        参考 tests/test_douyin_playwright.py 的实现方式
        """
        from playwright.async_api import async_playwright
        import asyncio
        
        # 获取 cookies 文件路径
        try:
            from config import DOUYIN_COOKIES_FILE
            cookies_file = DOUYIN_COOKIES_FILE
        except ImportError:
            cookies_file = "/opt/app/text2sql/douyin_cookies.txt"
        
        video_url = ""
        title = ""
        author = ""
        video_id = self.extract_video_id(page_url) or ""
        
        # 将URL标准化为 /video/{id} 格式，避免精选/搜索页面无法获取视频
        page_url = self.normalize_url(page_url)
        
        logger.info(f"[Douyin] 目标视频ID: {video_id}, 访问URL: {page_url}")
        
        async with async_playwright() as p:
            logger.info("[Douyin] 启动浏览器...")
            browser = await p.chromium.launch(headless=True)
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            
            # 加载 cookies（如果有）
            if os.path.exists(cookies_file):
                try:
                    cookies = parse_netscape_cookies(cookies_file)
                    if cookies:
                        await context.add_cookies(cookies)
                        logger.info(f"[Douyin] 已加载 {len(cookies)} 个 cookies")
                except Exception as e:
                    logger.warning(f"[Douyin] 加载 cookies 失败: {e}")
            else:
                logger.warning(f"[Douyin] Cookies 文件不存在: {cookies_file}")
            
            page = await context.new_page()
            
            # 监听网络请求，捕获视频地址
            video_urls = []
            
            async def handle_response(response):
                resp_url = response.url
                # 只捕获包含当前视频ID的请求，或者是主视频流
                if any(x in resp_url for x in ['douyinvod', 'v26-web', 'v3-web']):
                    content_type = response.headers.get('content-type', '')
                    if 'video' in content_type or 'octet-stream' in content_type:
                        video_urls.append(resp_url)
                        logger.info(f"[Douyin] 捕获视频URL: {resp_url[:80]}...")
            
            page.on("response", handle_response)
            
            try:
                logger.info(f"[Douyin] 访问: {page_url}")
                await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
                
                # 等待视频加载
                logger.info("[Douyin] 等待视频加载...")
                await asyncio.sleep(5)
                
                # 尝试点击播放按钮（如果有）
                try:
                    play_btn = await page.query_selector('[class*="play"], [class*="Play"]')
                    if play_btn:
                        await play_btn.click()
                        await asyncio.sleep(2)
                except:
                    pass
                
                # 尝试获取视频标题
                try:
                    title_elem = await page.query_selector('[class*="title"], [class*="desc"], h1')
                    if title_elem:
                        title = await title_elem.inner_text()
                except:
                    pass
                
                # 尝试获取作者
                try:
                    author_el = await page.query_selector('[data-e2e="video-author-name"]')
                    if author_el:
                        author = await author_el.inner_text()
                except:
                    pass
                
                # 方法1: 直接从 video 标签获取当前播放的视频
                video_elem = await page.query_selector('video[src]')
                if video_elem:
                    src = await video_elem.get_attribute('src')
                    if src and src.startswith('http') and 'douyinvod' in src:
                        video_url = src
                        logger.info("[Douyin] 从 video 标签获取成功")
                
                # 方法2: 如果 video 标签没有，从捕获的第一个请求获取
                if not video_url and video_urls:
                    video_url = video_urls[0]
                    logger.info("[Douyin] 从网络请求捕获成功")
                
                # 方法3: 从页面脚本中提取
                if not video_url:
                    content = await page.content()
                    
                    # 尝试正则匹配包含视频ID的URL
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
                logger.error(f"[Douyin] 页面加载失败: {e}")
                raise
            
            await browser.close()
        
        return VideoInfo(
            real_url=video_url,
            title=title.strip() if title else "",
            author=author.strip() if author else "",
            video_id=video_id,
        )
