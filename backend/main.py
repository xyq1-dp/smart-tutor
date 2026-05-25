"""
FastAPI 应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.chat import router as chat_router
from backend.api.resource import router as resource_router
from backend.api.path import router as path_router
from backend.api.assessment import router as assessment_router
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


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "smart-tutor"}
