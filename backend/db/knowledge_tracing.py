"""
知识追踪算法 — 基于指数遗忘模型的掌握概率计算与复习推荐

核心模型：
  掌握概率更新（贝叶斯形式）:
    P_new = P_old + (1 - P_old) * learn_rate * quality_score

  遗忘衰减（艾宾浩斯指数遗忘）:
    effective_rate = base_rate * exp(-review_count / decay_factor)
    P_t = P_0 * exp(-effective_rate * days_since_last_review)

  复习优先级:
    priority = (1 - P) * importance_weight * (1 + days_overdue * 0.1)
"""

import json
import math
from datetime import datetime

from backend.db.models import (
    get_user_knowledge_state,
    upsert_knowledge_state,
    get_chapter_average_mastery,
    get_kc_mastery_map,
    get_all_kcs,
    get_kcs_by_ids,
    get_weak_kcs,
    get_user_errors,
    get_error_patterns,
    get_knowledge_state_summary,
    init_knowledge_state_for_user,
    init_knowledge_state_from_diagnostic,
)

# ============================================================
# 模型参数
# ============================================================
LEARN_RATE = 0.1
BASE_FORGET_RATE = 0.05
DECAY_FACTOR = 3
MASTERY_THRESHOLD = 0.6  # P >= 0.6 视为"已掌握"
WEAK_THRESHOLD = 0.3     # P < 0.3 视为"薄弱"

# ============================================================
# 43个KC的依赖关系（有向无环图）
# ============================================================
KC_DEPENDENCIES: dict[str, list[str]] = {
    "kc_ch1_01": [],
    "kc_ch1_02": ["kc_ch1_01"],
    "kc_ch1_03": ["kc_ch1_02"],
    "kc_ch1_04": ["kc_ch1_02"],
    "kc_ch1_05": ["kc_ch1_02", "kc_ch1_04"],
    "kc_ch1_06": ["kc_ch1_02"],
    "kc_ch2_01": ["kc_ch1_02", "kc_ch1_04"],
    "kc_ch2_02": ["kc_ch2_01"],
    "kc_ch2_03": ["kc_ch2_01"],
    "kc_ch2_04": ["kc_ch2_02", "kc_ch2_03"],
    "kc_ch2_05": ["kc_ch2_02", "kc_ch2_03"],
    "kc_ch2_06": ["kc_ch2_04", "kc_ch2_05"],
    "kc_ch3_01": ["kc_ch2_06"],
    "kc_ch3_02": ["kc_ch3_01"],
    "kc_ch3_03": ["kc_ch3_02"],
    "kc_ch3_04": ["kc_ch3_01"],
    "kc_ch3_05": ["kc_ch3_01", "kc_ch1_02"],
    "kc_ch3_06": ["kc_ch3_01"],
    "kc_ch3_07": ["kc_ch2_02", "kc_ch3_01"],
    "kc_ch3_08": ["kc_ch3_01", "kc_ch3_03"],
    "kc_ch4_01": ["kc_ch2_02", "kc_ch1_05"],
    "kc_ch4_02": ["kc_ch4_01"],
    "kc_ch4_03": ["kc_ch4_01", "kc_ch2_02"],
    "kc_ch4_04": ["kc_ch4_03"],
    "kc_ch4_05": ["kc_ch4_01", "kc_ch2_02"],
    "kc_ch4_06": ["kc_ch4_03", "kc_ch4_04", "kc_ch4_05"],
    "kc_ch4_07": ["kc_ch4_01", "kc_ch4_03"],
    "kc_ch4_08": ["kc_ch4_01", "kc_ch4_02", "kc_ch4_03", "kc_ch4_04", "kc_ch4_05", "kc_ch4_06", "kc_ch4_07"],
    "kc_ch5_01": ["kc_ch3_01"],
    "kc_ch5_02": ["kc_ch5_01"],
    "kc_ch5_03": ["kc_ch5_02"],
    "kc_ch5_04": ["kc_ch5_02", "kc_ch5_03"],
    "kc_ch5_05": ["kc_ch5_04"],
    "kc_ch5_06": ["kc_ch5_05"],
    "kc_ch5_07": ["kc_ch5_02", "kc_ch5_04"],
    "kc_ch5_08": ["kc_ch2_01", "kc_ch5_02"],
    "kc_ch6_01": ["kc_ch2_02", "kc_ch1_03"],
    "kc_ch6_02": ["kc_ch6_01"],
    "kc_ch6_03": ["kc_ch1_02"],
    "kc_ch6_04": ["kc_ch4_03"],
    "kc_ch6_05": ["kc_ch3_06"],
    "kc_ch6_06": ["kc_ch6_01", "kc_ch6_04", "kc_ch4_03"],
    "kc_ch6_07": ["kc_ch5_08", "kc_ch3_01", "kc_ch4_01"],
}

