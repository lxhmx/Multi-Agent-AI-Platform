"""
钉钉智能自动化脚本

访问魔塔社区 MCP 广场，搜索钉钉相关服务。
"""

from typing import Any, Dict, Optional


async def run(page, action: str = "browse", keyword: Optional[str] = None) -> Dict[str, Any]:
    """
    执行钉钉相关自动化任务
    
    Args:
        page: Playwright Page 对象
        action: 操作类型
        keyword: 搜索关键词
        
    Returns:
        执行结果字典
    """
    result = {
        "action": action,
        "status": "success",
        "data": None
    }
    
    try:
        # 访问魔塔社区
        await page.goto("https://www.modelscope.cn/home")
        await page.wait_for_load_state("networkidle")
        
        # 点击 MCP 广场
        await page.get_by_role("link", name="MCP广场").click()
        await page.wait_for_load_state("networkidle")
        
        # 搜索钉钉
        search_box = page.get_by_role("textbox", name="搜索MCP服务")
        await search_box.click()
        await search_box.fill("钉钉")
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle")
        await page.get_by_role("link", name="钉钉MCP Hosted 交流协作工具 @open-").click()
        await page.get_by_role("button", name="知道了").click()
        
        # 处理弹出窗口
        async with page.expect_popup() as page1_info:
            await page.get_by_role("link", name="https://open.dingtalk.com/").click()
        page1 = await page1_info.value
        
        result["data"] = {
            "message": "已成功搜索钉钉相关 MCP 服务"
        }
        
    except Exception as e:
        result["status"] = "error"
        result["data"] = {"error": str(e)}
    
    return result
