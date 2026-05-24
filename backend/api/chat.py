"""对话接口 - 学习画像构建 + 智能对话"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.llm.spark import spark_chat_stream
from backend.db.models import ensure_user, get_profile

router = APIRouter()

# 画像维度定义（用于 system prompt）
PROFILE_DIMENSIONS = {
    "knowledge_level": "知识基础（入门/基础/进阶/熟练）",
    "learning_goal": "学习目标（考证/求职/兴趣/课程要求）",
    "cognitive_style": "认知风格（视觉型/文字型/动手型）",
    "pace": "学习节奏偏好（快速/正常/细致）",
    "weak_points": "知识薄弱点列表",
    "interest_areas": "兴趣方向",
}


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest):
    """对话接口 - 流式返回"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 构建 system prompt - 引导画像构建
    system_prompt = {
        "role": "system",
        "content": _build_system_prompt(req.history),
    }

    messages = [system_prompt] + req.history + [
        {"role": "user", "content": req.message}
    ]

    async def generate():
        async for chunk in spark_chat_stream(messages):
            if chunk.startswith("[错误"):
                yield f"data: {json.dumps({'error': chunk})}\n\n"
                break
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


def _build_system_prompt(history: list[dict]) -> str:
    """根据对话历史构建系统提示词"""
    has_profile_info = any(
        "学习目标" in msg.get("content", "")
        or "知识基础" in msg.get("content", "")
        for msg in history
    )

    if not has_profile_info:
        return (
            "你是一个友好的个性化学习助手。你的首要任务是了解学生的学习情况，"
            "通过自然对话逐步收集以下信息：\n"
            "1. 当前知识基础（例如：学过哪些编程语言、掌握到什么程度）\n"
            "2. 学习目标（例如：通过考试、找工作、做项目）\n"
            "3. 偏好的学习方式（看视频、读文档、动手写代码）\n"
            "4. 学习节奏偏好（快速过一遍还是精打细磨）\n"
            "5. 哪些知识点感觉困难\n"
            "6. 感兴趣的方向\n\n"
            "请注意：每次对话只自然涉及1-2个维度，不要像填表一样一股脑问完。\n"
            "用轻松友好的语气，像学长/学姐一样和学生聊天。\n"
            "回答始终用中文。"
        )
    else:
        return (
            "你是一个专业的 Python 学习助手。你需要：\n"
            "1. 根据学生的学习画像，提供个性化的学习建议和资源\n"
            "2. 用清晰易懂的方式解释 Python 知识\n"
            "3. 引导学生进行自主思考\n"
            "4. 回答始终用中文，注意内容的准确性\n"
        )


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """获取用户画像"""
    ensure_user(user_id)
    profile = get_profile(user_id)
    if profile is None:
        return {"user_id": user_id, "profile": None, "message": "画像尚未构建"}
    return {"user_id": user_id, "profile": profile}


@router.get("/profile/{user_id}/dimensions")
async def get_profile_dimensions(user_id: str):
    """获取 6 个画像维度的简化版本（给前端侧边栏用）"""
    ensure_user(user_id)
    profile = get_profile(user_id)
    if profile is None:
        return {
            "user_id": user_id,
            "dimensions": [
                {"key": "knowledge_level", "label": "知识基础", "value": "未知"},
                {"key": "learning_goal", "label": "学习目标", "value": "未设定"},
                {"key": "cognitive_style", "label": "认知风格", "value": "未设定"},
                {"key": "pace", "label": "学习节奏", "value": "正常"},
                {"key": "weak_points", "label": "薄弱点", "value": "待检测"},
                {"key": "interest_areas", "label": "兴趣方向", "value": "待检测"},
            ],
        }

    dims = [
        ("knowledge_level", "知识基础", profile.get("knowledge_level", "未知")),
        ("learning_goal", "学习目标", profile.get("learning_goal", "未设定")),
        ("cognitive_style", "认知风格", profile.get("cognitive_style", "未设定")),
        ("pace", "学习节奏", profile.get("pace", "正常")),
        ("weak_points", "薄弱点", _format_list(profile.get("weak_points", "[]"))),
        ("interest_areas", "兴趣方向", _format_list(profile.get("interest_areas", "[]"))),
    ]
    return {
        "user_id": user_id,
        "dimensions": [
            {"key": k, "label": label, "value": value}
            for k, label, value in dims
        ],
    }


def _format_list(raw) -> str:
    """将 JSON 字符串列表格式化为可读文本"""
    if isinstance(raw, list):
        return ", ".join(raw)
    if isinstance(raw, str):
        try:
            items = json.loads(raw)
            if isinstance(items, list):
                return ", ".join(items)
        except (json.JSONDecodeError, ValueError):
            pass
        return raw
    return str(raw)
