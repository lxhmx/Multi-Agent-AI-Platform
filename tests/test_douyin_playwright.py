"""
测试抖音视频解析 - 使用 Playwright 模拟浏览器

安装：
    pip install playwright
    playwright install chromium
"""

import asyncio
import json
import os
import re
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请先安装 playwright:")
    print("  pip install playwright")
    print("  playwright install chromium")
    exit(1)


async def parse_douyin_video(url: str) -> dict:
    """使用 Playwright 解析抖音视频"""
    
    result = {
        "success": False,
        "title": "",
        "video_url": "",
        "message": ""
    }
    
    os.makedirs("test_downloads", exist_ok=True)
    
    async with async_playwright() as p:
        print("启动浏览器...")
        browser = await p.chromium.launch(
            headless=True,  # 无头模式，后台运行不显示窗口
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        
        # 加载 cookies（如果有）- 支持 Windows 和 Linux
        cookies_files = [
            r"C:\Users\lxh10\Downloads\douyin_cookies.txt",  # Windows
            "/opt/app/video/cookies/douyin_cookies.txt",     # Linux
        ]
        
        cookies_file = None
        for f in cookies_files:
            if os.path.exists(f):
                cookies_file = f
                break
        
        if cookies_file:
            try:
                cookies = parse_netscape_cookies(cookies_file)
                if cookies:
                    await context.add_cookies(cookies)
                    print(f"已加载 {len(cookies)} 个 cookies")
            except Exception as e:
                print(f"加载 cookies 失败: {e}")
        
        page = await context.new_page()
        
        # 提取视频ID用于匹配
        video_id = url.split("/video/")[-1].split("?")[0]
        print(f"目标视频ID: {video_id}")
        
        # 监听网络请求，捕获视频地址
        video_urls = []
        
        async def handle_response(response):
            resp_url = response.url
            # 只捕获包含当前视频ID的请求，或者是主视频流
            if any(x in resp_url for x in ['douyinvod', 'v26-web', 'v3-web']):
                content_type = response.headers.get('content-type', '')
                if 'video' in content_type or 'octet-stream' in content_type:
                    # 记录URL和请求时间，后面取第一个（当前视频）
                    video_urls.append(resp_url)
                    print(f"捕获视频URL: {resp_url[:80]}...")
        
        page.on("response", handle_response)
        
        try:
            print(f"访问: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 等待视频加载
            print("等待视频加载...")
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
                    result["title"] = await title_elem.inner_text()
            except:
                pass
            
            # 方法1: 直接从 video 标签获取当前播放的视频
            video_elem = await page.query_selector('video[src]')
            if video_elem:
                src = await video_elem.get_attribute('src')
                if src and src.startswith('http') and 'douyinvod' in src:
                    result["video_url"] = src
                    result["success"] = True
                    result["message"] = "从 video 标签获取成功"
            
            # 方法2: 如果 video 标签没有，从捕获的第一个请求获取
            if not result["success"] and video_urls:
                # 取第一个捕获的视频（通常是当前播放的）
                result["video_url"] = video_urls[0]
                result["success"] = True
                result["message"] = "从网络请求捕获成功"
            
            # 方法3: 从页面脚本中提取
            if not result["success"]:
                content = await page.content()
                
                # 保存页面供调试
                with open("test_downloads/douyin_playwright.html", "w", encoding="utf-8") as f:
                    f.write(content)
                
                # 尝试正则匹配包含视频ID的URL
                patterns = [
                    rf'(https?://[^"\']+douyinvod[^"\']*{video_id}[^"\']*)',
                    r'(https?://[^"\']+douyinvod[^"\']+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        video_url = match.group(1).replace("\\u002F", "/")
                        result["video_url"] = video_url
                        result["success"] = True
                        result["message"] = f"正则匹配成功"
                        break
            
            if not result["success"]:
                result["message"] = "未找到视频地址"
                
        except Exception as e:
            result["message"] = f"页面加载失败: {str(e)}"
        
        await browser.close()
    
    return result


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


async def download_video(video_url: str, output_path: str) -> bool:
    """下载视频"""
    import httpx
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.douyin.com/",
    }
    
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=120) as client:
            print(f"下载视频: {video_url[:80]}...")
            resp = await client.get(video_url)
            
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                print(f"✅ 下载成功: {output_path} ({len(resp.content) / 1024 / 1024:.2f} MB)")
                return True
            else:
                print(f"❌ 下载失败: HTTP {resp.status_code}, 大小: {len(resp.content)}")
                return False
    except Exception as e:
        print(f"❌ 下载出错: {e}")
        return False


async def main():
    # 测试链接
    test_url = "https://www.douyin.com/video/7579458345313127680"
    
    print("=" * 60)
    print("抖音视频解析测试 (Playwright)")
    print("=" * 60)
    
    result = await parse_douyin_video(test_url)
    
    print(f"\n{'='*60}")
    print("解析结果:")
    print(f"  成功: {'✅' if result['success'] else '❌'}")
    print(f"  标题: {result['title'][:50] if result['title'] else '无'}")
    print(f"  视频URL: {result['video_url'][:100] if result['video_url'] else '无'}...")
    print(f"  信息: {result['message']}")
    
    # 尝试下载
    if result["success"] and result["video_url"]:
        print(f"\n{'='*60}")
        print("尝试下载视频...")
        await download_video(result["video_url"], "test_downloads/douyin_test.mp4")


if __name__ == "__main__":
    asyncio.run(main())
