"""
多智能体协调器 — 5 个 Agent 协同生成学习资源

协调流程：
  ProfileAgent（读画像） → 并行调用 5 个 ResourceAgent
  → DocAgent + MindmapAgent + ExerciseAgent + ReadingAgent + PracticeAgent
  → 汇总返回
"""

import json
import asyncio
from typing import TypedDict


class AgentState(TypedDict):
    """多智能体共享状态"""
    user_id: str
    topic: str
    profile: dict
    resource_types: list[str]
    generated: dict[str, str]  # {type: content}
    kb_context: str
    stage: str
    errors: list[str]


async def run_resource_orchestrator(
    user_id: str,
    topic: str,
    resource_types: list[str] = None,
    progress_callback=None,
) -> dict:
    """
    多智能体资源生成编排器入口。

    协调 5 个专业 Agent：
    - DocAgent: 课程讲解文档
    - MindmapAgent: Mermaid 思维导图
    - ExerciseAgent: 自适应练习题
    - ReadingAgent: 拓展阅读材料
    - PracticeAgent: 代码实操案例

    Args:
        user_id: 用户 ID
        topic: 知识点主题（如 "Python 列表"）
        resource_types: 需要生成的资源类型列表，默认全部 5 种
        progress_callback: 可选，进度回调 async fn(stage, data)

    Returns:
        {"topic": ..., "resources": {...}, "profile_used": {...}}
    """
    from backend.db.models import get_profile, ensure_user
    from backend.db.vector_store import search_knowledge
    from backend.agents.resource_agent import generate_resource

    ensure_user(user_id)
    profile = get_profile(user_id) or {}

    # 解析 JSON 字符串字段
    for field in ["weak_points", "interest_areas"]:
        raw = profile.get(field, "[]")
        if isinstance(raw, str):
            try:
                profile[field] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                profile[field] = []

    if resource_types is None:
        resource_types = ["doc", "mindmap", "exercise", "reading", "practice"]

    # === Stage 1: 知识库检索（RAG 增强） ===
    if progress_callback:
        await progress_callback("kb_search", {"message": "正在检索相关知识..."})

    kb_context = ""
    try:
        kb_results = search_knowledge(topic, n_results=3)
        kb_context = "\n---\n".join(
            r["content"][:600] for r in kb_results
        )
    except Exception:
        kb_results = []

    # === Stage 2: 并行生成资源（每个 Agent 独立工作） ===
    if progress_callback:
        await progress_callback("generating", {
            "message": f"正在调度 {len(resource_types)} 个智能体生成资源...",
            "types": resource_types,
        })

    results = {}
    errors = []

    # 逐个生成（避免 LLM API 并发限流），同时汇报进度
    for rtype in resource_types:
        if progress_callback:
            await progress_callback("agent_start", {"type": rtype})

        try:
            content = await generate_resource(rtype, topic, profile)
            results[rtype] = content
            if progress_callback:
                await progress_callback("agent_done", {
                    "type": rtype,
                    "preview": content[:150] + "..." if len(content) > 150 else content,
                })
        except Exception as e:
            errors.append(f"{rtype}: {str(e)}")
            results[rtype] = f"[生成失败] {str(e)}"
            if progress_callback:
                await progress_callback("agent_error", {"type": rtype, "error": str(e)})

    # === Stage 3: 汇总 ===
    if progress_callback:
        await progress_callback("complete", {
            "message": f"全部完成！成功 {len(results) - len(errors)}/{len(results)} 个",
        })

    return {
        "topic": topic,
        "profile_used": {
            "knowledge_level": profile.get("knowledge_level", "beginner"),
            "learning_goal": profile.get("learning_goal", ""),
            "cognitive_style": profile.get("cognitive_style", ""),
        },
        "kb_references": len(kb_results),
        "resources": results,
        "errors": errors,
    }
