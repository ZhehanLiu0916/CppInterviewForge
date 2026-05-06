import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.models.schemas import (
    AskRequest,
    ApiResponse,
    ReviewRequest,
    ReviewResponseData,
)
from app.graphs.question.graph import run_question_graph
from app.graphs.review.graph import run_review_graph

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=ApiResponse)
async def ask_question(request: AskRequest):
    """单问题解答接口。"""
    try:
        result = await run_question_graph(
            question=request.question,
            answer_type=request.answer_type,
        )
        return ApiResponse(
            code=0,
            message="success",
            data=result,
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "c++" in error_msg or "not c++" in error_msg:
            return ApiResponse(code=1001, message=str(e))
        return ApiResponse(code=1002, message=str(e))
    except TimeoutError:
        logger.error("Ask request timed out")
        return ApiResponse(code=2002, message="生成超时，请稍后重试")
    except Exception as e:
        error_msg = str(e).lower()
        if "api" in error_msg and ("key" in error_msg or "unauthorized" in error_msg):
            return ApiResponse(code=2001, message="LLM API调用失败，请检查API Key配置")
        if "content" in error_msg and "policy" in error_msg:
            return ApiResponse(code=2003, message="该问题涉及敏感内容，请调整问题后重试")
        if "chroma" in error_msg or "vector" in error_msg:
            return ApiResponse(code=3001, message="向量数据库暂不可用，请稍后重试")
        logger.error(f"Ask request error: {e}")
        return ApiResponse(code=9999, message="服务暂时不可用，请稍后重试")


@router.post("/review", response_model=ApiResponse)
async def review_interview(request: ReviewRequest):
    """面试复盘接口。"""
    try:
        report = await run_review_graph(
            transcript=request.transcript,
            metadata=request.metadata,
        )
        return ApiResponse(
            code=0,
            message="success",
            data={"report": report, "metadata": request.metadata},
        )
    except ValueError as e:
        error_msg = str(e).lower()
        if "short" in error_msg or "length" in error_msg:
            return ApiResponse(code=1003, message=str(e))
        return ApiResponse(code=1004, message=str(e))
    except TimeoutError:
        logger.error("Review request timed out")
        return ApiResponse(code=2002, message="复盘生成超时，请稍后重试")
    except Exception as e:
        error_msg = str(e).lower()
        if "api" in error_msg and ("key" in error_msg or "unauthorized" in error_msg):
            return ApiResponse(code=2001, message="LLM API调用失败，请检查API Key配置")
        if "content" in error_msg and "policy" in error_msg:
            return ApiResponse(code=2003, message="该问题涉及敏感内容，请调整问题后重试")
        if "chroma" in error_msg or "vector" in error_msg:
            return ApiResponse(code=3001, message="向量数据库暂不可用，请稍后重试")
        logger.error(f"Review request error: {e}")
        return ApiResponse(code=9999, message="服务暂时不可用，请稍后重试")


@router.get("/health")
async def health_check():
    """健康检查接口。"""
    components = {
        "llm": "unknown",
        "chroma": "unknown",
        "embedding": "unknown",
    }

    # 检查LLM
    try:
        from app.services.llm import get_llm

        llm = get_llm()
        # 简单ping测试
        await llm.ainvoke("ping")
        components["llm"] = "connected"
    except Exception as e:
        logger.warning(f"LLM health check failed: {e}")
        components["llm"] = "disconnected"

    # 检查Chroma
    try:
        from app.services.retriever import get_retriever

        retriever = await get_retriever()
        count = retriever.count()
        components["chroma"] = "connected" if count >= 0 else "disconnected"
    except Exception as e:
        logger.warning(f"Chroma health check failed: {e}")
        components["chroma"] = "disconnected"

    # 检查Embedding
    try:
        from app.core.config import settings

        if settings.EMBEDDING_MODEL:
            components["embedding"] = "loaded"
    except Exception as e:
        logger.warning(f"Embedding health check failed: {e}")
        components["embedding"] = "not_loaded"

    status = (
        "healthy"
        if all(v == "connected" or v == "loaded" for v in components.values())
        else "degraded"
    )

    return {"status": status, "version": "1.0.0", "components": components}
