"""学习路径规划接口 — 个性化路径生成"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


def _normalize_stages(path: list[dict]) -> list[dict]:
    """兼容 LLM 返回的不同字段名（chapter ↔ title），并排序"""
    for s in path:
        if "title" not in s and "chapter" in s:
            s["title"] = s.pop("chapter")
    path.sort(key=lambda s: s.get("order", 0))
    return path


class PathRequest(BaseModel):
    user_id: str


@router.get("/path/default")
async def get_default_path():
    """返回默认学习路径（无需画像的兜底）"""
    return _default_path("默认路径")


@router.get("/path/{user_id}")
async def get_personalized_path(user_id: str):
    """根据学生画像返回个性化学习路径"""
    from backend.db.models import ensure_user, get_profile, record_behavior
    from backend.agents.path_agent import plan_learning_path

    ensure_user(user_id)
    profile = get_profile(user_id)

    # 记录路径查看行为
    try:
        record_behavior(user_id, "path_view", {"source": "get_path"})
    except Exception:
        pass

    has_profile = profile and bool(profile.get("learning_goal"))
    if not has_profile:
        return _default_path("画像未建立，显示默认路径")

    try:
        # 注入评估数据增强画像
        from backend.db.models import get_latest_assessment
        assessment = get_latest_assessment(user_id)
        enriched_profile = dict(profile)
        if assessment:
            suggestions_str = assessment.get("suggestions", "")
            if isinstance(suggestions_str, str):
                try:
                    suggestions = json.loads(suggestions_str)
                except (json.JSONDecodeError, ValueError):
                    suggestions = {}
            else:
                suggestions = suggestions_str or {}

            dims = assessment.get("dimensions", {})
            if isinstance(dims, str):
                try:
                    dims = json.loads(dims)
                except (json.JSONDecodeError, ValueError):
                    dims = {}

            enriched_profile["_assessment_score"] = assessment.get("overall_score", 0)
            enriched_profile["_focus_topics"] = suggestions.get("focus_topics", [])
            enriched_profile["_knowledge_mastery"] = dims.get("knowledge_mastery", {}).get("score", 0)

        result = await plan_learning_path(enriched_profile)
        if "error" in result:
            return _default_path(result.get("error", ""))

        response = {
            "course": "Python 程序设计基础",
            "personalized": True,
            "starting_point": result.get("starting_point", ""),
            "total_estimated_hours": result.get("total_estimated_hours", 42),
            "weekly_plan": result.get("weekly_plan", ""),
            "stages": _normalize_stages(result.get("path", [])),
        }
        if assessment:
            response["assessment_summary"] = {
                "overall_score": assessment.get("overall_score"),
                "summary": assessment.get("summary", ""),
                "evaluated_at": assessment.get("created_at", ""),
            }
        return response
    except Exception as e:
        return _default_path(f"路径规划失败: {str(e)}")


@router.post("/path/plan")
async def regenerate_path(req: PathRequest):
    """强制重新规划学习路径（调用 LLM 重新生成）"""
    from backend.db.models import ensure_user, get_profile
    from backend.agents.path_agent import plan_learning_path

    ensure_user(req.user_id)
    profile = get_profile(req.user_id)

    # 记录路径规划行为
    try:
        from backend.db.models import record_behavior
        record_behavior(req.user_id, "path_plan", {"source": "regenerate"})
    except Exception:
        pass

    if not profile or not profile.get("learning_goal"):
        raise HTTPException(status_code=400, detail="请先在聊天中建立学习画像")

    try:
        from backend.db.models import get_latest_assessment
        assessment = get_latest_assessment(req.user_id)
        enriched_profile = dict(profile)
        if assessment:
            suggestions_str = assessment.get("suggestions", "")
            if isinstance(suggestions_str, str):
                try:
                    suggestions = json.loads(suggestions_str)
                except (json.JSONDecodeError, ValueError):
                    suggestions = {}
            else:
                suggestions = suggestions_str or {}

            dims = assessment.get("dimensions", {})
            if isinstance(dims, str):
                try:
                    dims = json.loads(dims)
                except (json.JSONDecodeError, ValueError):
                    dims = {}

            enriched_profile["_assessment_score"] = assessment.get("overall_score", 0)
            enriched_profile["_focus_topics"] = suggestions.get("focus_topics", [])
            enriched_profile["_knowledge_mastery"] = dims.get("knowledge_mastery", {}).get("score", 0)

        result = await plan_learning_path(enriched_profile)
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        response = {
            "course": "Python 程序设计基础",
            "personalized": True,
            "starting_point": result.get("starting_point", ""),
            "total_estimated_hours": result.get("total_estimated_hours", 42),
            "weekly_plan": result.get("weekly_plan", ""),
            "stages": _normalize_stages(result.get("path", [])),
        }
        if assessment:
            response["assessment_summary"] = {
                "overall_score": assessment.get("overall_score"),
                "summary": assessment.get("summary", ""),
                "evaluated_at": assessment.get("created_at", ""),
            }
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _default_path(note: str = "") -> dict:
    return {
        "course": "Python 程序设计基础",
        "personalized": False,
        "note": note,
        "starting_point": "Python 基础语法",
        "total_estimated_hours": 42,
        "stages": [
            {
                "order": 1,
                "title": "Python 基础语法",
                "topics": ["变量与数据类型", "输入输出", "运算符", "字符串基础"],
                "estimated_hours": 4,
                "priority": "high",
                "tips": "",
            },
            {
                "order": 2,
                "title": "流程控制",
                "topics": ["条件判断 if/elif/else", "for 循环", "while 循环", "break/continue"],
                "estimated_hours": 6,
                "priority": "high",
                "tips": "",
            },
            {
                "order": 3,
                "title": "函数与模块",
                "topics": ["函数定义与调用", "参数与返回值", "作用域", "模块导入"],
                "estimated_hours": 6,
                "priority": "high",
                "tips": "",
            },
            {
                "order": 4,
                "title": "数据结构",
                "topics": ["列表与元组", "字典与集合", "列表推导式", "数据操作练习"],
                "estimated_hours": 8,
                "priority": "medium",
                "tips": "",
            },
            {
                "order": 5,
                "title": "面向对象编程",
                "topics": ["类与对象", "继承与多态", "魔法方法", "异常处理"],
                "estimated_hours": 8,
                "priority": "medium",
                "tips": "",
            },
            {
                "order": 6,
                "title": "综合项目实战",
                "topics": ["文件操作", "第三方库使用", "小型项目开发", "代码调试"],
                "estimated_hours": 10,
                "priority": "low",
                "tips": "",
            },
        ],
    }
