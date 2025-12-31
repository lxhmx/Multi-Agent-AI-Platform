"""
Skill 基类和数据模型

定义 Skill 的数据结构，用于存储从 YAML 加载的技能元数据。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class SkillParameter:
    """技能参数定义"""
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    default: Any = None


@dataclass
class Skill:
    """
    技能数据模型
    
    Attributes:
        id: 技能唯一标识（对应脚本文件名）
        name: 技能显示名称（用户看到的名字）
        description: 技能描述（LLM 用于理解技能用途）
        triggers: 触发关键词列表（LLM 匹配用）
        script_path: 对应的 Playwright 脚本路径
        parameters: 技能参数列表
        require_confirmation: 执行前是否需要用户确认
        tags: 标签（用于分类）
    """
    id: str
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    script_path: str = ""
    parameters: List[SkillParameter] = field(default_factory=list)
    require_confirmation: bool = True
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], skill_id: str) -> "Skill":
        """从字典创建 Skill 实例"""
        skill_data = data.get("skill", data)
        
        # 解析参数
        params = []
        for p in skill_data.get("parameters", []):
            params.append(SkillParameter(
                name=p.get("name", ""),
                type=p.get("type", "string"),
                required=p.get("required", False),
                description=p.get("description", ""),
                default=p.get("default"),
            ))
        
        return cls(
            id=skill_data.get("id", skill_id),
            name=skill_data.get("name", skill_id),
            description=skill_data.get("description", ""),
            triggers=skill_data.get("triggers", []),
            script_path=skill_data.get("script", f"scripts/{skill_id}.py"),
            parameters=params,
            require_confirmation=skill_data.get("require_confirmation", True),
            tags=skill_data.get("tags", []),
        )
    
    def to_prompt_description(self) -> str:
        """生成供 LLM 理解的描述文本"""
        desc = f"- **{self.name}** (ID: {self.id})\n"
        desc += f"  描述: {self.description}\n"
        desc += f"  触发词: {', '.join(self.triggers)}\n"
        if self.parameters:
            desc += f"  参数: {', '.join(p.name for p in self.parameters)}\n"
        return desc
