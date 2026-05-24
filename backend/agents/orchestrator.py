"""
多智能体协调器 — 基于 LangGraph 的多智能体编排

协调 5 个智能体协同工作：
- ProfileAgent: 学习画像构建
- ResourceAgent: 多模态资源生成
- PathAgent: 学习路径规划
- TutorAgent: 智能辅导（加分项）
- AssessmentAgent: 学习效果评估（加分项）
"""

from typing import TypedDict, Annotated
import operator


class AgentState(TypedDict):
    """多智能体共享状态"""
    user_id: str
    user_message: str
    chat_history: list[dict]
    profile: dict | None
    # 累积的消息，用 add 合并
    messages: Annotated[list[dict], operator.add]
    # 当前阶段
    stage: str  # profile / resource / path / tutor / assessment
    # 生成的资源
    generated_resources: list[dict]
    # 最终响应
    final_response: str


def build_orchestrator():
    """
    构建 LangGraph 多智能体编排图

    流程：
    START → profile_node → resource_node → path_node → tutor_node → END
                      ↑            ↓            ↓          ↓
                      └──────── 共享状态 ─────────┘
    """
    # 第 3 周实现，目前返回占位说明
    return None


async def run_orchestrator(
    user_id: str,
    message: str,
    history: list[dict],
) -> dict:
    """
    运行多智能体协调流程（占位实现，第 3 周完善）

    Returns:
        {"response": "...", "resources": [...], "path_update": {...}}
    """
    from backend.llm.spark import spark_chat

    system_prompt = {
        "role": "system",
        "content": (
            "你是智能学习助手的中央协调器。目前系统处于早期开发阶段。\n"
            "请友好地回复学生，并逐步收集学习画像信息。\n"
            "回答始终用中文。"
        ),
    }

    messages = [system_prompt] + history + [{"role": "user", "content": message}]
    response = await spark_chat(messages)

    return {
        "response": response,
        "resources": [],
        "path_update": {},
        "stage": "profile",
    }
