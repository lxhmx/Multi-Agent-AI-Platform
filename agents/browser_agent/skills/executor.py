"""
Skill 执行器

负责执行 Playwright 脚本。
"""

import asyncio
import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from agents.browser_agent.skills.base_skill import Skill
from agents.browser_agent.skills.registry import get_registry

logger = logging.getLogger(__name__)


class SkillExecutor:
    """
    技能执行器
    
    负责加载并执行 Playwright 脚本。
    执行完成后保持浏览器和页面打开，不自动关闭。
    """
    
    def __init__(self, headless: bool = False):
        """
        初始化执行器
        
        Args:
            headless: 是否使用无头模式运行浏览器
        """
        self.headless = headless
        self.registry = get_registry()
        self._browser = None
        self._playwright = None
        self._context = None  # 保持 context 不关闭
        self._page = None     # 保持 page 不关闭
    
    async def _ensure_browser(self):
        """确保浏览器已启动"""
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
        return self._browser
    
    async def _get_page(self):
        """获取页面实例，复用已有的或创建新的"""
        browser = await self._ensure_browser()
        
        # 如果没有 context 或已关闭，创建新的
        if self._context is None:
            self._context = await browser.new_context()
            self._page = await self._context.new_page()
        
        return self._page
    
    async def execute(
        self, 
        skill: Skill, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行技能对应的脚本
        
        Args:
            skill: 要执行的技能
            params: 传递给脚本的参数
            
        Returns:
            执行结果字典，包含 success, message, data 等字段
        """
        params = params or {}
        
        # 获取脚本路径
        skills_dir = Path(__file__).parent
        script_path = skills_dir / skill.script_path
        
        if not script_path.exists():
            return {
                "success": False,
                "message": f"脚本文件不存在: {script_path}",
                "data": None
            }
        
        try:
            # 动态加载脚本模块
            spec = importlib.util.spec_from_file_location(skill.id, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取页面（复用已有的）
            page = await self._get_page()
            
            # 执行脚本的 run 函数
            if hasattr(module, "run"):
                run_func = module.run
                
                # 检查是否是异步函数
                if asyncio.iscoroutinefunction(run_func):
                    result = await run_func(page, **params)
                else:
                    result = run_func(page, **params)
                
                # 不关闭 context 和 page，保持浏览器打开
                
                return {
                    "success": True,
                    "message": f"技能 '{skill.name}' 执行成功",
                    "data": result
                }
            else:
                return {
                    "success": False,
                    "message": f"脚本 {script_path} 缺少 run 函数",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"执行技能 {skill.name} 失败: {e}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "data": None
            }
    
    async def execute_by_id(
        self, 
        skill_id: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        根据技能 ID 执行
        
        Args:
            skill_id: 技能 ID
            params: 参数
            
        Returns:
            执行结果
        """
        skill = self.registry.get(skill_id)
        if not skill:
            return {
                "success": False,
                "message": f"未找到技能: {skill_id}",
                "data": None
            }
        return await self.execute(skill, params)
    
    async def close(self):
        """关闭浏览器和 Playwright（只在明确需要时调用）"""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
