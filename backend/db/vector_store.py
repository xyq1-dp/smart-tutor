"""
ChromaDB 向量存储 — 用于知识检索和资源匹配
"""

import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma")

# 使用讯飞或其他兼容的 embedding 模型
# 如果无法使用远程 embedding，使用 Chroma 默认的 sentence-transformers
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

_client = None


def get_collection(name: str = "python_course"):
    """获取或创建 ChromaDB 集合"""
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)

    return _client.get_or_create_collection(
        name=name,
        embedding_function=_ef,
    )


def index_chapter(chapter_id: str, title: str, content: str):
    """将知识库章节内容索引入向量数据库"""
    collection = get_collection()

    # 按段落分割，每个段落作为一个检索单元
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
    """搜索最相关的知识内容"""
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
