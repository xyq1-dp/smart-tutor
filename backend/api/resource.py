"""资源生成接口 — 多智能体协同"""

import json
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ResourceRequest(BaseModel):
    topic: str
    resource_types: list[str] = None  # 默认全部 5 种
    user_id: str = "default"


@router.post("/resource/generate")
async def generate_resource(req: ResourceRequest):
    """多智能体协同生成个性化学习资源（SSE 流式返回进度）"""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="知识点主题不能为空")

    valid_types = {"doc", "mindmap", "exercise", "reading", "practice"}
    if req.resource_types:
        requested = [t for t in req.resource_types if t in valid_types]
    else:
        requested = list(valid_types)

    if not requested:
        raise HTTPException(status_code=400, detail="未指定有效的资源类型")

    progress_queue = asyncio.Queue()

    async def progress_callback(stage: str, data: dict):
        await progress_queue.put({"stage": stage, **data})

    async def generate():
        from backend.agents.orchestrator import run_resource_orchestrator

        # 在后台运行编排器
        task = asyncio.create_task(
            run_resource_orchestrator(
                user_id=req.user_id,
                topic=req.topic,
                resource_types=requested,
                progress_callback=progress_callback,
            )
        )

        # 从队列读取进度并发送 SSE
        while True:
            try:
                event = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["stage"] == "complete":
                    break
            except asyncio.TimeoutError:
                # 检查任务是否完成
                if task.done():
                    break

        # 获取最终结果
        try:
            result = await task
        except Exception as e:
            result = {"topic": req.topic, "resources": {}, "errors": [str(e)]}

        yield f"data: {json.dumps({'stage': 'result', 'data': result}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )


@router.get("/resource/types")
async def list_resource_types():
    """返回支持的 5 种资源类型"""
    return {
        "types": [
            {"id": "doc", "name": "课程讲解文档", "icon": "📄",
             "desc": "根据知识水平定制的详细讲解"},
            {"id": "mindmap", "name": "知识点思维导图", "icon": "🧠",
             "desc": "Mermaid 格式脑图，直观梳理知识脉络"},
            {"id": "exercise", "name": "自适应练习题", "icon": "✏️",
             "desc": "3选+2码，难度根据水平浮动"},
            {"id": "reading", "name": "拓展阅读材料", "icon": "📚",
             "desc": "精选书籍/博客/视频推荐"},
            {"id": "practice", "name": "代码实操案例", "icon": "💻",
             "desc": "真实场景项目 + 逐行注释"},
        ]
    }


@router.post("/resource/generate_single")
async def generate_single(req: ResourceRequest):
    """生成单个资源（非流式，直接返回）"""
    from backend.agents.orchestrator import run_resource_orchestrator

    types = req.resource_types[:1] if req.resource_types else ["doc"]
    result = await run_resource_orchestrator(
        user_id=req.user_id,
        topic=req.topic,
        resource_types=types,
    )
    return result
