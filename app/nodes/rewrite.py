import logging
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.services.llm import get_llm
from app.core.prompts import REWRITE_PROMPT
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


async def rewrite_node(state: dict) -> dict:
    """对用户输入问题进行改写和关键词提取。"""
    question = state.get("question", "")
    if not question:
        return {"rewritten_query": question, "keywords": []}

    llm = get_llm()
    prompt = REWRITE_PROMPT.format(question=question)

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = extract_json(response.content)
        keywords = result.get("keywords", [])
        rewritten_query = result.get("rewritten_query", question)
        logger.debug(f"Rewrite: '{question}' -> '{rewritten_query}', keywords={keywords}")
        return {
            "rewritten_query": rewritten_query,
            "keywords": keywords,
        }
    except ValueError as e:
        logger.warning(f"Rewrite node JSON parse failed: {e}, using original")
        return {"rewritten_query": question, "keywords": []}
    except Exception as e:
        logger.error(f"Rewrite node failed: {e}")
        return {"rewritten_query": question, "keywords": []}
