import logging
from typing import List, Dict

from langchain_core.messages import HumanMessage

from app.core.prompts import EVALUATE_ANSWER_PROMPT
from app.services.llm import get_llm
from app.utils.text import extract_json

logger = logging.getLogger(__name__)


async def evaluate_node(state: dict) -> dict:
    """逐题对比评估面试者回答和参考答案。"""
    questions = state.get("questions", [])
    reference_answers = state.get("reference_answers", [])
    interviewee_answers = state.get("interviewee_answers", [])

    evaluations = []

    # 建立id到参考答案的映射
    ref_map = {r["question_id"]: r for r in reference_answers}
    ans_map = {a["question_id"]: a for a in interviewee_answers}

    for q in questions:
        qid = q.get("id", 0)
        q_text = q.get("text", "")

        ref = ref_map.get(qid, {})
        ans = ans_map.get(qid, {})

        # 准备输入
        ref_short = ref.get("short_answer", {}).get("content", "") if ref else ""
        interviewee_text = ans.get("answer_text", "[未回答]")

        llm = get_llm()  # 使用默认参数
        prompt = EVALUATE_ANSWER_PROMPT.format(
            question=q_text,
            reference_answer=ref_short,
            interviewee_answer=interviewee_text,
        )

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            result = extract_json(response.content)

            # 计算综合评分
            scores = result
            overall = _calc_overall_score(scores)

            evaluations.append(
                {
                    "question_id": qid,
                    "question_text": q_text,
                    "interviewee_summary": interviewee_text[:200],
                    "scores": scores,
                    "overall_score": overall,
                }
            )
        except ValueError as e:
            logger.warning(f"Evaluate JSON parse failed for Q{qid}: {e}")
            evaluations.append(_fallback_evaluation(qid, q_text, interviewee_text))
        except Exception as e:
            logger.error(f"Evaluate failed for Q{qid}: {e}")
            evaluations.append(_fallback_evaluation(qid, q_text, interviewee_text))

    logger.info(f"Evaluated {len(evaluations)} questions")
    return {"evaluations": evaluations}


def _calc_overall_score(scores: Dict) -> float:
    """计算综合评分（5维度平均）。"""
    total = 0.0
    count = 0
    for key in ["accuracy", "completeness", "logic", "terminology", "relevance"]:
        if key in scores:
            total += scores[key].get("score", 0)
            count += 1
    return round(total / count, 1) if count > 0 else 0.0


def _fallback_evaluation(qid, q_text, interviewee_text) -> Dict:
    """评估失败时的降级结果。"""
    default_score = {"score": 0, "issues": ["评估失败"], "suggestions": ["请重新评估"]}
    return {
        "question_id": qid,
        "question_text": q_text,
        "interviewee_summary": interviewee_text[:200],
        "scores": {
            "accuracy": default_score,
            "completeness": default_score,
            "logic": default_score,
            "terminology": default_score,
            "relevance": default_score,
        },
        "overall_score": 0.0,
    }
