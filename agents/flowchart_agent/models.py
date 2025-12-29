"""
流程图数据模型
定义 DiagramNode, DiagramEdge, DiagramData 等 Pydantic 模型
用于流程图数据的序列化和反序列化

Requirements: 7.1, 7.2, 7.3, 7.4
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DiagramNode(BaseModel):
    """
    图表节点模型
    
    Attributes:
        id: 节点唯一标识符
        type: 节点类型 (rectangle, diamond, oval, parallelogram)
        label: 节点标签文本
        x: X 坐标位置
        y: Y 坐标位置
        width: 节点宽度
        height: 节点高度
        style: 可选的样式配置
    """
    id: str = Field(..., min_length=1, description="节点唯一标识符")
    type: str = Field(..., description="节点类型: rectangle, diamond, oval, parallelogram")
    label: str = Field(..., description="节点标签文本")
    x: float = Field(..., description="X 坐标位置")
    y: float = Field(..., description="Y 坐标位置")
    width: float = Field(..., gt=0, description="节点宽度，必须大于0")
    height: float = Field(..., gt=0, description="节点高度，必须大于0")
    style: Optional[Dict[str, Any]] = Field(default=None, description="可选的样式配置")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        """验证节点类型"""
        valid_types = {'rectangle', 'diamond', 'oval', 'parallelogram', 'custom'}
        if v not in valid_types:
            raise ValueError(f"节点类型必须是以下之一: {valid_types}")
        return v


class DiagramEdge(BaseModel):
    """
    图表连接/边模型
    
    Attributes:
        id: 连接唯一标识符
        source: 源节点 ID
        target: 目标节点 ID
        label: 可选的连接标签
        style: 可选的样式配置
    """
    id: str = Field(..., min_length=1, description="连接唯一标识符")
    source: str = Field(..., min_length=1, description="源节点 ID")
    target: str = Field(..., min_length=1, description="目标节点 ID")
    label: Optional[str] = Field(default=None, description="可选的连接标签")
    style: Optional[Dict[str, Any]] = Field(default=None, description="可选的样式配置")


class DiagramData(BaseModel):
    """
    图表数据模型
    
    包含完整的图表信息，支持序列化和反序列化
    
    Attributes:
        id: 图表唯一标识符
        title: 图表标题
        diagram_type: 图表类型 (flowchart, sequence, orgchart)
        nodes: 节点列表
        edges: 连接列表
        svg_content: 可选的 SVG 内容
        xml_content: 可选的 XML 内容 (Draw.io 格式)
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: str = Field(..., min_length=1, description="图表唯一标识符")
    title: str = Field(..., description="图表标题")
    diagram_type: str = Field(default="flowchart", description="图表类型: flowchart, sequence, orgchart")
    nodes: List[DiagramNode] = Field(default_factory=list, description="节点列表")
    edges: List[DiagramEdge] = Field(default_factory=list, description="连接列表")
    svg_content: Optional[str] = Field(default=None, description="SVG 内容")
    xml_content: Optional[str] = Field(default=None, description="Draw.io XML 内容")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    @field_validator('diagram_type')
    @classmethod
    def validate_diagram_type(cls, v: str) -> str:
        """验证图表类型"""
        valid_types = {'flowchart', 'sequence', 'orgchart'}
        if v not in valid_types:
            raise ValueError(f"图表类型必须是以下之一: {valid_types}")
        return v

    def to_json(self) -> str:
        """
        序列化为 JSON 字符串
        
        Requirements: 7.1, 7.3
        
        Returns:
            str: JSON 格式的字符串，包含所有节点位置、连接、标签和样式信息
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "DiagramData":
        """
        从 JSON 字符串反序列化
        
        Requirements: 7.2, 7.4
        
        Args:
            json_str: JSON 格式的字符串
            
        Returns:
            DiagramData: 反序列化后的图表数据对象
            
        Raises:
            ValidationError: 当 JSON 结构不符合 DiagramData schema 时
        """
        return cls.model_validate_json(json_str)



def generate_filename(title: Optional[str], format: str = "svg") -> str:
    """
    根据图表标题生成下载文件名
    
    Requirements: 3.3
    
    Args:
        title: 图表标题，可以为 None 或空字符串
        format: 文件格式后缀，默认为 "svg"
        
    Returns:
        str: 生成的文件名
        
    规则:
        - 如果 title 非空，使用清理后的标题作为文件名
        - 清理规则：移除非法字符 (<>:"/\\|?*)，将空格替换为下划线，截断到50字符
        - 如果 title 为空或 None，使用时间戳格式 (YYYYMMDD)
    """
    if title and title.strip():
        # 清理标题中的非法字符
        sanitized = title.strip()
        # 移除文件名非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        # 将空格替换为下划线
        sanitized = re.sub(r'\s+', '_', sanitized)
        # 截断到50字符
        sanitized = sanitized[:50]
        return f"{sanitized}.{format}"
    else:
        # 使用时间戳
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"flowchart_{timestamp}.{format}"
