import os
from typing import Optional


class Settings:
    # LLM配置
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "deepseek-chat")
    LLM_BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # 备选模型配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL_NAME: str = os.getenv("QWEN_MODEL_NAME", "qwen-plus")

    # Chroma配置
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "cpp_interview_kb")

    # Embedding配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text2vec-large-chinese")
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "cpu")

    # 检索配置
    RETRIEVAL_THRESHOLD: float = float(os.getenv("RETRIEVAL_THRESHOLD", "0.8"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))

    # 在线搜索配置
    SEARCH_ENGINE: str = os.getenv("SEARCH_ENGINE", "tavily")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SEARCH_MAX_RESULTS: int = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
    SEARCH_CONTENT_LIMIT: int = int(os.getenv("SEARCH_CONTENT_LIMIT", "3"))
    SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "5"))

    # 知识库目录
    BOOK_DIR: str = os.getenv("BOOK_DIR", "./books")

    # 服务配置
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "4"))

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "./logs")


settings = Settings()
