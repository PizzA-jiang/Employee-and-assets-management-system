"""ChromaDB 向量存储服务

向量数据持久化在项目目录 D:\\code\\chroma_data\\ 下。
文档块以 chunk_db_id (数据库中 KnowledgeChunk.id) 作为唯一标识存储。
"""
import logging
import os
from typing import List, Optional
from dataclasses import dataclass

from app.services import embedding

logger = logging.getLogger(__name__)

# 向量数据库持久化目录: 项目根目录下的 chroma_data 文件夹
CHROMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "chroma_data",
)

COLLECTION_NAME = "knowledge_chunks"


@dataclass
class VectorSearchResult:
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    score: float


class VectorStore:
    """ChromaDB 向量存储实现"""

    def __init__(self):
        self._client = None
        self._collection = None

    def _get_collection(self):
        """懒加载 ChromaDB collection (单例)"""
        if self._collection is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready at {CHROMA_DIR}")
        return self._collection

    def init_collection(self, collection_name: str = COLLECTION_NAME):
        return self._get_collection()

    def add_chunks(
        self,
        chunk_ids: List[int],
        documents: List[str],
        metadatas: List[dict],
        embeddings: Optional[List[List[float]]] = None,
    ) -> bool:
        """存储文本块向量。embeddings 为空时自动调用本地嵌入模型生成。"""
        if not chunk_ids:
            return True
        try:
            if not embeddings:
                embeddings = embedding.encode(documents)
            collection = self._get_collection()
            collection.upsert(
                ids=[str(cid) for cid in chunk_ids],
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            return True
        except Exception:
            logger.exception("Failed to add chunks to vector store")
            return False

    def search_by_text(self, query_text: str, top_k: int = 5) -> List[VectorSearchResult]:
        """以查询文本做语义搜索: 本地模型编码 -> ChromaDB 相似度检索"""
        try:
            query_embedding = embedding.encode_query(query_text)
            collection = self._get_collection()
            if collection.count() == 0:
                return []
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
            search_results = []
            ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            for i in range(len(ids)):
                meta = metas[i] or {}
                # cosine distance -> 相似度分数 (1 - distance)
                score = 1.0 - dists[i]
                search_results.append(VectorSearchResult(
                    chunk_id=int(ids[i]),
                    document_id=int(meta.get("document_id", 0)),
                    document_title=meta.get("document_title", ""),
                    content=docs[i],
                    score=round(float(score), 4),
                ))
            return search_results
        except Exception:
            logger.exception("Failed to search vector store")
            return []

    def delete_chunks(self, chunk_ids: List[int]) -> bool:
        """删除指定分块的向量"""
        if not chunk_ids:
            return True
        try:
            collection = self._get_collection()
            collection.delete(ids=[str(cid) for cid in chunk_ids])
            return True
        except Exception:
            logger.exception("Failed to delete chunks from vector store")
            return False

    def delete_document(self, document_id: int) -> bool:
        """删除某文档的全部向量"""
        try:
            collection = self._get_collection()
            collection.delete(where={"document_id": document_id})
            return True
        except Exception:
            logger.exception(f"Failed to delete vectors for document {document_id}")
            return False

    def get_collection_stats(self) -> dict:
        try:
            collection = self._get_collection()
            return {"total_chunks": collection.count(), "status": "ok"}
        except Exception:
            return {"total_chunks": 0, "status": "error"}


vector_store = VectorStore()
