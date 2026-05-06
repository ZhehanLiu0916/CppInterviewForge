import logging
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

from app.models.state import QuestionState
from app.nodes import rewrite, retrieve, validate, generate, format
from app.nodes.web_search import web_search_node

logger = logging.getLogger(__name__)


def _should_use_kb(state: QuestionState) -> str:
    """条件边：是否使用知识库回答。"""
    if state.get("use_knowledge_base"):
        return "validate"
    return "web_search"


def _after_validate(state: QuestionState) -> str:
    """条件边：校验后无论通过与否都走向generate。"""
    return "generate"


def _build_question_graph() -> StateGraph:
    """构建单问题解答LangGraph。"""
    graph = StateGraph(QuestionState)

    # 添加节点
    graph.add_node("rewrite", rewrite.rewrite_node)
    graph.add_node("retrieve", retrieve.retrieve_node)
    graph.add_node("validate", validate.validate_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("generate", generate.generate_node)
    graph.add_node("format", format.format_node)

    # 设置入口
    graph.set_entry_point("rewrite")

    # 添加边
    graph.add_edge("rewrite", "retrieve")

    # 条件边：retrieve → validate/web_search
    graph.add_conditional_edges(
        "retrieve",
        _should_use_kb,
        {"validate": "validate", "web_search": "web_search"},
    )

    # 条件边：validate → generate（无论通过与否）
    graph.add_conditional_edges(
        "validate",
        _after_validate,
        {"generate": "generate"},
    )

    # web_search → generate
    graph.add_edge("web_search", "generate")

    # generate → format → END
    graph.add_edge("generate", "format")
    graph.add_edge("format", END)

    return graph


_question_app = None


def _get_question_app():
    """获取编译后的QuestionGraph应用（单例）。"""
    global _question_app
    if _question_app is None:
        _question_app = _build_question_graph().compile()
        logger.info("QuestionGraph compiled successfully")
    return _question_app


async def run_question_graph(
    question: str, answer_type: str = "both"
) -> dict:
    """运行单问题解答图。
    
    Args:
        question: 用户问题
        answer_type: 回答类型 (short/detailed/both)
    
    Returns:
        包含short_answer/detailed_answer/source_info等的字典
    """
    app = _get_question_app()
    initial_state: QuestionState = {
        "question": question,
        "answer_type": answer_type,
    }
    result = await app.ainvoke(initial_state)
    return result
