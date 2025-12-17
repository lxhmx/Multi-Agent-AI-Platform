"""Session repository for chat history management."""
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from common.conn_mysql import get_connection


def create_session(user_id: int, title: Optional[str] = None) -> dict:
    """Create a new chat session."""
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
    """Get paginated sessions for a user, ordered by updated_at desc."""
    offset = (page - 1) * page_size
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) FROM chat_sessions WHERE user_id = %s",
                (user_id,)
            )
            total = cursor.fetchone()[0]
            
            # Get sessions with message count
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
    """Get a single session by ID."""
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
    """Update session title."""
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
    """Delete a session and all its messages (cascade)."""
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
    """Check if a session belongs to a specific user."""
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
