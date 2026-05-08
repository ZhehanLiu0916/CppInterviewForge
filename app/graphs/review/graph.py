import logging
from langgraph.graph import StateGraph, END

from app.models.state import ReviewState
from app.nodes import preprocess, extract_questions, extract_answers, evaluate, generate_report

logger = logging.getLogger(__name__)


def _has_questions(state: ReviewState) -> str:
    """条件边：是否识别到问题。"""
    if state.get("questions"):
        return "process"
    return "end"


def _build_review_graph() -> StateGraph:
    """构建面试复盘LangGraph。"""
    graph = StateGraph(ReviewState)

    # 添加节点
    graph.add_node("preprocess", preprocess.preprocess_node)
    graph.add_node("extract_questions", extract_questions.extract_questions_node)
    graph.add_node("extract_answers", extract_answers.extract_answers_node)
    graph.add_node("answer_questions", _answer_questions_node)
    graph.add_node("evaluate", evaluate.evaluate_node)
    graph.add_node("generate_report", generate_report.generate_report_node)

    # 设置入口
    graph.set_entry_point("preprocess")

    # 并行：preprocess后同时启动问题提取和回答提取
    graph.add_edge("preprocess", "extract_questions")
    graph.add_edge("preprocess", "extract_answers")

    # 两个提取完成后，启动answer_questions
    graph.add_edge(["extract_questions", "extract_answers"], "answer_questions")

    # 回答问题后评估
    graph.add_edge("answer_questions", "evaluate")

    # 评估后生成报告
    graph.add_edge("evaluate", "generate_report")

    # 报告生成后结束
    graph.add_edge("generate_report", END)

    return graph


async def _answer_questions_node(state: ReviewState) -> dict:
    """逐题调用QuestionGraph获取参考答案。"""
    from app.graphs.question.graph import run_question_graph

    questions = state.get("questions", [])
    reference_answers = []

    for q in questions:
        try:
            result = await run_question_graph(
                question=q.get("text", ""),
                answer_type="both",
            )
            reference_answers.append(
                {
                    "question_id": q.get("id", 0),
                    "question_text": q.get("text", ""),
                    "short_answer": result.get("short_answer", {}),
                    "detailed_answer": result.get("detailed_answer", {}),
                    "source": result.get("source", {}),
                }
            )
        except Exception as e:
            logger.error(f"Answer question {q.get('id')} failed: {e}")
            reference_answers.append(
                {
                    "question_id": q.get("id", 0),
                    "question_text": q.get("text", ""),
                    "short_answer": {"content": "[解答失败]", "word_count": 0},
                    "detailed_answer": {"knowledge_positioning": "", "core_principle": "", "common_exams": "", "pitfalls": ""},
                    "source": {"type": "ai_generated"},
                }
            )

    return {"reference_answers": reference_answers}


_review_app = None


def _get_review_app():
    """获取编译后的ReviewGraph应用。"""
    global _review_app
    if _review_app is None:
        _review_app = _build_review_graph().compile()
        logger.info("ReviewGraph compiled successfully")
    return _review_app


async def run_review_graph(
    transcript: str, metadata: dict | None = None,
) -> dict:
    """运行面试复盘图。"""
    app = _get_review_app()
    initial_state: ReviewState = {
        "raw_transcript": transcript,
        "metadata": metadata,
    }
    result = await app.ainvoke(initial_state)
    return result.get("report", {})