# 预计算：每个KC的"重要性权重"（被多少后续KC依赖）
_importance_cache: dict[str, int] | None = None


def _compute_importance() -> dict[str, int]:
    global _importance_cache
    if _importance_cache is not None:
        return _importance_cache
    importance: dict[str, int] = {kc: 0 for kc in KC_DEPENDENCIES}
    for kc, prereqs in KC_DEPENDENCIES.items():
        for p in prereqs:
            importance[p] = importance.get(p, 0) + 1
    _importance_cache = importance
    return importance


KC_IMPORTANCE = _compute_importance()


# ============================================================
# KC → 关键词映射（用于文本→KC推断）
# ============================================================
KC_KEYWORDS: dict[str, list[str]] = {
    "kc_ch1_01": ["python", "python简介", "环境搭建", "安装python", "解释器"],
    "kc_ch1_02": ["变量", "赋值", "数据类型", "int", "float", "str", "bool", "None", "type"],
    "kc_ch1_03": ["print", "input", "输出", "输入", "格式化", "f-string", "f字符串"],
    "kc_ch1_04": ["运算符", "表达式", "算术", "比较", "逻辑", "and", "or", "not", "加减乘除", "%", "**"],
    "kc_ch1_05": ["字符串", "索引", "切片", "upper", "lower", "replace", "split", "strip", "len"],
    "kc_ch1_06": ["类型转换", "int()", "float()", "str()", "bool()", "转换"],
    "kc_ch2_01": ["if", "elif", "else", "条件判断", "条件语句", "三元", "分支"],
    "kc_ch2_02": ["for", "range", "遍历", "迭代", "enumerate", "for循环"],
    "kc_ch2_03": ["while", "while循环", "条件循环", "无限循环"],
    "kc_ch2_04": ["break", "continue", "跳出循环", "跳过"],
    "kc_ch2_05": ["嵌套循环", "循环嵌套", "多层循环", "九九乘法表"],
    "kc_ch2_06": ["猜数字", "素数", "判断素数", "流程控制综合"],
    "kc_ch3_01": ["def", "函数定义", "函数调用", "定义函数", "调用函数", "文档字符串"],
    "kc_ch3_02": ["参数", "默认参数", "位置参数", "形参", "实参"],
    "kc_ch3_03": ["关键字参数", "可变参数", "*args", "**kwargs", "不定长参数"],
    "kc_ch3_04": ["return", "返回值", "返回", "多返回值", "元组解包"],
    "kc_ch3_05": ["作用域", "全局变量", "局部变量", "global", "LEGB", "命名空间"],
    "kc_ch3_06": ["import", "from import", "模块", "导入", "自定义模块", "as", "别名"],
    "kc_ch3_07": ["内置函数", "max", "min", "sum", "sorted", "zip", "map", "filter", "enumerate"],
    "kc_ch3_08": ["lambda", "匿名函数", "lambda表达式", "sort key"],
    "kc_ch4_01": ["列表", "list", "append", "insert", "remove", "pop", "sort", "索引", "切片"],
    "kc_ch4_02": ["元组", "tuple", "不可变", "解包", "单元素元组"],
    "kc_ch4_03": ["字典", "dict", "键值对", "get", "items", "keys", "values", "del"],
    "kc_ch4_04": ["集合", "set", "去重", "交集", "并集", "差集", "add", "discard"],
    "kc_ch4_05": ["列表推导式", "列表推导", "list comprehension", "[x for"],
    "kc_ch4_06": ["字典推导式", "集合推导式", "dict comprehension", "set comprehension", "{k:v for", "{x for"],
    "kc_ch4_07": ["嵌套", "嵌套列表", "嵌套字典", "列表套字典", "多维"],
    "kc_ch4_08": ["数据结构选择", "选型", "对比", "list vs tuple", "dict vs set"],
    "kc_ch5_01": ["面向对象", "OOP", "封装", "继承", "多态", "面向对象思想"],
    "kc_ch5_02": ["class", "类", "对象", "实例", "创建类", "定义类"],
    "kc_ch5_03": ["__init__", "构造方法", "构造函数", "初始化", "self"],
    "kc_ch5_04": ["实例方法", "实例属性", "classmethod", "staticmethod", "类方法", "静态方法"],
    "kc_ch5_05": ["继承", "super", "父类", "子类", "super()", "重写", "override"],
    "kc_ch5_06": ["多态", "方法重写", "鸭子类型", "多态性"],
    "kc_ch5_07": ["魔法方法", "__str__", "__repr__", "__add__", "__eq__", "__len__", "magic method", "dunder"],
    "kc_ch5_08": ["try", "except", "finally", "异常", "异常处理", "raise", "自定义异常", "错误处理"],
    "kc_ch6_01": ["文件", "open", "with", "read", "write", "readlines", "文件操作", "读写文件", "文件读写"],
    "kc_ch6_02": ["os", "路径", "os.path", "getcwd", "listdir", "目录"],
    "kc_ch6_03": ["datetime", "时间", "日期", "timedelta", "strftime", "strptime"],
    "kc_ch6_04": ["json", "json.dumps", "json.loads", "序列化", "反序列化", "JSON"],
    "kc_ch6_05": ["pip", "第三方库", "安装", "包管理", "pip install", "第三方包"],
    "kc_ch6_06": ["学生成绩", "成绩管理", "管理系统", "CRUD", "项目实战", "图书管理"],
    "kc_ch6_07": ["调试", "debug", "pdb", "assert", "断点", "PEP", "编码规范", "代码风格", "PEP8"],
}

