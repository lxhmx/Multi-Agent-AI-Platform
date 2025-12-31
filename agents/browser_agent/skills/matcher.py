"""
Skill 匹配器

使用 LLM 根据用户输入和对话历史匹配最合适的技能。
LLM 能理解上下文，比如用户说"确认"时知道是确认执行之前提到的技能。
"""

import json
import logging
from typing import Optional, List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from agents.browser_agent.skills.base_skill import Skill
from agents.browser_agent.skills.registry import get_registry

logger = logging.getLogger(__name__)

# LLM 技能匹配的系统提示词
MATCHER_SYSTEM_PROMPT = """你是一个浏览器自动化助手，负责理解用户意图并匹配合适的技能。

## 可用技能
{skills_description}

## 你的任务
根据用户的输入和对话历史，判断用户想要做什么，返回 JSON 格式的结果。

## 返回格式
必须返回有效的 JSON，格式如下：
```json
{{
    "action": "execute_skill" | "confirm_skill" | "cancel" | "none",
    "skill_id": "技能ID（如果 action 是 execute_skill 或 confirm_skill）",
    "reason": "简短说明你的判断理由"
}}
```

## action 说明
- "execute_skill": 用户明确要求执行某个技能（如"执行魔塔社区脚本"）
- "confirm_skill": 用户在确认执行之前提到的技能（如回复"确认"、"好"、"是"）
- "cancel": 用户取消或拒绝执行（如"取消"、"不要"、"算了"）
- "none": 用户的请求与技能无关，或无法匹配到任何技能

## 重要规则
1. 仔细阅读对话历史，理解上下文
2. 如果上一轮 AI 询问用户是否确认执行某技能，而用户回复了肯定词（确认/好/是/yes/ok），则 action 应为 "confirm_skill"
3. 如果用户的输入与任何技能都不相关，返回 action: "none"
4. 只返回 JSON，不要有其他内容
"""


class SkillMatcher:
    """
    技能匹配器
    
    使用 LLM 理解用户意图和对话上下文，智能匹配技能。
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        初始化匹配器
        
        Args:
            llm: LangChain LLM 实例
        """
        self.llm = llm
        self.registry = get_registry()
    
    def match_by_keywords(self, user_input: str) -> Optional[Skill]:
        """
        基于关键词快速匹配技能（不使用 LLM）
        
        Args:
            user_input: 用户输入
            
        Returns:
            匹配到的技能，如果没有匹配则返回 None
        """
        user_input_lower = user_input.lower()
        skills = self.registry.get_all()
        
        best_match: Optional[Skill] = None
        best_score = 0
        
        for skill in skills:
            score = 0
            
            # 检查技能名称
            if skill.name.lower() in user_input_lower:
                score += 10
            
            # 检查触发词
            for trigger in skill.triggers:
                if trigger.lower() in user_input_lower:
                    score += 5
            
            # 检查 ID
            if skill.id.lower() in user_input_lower:
                score += 3
            
            if score > best_score:
                best_score = score
                best_match = skill
        
        if best_score > 0:
            logger.info(f"关键词匹配成功: {best_match.name} (score: {best_score})")
            return best_match
        
        return None
    
    async def match_with_context(
        self, 
        user_input: str, 
        history: List[BaseMessage]
    ) -> Dict[str, Any]:
        """
        使用 LLM 结合对话历史进行智能匹配
        
        Args:
            user_input: 用户当前输入
            history: 对话历史
            
        Returns:
            匹配结果字典，包含 action, skill_id, reason
        """
        if self.llm is None:
            logger.warning("LLM 未配置，回退到关键词匹配")
            skill = self.match_by_keywords(user_input)
            if skill:
                return {
                    "action": "execute_skill",
                    "skill_id": skill.id,
                    "reason": "关键词匹配"
                }
            return {"action": "none", "skill_id": None, "reason": "无匹配"}
        
        # 构建技能描述
        skills_desc = self.registry.get_skills_prompt()
        
        # 构建消息列表
        system_prompt = MATCHER_SYSTEM_PROMPT.format(skills_description=skills_desc)
        messages = [SystemMessage(content=system_prompt)]
        
        # 添加历史对话
        messages.extend(history)
        
        # 添加当前用户输入
        messages.append(HumanMessage(content=user_input))
        
        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            
            # 提取 JSON（处理可能的 markdown 代码块）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            logger.info(f"LLM 匹配结果: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM 返回的 JSON 解析失败: {e}, content: {content}")
            # 回退到关键词匹配
            skill = self.match_by_keywords(user_input)
            if skill:
                return {
                    "action": "execute_skill",
                    "skill_id": skill.id,
                    "reason": "JSON解析失败，回退到关键词匹配"
                }
            return {"action": "none", "skill_id": None, "reason": "解析失败"}
            
        except Exception as e:
            logger.error(f"LLM 匹配失败: {e}")
            return {"action": "none", "skill_id": None, "reason": str(e)}
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """根据 ID 获取技能"""
        return self.registry.get(skill_id)
    
    def get_all_skills_for_prompt(self) -> str:
        """获取所有技能的描述，用于构建 prompt"""
        return self.registry.get_skills_prompt()
