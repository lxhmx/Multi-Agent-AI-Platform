"""
Pytest 配置和测试夹具
用于聊天历史功能的测试
"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.conn_mysql import get_connection


@pytest.fixture(scope="function")
def db_connection():
    """提供数据库连接"""
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def test_user(db_connection):
    """创建测试用户，测试结束后清理"""
    cursor = db_connection.cursor()
    
    # 创建测试用户
    cursor.execute(
        """
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
        """,
        ("test_user_pbt", "test_pbt@example.com", "hashed_password")
    )
    db_connection.commit()
    user_id = cursor.lastrowid
    
    yield user_id
    
    # 清理：删除测试用户（级联删除会话和消息）
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db_connection.commit()
    cursor.close()


@pytest.fixture(scope="function")
def cleanup_sessions(db_connection, test_user):
    """跟踪并清理测试期间创建的会话"""
    session_ids = []
    
    yield session_ids
    
    # 清理会话
    cursor = db_connection.cursor()
    for session_id in session_ids:
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
    db_connection.commit()
    cursor.close()
