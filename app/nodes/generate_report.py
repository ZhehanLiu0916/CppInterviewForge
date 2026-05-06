import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def _build_questions_summary(questions: List[Dict]) -> Dict:
    """构建面试问题汇总模块。"""
    return {
        "total_count": len(questions),
        "questions": [
            {
                "id": q.get("id", i + 1),
                "text": q.get("text", ""),
                "sub_questions": q.get("sub_questions", []),
            }
            for i, q in enumerate(questions)
        ],
    }


def _build_reference_answers(reference_answers: List[Dict]) -> List[Dict]:
    """构建各问题参考答案模块。"""
    result = []
    for ra in reference_answers:
        result.append(
            {
                "question_id": ra.get("question_id", 0),
                "question_text": ra.get("question_text", ""),
                "short_answer": ra.get("short_answer", {}),
                "detailed_answer": ra.get("detailed_answer", {}),
                "source": ra.get("source", {}),
            }
        )
    return result


def _build_evaluations(evaluations: List[Dict]) -> List[Dict]:
    """构建各问题回答评估模块。"""
    result = []
    for ev in evaluations:
        result.append(
            {
                "question_id": ev.get("question_id", 0),
                "question_text": ev.get("question_text", ""),
                "interviewee_summary": ev.get("interviewee_summary", ""),
                "scores": ev.get("scores", {}),
                "overall_score": ev.get("overall_score", 0.0),
            }
        )
    return result


async def generate_report_node(state: Dict) -> Dict:
    """组装完整的5模块复盘报告（含部分报告处理）。"""
    questions = state.get("questions", [])
    reference_answers = state.get("reference_answers", [])
    evaluations = state.get("evaluations", [])
    metadata = state.get("metadata")

    # 异常7：整体报告生成超时 → 返回已生成的部分模块
    if state.get("_timeout"):
        logger.warning("Report generation timed out, returning partial report")
        partial_report = {
            "questions_summary": _build_questions_summary(questions),
            "reference_answers": _build_reference_answers(reference_answers),
            "answer_evaluations": _build_evaluations(evaluations),
            "_partial": True,
            "_timeout": True,
            "_message": "报告因超时截断，请重试获取完整报告",
        }
        return {"report": partial_report}

    # 异常5：部分问题解答失败 → 跳过失败问题（已在逐题解答中处理）
    # 此处直接使用已有数据

    # 模块1&2&3：直接使用已有数据
    report = {
        "questions_summary": _build_questions_summary(questions),
        "reference_answers": _build_reference_answers(reference_answers),
        "answer_evaluations": _build_evaluations(evaluations),
    }

    # 模块4&5：调用LLM生成（如果尚未生成）
    # 注意：这些由ReviewGraph中的单独节点处理
    # 此处仅组装已有数据

    # 检查是否有错误标记
    errors = []
    if state.get("error"):
        errors.append(state["error"])
    for ev in evaluations:
        if ev.get("scores", {}).get("error"):
            errors.append("部分评估失败")

    if errors:
        report["_partial"] = True
        report["_errors"] = errors

    logger.info(f"Report generated with {len(questions)} questions, {len(evaluations)} evaluations")
    return {"report": report}
