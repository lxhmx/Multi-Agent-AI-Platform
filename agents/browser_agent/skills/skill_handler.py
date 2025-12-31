"""
Skill 处理器

集成 Matcher 和 Executor，提供统一的技能处理接口。
使用 LLM 理解对话上下文，智能处理用户请求。
"""

import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage

from agents.browser_agent.skills.registry import get_registry
from agents.browser_agent.skills.matcher import SkillMatcher
from agents.browser_agent.skills.executor import SkillExecutor

logger = logging.getLogger(__name__)


class SkillHandler:
    """
    技能处理器
    
    整合技能匹配和执行功能，使用 LLM 理解对话上下文。
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None, headless: bool = False):
        """
        初始化处理器
        
        Args:
            llm: LLM 实例，用于语义匹配
            headless: 是否使用无头浏览器
        """
        self.registry = get_registry()
        self.matcher = SkillMatcher(llm=llm)
        self.executor = SkillExecutor(headless=headless)
        
        # 确保技能已加载
        self.registry.load()
    
    async def handle(
        self, 
        user_input: str, 
        history: Optional[List[BaseMessage]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入，使用 LLM 理解上下文并匹配执行技能
        
        Args:
            user_input: 用户输入
            history: 对话历史
            params: 额外参数
            
        Returns:
            处理结果
        """
        history = history or []
        
        # 使用 LLM 理解用户意图
        match_result = await self.matcher.match_with_context(user_input, history)
        action = match_result.get("action", "none")
        skill_id = match_result.get("skill_id")
        reason = match_result.get("reason", "")
        
        # 根据 action 处理
        if action == "none":
            return {
                "success": False,
                "matched": False,
                "action": "none",
                "message": "未识别到技能请求",
                "reason": reason,
                "available_skills": [s.name for s in self.registry.get_all()]
            }
        
        if action == "cancel":
            return {
                "success": True,
                "matched": True,
                "action": "cancel",
                "message": "已取消操作",
                "reason": reason
            }
        
        # execute_skill 或 confirm_skill 都需要执行技能
        if action in ("execute_skill", "confirm_skill"):
            skill = self.matcher.get_skill(skill_id)
            
            if not skill:
                return {
                    "success": False,
                    "matched": False,
                    "action": action,
                    "message": f"未找到技能: {skill_id}",
                    "reason": reason
                }
            
            # 如果是 execute_skill 且技能需要确认，先返回确认请求
            if action == "execute_skill" and skill.require_confirmation:
                return {
                    "success": True,
                    "matched": True,
                    "action": "need_confirm",
                    "skill": skill.name,
                    "skill_id": skill.id,
                    "message": f"即将执行技能: **{skill.name}**\n\n{skill.description}\n\n请回复「确认」继续执行，或「取消」放弃。",
                    "reason": reason
                }
            
            # 执行技能
            result = await self.executor.execute(skill, params)
            result["matched"] = True
            result["action"] = action
            result["skill"] = skill.name
            result["skill_id"] = skill.id
            result["reason"] = reason
            
            return result
        
        # 未知 action
        return {
            "success": False,
            "matched": False,
            "action": action,
            "message": f"未知操作: {action}",
            "reason": reason
        }
    
    async def handle_stream(
        self, 
        user_input: str,
        history: Optional[List[BaseMessage]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式处理用户输入
        
        Args:
            user_input: 用户输入
            history: 对话历史
            params: 额外参数
            
        Yields:
            处理进度和结果
        """
        history = history or []
        
        yield "🔍 正在理解您的请求...\n\n"
        
        # 使用 LLM 理解用户意图
        match_result = await self.matcher.match_with_context(user_input, history)
        action = match_result.get("action", "none")
        skill_id = match_result.get("skill_id")
        
        if action == "none":
            yield "❌ 未识别到技能请求\n\n"
            yield "**可用技能:**\n"
            for s in self.registry.get_all():
                yield f"- {s.name}: {s.description}\n"
            return
        
        if action == "cancel":
            yield "✅ 已取消操作\n"
            return
        
        # execute_skill 或 confirm_skill
        if action in ("execute_skill", "confirm_skill"):
            skill = self.matcher.get_skill(skill_id)
            
            if not skill:
                yield f"❌ 未找到技能: {skill_id}\n"
                return
            
            # 如果是 execute_skill 且需要确认
            if action == "execute_skill" and skill.require_confirmation:
                yield f"✅ 匹配到技能: **{skill.name}**\n"
                yield f"📝 {skill.description}\n\n"
                yield "⚠️ 此技能需要确认后执行\n"
                yield "请回复「确认」来执行，或「取消」放弃\n"
                return
            
            # 执行技能
            if action == "confirm_skill":
                yield f"✅ 收到确认，开始执行: **{skill.name}**\n\n"
            else:
                yield f"✅ 匹配到技能: **{skill.name}**\n\n"
            
            yield "🚀 正在执行...\n\n"
            
            result = await self.executor.execute(skill, params)
            
            if result["success"]:
                yield f"✅ **执行成功**\n\n"
                yield f"{result['message']}\n"
                if result.get("data"):
                    yield f"\n**结果:**\n```\n{result['data']}\n```\n"
            else:
                yield f"❌ **执行失败**\n\n"
                yield f"{result['message']}\n"
    
    def is_skill_request(self, user_input: str) -> bool:
        """
        快速判断用户输入是否可能是技能请求（不使用 LLM）
        
        用于在 BrowserAgent 中快速决定是否走 Skills 流程
        """
        # 检查是否包含技能相关关键词
        skill_keywords = ["执行", "运行", "启动", "脚本", "技能", "skill", "确认", "取消"]
        user_input_lower = user_input.lower()
        
        for keyword in skill_keywords:
            if keyword in user_input_lower:
                return True
        
        # 检查是否匹配任何技能的触发词
        skill = self.matcher.match_by_keywords(user_input)
        return skill is not None
    
    async def close(self):
        """关闭资源"""
        await self.executor.close()
