"""
流程图智能体的属性测试

使用 Hypothesis 库进行属性测试
每个测试至少运行 100 次迭代
"""
import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck
from pydantic import ValidationError
import sys
from pathlib import Path
import json

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.flowchart_agent.models import DiagramNode, DiagramEdge, DiagramData


# ============================================================================
# 自定义测试数据生成策略
# ============================================================================

# 节点类型策略
node_type_strategy = st.sampled_from(['rectangle', 'diamond', 'oval', 'parallelogram', 'custom'])

# 图表类型策略
diagram_type_strategy = st.sampled_from(['flowchart', 'sequence', 'orgchart'])

# 简化的 ID 策略（使用简单字符集加速生成）
simple_id_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789_',
    min_size=1,
    max_size=20
)

# 标题策略
title_strategy = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-',
    min_size=0,
    max_size=50
)

# 坐标策略
coordinate_strategy = st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False)

# 尺寸策略（必须大于0）
size_strategy = st.floats(min_value=1.0, max_value=500, allow_nan=False, allow_infinity=False)

# 简化的样式策略
style_strategy = st.one_of(
    st.none(),
    st.fixed_dictionaries({
        'fill': st.sampled_from(['#fff', '#000', '#f00', '#0f0', '#00f']),
        'stroke': st.sampled_from(['#000', '#333', '#666', '#999'])
    })
)


# DiagramNode 生成策略
@st.composite
def diagram_node_strategy(draw, node_id=None):
    """生成有效的 DiagramNode"""
    return DiagramNode(
        id=node_id or draw(simple_id_strategy),
        type=draw(node_type_strategy),
        label=draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz ', min_size=0, max_size=30)),
        x=draw(coordinate_strategy),
        y=draw(coordinate_strategy),
        width=draw(size_strategy),
        height=draw(size_strategy),
        style=draw(style_strategy)
    )


# DiagramEdge 生成策略
@st.composite
def diagram_edge_strategy(draw, source_id=None, target_id=None):
    """生成有效的 DiagramEdge"""
    return DiagramEdge(
        id=draw(simple_id_strategy),
        source=source_id or draw(simple_id_strategy),
        target=target_id or draw(simple_id_strategy),
        label=draw(st.one_of(st.none(), st.text(alphabet='abcdefghijklmnopqrstuvwxyz ', min_size=0, max_size=20))),
        style=draw(style_strategy)
    )


# DiagramData 生成策略
@st.composite
def diagram_data_strategy(draw):
    """生成有效的 DiagramData，确保边引用有效的节点"""
    # 生成节点（限制数量以加速）
    num_nodes = draw(st.integers(min_value=0, max_value=5))
    nodes = []
    node_ids = []
    
    for i in range(num_nodes):
        node_id = f"node_{i}"
        node = draw(diagram_node_strategy(node_id=node_id))
        nodes.append(node)
        node_ids.append(node_id)
    
    # 生成边（只有当有至少2个节点时才生成边）
    edges = []
    if len(node_ids) >= 2:
        num_edges = draw(st.integers(min_value=0, max_value=min(3, len(node_ids))))
        for i in range(num_edges):
            source = draw(st.sampled_from(node_ids))
            target = draw(st.sampled_from(node_ids))
            edge = draw(diagram_edge_strategy(source_id=source, target_id=target))
            edges.append(edge)
    
    return DiagramData(
        id=draw(simple_id_strategy),
        title=draw(title_strategy),
        diagram_type=draw(diagram_type_strategy),
        nodes=nodes,
        edges=edges,
        svg_content=draw(st.one_of(st.none(), st.text(alphabet='<svg>/abcdefghijklmnopqrstuvwxyz', min_size=0, max_size=100))),
        xml_content=draw(st.one_of(st.none(), st.text(alphabet='<xml>/abcdefghijklmnopqrstuvwxyz', min_size=0, max_size=100)))
    )


# ============================================================================
# 属性测试
# ============================================================================

