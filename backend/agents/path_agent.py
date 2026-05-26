"""
学习路径规划智能体 — 动态生成 + 调整个性化学习路径
"""

from backend.llm.deepseek import deepseek_chat
import json


PATH_PLANNING_PROMPT = """你是一位课程设计专家。请根据以下信息规划个性化学习路径。

课程：Python 程序设计基础
{knowledge_graph}

学生画像：
- 知识基础：{knowledge_level}
- 学习目标：{learning_goal}
- 学习节奏：{pace}
- 薄弱点：{weak_points}
- 兴趣方向：{interest_areas}

当前各章节掌握度（0%~100%，基于43个知识点的概率估算）：
{chapter_mastery}

要求：
1. 根据掌握度判断学生当前应从哪里开始（≥60%可跳过，30%~60%降低优先级，<30%重点学习）
2. 为每个阶段设定具体的学习目标
3. 估算每个阶段的建议学时
4. 标注哪些是需要重点攻克的内容
5. 根据学习节奏调整每个阶段的时长
6. 掌握度≥60%的章节 priority 设为 "done"

请用 JSON 格式返回：
{{
  "starting_point": "应开始的章节",
  "path": [
    {{
      "order": 1,
      "title": "章节名",
      "topics": ["必学知识点"],
      "estimated_hours": 4,
      "priority": "high/medium/low",
      "tips": "学习建议"
    }}
  ],
  "total_estimated_hours": 42,
  "weekly_plan": "建议的每周学习计划"
}}
"""


async def plan_learning_path(profile: dict) -> dict:
    """
    根据学生画像规划个性化学习路径

    Args:
        profile: 包含 6 个维度信息的画像字典

    Returns:
        路径规划结果
    """
    weak_points = profile.get("weak_points", [])
    if isinstance(weak_points, str):
        weak_points = json.loads(weak_points) if weak_points else []

    interest_areas = profile.get("interest_areas", [])
    if isinstance(interest_areas, str):
        interest_areas = json.loads(interest_areas) if interest_areas else []

    # 构建章节掌握度文本（使用概率值）
    chapter_mastery = profile.get("_chapter_mastery", {})
    if chapter_mastery:
        progress_lines = []
        for ch, p in chapter_mastery.items():
            if p >= 0.6:
                label = "✅ 已掌握"
            elif p >= 0.3:
                label = "🔄 学习中"
            else:
                label = "⬜ 未开始"
            progress_lines.append(f"- {ch}：{label} ({p:.0%})")
        progress_text = "\n".join(progress_lines)
    else:
        progress_text = "暂无学习记录"

    # 获取知识图谱文本
    try:
        from backend.db.knowledge_tracing import get_kc_graph_summary
        knowledge_graph = get_kc_graph_summary()
    except Exception:
        knowledge_graph = """1. Python 基础语法（变量、类型、输入输出、运算符、字符串）
2. 流程控制（if/else、for 循环、while 循环、break/continue）
3. 函数与模块（函数定义、参数、作用域、模块、lambda）
4. 数据结构（列表、元组、字典、集合、推导式）
5. 面向对象编程（类、继承、多态、异常处理）
6. 综合项目实战（文件操作、第三方库、项目开发）"""

    prompt = PATH_PLANNING_PROMPT.format(
        knowledge_graph=knowledge_graph,
        knowledge_level=profile.get("knowledge_level", "beginner"),
        learning_goal=profile.get("learning_goal", "掌握 Python 基础"),
        pace=profile.get("pace", "normal"),
        weak_points=", ".join(weak_points) if weak_points else "无",
        interest_areas=", ".join(interest_areas) if interest_areas else "通用",
        chapter_mastery=progress_text,
    )

    result = await deepseek_chat(
        [{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {"error": "路径规划解析失败", "raw": result}


async def adjust_path_by_progress(
    current_path: dict,
    completed_topics: list[str],
    assessment_results: dict,
) -> dict:
    """
    根据学习进度和评估结果动态调整学习路径

    Args:
        current_path: 当前路径规划
        completed_topics: 已完成的知识点
        assessment_results: 最近的评估结果

    Returns:
        调整后的路径
    """
    prompt = f"""你是一位自适应学习专家。当前学习路径需要根据学生进展调整。

当前路径：{json.dumps(current_path, ensure_ascii=False)}
已完成知识点：{completed_topics}
评估结果：{json.dumps(assessment_results, ensure_ascii=False)}

请分析后给出调整建议，JSON 格式：
{{
  "should_adjust": true/false,
  "reason": "调整原因",
  "adjusted_path": [...],
  "focus_areas": ["需要重点复习的知识点"]
}}
"""
    result = await deepseek_chat([{"role": "user", "content": prompt}], temperature=0.3)

    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {"should_adjust": False, "reason": "无法分析"}
