"""Message repository for chat history management."""
from typing import Optional, List, Tuple
from common.conn_mysql import get_connection


def create_message(session_id: str, role: str, content: str) -> dict:
    """Create a new message in a session."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (%s, %s, %s)
                """,
                (session_id, role, content)
            )
            message_id = cursor.lastrowid
            
            # Update session's updated_at
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                (session_id,)
            )
            conn.commit()
            
            cursor.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM chat_messages WHERE id = %s
                """,
                (message_id,)
            )
            row = cursor.fetchone()
            return {
                'id': row[0],
                'session_id': row[1],
                'role': row[2],
                'content': row[3],
                'created_at': row[4]
            }
    finally:
        conn.close()


def get_messages_by_session(session_id: str, limit: int = 100, offset: int = 0) -> List[dict]:
    """Get messages for a session, ordered by created_at asc."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, session_id, role, content, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
                """,
                (session_id, limit, offset)
            )
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'session_id': row[1],
                    'role': row[2],
                    'content': row[3],
                    'created_at': row[4]
                }
                for row in rows
            ]
    finally:
        conn.close()


def get_message_count(session_id: str) -> int:
    """Get the number of messages in a session."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE session_id = %s",
                (session_id,)
            )
            return cursor.fetchone()[0]
    finally:
        conn.close()
