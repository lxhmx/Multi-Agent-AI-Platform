"""
Browser Skills 模块

基于 Anthropic Skills 概念实现的浏览器自动化技能框架。
每个 Skill 对应一个 Playwright 脚本，通过 YAML 定义元数据，
LLM 根据用户意图自动匹配并执行对应脚本。

使用方法：
1. 在 skills/definitions/ 目录下创建 YAML 技能定义文件
2. 在 skills/scripts/ 目录下创建对应的 Playwright 脚本
3. 使用 SkillHandler 处理用户请求

示例：
    from agents.browser_agent.skills import SkillHandler
    
    handler = SkillHandler(llm=your_llm)
    result = await handler.handle("执行魔塔社区脚本")
"""

from agents.browser_agent.skills.base_skill import Skill, SkillParameter
from agents.browser_agent.skills.registry import SkillRegistry, get_registry
from agents.browser_agent.skills.executor import SkillExecutor
from agents.browser_agent.skills.matcher import SkillMatcher
from agents.browser_agent.skills.skill_handler import SkillHandler

__all__ = [
    "Skill",
    "SkillParameter", 
    "SkillRegistry",
    "get_registry",
    "SkillExecutor", 
    "SkillMatcher",
    "SkillHandler",
]
