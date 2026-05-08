import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def _parse_detailed_answer(raw: str) -> Dict:
    """解析LLM生成的详细回答，提取4段结构。"""
    sections = {
        "knowledge_positioning": "",
        "core_principle": "",
        "common_exams": "",
        "pitfalls": "",
    }

    # 正则提取4个段落
    patterns = {
        "knowledge_positioning": r"📍\s*知识点定位[：:]\s*(.*?)(?=🔍|📝|⚠️|$)",
        "core_principle": r"🔍\s*核心原理拆解[：:]\s*(.*?)(?=📍|📝|⚠️|$)",
        "common_exams": r"📝\s*常见考法说明[：:]\s*(.*?)(?=📍|🔍|⚠️|$)",
        "pitfalls": r"⚠️\s*易错点提示[：:]\s*(.*?)(?=📍|🔍|📝|$)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw, re.DOTALL)
        if match:
            sections[key] = match.group(1).strip()

    # 如果解析失败，将原始内容放入knowledge_positioning
    if not any(sections.values()):
        logger.warning("Failed to parse detailed answer, using raw content")
        sections["knowledge_positioning"] = raw[:500]
        sections["core_principle"] = ""
        sections["common_exams"] = ""
        sections["pitfalls"] = ""

    return sections


def _build_metadata(state: Dict) -> Dict:
    """构建知识库元数据（仅知识库来源时）。"""
    metadata = state.get("knowledge_base_metadata", {})
    if not metadata:
        return {}

    return {
        "category": metadata.get("category"),
        "sub_category": metadata.get("sub_category"),
        "difficulty": metadata.get("difficulty"),
    }


async def format_node(state: Dict) -> Dict:
    """格式化输出，解析详细回答并组装来源信息。"""
    answer_type = state.get("answer_type", "both")
    result = {"question": state.get("question", "")}

    # 简要回答
    if answer_type in ("short", "both"):
        result["short_answer"] = {
            "content": state.get("short_answer", ""),
            "word_count": state.get("short_answer_word_count", 0),
        }

    # 详细回答
    if answer_type in ("detailed", "both"):
        raw = state.get("detailed_answer_raw", "")
        result["detailed_answer"] = _parse_detailed_answer(raw)

    # 来源信息
    result["source"] = state.get("source_info", {"type": "ai_generated"})

    # 知识库元数据（仅知识库来源时）
    if result["source"].get("type") == "knowledge_base":
        result["metadata"] = _build_metadata(state)
    else:
        result["metadata"] = None

    logger.debug(f"Format node: source={result['source']['type']}")
    return result
