import logging
from langchain_core.messages import HumanMessage

from app.core.prompts import EXTRACT_QUESTIONS_PROMPT
from app.services.llm import get_llm
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


async def extract_questions_node(state: dict) -> dict:
    """从预处理文本中提取面试问题。"""
    cleaned = state.get("cleaned_transcript", "")
    if not cleaned:
        return {"questions": [], "error": "预处理文本为空"}

    llm = get_llm(temperature=0.3, max_tokens=1024)
    prompt = EXTRACT_QUESTIONS_PROMPT.format(transcript=cleaned)

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = extract_json(response.content)
        questions = result.get("questions", [])
        
        # 异常3：问题提取结果为0
        if not questions:
            logger.warning("No questions extracted")
            return {"questions": [], "error": "未识别到面试问题", "error_code": 1004}
        
        # 确保每个问题有id和text
        for i, q in enumerate(questions, 1):
            if "id" not in q:
                q["id"] = i
            if "sub_questions" not in q:
                q["sub_questions"] = []
        
        logger.info(f"Extracted {len(questions)} questions")
        return {"questions": questions}
    except ValueError as e:
        logger.error(f"Extract questions JSON parse failed: {e}")
        return {"questions": [], "error": "问题提取解析失败", "error_code": 1004}
    except TimeoutError:
        logger.error("Extract questions timed out")
        return {"questions": [], "error": "问题提取超时", "error_code": 2002}
    except Exception as e:
        logger.error(f"Extract questions failed: {e}")
        return {"questions": [], "error": str(e), "error_code": 9999}
