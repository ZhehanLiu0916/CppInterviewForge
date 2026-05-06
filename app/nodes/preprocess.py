import re
import logging
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.prompts import PREPROCESS_PROMPT
from app.services.llm import get_llm

logger = logging.getLogger(__name__)


async def preprocess_node(state: dict) -> dict:
    """对面试录音转写文本进行预处理和结构化。"""
    transcript = state.get("raw_transcript", "")
    
    # 异常1：输入文本过短（<50字）
    if len(transcript) < 50:
        logger.warning("Transcript too short")
        return {"cleaned_transcript": "", "error": "输入文本过短，请提供完整的面试录音转写文本。", "error_code": 1003}

    # 异常6：输入文本超过token限制（分段处理）
    if len(transcript) > 50000:
        logger.warning("Transcript too long, truncating")
        transcript = transcript[:50000]

    # 第一步：规则预处理（快速处理）
    cleaned = _rule_based_clean(transcript)

    # 第二步：LLM辅助处理（说话人分离+结构化）
    try:
        llm = get_llm()
        prompt = PREPROCESS_PROMPT.format(transcript=cleaned)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        cleaned = response.content.strip()
        
        # 异常2：无法识别面试官/面试者
        if "[面试官]" not in cleaned and "[面试者]" not in cleaned:
            logger.warning("Failed to identify speakers, using original")
            # 尝试简单规则：包含"？"的可能是面试官
            cleaned = _fallback_speaker_identification(transcript)
            if "[面试官]" not in cleaned:
                return {
                    "cleaned_transcript": cleaned,
                    "error": "无法识别面试官/面试者，请检查文本格式",
                }
        
        logger.debug(f"Preprocessed text length: {len(cleaned)}")
        return {"cleaned_transcript": cleaned}
    except Exception as e:
        logger.error(f"Preprocess LLM failed: {e}, using rule-based result")
        return {"cleaned_transcript": cleaned}


def _fallback_speaker_identification(text: str) -> str:
    """降级方案：基于规则的说话人识别。"""
    lines = text.split("\n")
    result = []
    for line in lines:
        if "？" in line or "？" in line:
            result.append(f"[面试官] {line}")
        else:
            result.append(f"[面试者] {line}")
    return "\n".join(result)


def _rule_based_clean(text: str) -> str:
    """基于规则的快速清洗。"""
    lines = text.split("\n")
    result = []
    for line in lines:
        # 去除语气词
        line = re.sub(r"(嗯+|啊+|就是+|然后+|那个+)", "", line)
        # 去除多余空格
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            result.append(line)
    return "\n".join(result)
