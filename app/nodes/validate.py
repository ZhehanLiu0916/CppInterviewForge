import logging
from datetime import datetime, timedelta
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.services.llm import get_validator_llm
from app.core.prompts import VALIDATE_ACCURACY_PROMPT
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


async def validate_node(state: dict) -> dict:
    """对知识库检索结果进行双重校验（准确性+时效性）。"""
    retrieval_results = state.get("retrieval_results", [])
    if not retrieval_results:
        return {"validation_passed": False}

    top_result = retrieval_results[0]
    content = top_result.get("document", "")
    metadata = top_result.get("metadata", {})

    # 时效性校验：检查last_verified是否为6个月内
    last_verified = metadata.get("last_verified", "")
    if last_verified:
        try:
            verified_date = datetime.strptime(last_verified, "%Y-%m-%d")
            if verified_date < datetime.now() - timedelta(days=180):
                logger.info(f"Knowledge item expired: last_verified={last_verified}")
                return {
                    "validation_passed": False,
                    "knowledge_base_content": None,
                    "knowledge_base_metadata": None,
                }
        except ValueError:
            pass

    # 准确性校验：使用低成本LLM校验
    llm = get_validator_llm()
    prompt = VALIDATE_ACCURACY_PROMPT.format(content=content)

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = extract_json(response.content)
        is_accurate = result.get("is_accurate", False)

        if is_accurate:
            logger.info("Knowledge base accuracy check passed")
            return {
                "validation_passed": True,
                "knowledge_base_content": content,
                "knowledge_base_metadata": metadata,
            }
        else:
            reason = result.get("reason", "")
            logger.warning(f"Accuracy validation failed: {reason}")
            return {
                "validation_passed": False,
                "knowledge_base_content": None,
                "knowledge_base_metadata": None,
            }
    except ValueError as e:
        logger.warning(f"Validate node JSON parse failed: {e}, treating as passed")
        return {
            "validation_passed": True,
            "knowledge_base_content": content,
            "knowledge_base_metadata": metadata,
        }
    except Exception as e:
        logger.error(f"Validate node error: {e}, treating as passed")
        return {
            "validation_passed": True,
            "knowledge_base_content": content,
            "knowledge_base_metadata": metadata,
        }
