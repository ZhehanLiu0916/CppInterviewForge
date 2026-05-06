import logging
from typing import List, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    max_chars_per_result: int = 2000,
    timeout: int = 5,
) -> Dict:
    """调用Tavily Search API。"""
    if not settings.TAVILY_API_KEY:
        logger.warning("Tavily API key not configured")
        return {"results": []}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": search_depth,
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return {"results": []}


async def searxng_search(
    query: str,
    max_results: int = 5,
    searxng_url: str = "http://localhost:8080",
    timeout: int = 5,
) -> Dict:
    """调用SearXNG自建实例（降级方案）。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "number": max_results,
                },
            )
            response.raise_for_status()
            data = response.json()
            # 转换为与Tavily相似的格式
            results = []
            for item in data.get("results", [])[:max_results]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", "")[:max_chars_per_result],
                    }
                )
            return {"results": results}
    except Exception as e:
        logger.error(f"SearXNG search failed: {e}")
        return {"results": []}


async def fetch_page_content(url: str, max_chars: int = 2000, timeout: int = 3) -> str:
    """抓取页面正文内容。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            # 简单提取：去除HTML标签，取前max_chars字符
            import re
            text = re.sub(r"<[^>]+>", " ", response.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return ""


async def web_search(query: str, keywords: Optional[List[str]] = None) -> Dict:
    """执行在线搜索，返回合并结果。"""
    if settings.SEARCH_ENGINE.lower() == "searxng":
        data = await searxng_search(query, max_results=settings.SEARCH_MAX_RESULTS)
    else:
        data = await tavily_search(query, max_results=settings.SEARCH_MAX_RESULTS)

    results = data.get("results", [])
    if not results:
        logger.warning("Web search returned no results")
        return {"online_search_results": None, "online_search_urls": []}

    # 抓取Top-3正文
    contents = []
    urls = []
    for item in results[: settings.SEARCH_CONTENT_LIMIT]:
        url = item.get("url", "")
        content = item.get("content", "")
        if not content:
            content = await fetch_page_content(url)
        contents.append(f"[来源: {url}]\n{content}")
        urls.append(url)

    merged = "\n\n".join(contents)[:4000]

    logger.info(f"Web search: {len(results)} results, using top {len(urls)}")
    return {
        "online_search_results": merged,
        "online_search_urls": urls,
    }
