"""内容安全过滤 — 检查生成内容是否包含敏感/违规信息"""

import re
import os

# 加载敏感词列表
_SENSITIVE_WORDS: set[str] = set()

# 基础敏感词（政治、色情、暴力等，此处为示例）
_BASIC_FILTER = {
    "反动", "暴力", "赌博", "毒品", "色情",  # 示例，实际使用需完善
}


def init_sensitive_words():
    """从文件加载敏感词（如存在）"""
    global _SENSITIVE_WORDS
    _SENSITIVE_WORDS = set(_BASIC_FILTER)

    filter_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "sensitive_words.txt"
    )
    if os.path.exists(filter_path):
        with open(filter_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith("#"):
                    _SENSITIVE_WORDS.add(word)


def check_content(text: str) -> tuple[bool, str]:
    """
    检查文本是否包含敏感内容

    Returns:
        (is_safe, reason): is_safe=True 表示安全，False 表示需要拦截
    """
    if not _SENSITIVE_WORDS:
        init_sensitive_words()

    text_lower = text.lower()

    for word in _SENSITIVE_WORDS:
        if word.lower() in text_lower:
            return False, f"内容包含敏感词"

    # 检查是否出现明显的非法指令（prompt injection 防护）
    injection_patterns = [
        r"忽略.*(?:以上|之前|所有).*指令",
        r"ignore.*(?:above|previous|all).*instruction",
        r"你.*(?:必须|必须).*回答",
        r"忘记.*(?:角色|设定|system)",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "检测到可能的提示注入攻击"

    return True, ""


def filter_text(text: str, replacement: str = "[内容已过滤]") -> str:
    """将敏感词替换为占位符"""
    result = text
    for word in _SENSITIVE_WORDS:
        if word in result:
            result = result.replace(word, replacement)
    return result
