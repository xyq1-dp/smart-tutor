"""
FastAPI 应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.chat import router as chat_router
from backend.api.resource import router as resource_router
from backend.api.path import router as path_router
from backend.api.assessment import router as assessment_router
from backend.api.executor import router as executor_router
from backend.db.models import init_db

app = FastAPI(
    title="智能学习助手 API",
    description="高等教育个性化学习智能体系统 - 后端接口",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(resource_router, prefix="/api")
app.include_router(path_router, prefix="/api")
app.include_router(assessment_router, prefix="/api")
app.include_router(executor_router, prefix="/api")


@app.on_event("startup")
async def startup():
    init_db()
    # 初始化知识图谱（43个知识点）
    from backend.db.models import init_knowledge_components
    init_knowledge_components()
    # 自动索引知识库（增量，跳过已索引的）
    from backend.db.vector_store import auto_index_knowledge_base
    try:
        auto_index_knowledge_base()
    except Exception:
        pass  # 索失败不影响启动


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "smart-tutor"}


@app.get("/api/kb/stats")
async def kb_stats():
    """知识库索引状态"""
    from backend.db.vector_store import get_kb_stats
    return get_kb_stats()


@app.post("/api/kb/reindex")
async def kb_reindex():
    """强制重新索引知识库"""
    from backend.db.vector_store import reindex_knowledge_base
    return reindex_knowledge_base()
