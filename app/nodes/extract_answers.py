import json
import logging
from langchain_core.messages import HumanMessage

from app.core.prompts import EXTRACT_ANSWERS_PROMPT
from app.services.llm import get_llm

logger = logging.getLogger(__name__)


async def extract_answers_node(state: dict) -> dict:
    """从面试对话中提取面试者回答。"""
    questions = state.get("questions", [])
    cleaned = state.get("cleaned_transcript", "")

    if not questions:
        return {"interviewee_answers": []}
    if not cleaned:
        return {"interviewee_answers": []}

    llm = get_llm(temperature=0.3, max_tokens=2048)
    prompt = EXTRACT_ANSWERS_PROMPT.format(
        questions=json.dumps(questions, ensure_ascii=False),
        transcript=cleaned,
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = json.loads(response.content)
        answers = result.get("answers", [])
        
        # 确保每个回答有question_id和answer_text
        for ans in answers:
            if "question_id" not in ans:
                ans["question_id"] = 0
            if "answer_text" not in ans:
                ans["answer_text"] = "[未回答]"
        
        logger.info(f"Extracted {len(answers)} answers")
        return {"interviewee_answers": answers}
    except json.JSONDecodeError as e:
        logger.error(f"Extract answers JSON parse failed: {e}")
        return {"interviewee_answers": [], "error": "回答提取解析失败"}
    except TimeoutError:
        logger.error("Extract answers timed out")
        return {"interviewee_answers": [], "error": "回答提取超时", "error_code": 2002}
    except Exception as e:
        logger.error(f"Extract answers failed: {e}")
        return {"interviewee_answers": [], "error": str(e), "error_code": 9999}
