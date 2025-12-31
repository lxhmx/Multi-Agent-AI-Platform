"""
Playwright 脚本模板

使用方法：
1. 运行 `playwright codegen <目标网址>` 生成基础代码
2. 复制此文件并重命名为你的技能 ID（如 taobao_order.py）
3. 将 codegen 生成的代码放入 run() 函数中
4. 根据需要添加参数处理逻辑

注意事项：
- run() 函数必须是 async 的
- 第一个参数必须是 page（Playwright Page 对象）
- 返回值应该是一个字典，包含执行结果
"""

from typing import Any, Dict, Optional


async def run(page, **kwargs) -> Dict[str, Any]:
    """
    执行自动化任务
    
    Args:
        page: Playwright Page 对象
        **kwargs: 从 YAML 定义的参数
        
    Returns:
        执行结果字典，建议包含：
        - status: "success" / "error" / "warning"
        - message: 结果描述
        - data: 具体数据（可选）
    """
    result = {
        "status": "success",
        "message": "",
        "data": None
    }
    
    try:
        # ========== 在这里放入 playwright codegen 生成的代码 ==========
        
        # 示例：访问网站
        await page.goto("https://example.com")
        await page.wait_for_load_state("networkidle")
        
        # 示例：获取页面标题
        title = await page.title()
        
        # 示例：点击元素
        # await page.click("button.submit")
        
        # 示例：填写表单
        # await page.fill("input[name='username']", "your_username")
        
        # 示例：等待元素出现
        # await page.wait_for_selector(".result")
        
        # ========== codegen 代码结束 ==========
        
        result["message"] = "任务执行成功"
        result["data"] = {"title": title}
        
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"执行失败: {str(e)}"
    
    return result
