"""
聊天历史功能的属性测试

使用 Hypothesis 库进行属性测试
每个测试至少运行 100 次迭代
"""
import pytest
from hypothesis import given, settings, strategies as st
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.repositories import session_repo, message_repo


# 自定义测试数据生成策略
message_content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Z')),
    min_size=1,
    max_size=500
).filter(lambda x: x.strip())  # 确保去除空白后非空

role_strategy = st.sampled_from(['user', 'assistant'])


class TestMessagePersistenceRoundTrip:
    """
    **功能: 聊天历史, 属性 1: 消息持久化往返测试**
    
    对于添加到会话中的任何消息（用户或助手），检索该会话的消息时
    应返回与保存时完全相同的内容。
    
    **验证需求: 1.1, 1.2, 3.1**
    """
    
    @settings(max_examples=100)
    @given(
        content=message_content_strategy,
        role=role_strategy
    )
    def test_message_round_trip(self, test_user, cleanup_sessions, content, role):
        """
        属性：对于任何消息内容和角色，保存和检索应返回完全相同的内容
        """
        # 为测试创建会话
        session = session_repo.create_session(test_user, "测试会话")
        cleanup_sessions.append(session['id'])
        
        # 创建消息
        created_message = message_repo.create_message(
            session_id=session['id'],
            role=role,
            content=content
        )
        
        # 检索消息
        messages = message_repo.get_messages_by_session(session['id'])
        
        # 查找我们的消息
        found_message = next(
            (m for m in messages if m['id'] == created_message['id']),
            None
        )
        
        # 属性：内容应完全保留
        assert found_message is not None, "消息应该可以被检索到"
        assert found_message['content'] == content, \
            f"内容不匹配: 期望 '{content}', 实际 '{found_message['content']}'"
        assert found_message['role'] == role, \
            f"角色不匹配: 期望 '{role}', 实际 '{found_message['role']}'"


class TestUniqueSessionIdGeneration:
    """
    **功能: 聊天历史, 属性 5: 唯一会话 ID 生成**
    
    对于任意数量的会话创建请求，每个创建的会话都应具有唯一标识符，
    不会与任何现有会话 ID 冲突。
    
    **验证需求: 4.1**
    """
    
    @settings(max_examples=100)
    @given(
        num_sessions=st.integers(min_value=2, max_value=10),
        titles=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            min_size=2,
            max_size=10
        )
    )
    def test_unique_session_ids(self, test_user, cleanup_sessions, num_sessions, titles):
        """
        属性：创建多个会话应始终生成唯一的 ID
        """
        # 限制为可用的标题数量
        actual_count = min(num_sessions, len(titles))
        
        created_ids = set()
        
        for i in range(actual_count):
            session = session_repo.create_session(test_user, titles[i])
            cleanup_sessions.append(session['id'])
            
            # 属性：每个新 ID 应该是唯一的
            assert session['id'] not in created_ids, \
                f"检测到重复的会话 ID: {session['id']}"
            
            created_ids.add(session['id'])
        
        # 验证所有 ID 都是唯一的
        assert len(created_ids) == actual_count, \
            f"期望 {actual_count} 个唯一 ID, 实际 {len(created_ids)} 个"
