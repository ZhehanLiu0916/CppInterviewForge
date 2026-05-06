import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatZhipuAI
from loguru import logger

from app.core.config import settings


def get_llm(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    """获取LLM实例，根据settings.LLM_PROVIDER自动选择Provider。"""
    provider = settings.LLM_PROVIDER.lower()
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE
    max_tok = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

    if provider == "deepseek":
        return ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL_NAME,
            base_url=settings.LLM_BASE_URL,
            temperature=temp,
            max_tokens=max_tok,
        )
    elif provider == "openai":
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL_NAME,
            temperature=temp,
            max_tokens=max_tok,
        )
    elif provider == "qwen":
        return ChatOpenAI(
            api_key=settings.QWEN_API_KEY,
            model=settings.QWEN_MODEL_NAME,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=temp,
            max_tokens=max_tok,
        )
    else:
        logger.warning(f"Unknown LLM provider: {provider}, falling back to deepseek")
        return ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL_NAME,
            base_url=settings.LLM_BASE_URL,
            temperature=temp,
            max_tokens=max_tok,
        )


def get_validator_llm() -> ChatOpenAI:
    """获取用于校验的低温度、低token模型实例。"""
    return get_llm(temperature=0.0, max_tokens=256)


def get_search_llm() -> ChatOpenAI:
    """获取用于搜索结果处理的模型实例。"""
    return get_llm(temperature=0.3, max_tokens=1024)
