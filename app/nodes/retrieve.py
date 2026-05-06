import logging
from app.core.config import settings
from app.services.retriever import get_retriever

logger = logging.getLogger(__name__)


async def retrieve_node(state: dict) -> dict:
    """执行多路检索并判断是否使用知识库回答。"""
    rewritten_query = state.get("rewritten_query", state.get("question", ""))
    keywords = state.get("keywords", [])

    try:
        retriever = await get_retriever()
        results = await retriever.multi_route_search(
            rewritten_query, keywords
        )
    except Exception as e:
        logger.error(f"Retrieve node failed: {e}")
        return {
            "retrieval_results": [],
            "max_similarity": 0.0,
            "use_knowledge_base": False,
        }

    max_sim = results[0]["similarity"] if results else 0.0
    use_kb = max_sim >= settings.RETRIEVAL_THRESHOLD

    logger.info(
        f"Retrieve: max_similarity={max_sim:.3f}, "
        f"use_knowledge_base={use_kb}"
    )

    return {
        "retrieval_results": results,
        "max_similarity": max_sim,
        "use_knowledge_base": use_kb,
    }
