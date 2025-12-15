"""
User repository for MySQL.
"""
from common.conn_mysql import get_mysql_connection


def get_by_id(user_id: int):
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_by_username(username: str):
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def create_user(username: str, email: str | None, password_hash: str):
    conn = get_mysql_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(username,email,password_hash) VALUES(%s,%s,%s)",
        (username, email, password_hash),
    )
    conn.commit()
    user_id = cur.lastrowid
    cur.close()
    conn.close()
    return user_id
