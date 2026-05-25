"""
辅导智能体 — 结构化答疑（讲解 + 图解 + 代码 + 练习 + 纠错）
"""

import json

TUTOR_SYSTEM_PROMPT = """你是一个专业的 Python 编程辅导老师。学生向你提问，你需要给出结构化的辅导回答。

当前学生画像：
{profile_text}

学生的问题：{question}

请严格按照以下五段式结构回答，使用 Markdown 格式：

---

## 📖 概念讲解
- 用通俗易懂的语言解释核心概念
- 配合生活中的类比帮助学生理解
- 难度根据学生画像中的知识基础动态调整

## 🧠 图解（Mermaid）
- 用 Mermaid 语法绘制知识结构图
- 优先使用 mindmap 类型，也可以用 flowchart
- 确保 Mermaid 语法正确

## 💻 代码示例
- 提供可直接运行的完整 Python 代码
- 代码要包含注释
- 至少 1 个示例，根据知识点可多个

## ✏️ 练习题
- 出 1 道选择题或填空题
- 根据学生薄弱点针对性出题
- 附上答案和解析

## ⚠️ 常见错误
- 列出 1-2 个初学者容易犯的错误
- 说明错误原因和正确做法

---

要求：
- 全部用中文回答
- 代码示例要完整可运行
- 如果学生问的不是 Python 相关问题，引导回 Python 学习
"""


def _is_tutor_question(message: str) -> bool:
    """检测是否为知识性提问（需要辅导模式）"""
    msg = message.strip()
    question_keywords = [
        "什么", "怎么", "如何", "为什么", "解释", "讲解", "介绍",
        "说说", "讲讲", "区别", "对比", "用法", "用途", "示例",
        "例子", "举例", "代码", "实现", "原理", "概念", "报错",
        "错误", "不会", "不懂", "帮我", "教我", "什么是",
    ]
    if any(kw in msg for kw in question_keywords):
        return True
    if msg.endswith("?") or msg.endswith("？"):
        return True
    return False


def build_tutor_prompt(user_id: str, question: str) -> str:
    """构建辅导模式的 system prompt"""
    from backend.db.models import get_profile

    profile = get_profile(user_id) or {}
    parts = []

    if profile.get("knowledge_level"):
        parts.append(f"- 知识基础：{profile['knowledge_level']}")
    if profile.get("learning_goal"):
        parts.append(f"- 学习目标：{profile['learning_goal']}")
    if profile.get("cognitive_style"):
        parts.append(f"- 认知风格：{profile['cognitive_style']}")
    if profile.get("pace"):
        parts.append(f"- 学习节奏：{profile['pace']}")

    for field in ["weak_points", "interest_areas"]:
        raw = profile.get(field)
        if raw and raw != "[]":
            try:
                items = json.loads(raw) if isinstance(raw, str) else raw
                if items:
                    parts.append(f"- {field}：{', '.join(items)}")
            except (json.JSONDecodeError, ValueError):
                pass

    profile_text = "\n".join(parts) if parts else "画像尚未建立"

    return TUTOR_SYSTEM_PROMPT.format(profile_text=profile_text, question=question)
