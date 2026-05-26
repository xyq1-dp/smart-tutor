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

    # 迁移：升级 learning_behaviors 表（向前兼容）
    for col, col_def in [
        ("duration", "REAL DEFAULT 0"),
        ("quality_score", "REAL DEFAULT 0"),
        ("context", "TEXT DEFAULT '{}'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE learning_behaviors ADD COLUMN {col} {col_def}")
        except Exception:
            pass  # 列已存在则跳过
    conn.commit()

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

        CREATE TABLE IF NOT EXISTS knowledge_components (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            chapter_id TEXT NOT NULL,
            chapter_order INTEGER NOT NULL,
            section_order INTEGER NOT NULL,
            description TEXT DEFAULT '',
            prerequisites TEXT DEFAULT '[]',
            difficulty INTEGER DEFAULT 1,
            estimated_minutes INTEGER DEFAULT 30,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS knowledge_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            kc_id TEXT NOT NULL,
            mastery_probability REAL DEFAULT 0.0,
            last_review_time TEXT,
            forgetting_rate REAL DEFAULT 0.05,
            review_count INTEGER DEFAULT 0,
            total_interactions INTEGER DEFAULT 0,
            last_quality_score REAL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (kc_id) REFERENCES knowledge_components(id),
            UNIQUE(user_id, kc_id)
        );

        CREATE TABLE IF NOT EXISTS error_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            error_type TEXT NOT NULL,
            error_message TEXT DEFAULT '',
            error_code TEXT DEFAULT '',
            related_kc_ids TEXT DEFAULT '[]',
            resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS resource_engagement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            resource_id TEXT DEFAULT '',
            resource_type TEXT DEFAULT '',
            topic TEXT DEFAULT '',
            duration_seconds REAL DEFAULT 0,
            scroll_depth_pct REAL DEFAULT 0,
            revisit_count INTEGER DEFAULT 0,
            backseek_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS diagnostic_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            chapter_id TEXT DEFAULT '',
            kc_id TEXT DEFAULT '',
            user_answer TEXT DEFAULT '',
            correct_answer TEXT DEFAULT '',
            is_correct INTEGER DEFAULT 0,
            response_time_seconds REAL DEFAULT 0,
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

def record_behavior(user_id: str, behavior_type: str, detail: dict = None,
                    duration: float = 0, quality_score: float = 0,
                    context: dict = None) -> None:
    """记录学习行为（含质量维度和上下文）"""
    conn = get_db()
    conn.execute(
        "INSERT INTO learning_behaviors (user_id, behavior_type, detail, "
        "duration, quality_score, context) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, behavior_type, json.dumps(detail or {}, ensure_ascii=False),
         duration, quality_score, json.dumps(context or {}, ensure_ascii=False)),
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


# === 知识组件初始化 ===

KC_DEFINITIONS = [
    # (id, name, chapter_id, chapter_order, section_order, description, prerequisites_json, difficulty, estimated_minutes)
    # 第1章：Python基础语法
    ("kc_ch1_01", "Python语言简介与环境搭建", "01_basics", 1, 1, "了解Python语言特点、应用领域，完成开发环境安装", "[]", 1, 20),
    ("kc_ch1_02", "变量与基本数据类型", "01_basics", 1, 2, "掌握变量的定义与赋值，理解int/float/str/bool/NoneType", '["kc_ch1_01"]', 1, 30),
    ("kc_ch1_03", "输入与输出(print/input)", "01_basics", 1, 3, "掌握print()格式化输出和input()获取用户输入", '["kc_ch1_02"]', 1, 25),
    ("kc_ch1_04", "运算符与表达式", "01_basics", 1, 4, "掌握算术/比较/逻辑运算符及优先级", '["kc_ch1_02"]', 1, 30),
    ("kc_ch1_05", "字符串基本操作", "01_basics", 1, 5, "掌握字符串索引、切片、常用方法(upper/lower/replace/split/strip)", '["kc_ch1_02","kc_ch1_04"]', 2, 35),
    ("kc_ch1_06", "类型转换", "01_basics", 1, 6, "掌握int()/float()/str()/bool()类型转换", '["kc_ch1_02"]', 1, 20),
    # 第2章：流程控制
    ("kc_ch2_01", "条件判断(if/elif/else)", "02_control_flow", 2, 1, "掌握if/elif/else结构、三元表达式、条件嵌套", '["kc_ch1_02","kc_ch1_04"]', 2, 40),
    ("kc_ch2_02", "for循环与range()", "02_control_flow", 2, 2, "掌握for循环遍历序列、range()生成序列、enumerate()", '["kc_ch2_01"]', 2, 40),
    ("kc_ch2_03", "while循环", "02_control_flow", 2, 3, "掌握while条件循环、无限循环与退出条件", '["kc_ch2_01"]', 2, 35),
    ("kc_ch2_04", "break与continue", "02_control_flow", 2, 4, "掌握break退出循环、continue跳过本次迭代", '["kc_ch2_02","kc_ch2_03"]', 2, 25),
    ("kc_ch2_05", "循环嵌套", "02_control_flow", 2, 5, "掌握多层循环的嵌套与执行顺序", '["kc_ch2_02","kc_ch2_03"]', 2, 30),
    ("kc_ch2_06", "流程控制综合应用", "02_control_flow", 2, 6, "综合运用条件判断和循环解决实际编程问题", '["kc_ch2_04","kc_ch2_05"]', 3, 40),
    # 第3章：函数与模块
    ("kc_ch3_01", "函数定义与调用", "03_functions", 3, 1, "掌握def关键字定义函数、函数调用、文档字符串", '["kc_ch2_06"]', 2, 35),
    ("kc_ch3_02", "位置参数与默认参数", "03_functions", 3, 2, "掌握位置参数、默认参数的使用", '["kc_ch3_01"]', 2, 30),
    ("kc_ch3_03", "关键字参数与可变参数(*args/**kwargs)", "03_functions", 3, 3, "掌握关键字参数、*args元组参数、**kwargs字典参数", '["kc_ch3_02"]', 3, 35),
    ("kc_ch3_04", "返回值与多返回值", "03_functions", 3, 4, "掌握return返回单个/多个值(元组解包)", '["kc_ch3_01"]', 2, 25),
    ("kc_ch3_05", "变量作用域(LEGB规则)", "03_functions", 3, 5, "理解局部/全局变量、global关键字、LEGB查找规则", '["kc_ch3_01","kc_ch1_02"]', 3, 30),
    ("kc_ch3_06", "模块导入与自定义模块", "03_functions", 3, 6, "掌握import/from-import/as别名、自定义.py模块", '["kc_ch3_01"]', 2, 30),
    ("kc_ch3_07", "常用内置函数", "03_functions", 3, 7, "掌握len/range/type/max/min/sum/sorted/enumerate/zip/map/filter", '["kc_ch2_02","kc_ch3_01"]', 2, 35),
    ("kc_ch3_08", "Lambda表达式", "03_functions", 3, 8, "掌握lambda匿名函数的定义与sort/map/filter配合使用", '["kc_ch3_01","kc_ch3_03"]', 3, 25),
    # 第4章：数据结构
    ("kc_ch4_01", "列表(创建/索引/切片/方法)", "04_data_structures", 4, 1, "掌握列表创建、索引、切片、append/insert/remove/pop/sort等方法", '["kc_ch2_02","kc_ch1_05"]', 2, 45),
    ("kc_ch4_02", "元组(不可变/解包)", "04_data_structures", 4, 2, "掌握元组不可变性、单元素元组、元组解包", '["kc_ch4_01"]', 2, 25),
    ("kc_ch4_03", "字典(键值对/CRUD/遍历)", "04_data_structures", 4, 3, "掌握字典创建、增删改查、get/items/keys/values遍历", '["kc_ch4_01","kc_ch2_02"]', 2, 40),
    ("kc_ch4_04", "集合(去重/集合运算)", "04_data_structures", 4, 4, "掌握集合去重特性、add/remove、交集并集差集对称差运算", '["kc_ch4_03"]', 2, 30),
    ("kc_ch4_05", "列表推导式", "04_data_structures", 4, 5, "掌握列表推导式语法[expr for x in iterable if cond]", '["kc_ch4_01","kc_ch2_02"]', 3, 30),
    ("kc_ch4_06", "字典推导式与集合推导式", "04_data_structures", 4, 6, "掌握字典推导式{k:v for ...}和集合推导式{x for ...}", '["kc_ch4_03","kc_ch4_04","kc_ch4_05"]', 3, 25),
    ("kc_ch4_07", "嵌套数据结构", "04_data_structures", 4, 7, "掌握列表嵌套字典、字典嵌套列表等复合结构的操作", '["kc_ch4_01","kc_ch4_03"]', 3, 35),
    ("kc_ch4_08", "数据结构选择与综合应用", "04_data_structures", 4, 8, "根据场景选择合适的数据结构(list/tuple/dict/set)", '["kc_ch4_01","kc_ch4_02","kc_ch4_03","kc_ch4_04","kc_ch4_05","kc_ch4_06","kc_ch4_07"]', 3, 30),
    # 第5章：面向对象编程
    ("kc_ch5_01", "面向对象思想概述", "05_oop", 5, 1, "理解封装、继承、多态的面向对象核心思想", '["kc_ch3_01"]', 2, 30),
    ("kc_ch5_02", "类的定义与对象创建", "05_oop", 5, 2, "掌握class关键字定义类、创建实例对象", '["kc_ch5_01"]', 2, 30),
    ("kc_ch5_03", "__init__构造方法", "05_oop", 5, 3, "掌握__init__初始化方法、self参数的含义", '["kc_ch5_02"]', 2, 30),
    ("kc_ch5_04", "实例属性与方法(含类方法/静态方法)", "05_oop", 5, 4, "掌握实例方法/属性、@classmethod、@staticmethod", '["kc_ch5_02","kc_ch5_03"]', 3, 40),
    ("kc_ch5_05", "继承与super()", "05_oop", 5, 5, "掌握单继承、super()调用父类方法、方法重写", '["kc_ch5_04"]', 3, 40),
    ("kc_ch5_06", "多态与方法重写", "05_oop", 5, 6, "理解多态概念、鸭子类型、方法重写的运行时分派", '["kc_ch5_05"]', 3, 30),
    ("kc_ch5_07", "魔法方法", "05_oop", 5, 7, "掌握__str__/__repr__/__add__/__eq__/__len__等常用魔法方法", '["kc_ch5_02","kc_ch5_04"]', 3, 35),
    ("kc_ch5_08", "异常处理(try/except/finally)", "05_oop", 5, 8, "掌握try/except/else/finally、raise抛出异常、自定义异常类", '["kc_ch2_01","kc_ch5_02"]', 3, 35),
    # 第6章：综合项目实战
    ("kc_ch6_01", "文件读写操作", "06_projects", 6, 1, "掌握open()文件操作、with语句、read/write/readlines", '["kc_ch2_02","kc_ch1_03"]', 2, 30),
    ("kc_ch6_02", "标准库: os与路径操作", "06_projects", 6, 2, "掌握os.path/os.getcwd/os.listdir等路径操作", '["kc_ch6_01"]', 2, 25),
    ("kc_ch6_03", "标准库: datetime与时间处理", "06_projects", 6, 3, "掌握datetime/date/timedelta/strftime/strptime", '["kc_ch1_02"]', 2, 25),
    ("kc_ch6_04", "JSON数据处理", "06_projects", 6, 4, "掌握json.dumps/json.loads/json.dump/json.load序列化", '["kc_ch4_03"]', 2, 25),
    ("kc_ch6_05", "第三方库安装与使用(pip)", "06_projects", 6, 5, "掌握pip install安装、导入和使用第三方包", '["kc_ch3_06"]', 1, 20),
    ("kc_ch6_06", "项目实战：学生成绩管理系统", "06_projects", 6, 6, "综合运用文件IO、JSON、字典/列表完成CRUD系统", '["kc_ch6_01","kc_ch6_04","kc_ch4_03"]', 3, 60),
    ("kc_ch6_07", "代码调试技巧与编码规范", "06_projects", 6, 7, "掌握print/assert/try-except/pdb调试及PEP 8编码规范", '["kc_ch5_08","kc_ch3_01","kc_ch4_01"]', 2, 30),
]


def init_knowledge_components():
    """初始化知识图谱（INSERT OR IGNORE，幂等安全）"""
    conn = get_db()
    for kc in KC_DEFINITIONS:
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_components "
            "(id, name, chapter_id, chapter_order, section_order, description, prerequisites, difficulty, estimated_minutes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            kc,
        )
    conn.commit()
    conn.close()


