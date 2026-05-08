import logging
from typing import List, Dict, Any, Optional
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import settings

logger = logging.getLogger(__name__)


class RetrieverService:
    """Chroma向量数据库服务。"""

    def __init__(self):
        self._client: Optional[PersistentClient] = None
        self._collection = None
        self._embedding_fn = None

    async def initialize(self):
        """初始化Chroma客户端和集合。"""
        try:
            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE,
            )
            self._client = PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self._collection = self._client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=self._embedding_fn,
            )
            count = self._collection.count()
            logger.info(
                f"Chroma initialized: collection={settings.CHROMA_COLLECTION_NAME}, "
                f"docs={count}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise

    async def search(
        self, query: str, top_k: Optional[int] = None
    ) -> List[Dict]:
        """语义向量检索（含缓存）。"""
        if self._collection is None:
            await self.initialize()

        k = top_k or settings.RETRIEVAL_TOP_K

        # 尝试缓存
        from app.services.cache import get_cache

        cache = get_cache()
        cache_key = (query, tuple(sorted(["semantic"])))
        cached = await cache.get(query, ("semantic",))
        if cached:
            logger.debug(f"Cache hit for query: {query}")
            return cached

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

        if not results["ids"] or not results["ids"][0]:
            return []

        items = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            similarity = 1.0 - distance
            items.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": similarity,
                }
            )

        items.sort(key=lambda x: x["similarity"], reverse=True)
        await cache.set(query, ("semantic",), items)
        return items

    async def search_by_keywords(
        self, keywords: List[str], top_k: Optional[int] = None
    ) -> List[Dict]:
        """关键词检索（元数据过滤）。"""
        if self._collection is None:
            await self.initialize()

        k = top_k or settings.RETRIEVAL_TOP_K
        where_filter = {"$or": []}
        for kw in keywords:
            where_filter["$or"].append({"tags": {"$contains": kw}})
            where_filter["$or"].append({"category": {"$eq": kw}})
            where_filter["$or"].append({"sub_category": {"$eq": kw}})
            where_filter["$or"].append({"heading_text": {"$contains": kw}})

        if not where_filter["$or"]:
            return []

        try:
            results = self._collection.query(
                query_texts=[" ".join(keywords)],
                n_results=k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}, falling back to semantic search")
            return await self.search(" ".join(keywords), top_k=k)

        if not results["ids"] or not results["ids"][0]:
            return []

        items = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            similarity = 1.0 - distance
            items.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": similarity,
                }
            )

        items.sort(key=lambda x: x["similarity"], reverse=True)
        return items

    async def multi_route_search(
        self, query: str, keywords: List[str], top_k: Optional[int] = None
    ) -> List[Dict]:
        """多路检索：合并语义检索和关键词检索结果。"""
        semantic_results = await self.search(query, top_k=top_k)
        keyword_results = await self.search_by_keywords(keywords, top_k=top_k)

        # 合并去重
        seen_ids = set()
        merged = []
        for item in semantic_results + keyword_results:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                merged.append(item)

        merged.sort(key=lambda x: x["similarity"], reverse=True)
        k = top_k or settings.RETRIEVAL_TOP_K
        return merged[:k]

    async def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict],
    ):
        """批量添加文档到Chroma。"""
        if self._collection is None:
            await self.initialize()

        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(f"Added {len(ids)} documents to Chroma")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    def count(self) -> int:
        """返回集合中的文档数量。"""
        if self._collection is None:
            return 0
        return self._collection.count()


_retriever: Optional[RetrieverService] = None
_cache: Optional["LRUCache"] = None


async def get_retriever() -> RetrieverService:
    """获取Retriever单例。"""
    global _retriever
    if _retriever is None:
        _retriever = RetrieverService()
        await _retriever.initialize()
    return _retriever


def get_cache() -> "LRUCache":
    """获取缓存单例。"""
    global _cache
    if _cache is None:
        from app.services.cache import get_cache as _get_cache
        _cache = _get_cache()
    return _cache
