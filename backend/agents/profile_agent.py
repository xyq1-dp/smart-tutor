"""
学习画像智能体 — 对话式画像构建

通过自然对话自动抽取 6 个维度的学生画像：
1. 知识基础（knowledge_level）
2. 学习目标（learning_goal）
3. 认知风格（cognitive_style）
4. 学习节奏（pace）
5. 薄弱点（weak_points）
6. 兴趣方向（interest_areas）
"""

from backend.llm.spark import spark_chat
import json


PROFILE_EXTRACTION_PROMPT = """你是一个学生画像分析专家。根据以下对话内容，
提取学生的学习画像。返回 JSON 格式：

{{
  "knowledge_level": "beginner/medium/advanced",
  "learning_goal": "学生的主要学习目标",
  "cognitive_style": "visual/textual/hands-on",
  "pace": "fast/normal/slow",
  "weak_points": ["知识点1", "知识点2"],
  "interest_areas": ["方向1", "方向2"],
  "confidence": 0.0~1.0  # 本次提取的置信度
}}

只提取对话中明确体现的信息，未知的维度用 null。

{long_term_memory}

对话：
{conversation}
"""


async def extract_profile_from_chat(
    user_id: str,
    chat_history: list[dict],
) -> dict:
    """
    从对话历史中提取用户画像（第 2 周核心功能）

    Args:
        user_id: 用户 ID
        chat_history: 最近对话记录，每条 {"role": "...", "content": "..."}

    Returns:
        画像字典，包含 6 个维度的分析结果
    """
    # 构建对话文本
    conversation = "\n".join(
        f"{msg['role']}: {msg['content'][:200]}"
        for msg in chat_history[-20:]  # 最近 20 轮
    )

    # 获取长期记忆
    from backend.db.models import get_profile_long_term_memory
    long_term = get_profile_long_term_memory(user_id)
    memory_text = f"该学生的历史关键信息（请结合当前对话综合判断）：\n{long_term}" if long_term else ""

    prompt = PROFILE_EXTRACTION_PROMPT.format(
        conversation=conversation,
        long_term_memory=memory_text,
    )

    result = await spark_chat(
        [{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            profile = json.loads(result[start:end])
            return profile
    except (json.JSONDecodeError, ValueError):
        pass

    return {"confidence": 0, "error": "解析失败"}


async def update_profile_dimension(
    user_id: str,
    dimension: str,
    chat_context: str,
) -> dict:
    """
    更新单个画像维度（随学随新）

    Args:
        user_id: 用户 ID
        dimension: 维度名（如 knowledge_level）
        chat_context: 最近的学习表现描述

    Returns:
        更新后的维度值
    """
    prompt = f"""根据学生的学习表现，评估其"{dimension}"维度的最新状态。

学习表现：{chat_context}

请用 JSON 返回：
{{
  "dimension": "{dimension}",
  "previous_value": "之前的值（如未知则null）",
  "new_value": "更新后的值",
  "reason": "更新的理由（一句话）"
}}
"""
    result = await spark_chat([{"role": "user", "content": prompt}], temperature=0.1)

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {"dimension": dimension, "new_value": None, "reason": "解析失败"}