# 章节ID → 章节名
CHAPTER_NAMES: dict[str, str] = {
    "01_basics": "Python基础语法",
    "02_control_flow": "流程控制",
    "03_functions": "函数与模块",
    "04_data_structures": "数据结构",
    "05_oop": "面向对象编程",
    "06_projects": "综合项目实战",
}


# ============================================================
# 核心算法
# ============================================================

def compute_mastery_update(current_p: float, quality_score: float,
                           learn_rate: float = LEARN_RATE) -> float:
    """单次交互后的掌握概率更新（贝叶斯形式）"""
    return min(1.0, current_p + (1.0 - current_p) * learn_rate * quality_score)


def compute_forgetting(mastery_p0: float, days_since_last_review: float,
                       review_count: int, base_rate: float = BASE_FORGET_RATE,
                       decay_factor: float = DECAY_FACTOR) -> float:
    """计算遗忘衰减后的掌握概率"""
    if days_since_last_review <= 0:
        return mastery_p0
    effective_rate = base_rate * math.exp(-review_count / decay_factor)
    return mastery_p0 * math.exp(-effective_rate * days_since_last_review)


def compute_review_priority(kc_id: str, current_p: float,
                            days_since_last_review: float) -> float:
    """计算复习优先级"""
    days_overdue = max(0, days_since_last_review - 7)
    importance = KC_IMPORTANCE.get(kc_id, 1)
    return (1.0 - current_p) * importance * (1.0 + days_overdue * 0.1)


def get_prerequisites(kc_id: str) -> list[str]:
    """获取某KC的直接前置依赖"""
    return KC_DEPENDENCIES.get(kc_id, [])


def get_dependents(kc_id: str) -> list[str]:
    """获取依赖某KC的所有后续KC"""
    return sorted([k for k, prereqs in KC_DEPENDENCIES.items() if kc_id in prereqs])


def is_ready_to_learn(kc_id: str, knowledge_states: dict[str, float]) -> bool:
    """判断某KC是否满足前置学习条件"""
    prereqs = get_prerequisites(kc_id)
    if not prereqs:
        return True
    return all(knowledge_states.get(p, 0) >= MASTERY_THRESHOLD for p in prereqs)


def get_learnable_topics(user_id: str) -> list[dict]:
    """获取当前可学习的KC列表（前置条件已满足 + 自身未掌握）"""
    states = get_user_knowledge_state(user_id)
    if not states:
        return []
    mastery_map = {s["kc_id"]: s["mastery_probability"] for s in states}
    all_kcs = {kc["id"]: kc for kc in get_all_kcs()}

    learnable = []
    for kc_id, kc_info in all_kcs.items():
        current_p = mastery_map.get(kc_id, 0)
        if current_p >= MASTERY_THRESHOLD:
            continue
        if is_ready_to_learn(kc_id, mastery_map):
            learnable.append({
                "kc_id": kc_id,
                "name": kc_info["name"],
                "chapter_id": kc_info["chapter_id"],
                "difficulty": kc_info["difficulty"],
                "current_mastery": current_p,
            })
    return learnable


# ============================================================
# 复习推荐
# ============================================================

