"""
评估智能体 — 多维度学习效果评估 + 动态调整建议
"""

import json
from backend.llm.deepseek import deepseek_chat


EVALUATION_PROMPT = """你是一位教育评估专家。请根据以下数据对学生的学习效果进行多维度评估。

## 学生画像
{profile_text}

## 学习行为数据
- 总行为次数：{total_behaviors}
- 行为类型分布：{type_counts}
- 最近活跃：{last_active}
- 接触过的知识点：{topics_touched}

## 知识点级掌握度（43个知识点）
- 已掌握(P≥0.6): {mastered_count} 个
- 学习中(0.3≤P<0.6): {learning_count} 个
- 薄弱(P<0.3): {weak_count} 个
- 平均掌握概率：{average_mastery}

## 各章节掌握度
{chapter_mastery_text}

## 薄弱知识点列表
{weak_list}

## 错误模式分析
{error_patterns}

## 资源参与度
{engagement_text}

## 最近对话记录
{chat_summary}

## 当前学习路径阶段
{path_progress}

## 上次评估结果
{last_assessment}

请从以下维度进行评估，返回 JSON：

{{
  "knowledge_mastery": {{
    "score": 0-100,
    "level": "入门/初级/中级/高级",
    "comment": "对已学知识的掌握程度分析"
  }},
  "engagement": {{
    "score": 0-100,
    "level": "低/中/高",
    "comment": "学习活跃度和投入程度分析"
  }},
  "progress": {{
    "score": 0-100,
    "comment": "相对于学习目标的完成进度"
  }},
  "weak_points": ["当前薄弱知识点"],
  "strengths": ["已掌握较好的方面"],
  "overall_score": 0-100,
  "summary": "综合评估总结（2-3句话）",
  "suggestions": {{
    "immediate": "本周具体学习建议",
    "short_term": "2周内的学习目标",
    "focus_topics": ["建议重点学习的知识点"]
  }},
  "path_adjustment": {{
    "should_adjust": true/false,
    "reason": "是否需要调整学习路径及原因",
    "recommended_order": ["调整后的学习顺序建议"]
  }}
}}

要求：评估客观准确，建议具体可执行。用中文。"""


COLD_START_PROMPT = """你是一位教育评估专家。这位学生刚开始使用学习系统，数据有限。

## 学生画像
{profile_text}

## 早期行为信号
- 总行为次数：{total_behaviors}
- 行为类型分布：{type_counts}
- 接触过的知识点：{topics_touched}

## 早期对话片段
{chat_summary}

这是学生的首次评估。请不要打过高或过低的分数——数据不足以做精确判断。
请根据画像信息给出一个保守的起点评估，重点放在基于画像的**学习建议**上，
而非对掌握度的精确判断。

返回 JSON 格式同上，但注意：
- overall_score 控制在 30-50 之间（初始基准线）
- knowledge_mastery.score 基于画像中的 knowledge_level 推算（beginner→30, medium→50, advanced→65）
- engagement.score 基于已有行为次数估算（<5次→20, 5-10次→35, >10次→50）
- summary 中说明"这是基于有限数据的初始评估，随着学习深入会更准确"
- suggestions 要具体、可执行，聚焦在"如何开始有效学习"

用中文。"""