class TestDiagramDataRoundTrip:
    """
    **Feature: flowchart-agent, Property 1: Diagram Data Round Trip**
    
    对于任何有效的 DiagramData 对象，将其序列化为 JSON 然后反序列化
    应该产生一个等效的 DiagramData 对象，所有节点、边和元数据都被保留。
    
    **Validates: Requirements 7.1, 7.2**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(diagram=diagram_data_strategy())
    def test_diagram_data_round_trip(self, diagram: DiagramData):
        """
        属性：对于任何有效的 DiagramData，序列化后反序列化应保留所有数据
        """
        # 序列化为 JSON
        json_str = diagram.to_json()
        
        # 反序列化
        restored = DiagramData.from_json(json_str)
        
        # 验证核心字段
        assert restored.id == diagram.id, f"ID 不匹配: {restored.id} != {diagram.id}"
        assert restored.title == diagram.title, f"标题不匹配: {restored.title} != {diagram.title}"
        assert restored.diagram_type == diagram.diagram_type, \
            f"图表类型不匹配: {restored.diagram_type} != {diagram.diagram_type}"
        
        # 验证节点数量和内容
        assert len(restored.nodes) == len(diagram.nodes), \
            f"节点数量不匹配: {len(restored.nodes)} != {len(diagram.nodes)}"
        
        for orig_node, rest_node in zip(diagram.nodes, restored.nodes):
            assert rest_node.id == orig_node.id
            assert rest_node.type == orig_node.type
            assert rest_node.label == orig_node.label
            assert rest_node.x == orig_node.x
            assert rest_node.y == orig_node.y
            assert rest_node.width == orig_node.width
            assert rest_node.height == orig_node.height
            assert rest_node.style == orig_node.style
        
        # 验证边数量和内容
        assert len(restored.edges) == len(diagram.edges), \
            f"边数量不匹配: {len(restored.edges)} != {len(diagram.edges)}"
        
        for orig_edge, rest_edge in zip(diagram.edges, restored.edges):
            assert rest_edge.id == orig_edge.id
            assert rest_edge.source == orig_edge.source
            assert rest_edge.target == orig_edge.target
            assert rest_edge.label == orig_edge.label
            assert rest_edge.style == orig_edge.style
        
        # 验证可选内容
        assert restored.svg_content == diagram.svg_content
        assert restored.xml_content == diagram.xml_content



class TestInvalidJsonDeserialization:
    """
    **Feature: flowchart-agent, Property 5: Invalid JSON Deserialization Rejection**
    
    对于任何格式错误的 JSON 字符串或不符合 DiagramData schema 的 JSON，
    from_json 方法应该抛出验证错误，而不是返回损坏的对象。
    
    **Validates: Requirements 7.4**
    """
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(invalid_json=st.one_of(
        # 完全无效的 JSON 语法
        st.just('not json at all'),
        st.just('{invalid}'),
        st.just('{"unclosed": '),
        # 有效 JSON 但缺少必需字段 (id 和 title 是必需的)
        st.just('{}'),
        st.just('{"title": "test"}'),  # 缺少 id
        st.just('{"id": "test"}'),  # 缺少 title
        # 有效 JSON 但字段类型错误
        st.just('{"id": 123, "title": "test"}'),  # id 应该是字符串
        st.just('{"id": "", "title": "test"}'),  # id 不能为空字符串
        st.just('{"id": "test", "title": "test", "diagram_type": "invalid_type"}'),  # 无效的图表类型
        # 节点数据无效
        st.just('{"id": "test", "title": "test", "nodes": [{"id": "", "type": "rectangle", "label": "test", "x": 0, "y": 0, "width": 10, "height": 10}]}'),  # 节点 id 为空
        st.just('{"id": "test", "title": "test", "nodes": [{"id": "n1", "type": "invalid_type", "label": "test", "x": 0, "y": 0, "width": 10, "height": 10}]}'),  # 无效节点类型
        st.just('{"id": "test", "title": "test", "nodes": [{"id": "n1", "type": "rectangle", "label": "test", "x": 0, "y": 0, "width": 0, "height": 10}]}'),  # width 必须 > 0
        st.just('{"id": "test", "title": "test", "nodes": [{"id": "n1", "type": "rectangle", "label": "test", "x": 0, "y": 0, "width": 10, "height": -1}]}'),  # height 必须 > 0
    ))
    def test_invalid_json_rejection(self, invalid_json: str):
        """
        属性：对于任何无效的 JSON 输入，from_json 应该抛出异常
        """
        with pytest.raises(Exception):
            # 应该抛出 ValidationError 或 JSONDecodeError
            DiagramData.from_json(invalid_json)
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        # 生成随机的非 JSON 字符串
        random_text=st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=',
            min_size=1,
            max_size=100
        ).filter(lambda x: not x.strip().startswith('{'))
    )
    def test_malformed_json_rejection(self, random_text: str):
        """
        属性：对于任何格式错误的 JSON 字符串，from_json 应该抛出异常
        """
        with pytest.raises(Exception):
            DiagramData.from_json(random_text)
    
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        # 生成缺少必需字段的 JSON
        partial_data=st.fixed_dictionaries({
            'id': st.one_of(st.none(), simple_id_strategy),
            'title': st.one_of(st.none(), title_strategy),
        }).filter(lambda d: d['id'] is None or d['title'] is None)
    )
    def test_missing_required_fields_rejection(self, partial_data: dict):
        """
        属性：对于缺少必需字段的 JSON，from_json 应该抛出验证错误
        """
        # 移除 None 值
        json_data = {k: v for k, v in partial_data.items() if v is not None}
        json_str = json.dumps(json_data)
        
        with pytest.raises(ValidationError):
            DiagramData.from_json(json_str)
