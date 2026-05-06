import time
from typing import Dict, Optional, Tuple, List


class LRUCache:
    """简单的LRU缓存实现。"""

    def __init__(self, capacity: int = 1000, ttl: int = 3600):
        self.capacity = capacity
        self.ttl = ttl  # TTL超时（秒）
        self.cache: Dict[str, Tuple[any, float]] = {}  # key -> (value, timestamp)
        self.order: List[str] = []  # LRU顺序

    def _make_key(self, query: str, keywords: tuple) -> str:
        """生成缓存键。"""
        return f"{query}:{':'.join(sorted(keywords))}"

    async def get(
        self, query: str, keywords: tuple
    ) -> Optional[List]:
        """获取缓存。"""
        key = self._make_key(query, keywords)
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            # TTL过期
            del self.cache[key]
            self.order.remove(key)
            return None

        # 更新LRU顺序
        self.order.remove(key)
        self.order.append(key)
        return value

    async def set(
        self, query: str, keywords: tuple, value: List
    ) -> None:
        """设置缓存。"""
        key = self._make_key(query, keywords)

        if key in self.cache:
            self.order.remove(key)
        elif len(self.cache) >= self.capacity:
            # 淘汰最久未使用的
            oldest = self.order.pop(0)
            del self.cache[oldest]

        self.cache[key] = (value, time.time())
        self.order.append(key)

    def clear(self):
        """清空缓存。"""
        self.cache.clear()
        self.order.clear()

    def stats(self) -> Dict:
        """返回缓存统计。"""
        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "ttl": self.ttl,
        }


# 全局缓存实例
_retrieval_cache: Optional[LRUCache] = None


def get_cache() -> LRUCache:
    """获取缓存单例。"""
    global _retrieval_cache
    if _retrieval_cache is None:
        from app.core.config import settings

        _retrieval_cache = LRUCache(
            capacity=1000, ttl=int(settings.RETRIEVAL_THRESHOLD * 3600)  # 用threshold*3600作为TTL
        )
    return _retrieval_cache
