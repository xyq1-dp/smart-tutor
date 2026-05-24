"""SQLite 数据模型 - 用户画像 & 学习记录"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tutor.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            major TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            knowledge_level TEXT DEFAULT 'beginner',
            learning_goal TEXT DEFAULT '',
            cognitive_style TEXT DEFAULT '',
            pace TEXT DEFAULT 'normal',
            weak_points TEXT DEFAULT '[]',
            interest_areas TEXT DEFAULT '[]',
            extra_info TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS learning_resources (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            topic TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS learning_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            status TEXT DEFAULT 'not_started',
            score REAL DEFAULT 0,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    conn.close()


def ensure_user(user_id: str, name: str = "", major: str = "") -> dict:
    """确保用户存在，不存在则创建"""
    conn = get_db()
    cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        conn.execute(
            "INSERT INTO users (id, name, major) VALUES (?, ?, ?)",
            (user_id, name, major),
        )
        conn.execute(
            "INSERT INTO user_profiles (user_id) VALUES (?)", (user_id,)
        )
        conn.commit()
        cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()
    conn.close()
    return dict(user)


def get_profile(user_id: str) -> dict | None:
    """获取用户画像"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_profile(user_id: str, **fields) -> None:
    """更新用户画像字段"""
    allowed = {
        "knowledge_level", "learning_goal", "cognitive_style",
        "pace", "weak_points", "interest_areas", "extra_info",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]

    conn = get_db()
    conn.execute(
        f"UPDATE user_profiles SET {set_clause}, updated_at = datetime('now') "
        f"WHERE user_id = ?",
        values,
    )
    conn.commit()
    conn.close()


def save_message(user_id: str, role: str, content: str) -> None:
    """保存聊天记录"""
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()
    conn.close()


def get_chat_history(user_id: str, limit: int = 50) -> list[dict]:
    """获取最近聊天记录"""
    conn = get_db()
    cur = conn.execute(
        "SELECT role, content FROM chat_history WHERE user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return list(reversed(rows))
