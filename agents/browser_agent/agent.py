"""
浏览器自动化智能体

基于 Browser-Use 实现，可以根据自然语言指令自动操作浏览器。
继承自 BaseAgent，遵循现有的智能体框架模式。
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, List

from langchain_core.tools import BaseTool

from agents.base import BaseAgent
from agents.browser_agent.prompts import SYSTEM_PROMPT, ROUTING_KEYWORDS, detect_task_type
from core.memory import AgentMemory

logger = logging.getLogger(__name__)


class BrowserAgent(BaseAgent):
    """
    浏览器自动化智能体
    
    负责：
    - 解析用户的自然语言指令
    - 使用 Browser-Use 自动操作浏览器
    - 支持网页导航、数据提取、表单填写等任务
    """
    
    name = "browser"
    description = "浏览器自动化智能体，可以根据自然语言指令自动操作浏览器完成各种任务"
    
    def __init__(self):
        self._memory = AgentMemory(max_rounds=10)
        self._browser = None
    
    def get_tools(self) -> List[BaseTool]:
        """
        返回浏览器相关的工具
        
        Browser-Use 内部管理工具，这里返回空列表
        """
        return []
    
    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        return SYSTEM_PROMPT
    
    async def _get_browser(self):
        """获取浏览器实例（懒加载）"""
        if self._browser is None:
            try:
                from browser_use import Browser
                self._browser = Browser(
                    headless=False,
                )
            except ImportError:
                logger.error("browser-use 未安装")
                raise
        return self._browser
    
    async def _create_agent(self, task: str):
        """创建 Browser-Use Agent"""
        try:
            from browser_use import Agent, ChatOpenAI
        except ImportError:
            logger.error("browser-use 未安装，请运行: pip install browser-use playwright")
            raise ImportError("browser-use 未安装，请运行: pip install browser-use playwright")
        
        from config import API_KEY, VANNA_API_BASE
        
        llm = ChatOpenAI(
            model="qwen3-max",
            api_key=API_KEY,
            base_url=VANNA_API_BASE,
            temperature=0.3,
        )
        
        browser = await self._get_browser()
        
        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            use_vision=False,
        )
        return agent

    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """同步执行智能体"""
        return asyncio.run(self._run_async(question, session_id))
    
    async def _run_async(self, question: str, session_id: Optional[str] = None) -> str:
        """异步执行任务"""
        try:
            agent = await self._create_agent(question)
            result = await agent.run()
            output = self._extract_result(result)
            self._memory.add_message(session_id, question, output)
            return output
        except ImportError as e:
            return f"错误：{str(e)}"
        except Exception as e:
            logger.error(f"[BrowserAgent] 执行异常: {e}")
            return f"执行任务时出现错误：{str(e)}"
    
    async def run_stream(
        self, 
        question: str, 
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体
        
        Args:
            question: 用户问题/任务
            session_id: 会话 ID
        
        Yields:
            str: 流式输出的文本片段
        """
        full_output = ""
        
        try:
            task_type = detect_task_type(question)
            
            # 输出开始信息
            start_msg = "🚀 开始执行浏览器任务...\n\n"
            start_msg += f"📋 任务类型: {self._get_task_type_name(task_type)}\n"
            start_msg += f"📝 任务内容: {question}\n\n"
            start_msg += "⏳ 正在启动浏览器，请稍候...\n\n"
            
            full_output += start_msg
            yield start_msg
            
            # 创建 Agent
            try:
                agent = await self._create_agent(question)
            except ImportError as e:
                error_msg = "\n❌ **任务执行失败**\n\n"
                error_msg += "**失败原因：** 缺少必要的依赖库\n\n"
                error_msg += f"**错误详情：** {str(e)}\n\n"
                error_msg += "**解决方案：** 请先安装依赖：\n```bash\npip install browser-use playwright\nplaywright install chromium\n```\n\n"
                error_msg += "安装完成后请重新尝试。"
                full_output += error_msg
                yield error_msg
                self._memory.add_message(session_id, question, full_output)
                return
            
            # 执行任务
            running_msg = "🔄 浏览器已启动，正在执行任务...\n\n"
            yield running_msg
            full_output += running_msg
            
            result = await agent.run()
            result_text = self._extract_result(result)
            
            # 成功完成的消息
            success_msg = "\n✅ **任务执行成功！**\n\n"
            success_msg += f"**执行结果：**\n{result_text}\n\n"
            success_msg += "如果您还有其他需要，请随时告诉我。"
            
            full_output += success_msg
            yield success_msg
            
            self._memory.add_message(session_id, question, full_output)
                
        except Exception as e:
            logger.error(f"[BrowserAgent] 流式处理异常: {e}")
            error_msg = "\n❌ **任务执行失败**\n\n"
            error_msg += f"**失败原因：** {str(e)}\n\n"
            error_msg += "**建议：**\n"
            error_msg += "- 检查网络连接是否正常\n"
            error_msg += "- 确认目标网站是否可访问\n"
            error_msg += "- 尝试简化任务描述后重试\n\n"
            error_msg += "如需帮助，请提供更多详情。"
            
            full_output += error_msg
            yield error_msg
            self._memory.add_message(session_id, question, full_output)
    
    def _extract_result(self, result) -> str:
        """从 Browser-Use 结果中提取文本"""
        if result is None:
            return "任务已完成，但没有返回具体结果。"
        
        if isinstance(result, str):
            return result
        
        if hasattr(result, 'final_result'):
            return str(result.final_result()) if callable(result.final_result) else str(result.final_result)
        
        if hasattr(result, 'history') and result.history:
            last_item = result.history[-1] if result.history else None
            if last_item and hasattr(last_item, 'result'):
                return str(last_item.result)
        
        return str(result)
    
    def _get_task_type_name(self, task_type: str) -> str:
        """获取任务类型的中文名称"""
        type_names = {
            "search": "搜索任务",
            "scrape": "数据采集",
            "form": "表单操作",
            "navigate": "网页导航",
            "download": "文件下载",
            "general": "通用任务",
        }
        return type_names.get(task_type, "通用任务")

    def can_handle(self, question: str) -> float:
        """判断是否适合处理该问题"""
        question_lower = question.lower()
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question_lower)
        
        if matched == 0:
            return 0.2
        
        score = 0.6 + (matched * 0.1)
        return min(score, 1.0)
    
    def clear_memory(self, session_id: str) -> None:
        """清除指定会话的记忆"""
        self._memory.clear(session_id)
    
    async def close(self):
        """关闭浏览器"""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")
            finally:
                self._browser = None
