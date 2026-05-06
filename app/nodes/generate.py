import logging
from langchain_core.messages import HumanMessage
from app.core.config import settings
from app.core.prompts import SHORT_ANSWER_PROMPT, DETAILED_ANSWER_PROMPT
from app.services.llm import get_llm
from app.utils.text import count_chinese_words

logger = logging.getLogger(__name__)


def _build_source_context(state: dict) -> str:
    """构建注入LLM的上下文。"""
    knowledge = state.get("knowledge_base_content")
    online = state.get("online_search_results")

    context_parts = []
    if knowledge:
        context_parts.append(f"参考知识库内容：\n{knowledge}\n")
    if online:
        context_parts.append(f"在线搜索结果：\n{online}\n")

    if context_parts:
        return "".join(context_parts)
    return ""


def _determine_source_info(state: dict) -> dict:
    """确定回答来源信息。"""
    if state.get("use_knowledge_base") and state.get("validation_passed"):
        metadata = state.get("knowledge_base_metadata", {})
        return {
            "type": "knowledge_base",
            "reference": metadata.get("source", ""),
            "similarity_score": state.get("max_similarity"),
        }
    elif state.get("online_search_results"):
        return {
            "type": "online_search",
            "reference": ", ".join(state.get("online_search_urls", [])),
            "similarity_score": None,
        }
    else:
        return {
            "type": "ai_generated",
            "reference": None,
            "similarity_score": None,
        }


async def generate_node(state: dict) -> dict:
    """调用LLM生成简要回答和详细回答。"""
    question = state.get("question", "")
    answer_type = state.get("answer_type", "both")
    source_context = _build_source_context(state)

    result = {}

    if answer_type in ("short", "both"):
        try:
            llm = get_llm()
            prompt = SHORT_ANSWER_PROMPT.format(
                source_context=source_context, question=question
            )
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            short_answer = response.content.strip()
            word_count = count_chinese_words(short_answer)

            # 字数截断保护
            if word_count > 200:
                short_answer = _truncate_to_200(short_answer)
                word_count = 200

            result["short_answer"] = short_answer
            result["short_answer_word_count"] = word_count
            logger.debug(f"Short answer generated: {word_count} chars")
        except Exception as e:
            logger.error(f"Short answer generation failed: {e}")
            result["short_answer"] = ""
            result["short_answer_word_count"] = 0

    if answer_type in ("detailed", "both"):
        try:
            llm = get_llm()
            prompt = DETAILED_ANSWER_PROMPT.format(
                source_context=source_context, question=question
            )
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            detailed_raw = response.content.strip()
            result["detailed_answer_raw"] = detailed_raw
            logger.debug("Detailed answer generated")
        except Exception as e:
            logger.error(f"Detailed answer generation failed: {e}")
            result["detailed_answer_raw"] = ""

    result["source_info"] = _determine_source_info(state)
    return result


def _truncate_to_200(text: str) -> str:
    """截断到200字（中文字符+英文单词）。"""
    return _truncate_to_word_limit(text, 200)


def _truncate_to_word_limit(text: str, max_words: int) -> str:
    """截断到指定字数。"""
    import re
    result = []
    word_count = 0
    for char in text:
        if re.match(r"[\u4e00-\u9fff]", char):
            word_count += 1
        elif re.match(r"[a-zA-Z]", char):
            if result and re.match(r"[a-zA-Z]", result[-1]):
                word_count += 1
        else:
            if result and re.match(r"[a-zA-Z]", result[-1]):
                word_count += 1
        if word_count > max_words:
            break
        result.append(char)
    return "".join(result).rstrip("，。、！？；：") + "…"