def get_next_review_recommendations(user_id: str, top_n: int = 5) -> list[dict]:
    """获取最需要复习的N个KC"""
    states = get_user_knowledge_state(user_id)
    if not states:
        # 新用户，初始化knowledge_state
        init_knowledge_state_for_user(user_id)
        states = get_user_knowledge_state(user_id)
        if not states:
            return []

    now = datetime.now()
    priorities = []
    for s in states:
        kc_id = s["kc_id"]
        # 应用遗忘曲线计算当前掌握概率
        p_stored = s["mastery_probability"]
        last_time_str = s.get("last_review_time")
        review_count = s.get("review_count", 0)

        if last_time_str and p_stored > 0:
            try:
                last_time = datetime.fromisoformat(last_time_str)
                days = (now - last_time).total_seconds() / 86400
            except (ValueError, TypeError):
                days = 999
            p_current = compute_forgetting(p_stored, days, review_count)
        else:
            days = 999
            p_current = p_stored

        if p_current >= MASTERY_THRESHOLD:
            continue

        priority = compute_review_priority(kc_id, p_current, days)
        priorities.append({
            "kc_id": kc_id,
            "name": s.get("name", kc_id),
            "chapter_id": s.get("chapter_id", ""),
            "mastery_probability": round(p_current, 4),
            "stored_probability": round(p_stored, 4),
            "review_count": review_count,
            "days_since_last_review": round(days, 1),
            "priority": round(priority, 4),
        })

    priorities.sort(key=lambda x: x["priority"], reverse=True)
    return priorities[:top_n]


# ============================================================
# 知识状态管理（高层封装）
# ============================================================

def update_kc_mastery(user_id: str, kc_id: str, quality_score: float) -> float | None:
    """记录一次KC交互，更新掌握概率。返回新的掌握概率"""
    if not kc_id or kc_id not in KC_DEPENDENCIES:
        return None

    # 获取当前掌握概率（含遗忘衰减）
    from backend.db.models import get_single_kc_state
    current_state = get_single_kc_state(user_id, kc_id)

    if current_state and current_state["mastery_probability"] > 0:
        p_stored = current_state["mastery_probability"]
        last_time_str = current_state.get("last_review_time")
        review_count = current_state.get("review_count", 0)
        if last_time_str:
            try:
                last_time = datetime.fromisoformat(last_time_str)
                days = (datetime.now() - last_time).total_seconds() / 86400
            except (ValueError, TypeError):
                days = 0
        else:
            days = 0
        p_current = compute_forgetting(p_stored, days, review_count)
    else:
        p_current = 0.0

    p_new = compute_mastery_update(p_current, quality_score)
    upsert_knowledge_state(user_id, kc_id, p_new, quality_score)
    return p_new


def get_chapter_mastery_map(user_id: str) -> dict[str, float]:
    """返回 {chapter_display_name: avg_mastery_p}"""
    raw = get_chapter_average_mastery(user_id)
    return {CHAPTER_NAMES.get(k, k): v for k, v in raw.items()}


def get_chapter_mastery_text(user_id: str) -> str:
    """生成章节掌握度的文本摘要"""
    mastery = get_chapter_mastery_map(user_id)
    if not mastery:
        return ""
    lines = []
    for ch, p in mastery.items():
        if p >= 0.6:
            status = "已掌握"
        elif p >= 0.3:
            status = "学习中"
        else:
            status = "薄弱"
        lines.append(f"  {ch}: {status} ({p:.0%})")
    return "\n".join(lines)


def get_knowledge_level_from_state(user_id: str) -> str:
    """从知识状态推断学生整体水平"""
    summary = get_knowledge_state_summary(user_id)
    avg = summary.get("average_mastery", 0)
    mastered = summary.get("mastered_count", 0)
    if mastered >= 30:
        return "advanced"
    elif avg >= 0.5:
        return "medium"
    else:
        return "beginner"


def get_kc_mastery_stats(user_id: str) -> dict:
    """KC级掌握统计（供评估Agent使用）"""
    states = get_user_knowledge_state(user_id)
    if not states:
        return {"total": 0, "mastered": [], "weak": [], "learning": []}
    mastered = []
    weak = []
    learning = []
    for s in states:
        p = s["mastery_probability"]
        item = {"kc_id": s["kc_id"], "name": s.get("name", ""), "mastery": round(p, 4)}
        if p >= MASTERY_THRESHOLD:
            mastered.append(item)
        elif p < WEAK_THRESHOLD:
            weak.append(item)
        else:
            learning.append(item)
    return {
        "total": len(states),
        "mastered": mastered,
        "weak": weak,
        "learning": learning,
        "summary": get_knowledge_state_summary(user_id),
    }


