"""
ChromaDB 向量存储 — 用于知识检索和资源匹配
"""

import os

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")

_client = None
_ef = None
_ef_available = True


def _get_embedding_function():
    """延迟加载 embedding function，避免缺少依赖时 import 报错"""
    global _ef, _ef_available
    if _ef is not None:
        return _ef
    if not _ef_available:
        return None
    try:
        from chromadb.utils import embedding_functions
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        return _ef
    except (ImportError, ValueError):
        _ef_available = False
        return None


def get_collection(name: str = "python_course"):
    """获取或创建 ChromaDB 集合"""
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        import chromadb
        _client = chromadb.PersistentClient(path=CHROMA_PATH)

    ef = _get_embedding_function()
    return _client.get_or_create_collection(
        name=name,
        embedding_function=ef,
    )


def index_chapter(chapter_id: str, title: str, content: str):
    """将知识库章节内容索引入向量数据库"""
    if not _get_embedding_function():
        return  # embedding 不可用，跳过

    collection = get_collection()
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    for i, para in enumerate(paragraphs):
        if len(para) < 10:
            continue
        collection.add(
            documents=[para],
            ids=[f"{chapter_id}_{i}"],
            metadatas=[{"chapter": chapter_id, "title": title, "chunk": i}],
        )


def search_knowledge(query: str, n_results: int = 5) -> list[dict]:
    """搜索最相关的知识内容（embedding 不可用时返回空）"""
    ef = _get_embedding_function()
    if ef is None:
        return []

    try:
        collection = get_collection()
        results = collection.query(query_texts=[query], n_results=n_results)
        return [
            {
                "content": doc,
                "chapter": meta.get("chapter", ""),
                "title": meta.get("title", ""),
            }
            for doc, meta in zip(results["documents"][0], results["metadatas"][0])
        ]
    except Exception:
        return []
