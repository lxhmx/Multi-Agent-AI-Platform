"""
Pytest configuration and fixtures for chat history tests.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.conn_mysql import get_connection


@pytest.fixture(scope="function")
def db_connection():
    """Provide a database connection for tests."""
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def test_user(db_connection):
    """Create a test user and clean up after test."""
    cursor = db_connection.cursor()
    
    # Create test user
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
    
    # Cleanup: delete test user (cascades to sessions and messages)
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db_connection.commit()
    cursor.close()


@pytest.fixture(scope="function")
def cleanup_sessions(db_connection, test_user):
    """Track and cleanup sessions created during tests."""
    session_ids = []
    
    yield session_ids
    
    # Cleanup sessions
    cursor = db_connection.cursor()
    for session_id in session_ids:
        cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
    db_connection.commit()
    cursor.close()