def get_kc_graph_summary() -> str:
    """生成知识图谱文本摘要（供path_agent注入prompt）"""
    all_kcs = get_all_kcs()
    chapter_kcs: dict[str, list[str]] = {}
    for kc in all_kcs:
        ch_name = CHAPTER_NAMES.get(kc["chapter_id"], kc["chapter_id"])
        if ch_name not in chapter_kcs:
            chapter_kcs[ch_name] = []
        chapter_kcs[ch_name].append(kc["name"])

    lines = ["知识图谱结构（学习顺序）："]
    prev_ch = None
    for ch_name in CHAPTER_NAMES.values():
        kc_names = chapter_kcs.get(ch_name, [])
        lines.append(f"\n{ch_name}（{len(kc_names)}个知识点）：")
        for i, name in enumerate(kc_names, 1):
            kc_id = [k["id"] for k in all_kcs if k["chapter_id"] in {
                k: v for k, v in CHAPTER_NAMES.items() if v == ch_name
            } and k["name"] == name]
            prereqs = [k["name"] for k in all_kcs if k["id"] in KC_DEPENDENCIES.get(
                kc_id[0] if kc_id else "", [])]
            prereq_text = f"（前置：{'、'.join(prereqs)}）" if prereqs else ""
            lines.append(f"  {i}. {name} {prereq_text}")
    return "\n".join(lines)


# ============================================================
# 文本/错误 → KC 推断
# ============================================================

def infer_kc_from_text(text: str) -> list[str]:
    """从文本中推断关联的知识点ID列表"""
    if not text:
        return []
    text_lower = text.lower()
    matched_kcs: list[tuple[str, float]] = []
    for kc_id, keywords in KC_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in text_lower:
                score += 1
        if score > 0:
            matched_kcs.append((kc_id, score / len(keywords)))
    matched_kcs.sort(key=lambda x: x[1], reverse=True)
    return [kc for kc, _ in matched_kcs[:5]]


# 错误类型 → KC 映射
ERROR_KC_MAP: dict[str, list[str]] = {
    "SyntaxError": ["kc_ch1_01", "kc_ch2_01", "kc_ch3_01"],
    "IndentationError": ["kc_ch1_01", "kc_ch2_01"],
    "NameError": ["kc_ch1_02", "kc_ch3_05"],
    "TypeError": ["kc_ch1_02", "kc_ch1_06", "kc_ch3_02"],
    "ValueError": ["kc_ch1_06", "kc_ch4_01"],
    "IndexError": ["kc_ch1_05", "kc_ch4_01"],
    "KeyError": ["kc_ch4_03"],
    "AttributeError": ["kc_ch4_01", "kc_ch5_02"],
    "ZeroDivisionError": ["kc_ch1_04"],
    "ModuleNotFoundError": ["kc_ch3_06", "kc_ch6_05"],
    "FileNotFoundError": ["kc_ch6_01"],
    "RecursionError": ["kc_ch3_01", "kc_ch3_04"],
    "UnboundLocalError": ["kc_ch3_05"],
    "ImportError": ["kc_ch3_06"],
}


def infer_kc_from_error(error_type: str, error_msg: str = "", code: str = "") -> list[str]:
    """从错误信息推断关联的KC"""
    result = set()

    # 1. 从错误类型映射
    base_kcs = ERROR_KC_MAP.get(error_type, [])
    result.update(base_kcs)

    # 2. 从错误消息推断
    if error_msg:
        msg_kcs = infer_kc_from_text(error_msg)
        result.update(msg_kcs)

    # 3. 从代码内容推断
    if code:
        code_kcs = infer_kc_from_text(code)
        result.update(code_kcs)

    # 4. 去重后返回（保留最多6个）
    return list(result)[:6]


# ============================================================
# 诊断测试初始化
# ============================================================

def run_diagnostic_init(user_id: str) -> dict:
    """运行诊断测试初始化：从诊断结果计算并写入knowledge_state"""
    mastery = init_knowledge_state_from_diagnostic(user_id)
    # 确保所有未诊断的KC也有初始状态
    init_knowledge_state_for_user(user_id)
    return get_knowledge_state_summary(user_id)


# ============================================================
# 用户初始化（确保新用户有完整knowledge_state）
# ============================================================

def ensure_user_knowledge_state(user_id: str) -> None:
    """确保用户有完整的knowledge_state记录"""
    states = get_user_knowledge_state(user_id)
    if not states or len(states) < 43:
        init_knowledge_state_for_user(user_id)
