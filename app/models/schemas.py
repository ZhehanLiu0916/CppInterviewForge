from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class AskRequest(BaseModel):
    """单问题解答请求体。"""
    question: str = Field(..., min_length=1, max_length=500, description="面试问题，1-500字")
    answer_type: str = Field("both", description="回答类型：short/detailed/both")


class SourceInfo(BaseModel):
    """回答来源信息。"""
    type: str
    reference: Optional[str] = None
    similarity_score: Optional[float] = None


class ShortAnswer(BaseModel):
    """简要回答。"""
    content: str
    word_count: int


class DetailedAnswer(BaseModel):
    """详细回答4段式。"""
    knowledge_positioning: str = ""
    core_principle: str = ""
    common_exams: str = ""
    pitfalls: str = ""


class AnswerMetadata(BaseModel):
    """知识库元数据（仅知识库来源时）。"""
    category: Optional[str] = None
    sub_category: Optional[str] = None
    difficulty: Optional[str] = None


class AskResponseData(BaseModel):
    """/ask接口响应数据。"""
    question: str
    short_answer: Optional[ShortAnswer] = None
    detailed_answer: Optional[DetailedAnswer] = None
    source: SourceInfo
    metadata: Optional[AnswerMetadata] = None


class ApiResponse(BaseModel):
    """通用API响应。"""
    code: int = 0
    message: str = "success"
    data: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    """面试复盘请求体。"""
    transcript: str = Field(..., min_length=50, max_length=50000, description="面试录音转写文本，50-50000字")
    metadata: Optional[Dict[str, str]] = None


class ReviewResponseData(BaseModel):
    """/review接口响应数据。"""
    report: Dict
    metadata: Optional[Dict[str, Any]] = None