# === 知识组件查询 ===

def get_kc_by_id(kc_id: str) -> dict | None:
    conn = get_db()
    cur = conn.execute("SELECT * FROM knowledge_components WHERE id = ?", (kc_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    try:
        d["prerequisites"] = json.loads(d["prerequisites"])
    except (json.JSONDecodeError, TypeError):
        d["prerequisites"] = []
    return d


def get_all_kcs() -> list[dict]:
    conn = get_db()
    cur = conn.execute("SELECT * FROM knowledge_components ORDER BY chapter_order, section_order")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for d in rows:
        try:
            d["prerequisites"] = json.loads(d["prerequisites"])
        except (json.JSONDecodeError, TypeError):
            d["prerequisites"] = []
    return rows


def get_chapter_kcs(chapter_id: str) -> list[dict]:
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM knowledge_components WHERE chapter_id = ? ORDER BY section_order",
        (chapter_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_kcs_by_ids(kc_ids: list[str]) -> list[dict]:
    if not kc_ids:
        return []
    placeholders = ",".join("?" for _ in kc_ids)
    conn = get_db()
    cur = conn.execute(
        f"SELECT * FROM knowledge_components WHERE id IN ({placeholders})",
        kc_ids,
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# === 知识状态管理 ===

def init_knowledge_state_for_user(user_id: str) -> None:
    """为新用户初始化全部43个KC的掌握状态（P=0）"""
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO knowledge_state (user_id, kc_id) "
        "SELECT ?, id FROM knowledge_components",
        (user_id,),
    )
    conn.commit()
    conn.close()


def get_user_knowledge_state(user_id: str) -> list[dict]:
    conn = get_db()
    cur = conn.execute(
        "SELECT ks.*, kc.name, kc.chapter_id, kc.chapter_order, kc.difficulty "
        "FROM knowledge_state ks JOIN knowledge_components kc ON ks.kc_id = kc.id "
        "WHERE ks.user_id = ? ORDER BY kc.chapter_order, kc.section_order",
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_single_kc_state(user_id: str, kc_id: str) -> dict | None:
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM knowledge_state WHERE user_id = ? AND kc_id = ?",
        (user_id, kc_id),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_knowledge_state(user_id: str, kc_id: str, mastery_probability: float,
                           quality_score: float = 0) -> None:
    """更新知识状态（使用INSERT OR REPLACE实现upsert）"""
    conn = get_db()
    cur = conn.execute(
        "SELECT mastery_probability, review_count, total_interactions "
        "FROM knowledge_state WHERE user_id = ? AND kc_id = ?",
        (user_id, kc_id),
    )
    row = cur.fetchone()
    now = datetime.now().isoformat()

    if row:
        new_count = row["review_count"] + 1
        new_total = row["total_interactions"] + 1
        # 使用贝叶斯更新：不倒退（取最大值防止遗忘曲线的衰减值覆盖更高的值）
        new_p = max(mastery_probability, row["mastery_probability"])
        conn.execute(
            "UPDATE knowledge_state SET mastery_probability = ?, last_review_time = ?, "
            "review_count = ?, total_interactions = ?, last_quality_score = ?, "
            "updated_at = ? WHERE user_id = ? AND kc_id = ?",
            (new_p, now, new_count, new_total, quality_score, now, user_id, kc_id),
        )
    else:
        conn.execute(
            "INSERT INTO knowledge_state (user_id, kc_id, mastery_probability, "
            "last_review_time, review_count, total_interactions, last_quality_score, updated_at) "
            "VALUES (?, ?, ?, ?, 1, 1, ?, ?)",
            (user_id, kc_id, mastery_probability, now, quality_score, now),
        )
    conn.commit()
    conn.close()


def get_chapter_average_mastery(user_id: str) -> dict[str, float]:
    """返回各章节平均掌握概率 {chapter_id: avg_mastery}"""
    conn = get_db()
    cur = conn.execute(
        "SELECT kc.chapter_id, AVG(ks.mastery_probability) as avg_mastery "
        "FROM knowledge_state ks JOIN knowledge_components kc ON ks.kc_id = kc.id "
        "WHERE ks.user_id = ? GROUP BY kc.chapter_id ORDER BY kc.chapter_order",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return {r["chapter_id"]: round(r["avg_mastery"], 4) for r in rows}


def get_kc_mastery_map(user_id: str) -> dict[str, float]:
    """返回 {kc_id: mastery_probability} 映射"""
    conn = get_db()
    cur = conn.execute(
        "SELECT kc_id, mastery_probability FROM knowledge_state WHERE user_id = ?",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return {r["kc_id"]: r["mastery_probability"] for r in rows}


def get_knowledge_state_summary(user_id: str) -> dict:
    """知识状态摘要：总数、平均值、已掌握数（P≥0.6）、弱项数（P<0.3）"""
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) as total, AVG(mastery_probability) as avg_p, "
        "SUM(CASE WHEN mastery_probability >= 0.6 THEN 1 ELSE 0 END) as mastered, "
        "SUM(CASE WHEN mastery_probability < 0.3 THEN 1 ELSE 0 END) as weak "
        "FROM knowledge_state WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return {
        "total_kcs": row["total"],
        "average_mastery": round(row["avg_p"], 4) if row["avg_p"] else 0,
        "mastered_count": row["mastered"] or 0,
        "weak_count": row["weak"] or 0,
    }


def get_weak_kcs(user_id: str, max_p: float = 0.3, limit: int = 10) -> list[dict]:
    """获取薄弱知识点（P < max_p），按掌握概率升序"""
    conn = get_db()
    cur = conn.execute(
        "SELECT ks.*, kc.name, kc.chapter_id "
        "FROM knowledge_state ks JOIN knowledge_components kc ON ks.kc_id = kc.id "
        "WHERE ks.user_id = ? AND ks.mastery_probability < ? "
        "ORDER BY ks.mastery_probability ASC LIMIT ?",
        (user_id, max_p, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# === 错误记录 ===

def record_error(user_id: str, error_type: str, error_message: str = "",
                 error_code: str = "", related_kc_ids: list = None) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO error_records (user_id, error_type, error_message, error_code, related_kc_ids) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, error_type, error_message[:500], error_code[:1000],
         json.dumps(related_kc_ids or [], ensure_ascii=False)),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return eid


def get_user_errors(user_id: str, limit: int = 50) -> list[dict]:
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM error_records WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    for d in rows:
        try:
            d["related_kc_ids"] = json.loads(d["related_kc_ids"])
        except (json.JSONDecodeError, TypeError):
            d["related_kc_ids"] = []
    return rows


def get_error_patterns(user_id: str) -> dict:
    """按错误类型聚合，返回 {error_type: count}"""
    conn = get_db()
    cur = conn.execute(
        "SELECT error_type, COUNT(*) as cnt FROM error_records "
        "WHERE user_id = ? GROUP BY error_type ORDER BY cnt DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return {r["error_type"]: r["cnt"] for r in rows}


def get_errors_by_kc(user_id: str) -> dict[str, int]:
    """按关联知识点聚合错误次数"""
    errors = get_user_errors(user_id, limit=200)
    kc_counts: dict[str, int] = {}
    for e in errors:
        for kc_id in e.get("related_kc_ids", []):
            kc_counts[kc_id] = kc_counts.get(kc_id, 0) + 1
    return dict(sorted(kc_counts.items(), key=lambda x: x[1], reverse=True))


# === 资源行为深度 ===

def record_resource_engagement(user_id: str, resource_id: str = "", resource_type: str = "",
                                topic: str = "", duration: float = 0, scroll_depth: float = 0,
                                revisit: int = 0, backseek: int = 0) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO resource_engagement (user_id, resource_id, resource_type, topic, "
        "duration_seconds, scroll_depth_pct, revisit_count, backseek_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, resource_id, resource_type, topic, duration, scroll_depth, revisit, backseek),
    )
    conn.commit()
    conn.close()


def get_engagement_summary(user_id: str) -> dict:
    """资源参与度摘要"""
    conn = get_db()
    cur = conn.execute(
        "SELECT COUNT(*) as total, AVG(duration_seconds) as avg_duration, "
        "AVG(scroll_depth_pct) as avg_scroll, SUM(revisit_count) as total_revisits "
        "FROM resource_engagement WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return {
        "total_engagements": row["total"] or 0,
        "avg_duration_seconds": round(row["avg_duration"], 1) if row["avg_duration"] else 0,
        "avg_scroll_depth_pct": round(row["avg_scroll"], 1) if row["avg_scroll"] else 0,
        "total_revisits": row["total_revisits"] or 0,
    }


def get_engagement_by_topic(user_id: str) -> dict[str, dict]:
    """按主题聚合参与度"""
    conn = get_db()
    cur = conn.execute(
        "SELECT topic, COUNT(*) as cnt, SUM(duration_seconds) as total_duration, "
        "AVG(scroll_depth_pct) as avg_scroll "
        "FROM resource_engagement WHERE user_id = ? AND topic != '' "
        "GROUP BY topic ORDER BY cnt DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return {
        r["topic"]: {
            "count": r["cnt"],
            "total_duration": r["total_duration"] or 0,
            "avg_scroll": round(r["avg_scroll"], 1) if r["avg_scroll"] else 0,
        }
        for r in rows
    }


# === 诊断测试 ===

def save_diagnostic_answer(user_id: str, question_id: str, chapter_id: str,
                           kc_id: str = "", user_answer: str = "", correct_answer: str = "",
                           is_correct: int = 0, response_time: float = 0) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO diagnostic_results (user_id, question_id, chapter_id, kc_id, "
        "user_answer, correct_answer, is_correct, response_time_seconds) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, question_id, chapter_id, kc_id, user_answer, correct_answer,
         is_correct, response_time),
    )
    conn.commit()
    conn.close()


def get_diagnostic_results(user_id: str) -> list[dict]:
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM diagnostic_results WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_latest_diagnostic_summary(user_id: str) -> dict | None:
    """获取最近一次诊断测试的汇总（同一批次 = 同一天内）"""
    conn = get_db()
    cur = conn.execute(
        "SELECT * FROM diagnostic_results WHERE user_id = ? "
        "ORDER BY id DESC LIMIT 50",
        (user_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    if not rows:
        return None
    total = len(rows)
    correct = sum(1 for r in rows if r["is_correct"])
    return {
        "total_questions": total,
        "correct_count": correct,
        "accuracy": round(correct / total, 3) if total > 0 else 0,
        "last_test_time": rows[0]["created_at"],
    }


def compute_diagnostic_mastery(user_id: str) -> dict[str, float]:
    """从诊断测试结果计算每个KC的初始掌握概率"""
    conn = get_db()
    cur = conn.execute(
        "SELECT kc_id, AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) as accuracy, "
        "COUNT(*) as cnt "
        "FROM diagnostic_results WHERE user_id = ? AND kc_id != '' "
        "GROUP BY kc_id",
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    result = {}
    for r in rows:
        if r["cnt"] > 0:
            # 答对 → P=0.65，答错 → P=0.15，按比例混合
            result[r["kc_id"]] = round(r["accuracy"] * 0.5 + 0.1, 4)
    return result


def init_knowledge_state_from_diagnostic(user_id: str) -> None:
    """从诊断结果初始化knowledge_state"""
    mastery = compute_diagnostic_mastery(user_id)
    if not mastery:
        return
    conn = get_db()
    now = datetime.now().isoformat()
    for kc_id, p in mastery.items():
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_state "
            "(user_id, kc_id, mastery_probability, last_review_time, review_count, total_interactions, updated_at) "
            "VALUES (?, ?, ?, ?, 1, 1, ?)",
            (user_id, kc_id, p, now, now),
        )
    conn.commit()
    conn.close()
