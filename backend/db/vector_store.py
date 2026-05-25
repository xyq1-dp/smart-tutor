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


def auto_index_knowledge_base() -> dict:
    """启动时自动索引知识库所有章节（增量，跳过已索引的）"""
    import os as _os
    kb_dir = _os.path.join(_os.path.dirname(__file__), "..", "..", "knowledge_base")
    chapters_dir = _os.path.join(kb_dir, "chapters")

    if not _os.path.isdir(chapters_dir):
        return {"status": "no_kb_dir", "indexed": 0}

    # 获取已索引的章节
    try:
        collection = get_collection()
        existing = collection.get()
        indexed_ids = set(existing.get("ids", []))
    except Exception:
        indexed_ids = set()

    indexed_count = 0
    skipped_count = 0
    chapter_files = sorted(_os.listdir(chapters_dir))

    for fname in chapter_files:
        if not fname.endswith(".md"):
            continue
        chapter_id = fname.replace(".md", "")
        filepath = _os.path.join(chapters_dir, fname)

        # 检查是否已索引
        has_indexed = any(i.startswith(f"{chapter_id}_") for i in indexed_ids)
        if has_indexed:
            skipped_count += 1
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取标题
        title = chapter_id
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        index_chapter(chapter_id, title, content)
        indexed_count += 1

    return {
        "status": "ok",
        "indexed": indexed_count,
        "skipped": skipped_count,
        "total_chapters": len(chapter_files),
        "embedding_available": _get_embedding_function() is not None,
    }


def get_kb_stats() -> dict:
    """获取知识库索引状态"""
    try:
        collection = get_collection()
        data = collection.get()
        doc_count = len(data.get("ids", []))
        chapters = set()
        for meta in data.get("metadatas", []):
            if meta and meta.get("chapter"):
                chapters.add(meta["chapter"])
        return {
            "total_documents": doc_count,
            "chapters_indexed": len(chapters),
            "chapter_list": sorted(chapters),
            "embedding_available": _get_embedding_function() is not None,
        }
    except Exception as e:
        return {
            "total_documents": 0,
            "chapters_indexed": 0,
            "chapter_list": [],
            "embedding_available": _get_embedding_function() is not None,
            "error": str(e),
        }


def reindex_knowledge_base() -> dict:
    """强制重新索引（先清空再索引）"""
    try:
        collection = get_collection()
        existing = collection.get()
        ids = existing.get("ids", [])
        if ids:
            collection.delete(ids=ids)
    except Exception:
        pass
    return auto_index_knowledge_base()
