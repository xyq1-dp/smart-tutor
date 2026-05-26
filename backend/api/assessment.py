"""学习评估接口 — 多维度评估 + 行为追踪"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class EvaluateRequest(BaseModel):
    user_id: str


@router.post("/assessment/evaluate")
async def trigger_evaluation(req: EvaluateRequest):
    """触发一次学习效果评估"""
    from backend.db.models import ensure_user, get_profile
    from backend.agents.evaluation_agent import evaluate_learning
    from backend.db.knowledge_tracing import ensure_user_knowledge_state

    ensure_user(req.user_id)
    ensure_user_knowledge_state(req.user_id)
    profile = get_profile(req.user_id)

    if not profile or not profile.get("learning_goal"):
        raise HTTPException(
            status_code=400,
            detail="请先在聊天中建立学习画像，再进行评估",
        )

    result = await evaluate_learning(req.user_id)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # 保存评估结果
    from backend.db.models import save_assessment

    dims = {
        "knowledge_mastery": result.get("knowledge_mastery", {}),
        "engagement": result.get("engagement", {}),
        "progress": result.get("progress", {}),
    }
    weak_change = result.get("weak_points", [])
    overall = result.get("overall_score", 0)
    summary = result.get("summary", "")
    suggestions = json.dumps(result.get("suggestions", {}), ensure_ascii=False)

    assessment_id = save_assessment(
        user_id=req.user_id,
        dimensions=dims,
        summary=summary,
        suggestions=suggestions,
        weak_points_change=weak_change,
        overall_score=overall,
    )

    result["assessment_id"] = assessment_id
    return result


@router.post("/assessment/diagnostic")
async def submit_diagnostic(req: EvaluateRequest):
    """根据诊断测试结果初始化知识状态"""
    from backend.db.models import ensure_user, get_diagnostic_results
    from backend.db.knowledge_tracing import run_diagnostic_init

    ensure_user(req.user_id)
    summary = run_diagnostic_init(req.user_id)
    diagnostic = get_diagnostic_results(req.user_id)

    return {
        "user_id": req.user_id,
        "knowledge_summary": summary,
        "diagnostic_results": diagnostic,
    }


@router.get("/assessment/{user_id}")
async def get_assessment(user_id: str):
    """获取最新评估结果"""
    from backend.db.models import ensure_user, get_latest_assessment

    ensure_user(user_id)
    assessment = get_latest_assessment(user_id)

    if not assessment:
        return {
            "user_id": user_id,
            "has_assessment": False,
            "message": "暂无评估记录，请先触发评估",
        }

    return {
        "user_id": user_id,
        "has_assessment": True,
        "assessment": assessment,
    }


@router.get("/assessment/{user_id}/history")
async def get_assessment_history(user_id: str):
    """获取评估历史"""
    from backend.db.models import ensure_user, get_assessment_history

    ensure_user(user_id)
    history = get_assessment_history(user_id)

    return {
        "user_id": user_id,
        "count": len(history),
        "history": history,
    }


@router.post("/assessment/record-behavior")
async def record_behavior(req: EvaluateRequest):
    """手动记录学习行为（前端调用）"""
    from backend.db.models import ensure_user

    ensure_user(req.user_id)
    # 行为记录在各 API 中自动完成，此端点仅为前端手动触发
    return {"status": "ok"}
