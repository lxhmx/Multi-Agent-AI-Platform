"""
Skill 注册器

负责扫描和加载 skills/definitions 目录下的所有 YAML 技能定义文件。
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from agents.browser_agent.skills.base_skill import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    技能注册器
    
    自动扫描 definitions 目录，加载所有 YAML 技能定义。
    提供技能查询和列表功能。
    """
    
    def __init__(self, skills_dir: Optional[str] = None):
        """
        初始化注册器
        
        Args:
            skills_dir: skills 目录路径，默认为当前模块所在目录
        """
        if skills_dir is None:
            skills_dir = Path(__file__).parent
        self.skills_dir = Path(skills_dir)
        self.definitions_dir = self.skills_dir / "definitions"
        self.scripts_dir = self.skills_dir / "scripts"
        
        self._skills: Dict[str, Skill] = {}
        self._loaded = False
    
    def load(self) -> None:
        """加载所有技能定义"""
        if not self.definitions_dir.exists():
            logger.warning(f"技能定义目录不存在: {self.definitions_dir}")
            self.definitions_dir.mkdir(parents=True, exist_ok=True)
            return
        
        self._skills.clear()
        
        for yaml_file in self.definitions_dir.glob("*.yaml"):
            # 跳过模板文件（以 _ 开头）
            if yaml_file.stem.startswith("_"):
                continue
                
            try:
                skill = self._load_skill_file(yaml_file)
                if skill:
                    self._skills[skill.id] = skill
                    logger.info(f"已加载技能: {skill.name} ({skill.id})")
            except Exception as e:
                logger.error(f"加载技能文件失败 {yaml_file}: {e}")
        
        # 同时支持 .yml 扩展名
        for yml_file in self.definitions_dir.glob("*.yml"):
            # 跳过模板文件（以 _ 开头）
            if yml_file.stem.startswith("_"):
                continue
                
            try:
                skill = self._load_skill_file(yml_file)
                if skill:
                    self._skills[skill.id] = skill
                    logger.info(f"已加载技能: {skill.name} ({skill.id})")
            except Exception as e:
                logger.error(f"加载技能文件失败 {yml_file}: {e}")
        
        self._loaded = True
        logger.info(f"共加载 {len(self._skills)} 个技能")
    
    def _load_skill_file(self, file_path: Path) -> Optional[Skill]:
        """加载单个技能文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data:
            return None
        
        # 使用文件名（不含扩展名）作为默认 ID
        skill_id = file_path.stem
        skill = Skill.from_dict(data, skill_id)
        
        # 验证脚本文件是否存在
        script_path = self.skills_dir / skill.script_path
        if not script_path.exists():
            logger.warning(f"技能 {skill.id} 的脚本文件不存在: {script_path}")
        
        return skill
    
    def get(self, skill_id: str) -> Optional[Skill]:
        """根据 ID 获取技能"""
        if not self._loaded:
            self.load()
        return self._skills.get(skill_id)
    
    def get_all(self) -> List[Skill]:
        """获取所有技能"""
        if not self._loaded:
            self.load()
        return list(self._skills.values())
    
    def get_by_name(self, name: str) -> Optional[Skill]:
        """根据名称获取技能"""
        if not self._loaded:
            self.load()
        for skill in self._skills.values():
            if skill.name == name:
                return skill
        return None
    
    def reload(self) -> None:
        """重新加载所有技能"""
        self._loaded = False
        self.load()
    
    def get_skills_prompt(self) -> str:
        """生成供 LLM 使用的技能列表描述"""
        if not self._loaded:
            self.load()
        
        if not self._skills:
            return "当前没有可用的浏览器自动化技能。"
        
        prompt = "## 可用的浏览器自动化技能\n\n"
        for skill in self._skills.values():
            prompt += skill.to_prompt_description() + "\n"
        
        return prompt


# 全局单例
_registry: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """获取全局技能注册器实例"""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
