"""SQLite 数据模型 - 用户画像 & 学习记录"""

import json
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

        CREATE TABLE IF NOT EXISTS learning_behaviors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            behavior_type TEXT NOT NULL,
            detail TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS profile_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            snapshot TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS assessment_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            dimensions TEXT NOT NULL,
            summary TEXT DEFAULT '',
            suggestions TEXT DEFAULT '',
            weak_points_change TEXT DEFAULT '[]',
            overall_score REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
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


def save_profile_snapshot(user_id: str) -> None:
    """将当前画像存档为快照（在更新前调用）"""
    current = get_profile(user_id)
    if not current:
        return
    # 只存档有值的维度
    snapshot = {k: v for k, v in current.items()
                if v and v != "[]" and k != "user_id" and k != "updated_at"}
    if not snapshot:
        return
    conn = get_db()
    conn.execute(
        "INSERT INTO profile_snapshots (user_id, snapshot) VALUES (?, ?)",
        (user_id, json.dumps(snapshot, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def get_profile_snapshots(user_id: str, limit: int = 10) -> list[dict]:
    """获取画像快照历史"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM profile_snapshots WHERE user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_profile_long_term_memory(user_id: str) -> str:
    """从历史快照中提取长期关键信息（供 profile_agent 参考）"""
    snapshots = get_profile_snapshots(user_id, limit=5)
    if not snapshots:
        return ""

    # 汇总历史中的关键字段
    all_goals = set()
    all_interests = set()
    all_weak = set()
    for s in snapshots:
        try:
            snap = json.loads(s["snapshot"]) if isinstance(s["snapshot"], str) else s["snapshot"]
        except (json.JSONDecodeError, TypeError):
            continue
        if snap.get("learning_goal"):
            all_goals.add(snap["learning_goal"])
        interests = snap.get("interest_areas", [])
        if isinstance(interests, str):
            try:
                interests = json.loads(interests)
            except (json.JSONDecodeError, ValueError):
                interests = []
        for item in interests:
            all_interests.add(item)
        weak = snap.get("weak_points", [])
        if isinstance(weak, str):
            try:
                weak = json.loads(weak)
            except (json.JSONDecodeError, ValueError):
                weak = []
        for item in weak:
            all_weak.add(item)

    parts = []
    if all_goals:
        parts.append(f"历史学习目标：{'、'.join(list(all_goals)[-3:])}")
    if all_interests:
        parts.append(f"持续关注方向：{'、'.join(list(all_interests)[-5:])}")
    if all_weak:
        parts.append(f"历史薄弱点：{'、'.join(list(all_weak)[-5:])}")
    return "\n".join(parts)


def update_profile(user_id: str, **fields) -> None:
    """更新用户画像字段（自动存档旧画像）"""
    allowed = {
        "knowledge_level", "learning_goal", "cognitive_style",
        "pace", "weak_points", "interest_areas", "extra_info",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return

    # 更新前存档
    save_profile_snapshot(user_id)

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


# === 学习行为追踪 ===

def record_behavior(user_id: str, behavior_type: str, detail: dict = None) -> None:
    """记录学习行为"""
    conn = get_db()
    conn.execute(
        "INSERT INTO learning_behaviors (user_id, behavior_type, detail) VALUES (?, ?, ?)",
        (user_id, behavior_type, json.dumps(detail or {}, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def get_behaviors(user_id: str, limit: int = 100) -> list[dict]:
    """获取用户最近学习行为"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM learning_behaviors WHERE user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return list(reversed(rows))


def get_behavior_summary(user_id: str) -> dict:
    """统计用户行为摘要（供评估使用）"""
    conn = get_db()
    cur = conn.execute(
        "SELECT behavior_type, COUNT(*) as cnt "
        "FROM learning_behaviors WHERE user_id = ? "
        "GROUP BY behavior_type",
        (user_id,),
    )
    type_counts = {r["behavior_type"]: r["cnt"] for r in cur.fetchall()}

    cur = conn.execute(
        "SELECT COUNT(*) as cnt FROM learning_behaviors WHERE user_id = ?",
        (user_id,),
    )
    total = cur.fetchone()["cnt"]

    # 最近活跃时间
    cur = conn.execute(
        "SELECT MAX(created_at) as last_active FROM learning_behaviors WHERE user_id = ?",
        (user_id,),
    )
    last = cur.fetchone()["last_active"]

    # 资源相关 topic 统计
    cur = conn.execute(
        "SELECT detail FROM learning_behaviors WHERE user_id = ? AND behavior_type IN ('resource_generate', 'resource_view')",
        (user_id,),
    )
    topics = set()
    for r in cur.fetchall():
        try:
            d = json.loads(r["detail"])
            if d.get("topic"):
                topics.add(d["topic"])
        except (json.JSONDecodeError, ValueError):
            pass

    conn.close()
    return {
        "total_behaviors": total,
        "type_counts": type_counts,
        "last_active": last,
        "topics_touched": list(topics),
    }


# === 评估记录 ===

def save_assessment(user_id: str, dimensions: dict, summary: str = "",
                    suggestions: str = "", weak_points_change: list = None,
                    overall_score: float = 0) -> int:
    """保存评估结果"""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO assessment_records (user_id, dimensions, summary, suggestions, "
        "weak_points_change, overall_score) VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            json.dumps(dimensions, ensure_ascii=False),
            summary,
            suggestions,
            json.dumps(weak_points_change or [], ensure_ascii=False),
            overall_score,
        ),
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def get_latest_assessment(user_id: str) -> dict | None:
    """获取最新评估"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM assessment_records WHERE user_id = ? "
        "ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None

    d = dict(row)
    for field in ["dimensions", "weak_points_change"]:
        try:
            d[field] = json.loads(d[field])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def get_assessment_history(user_id: str, limit: int = 10) -> list[dict]:
    """获取评估历史"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM assessment_records WHERE user_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# === 学习进度追踪 ===

# 知识点关键词 → 课程章节映射
TOPIC_CHAPTER_MAP = {
    "变量": "Python 基础语法", "类型": "Python 基础语法", "输入输出": "Python 基础语法",
    "运算符": "Python 基础语法", "字符串": "Python 基础语法", "基础语法": "Python 基础语法",
    "print": "Python 基础语法", "input": "Python 基础语法",

    "if": "流程控制", "for": "流程控制", "while": "流程控制",
    "循环": "流程控制", "条件": "流程控制", "break": "流程控制",
    "continue": "流程控制", "流程控制": "流程控制",

    "函数": "函数与模块", "参数": "函数与模块", "作用域": "函数与模块",
    "模块": "函数与模块", "lambda": "函数与模块", "装饰器": "函数与模块",
    "返回值": "函数与模块",

    "列表": "数据结构", "元组": "数据结构", "字典": "数据结构",
    "集合": "数据结构", "推导": "数据结构", "数据结构": "数据结构",
    "切片": "数据结构",

    "类": "面向对象编程", "继承": "面向对象编程", "多态": "面向对象编程",
    "异常": "面向对象编程", "OOP": "面向对象编程", "面向对象": "面向对象编程",
    "__init__": "面向对象编程", "魔法方法": "面向对象编程",

    "项目": "综合项目实战", "文件": "综合项目实战", "第三方库": "综合项目实战",
    "实战": "综合项目实战", "综合": "综合项目实战", "pip": "综合项目实战",
    "调试": "综合项目实战",
}


def detect_topic_chapter(text: str) -> str | None:
    """从文本中检测知识点对应的章节，返回章节名或 None"""
    for keyword, chapter in TOPIC_CHAPTER_MAP.items():
        if keyword.lower() in text.lower():
            return chapter
    return None


def update_topic_progress(user_id: str, topic: str, status: str = "in_progress",
                          score: float = 0) -> None:
    """更新知识点学习进度（upsert）"""
    conn = get_db()
    cur = conn.execute(
        "SELECT id, status FROM learning_progress WHERE user_id = ? AND topic = ?",
        (user_id, topic),
    )
    row = cur.fetchone()
    if row:
        # 不降级：completed 保持 completed
        new_status = status
        if row["status"] == "completed" and status != "completed":
            new_status = "completed"
        conn.execute(
            "UPDATE learning_progress SET status = ?, score = MAX(score, ?), "
            "completed_at = CASE WHEN ? = 'completed' THEN datetime('now') ELSE completed_at END "
            "WHERE id = ?",
            (new_status, score, status, row["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO learning_progress (user_id, topic, status, score, completed_at) "
            "VALUES (?, ?, ?, ?, CASE WHEN ? = 'completed' THEN datetime('now') ELSE NULL END)",
            (user_id, topic, status, score, status),
        )
    conn.commit()
    conn.close()


def get_all_topic_progress(user_id: str) -> list[dict]:
    """获取用户所有知识点进度"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM learning_progress WHERE user_id = ? ORDER BY id",
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_chapter_progress(user_id: str) -> dict[str, str]:
    """汇总各章节的学习状态，返回 {chapter_name: status}"""
    topic_rows = get_all_topic_progress(user_id)
    chapter_status = {}
    for row in topic_rows:
        topic = row["topic"]
        status = row["status"]
        # 找这个 topic 属于哪个 chapter
        chapter = None
        for keyword, ch in TOPIC_CHAPTER_MAP.items():
            if keyword in topic:
                chapter = ch
                break
        if not chapter:
            chapter = topic  # fallback

        current = chapter_status.get(chapter, "not_started")
        if status == "completed" or current == "completed":
            chapter_status[chapter] = "completed"
        elif status == "in_progress":
            chapter_status[chapter] = "in_progress"
        elif current == "not_started":
            chapter_status[chapter] = "not_started"
    return chapter_status
