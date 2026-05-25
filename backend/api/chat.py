"""对话接口 - 学习画像构建 + 智能对话"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.llm.spark import spark_chat_stream
from backend.db.models import ensure_user, get_profile, save_message, update_profile
from backend.agents.profile_agent import extract_profile_from_chat
from backend.agents.tutor_agent import _is_tutor_question, build_tutor_prompt
from backend.utils.safety import check_content
from backend.utils.anti_hallucination import add_citations

router = APIRouter()

PROFILE_LABELS = {
    "knowledge_level": "知识基础",
    "learning_goal": "学习目标",
    "cognitive_style": "认知风格",
    "pace": "学习节奏",
    "weak_points": "薄弱点",
    "interest_areas": "兴趣方向",
}


class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    history: list[dict] = []


@router.post("/chat")
async def chat(req: ChatRequest):
    """对话接口 - 流式返回 + 画像自动更新"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 内容安全检查
    is_safe, reason = check_content(req.message)
    if not is_safe:
        raise HTTPException(status_code=422, detail=f"消息包含不当内容：{reason}")

    ensure_user(req.user_id)
    profile = get_profile(req.user_id)
    has_profile = profile and bool(profile.get("learning_goal"))

    # 检测是否为辅导模式（有画像 + 知识性提问）
    is_tutor_mode = has_profile and _is_tutor_question(req.message)

    if is_tutor_mode:
        system_content = build_tutor_prompt(req.user_id, req.message)
    else:
        system_content = _build_system_prompt(req.user_id)

    system_prompt = {"role": "system", "content": system_content}

    messages = [system_prompt] + req.history + [
        {"role": "user", "content": req.message}
    ]

    async def generate():
        full_response = ""
        async for chunk in spark_chat_stream(messages):
            if chunk.startswith("[错误"):
                yield f"data: {json.dumps({'error': chunk})}\n\n"
                return
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        # 为辅导/教学类回复添加来源声明
        if is_tutor_mode and full_response and "错误" not in full_response[:10]:
            citation = add_citations("")  # 只取引用声明部分
            full_response += citation
            yield f"data: {json.dumps({'content': citation})}\n\n"

        # 保存对话记录
        try:
            save_message(req.user_id, "user", req.message)
            save_message(req.user_id, "assistant", full_response)
        except Exception:
            pass

        # 记录学习行为 + 更新学习进度
        try:
            from backend.db.models import record_behavior, detect_topic_chapter, update_topic_progress
            btype = "tutor_question" if is_tutor_mode else "chat"
            topic_keywords = []
            for kw in ["列表", "字典", "函数", "类", "循环", "条件", "异常",
                        "文件", "模块", "面向对象", "推导", "装饰器", "字符串"]:
                if kw in req.message:
                    topic_keywords.append(kw)
            record_behavior(req.user_id, btype, {
                "question": req.message[:200],
                "tutor_mode": is_tutor_mode,
                "topics": topic_keywords,
                "response_len": len(full_response),
            })
            # 辅导模式自动标记知识点为学习中
            if is_tutor_mode:
                chapter = detect_topic_chapter(req.message)
                if chapter:
                    update_topic_progress(req.user_id, chapter, "in_progress")
        except Exception:
            pass

        # 从对话中提取画像并更新数据库
        try:
            all_history = req.history + [
                {"role": "user", "content": req.message},
                {"role": "assistant", "content": full_response},
            ]
            profile = await extract_profile_from_chat(req.user_id, all_history)
            if profile and profile.get("confidence", 0) > 0.5:
                update_fields = {}
                for dim in ["knowledge_level", "learning_goal", "cognitive_style", "pace"]:
                    if profile.get(dim):
                        update_fields[dim] = profile[dim]
                for dim in ["weak_points", "interest_areas"]:
                    if profile.get(dim):
                        update_fields[dim] = json.dumps(profile[dim], ensure_ascii=False)
                if update_fields:
                    update_profile(req.user_id, **update_fields)
        except Exception:
            pass

        yield f"data: {json.dumps({'done': True, 'tutor_mode': is_tutor_mode})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


def _build_system_prompt(user_id: str) -> str:
    """根据数据库中的画像构建系统提示词"""
    profile = get_profile(user_id)

    has_profile = profile and bool(profile.get("learning_goal"))

    if not has_profile:
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

    # 已建立画像，将画像信息注入 system prompt
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
                    parts.append(f"- {PROFILE_LABELS[field]}：{', '.join(items)}")
            except (json.JSONDecodeError, ValueError):
                pass

    profile_text = "\n".join(parts)

    return (
        "你是一个专业的 Python 学习助手。你需要：\n"
        "1. 根据学生的学习画像，提供个性化的学习建议和资源\n"
        "2. 用清晰易懂的方式解释 Python 知识\n"
        "3. 引导学生进行自主思考\n"
        "4. 回答始终用中文，注意内容的准确性\n\n"
        f"当前学生画像：\n{profile_text}\n\n"
        "请根据以上画像调整你的教学方式和推荐内容。"
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
