"""
会话数据访问模块
提供聊天会话相关的数据库操作
"""
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from common.conn_mysql import get_connection


def create_session(user_id: int, title: Optional[str] = None) -> dict:
    """创建新的聊天会话"""
    session_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_sessions (id, user_id, title)
                VALUES (%s, %s, %s)
                """,
                (session_id, user_id, title)
            )
            conn.commit()
            
            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM chat_sessions WHERE id = %s
                """,
                (session_id,)
            )
            row = cursor.fetchone()
            return {
                'id': row[0],
                'user_id': row[1],
                'title': row[2],
                'created_at': row[3],
                'updated_at': row[4],
                'message_count': 0
            }
    finally:
        conn.close()


def get_sessions_by_user(user_id: int, page: int = 1, page_size: int = 20) -> Tuple[List[dict], int]:
    """获取用户的会话列表（分页），按更新时间倒序排列"""
    offset = (page - 1) * page_size
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 获取总数
            cursor.execute(
                "SELECT COUNT(*) FROM chat_sessions WHERE user_id = %s",
                (user_id,)
            )
            total = cursor.fetchone()[0]
            
            # 获取会话列表（包含消息数量）
            cursor.execute(
                """
                SELECT s.id, s.user_id, s.title, s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                WHERE s.user_id = %s
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, page_size, offset)
            )
            rows = cursor.fetchall()
            sessions = [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'title': row[2],
                    'created_at': row[3],
                    'updated_at': row[4],
                    'message_count': row[5]
                }
                for row in rows
            ]
            return sessions, total
    finally:
        conn.close()


def get_session_by_id(session_id: str) -> Optional[dict]:
    """根据 ID 获取单个会话"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.id, s.user_id, s.title, s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                WHERE s.id = %s
                GROUP BY s.id
                """,
                (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'user_id': row[1],
                'title': row[2],
                'created_at': row[3],
                'updated_at': row[4],
                'message_count': row[5]
            }
    finally:
        conn.close()


def update_session_title(session_id: str, title: str) -> bool:
    """更新会话标题"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE chat_sessions SET title = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (title, session_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_session(session_id: str) -> bool:
    """删除会话及其所有消息（级联删除）"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM chat_sessions WHERE id = %s",
                (session_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()


def session_belongs_to_user(session_id: str, user_id: int) -> bool:
    """检查会话是否属于指定用户"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM chat_sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id)
            )
            return cursor.fetchone() is not None
    finally:
        conn.close()
