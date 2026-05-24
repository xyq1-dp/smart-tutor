"""资源生成接口"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ResourceRequest(BaseModel):
    topic: str
    resource_type: str  # doc / mindmap / exercise / reading / practice
    user_id: str = "default"
    context: dict = {}


@router.post("/resource/generate")
async def generate_resource(req: ResourceRequest):
    """生成个性化学习资源（占位，后续接入多智能体）"""
    return {
        "status": "pending",
        "message": f"资源生成功能将在第3周实现。类型: {req.resource_type}, 主题: {req.topic}",
    }


@router.get("/resource/types")
async def list_resource_types():
    """返回支持的资源类型"""
    return {
        "types": [
            {"id": "doc", "name": "课程讲解文档", "icon": "📄"},
            {"id": "mindmap", "name": "知识点思维导图", "icon": "🧠"},
            {"id": "exercise", "name": "练习题目", "icon": "✏️"},
            {"id": "reading", "name": "拓展阅读材料", "icon": "📚"},
            {"id": "practice", "name": "代码实操案例", "icon": "💻"},
        ]
    }
