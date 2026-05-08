import logging
from app.core.config import settings
from app.services.web_search import web_search

logger = logging.getLogger(__name__)


async def web_search_node(state: dict) -> dict:
    """在线搜索节点。"""
    rewritten_query = state.get("rewritten_query", state.get("question", ""))
    keywords = state.get("keywords", [])
    
    # 添加日志检查上游节点是否正确设置了字段
    logger.info(f"Web search node - rewritten_query: '{rewritten_query}', "
                f"question: '{state.get('question', '')}', "
                f"rewritten_query exists: {'rewritten_query' in state}, "
                f"question exists: {'question' in state}, "
                f"state keys: {list(state.keys())}")

    try:
        result = await web_search(
            rewritten_query, keywords=keywords
        )
        online_results = result.get("online_search_results")
        online_urls = result.get("online_search_urls", [])

        if online_results:
            logger.info(f"Web search successful: {len(online_urls)} sources")
            return {
                "online_search_results": online_results,
                "online_search_urls": online_urls,
            }
        else:
            logger.warning("Web search returned no results")
            return {
                "online_search_results": None,
                "online_search_urls": [],
            }
    except Exception as e:
        logger.error(f"Web search node failed: {e}")
        return {
            "online_search_results": None,
            "online_search_urls": [],
        }
