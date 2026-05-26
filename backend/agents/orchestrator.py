"""
多智能体协调器 — LangGraph StateGraph 编排 5 个 Agent 协同

图结构：
    START → load_context → generate_doc → generate_supporting → finalize → END
                            ↑_________________________________|

协同机制：
  - DocAgent 先产出核心讲解内容
  - ExerciseAgent / MindmapAgent / PracticeAgent 读取 doc 内容，确保与讲解一致
  - 共享状态 State 在节点间传递，每个 Agent 都能看到前序输出
"""

import json
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END


class OrchestratorState(TypedDict):
    """多智能体共享状态"""
    user_id: str
    topic: str
    profile: dict
    resource_types: list[str]
    kb_context: str
    doc_content: str          # DocAgent 产出（供后续 Agent 参考）
    generated: dict[str, str]
    errors: list[str]


def _make_load_context():
    """节点：加载画像 + 知识库检索"""
    async def load_context(state: OrchestratorState) -> dict:
        from backend.db.models import get_profile, ensure_user
        from backend.db.vector_store import search_knowledge

        ensure_user(state["user_id"])
        profile = get_profile(state["user_id"]) or {}

        for field in ["weak_points", "interest_areas"]:
            raw = profile.get(field, "[]")
            if isinstance(raw, str):
                try:
                    profile[field] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    profile[field] = []

        kb_context = ""
        try:
            kb_results = search_knowledge(state["topic"], n_results=3)
            kb_context = "\n---\n".join(r["content"][:600] for r in kb_results)
        except Exception:
            pass

        return {"profile": profile, "kb_context": kb_context}
    return load_context


def _make_generate_doc():
    """节点：DocAgent 先生成核心讲解文档（后续 Agent 参考）"""
    async def generate_doc(state: OrchestratorState) -> dict:
        from backend.agents.resource_agent import generate_resource

        if "doc" not in state["resource_types"]:
            return {"doc_content": ""}

        try:
            content = await generate_resource("doc", state["topic"], state["profile"])
            # 注入 KB 上下文增强
            if state["kb_context"] and content:
                content = f"{content}\n\n---\n📚 参考知识库：\n{state['kb_context'][:500]}"
            return {"doc_content": content, "generated": {"doc": content}}
        except Exception as e:
            return {"errors": [f"doc: {str(e)}"], "generated": {"doc": f"[生成失败] {str(e)}"}}

    return generate_doc


def _make_generate_supporting():
    """节点：其余 Agent 并行感知 doc 内容后生成（协同核心）"""
    async def generate_supporting(state: OrchestratorState) -> dict:
        from backend.agents.resource_agent import generate_resource
        from backend.utils.anti_hallucination import add_citations

        # 构建增强画像：注入 doc 摘要以便其他 Agent 对齐
        enriched_profile = dict(state["profile"])
        if state.get("doc_content"):
            summary = state["doc_content"][:400]
            enriched_profile["_doc_summary"] = summary
            enriched_profile["_kb_context"] = state.get("kb_context", "")

        results = dict(state.get("generated", {}))
        errors = list(state.get("errors", []))

        supporting_types = [t for t in state["resource_types"] if t != "doc"]

        for rtype in supporting_types:
            try:
                content = await generate_resource(rtype, state["topic"], enriched_profile)
                if rtype in ("reading",):
                    content = add_citations(content)
                results[rtype] = content
            except Exception as e:
                errors.append(f"{rtype}: {str(e)}")
                results[rtype] = f"[生成失败] {str(e)}"

        return {"generated": results, "errors": errors}

    return generate_supporting


def _make_finalize():
    """节点：汇总结果"""
    async def finalize(state: OrchestratorState) -> dict:
        results = state.get("generated", {})
        errors = state.get("errors", [])
        return {
            "generated": results,
            "errors": errors,
        }
    return finalize


def build_resource_graph() -> StateGraph:
    """构建资源生成 StateGraph"""
    graph = StateGraph(OrchestratorState)

    graph.add_node("load_context", _make_load_context())
    graph.add_node("generate_doc", _make_generate_doc())
    graph.add_node("generate_supporting", _make_generate_supporting())
    graph.add_node("finalize", _make_finalize())

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "generate_doc")
    graph.add_edge("generate_doc", "generate_supporting")
    graph.add_edge("generate_supporting", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


async def run_resource_orchestrator(
    user_id: str,
    topic: str,
    resource_types: list[str] = None,
    progress_callback=None,
) -> dict:
    """
    多智能体资源生成编排器入口（LangGraph 图执行）。

    协作流程：
      1. load_context: 读画像 + RAG 检索
      2. generate_doc: DocAgent 产出核心讲解（其他 Agent 后续对齐）
      3. generate_supporting: Mindmap/Exercise/Reading/Practice Agent 感知 doc 后生成
      4. finalize: 汇总
    """
    if resource_types is None:
        resource_types = ["doc", "mindmap", "exercise", "reading", "practice"]

    initial_state: OrchestratorState = {
        "user_id": user_id,
        "topic": topic,
        "profile": {},
        "resource_types": resource_types,
        "kb_context": "",
        "doc_content": "",
        "generated": {},
        "errors": [],
    }

    graph = build_resource_graph()

    # 流式执行各节点，通过 progress_callback 汇报进度（只执行一次）
    merged_state: dict = dict(initial_state)
    async for event in graph.astream(initial_state):
        node_name = list(event.keys())[0]
        node_output = event[node_name]
        # 累积合并每个节点的输出到 merged_state
        for key in ("profile", "kb_context", "doc_content", "generated", "errors"):
            if key in node_output:
                merged_state[key] = node_output[key]

        if progress_callback:
            if node_name == "load_context":
                await progress_callback("kb_search", {"message": "正在读取画像 + 检索知识库..."})
            elif node_name == "generate_doc":
                await progress_callback("agent_start", {"type": "doc"})
                if node_output.get("generated", {}).get("doc", "").startswith("[生成失败]"):
                    await progress_callback("agent_error", {"type": "doc", "error": "生成失败"})
                else:
                    content = node_output.get("generated", {}).get("doc", "")
                    await progress_callback("agent_done", {
                        "type": "doc",
                        "preview": content[:150] + "..." if len(content) > 150 else content,
                    })
            elif node_name == "generate_supporting":
                await progress_callback("generating", {
                    "message": "支持智能体感知文档内容后并行生成...",
                })
                for rtype in [t for t in resource_types if t != "doc"]:
                    g = node_output.get("generated", {}).get(rtype, "")
                    if g.startswith("[生成失败]"):
                        await progress_callback("agent_error", {"type": rtype, "error": "生成失败"})
                    elif g:
                        await progress_callback("agent_done", {
                            "type": rtype,
                            "preview": g[:150] + "..." if len(g) > 150 else g,
                        })
            elif node_name == "finalize":
                await progress_callback("complete", {
                    "message": "全部完成！",
                })

    # 使用合并后的状态（无需二次执行）
    final_state = merged_state

    profile = final_state.get("profile", {})
    return {
        "topic": topic,
        "profile_used": {
            "knowledge_level": profile.get("knowledge_level", "beginner"),
            "learning_goal": profile.get("learning_goal", ""),
            "cognitive_style": profile.get("cognitive_style", ""),
        },
        "kb_references": 1 if final_state.get("kb_context") else 0,
        "resources": final_state.get("generated", {}),
        "errors": final_state.get("errors", []),
    }