async def evaluate_learning(user_id: str) -> dict:
    """
    多维度学习效果评估

    综合画像、行为、对话、路径四方面数据，调用 LLM 进行评估。
    """
    from backend.db.models import (
        get_profile, get_behaviors, get_behavior_summary,
        get_chat_history, get_latest_assessment,
    )

    profile = get_profile(user_id) or {}
    behaviors = get_behaviors(user_id, limit=100)
    summary = get_behavior_summary(user_id)
    chat_history = get_chat_history(user_id, limit=30)
    last_assessment = get_latest_assessment(user_id)

    # 获取KC级知识状态
    from backend.db.knowledge_tracing import get_kc_mastery_stats, get_chapter_mastery_map
    from backend.db.models import get_error_patterns, get_engagement_summary
    kc_stats = get_kc_mastery_stats(user_id)
    chapter_mastery = get_chapter_mastery_map(user_id)
    error_patterns = get_error_patterns(user_id)
    engagement = get_engagement_summary(user_id)

    # 构建画像文本
    profile_parts = []
    for key, label in [
        ("knowledge_level", "知识基础"), ("learning_goal", "学习目标"),
        ("cognitive_style", "认知风格"), ("pace", "学习节奏"),
    ]:
        if profile.get(key):
            profile_parts.append(f"- {label}：{profile[key]}")
    for field, label in [("weak_points", "薄弱点"), ("interest_areas", "兴趣方向")]:
        raw = profile.get(field, "[]")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                raw = []
        if raw:
            profile_parts.append(f"- {label}：{', '.join(raw)}")
    profile_text = "\n".join(profile_parts) if profile_parts else "画像尚未建立"

    # 构建对话摘要
    chat_summary = ""
    if chat_history:
        recent = chat_history[-10:]
        chat_summary = "\n".join(
            f"[{m['role']}] {m['content'][:200]}" for m in recent
        )

    # 路径进度
    path_progress = _get_path_progress(user_id)

    # 上次评估
    last_assessment_text = "首次评估"
    if last_assessment:
        last_assessment_text = json.dumps({
            "overall_score": last_assessment.get("overall_score"),
            "summary": last_assessment.get("summary", ""),
            "created_at": last_assessment.get("created_at", ""),
        }, ensure_ascii=False)

    total_behaviors = summary.get("total_behaviors", 0)
    is_cold_start = total_behaviors < 10 and not last_assessment

    # 构建KC级掌握度文本
    kc_summary = kc_stats.get("summary", {})
    mastered_count = kc_summary.get("mastered_count", 0)
    learning_count = kc_summary.get("total_kcs", 43) - mastered_count - kc_summary.get("weak_count", 0)
    weak_count = kc_summary.get("weak_count", 0)
    average_mastery = kc_summary.get("average_mastery", 0)

    chapter_mastery_text = "\n".join(
        f"- {ch}: {p:.0%}" for ch, p in chapter_mastery.items()
    ) if chapter_mastery else "暂无数据"

    weak_list_text = "\n".join(
        f"- {w['name']} (掌握度: {w['mastery_probability']:.0%})"
        for w in kc_stats.get("weak", [])[:10]
    ) or "暂无"

    error_text = "\n".join(
        f"- {etype}: {cnt}次" for etype, cnt in error_patterns.items()
    ) if error_patterns else "暂无错误记录"

    engagement_text = (
        f"总互动{engagement.get('total_engagements', 0)}次，"
        f"平均停留{engagement.get('avg_duration_seconds', 0)}秒，"
        f"回访{engagement.get('total_revisits', 0)}次"
    ) if engagement.get("total_engagements", 0) > 0 else "暂无资源互动"

    if is_cold_start:
        prompt = COLD_START_PROMPT.format(
            profile_text=profile_text,
            total_behaviors=total_behaviors,
            type_counts=json.dumps(summary.get("type_counts", {}), ensure_ascii=False),
            topics_touched=", ".join(summary.get("topics_touched", [])) or "暂无",
            chat_summary=chat_summary or "暂无对话记录",
        )
    else:
        prompt = EVALUATION_PROMPT.format(
            profile_text=profile_text,
            total_behaviors=total_behaviors,
            type_counts=json.dumps(summary.get("type_counts", {}), ensure_ascii=False),
            last_active=summary.get("last_active", "未知"),
            topics_touched=", ".join(summary.get("topics_touched", [])) or "暂无",
            mastered_count=mastered_count,
            learning_count=learning_count,
            weak_count=weak_count,
            average_mastery=f"{average_mastery:.0%}",
            chapter_mastery_text=chapter_mastery_text,
            weak_list=weak_list_text,
            error_patterns=error_text,
            engagement_text=engagement_text,
            chat_summary=chat_summary or "暂无对话记录",
            path_progress=path_progress,
            last_assessment=last_assessment_text,
        )

    result = await deepseek_chat(
        [{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    # 冷启动标注
    if is_cold_start:
        result_copy = _parse_result(result)
        result_copy["assessment_type"] = "initial"
        result_copy["data_sufficiency"] = "low"
        return result_copy

    return _parse_result(result)


def _get_path_progress(user_id: str) -> str:
    """获取当前学习路径进度（基于KC掌握度，简版）"""
    from backend.db.knowledge_tracing import get_chapter_mastery_map, CHAPTER_NAMES

    mastery = get_chapter_mastery_map(user_id)
    if not mastery:
        return "暂无学习记录"

    all_stages = list(CHAPTER_NAMES.values())
    lines = ["各章节掌握度："]
    for stage in all_stages:
        p = mastery.get(stage, 0)
        if p >= 0.6:
            status = "已掌握"
        elif p >= 0.3:
            status = "学习中"
        else:
            status = "未开始"
        lines.append(f"- {stage}：{status} ({p:.0%})")
    return "\n".join(lines)


def _stage_keywords(stage: str) -> list[str]:
    """将课程阶段映射到关键词"""
    mapping = {
        "Python 基础语法": ["变量", "类型", "输入输出", "运算符", "字符串", "基础语法"],
        "流程控制": ["if", "for", "while", "循环", "条件", "流程控制"],
        "函数与模块": ["函数", "参数", "作用域", "模块", "lambda", "装饰"],
        "数据结构": ["列表", "元组", "字典", "集合", "推导", "数据结构"],
        "面向对象编程": ["类", "继承", "多态", "异常", "面向对象", "OOP"],
        "综合项目实战": ["项目", "文件", "第三方库", "实战", "综合"],
    }
    return mapping.get(stage, [stage])


def _parse_result(raw: str) -> dict:
    """解析 LLM 评估结果"""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return {"error": "评估结果解析失败", "raw": raw}


def build_adjustment_context(assessment: dict) -> dict:
    """
    从评估结果提取路径调整上下文（供 PathAgent 使用）
    """
    path_adj = assessment.get("path_adjustment", {})
    suggestions = assessment.get("suggestions", {})

    return {
        "should_adjust": path_adj.get("should_adjust", False),
        "reason": path_adj.get("reason", ""),
        "focus_topics": suggestions.get("focus_topics", []),
        "weak_points": assessment.get("weak_points", []),
        "overall_score": assessment.get("overall_score", 0),
    }
