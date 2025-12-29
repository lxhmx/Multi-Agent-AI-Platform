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
                # 新版 API：直接在 Browser 构造函数中传参数
                self._browser = Browser(
                    headless=False,  # 显示浏览器窗口
                    # channel="chrome",  # 使用系统 Chrome（可选）
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
        
        # 使用 browser-use 自带的 ChatOpenAI
        from config import API_KEY, VANNA_API_BASE
        
        # 使用 qwen-plus（通义千问），更稳定，不会有推理模式的 JSON 格式问题
        # 如果想用 DeepSeek，可以改为 "deepseek-v3.2" 或 "deepseek-v3.1"
        llm = ChatOpenAI(
            model="qwen-plus",  # 通义千问 Plus，稳定可靠
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
        """
        同步执行智能体
        
        Args:
            question: 用户问题/任务
            session_id: 会话 ID
        
        Returns:
            str: 执行结果
        """
        return asyncio.run(self._run_async(question, session_id))
    
    async def _run_async(self, question: str, session_id: Optional[str] = None) -> str:
        """异步执行任务"""
        try:
            agent = await self._create_agent(question)
            result = await agent.run()
            
            # 提取结果文本
            output = self._extract_result(result)
            
            # 保存到历史
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
        
        由于 Browser-Use 的特性，这里采用分步骤输出的方式
        
        Args:
            question: 用户问题/任务
            session_id: 会话 ID
        
        Yields:
            str: 流式输出的文本片段
        """
        full_output = ""
        
        try:
            # 检测任务类型
            task_type = detect_task_type(question)
            
            # 输出开始信息
            start_msg = f"🚀 开始执行浏览器任务...\n\n"
            start_msg += f"📋 任务类型: {self._get_task_type_name(task_type)}\n"
            start_msg += f"📝 任务内容: {question}\n\n"
            start_msg += "⏳ 正在启动浏览器，请稍候...\n\n"
            
            full_output += start_msg
            yield start_msg
            
            # 创建并执行 Agent
            try:
                agent = await self._create_agent(question)
            except ImportError as e:
                error_msg = f"\n❌ 错误：{str(e)}\n\n请先安装依赖：\n```bash\npip install browser-use playwright\nplaywright install chromium\n```"
                full_output += error_msg
                yield error_msg
                self._memory.add_message(session_id, question, full_output)
                return
            
            # 执行任务
            yield "🔄 浏览器已启动，正在执行任务...\n\n"
            full_output += "🔄 浏览器已启动，正在执行任务...\n\n"
            
            result = await agent.run()
            
            # 提取并输出结果
            result_text = self._extract_result(result)
            
            result_msg = f"\n✅ 任务执行完成！\n\n"
            result_msg += f"📊 执行结果:\n{result_text}\n"
            
            full_output += result_msg
            yield result_msg
            
            # 保存到历史
            self._memory.add_message(session_id, question, full_output)
                
        except Exception as e:
            logger.error(f"[BrowserAgent] 流式处理异常: {e}")
            error_msg = f"\n❌ 执行任务时出现错误：{str(e)}"
            yield error_msg
            self._memory.add_message(session_id, question, full_output + error_msg)
    
    def _extract_result(self, result) -> str:
        """从 Browser-Use 结果中提取文本"""
        if result is None:
            return "任务已完成，但没有返回具体结果。"
        
        if isinstance(result, str):
            return result
        
        # Browser-Use 返回的是 AgentHistoryList
        if hasattr(result, 'final_result'):
            return str(result.final_result()) if callable(result.final_result) else str(result.final_result)
        
        if hasattr(result, 'history') and result.history:
            # 获取最后一个历史记录
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
        """
        判断是否适合处理该问题
        
        浏览器相关问题返回高置信度。
        
        Args:
            question: 用户问题
        
        Returns:
            float: 0-1 的置信度分数
        """
        question_lower = question.lower()
        
        # 计算关键词匹配数量
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question_lower)
        
        if matched == 0:
            return 0.2
        
        # 基础分 0.6，每匹配一个关键词增加分数
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
