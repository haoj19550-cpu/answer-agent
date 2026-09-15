"""API 请求/响应模型（含 SSE 事件载荷）。统一错误格式见 ErrorResponse。"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.quiz import Difficulty, QuizConfig, StudyGoal  # noqa: F401  (re-export)


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class ApiError(Exception):
    """业务异常：API 层统一捕获转 ErrorResponse。"""

    def __init__(self, code: str, message: str, status_code: int = 400, detail: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


# ---------- 材料 ----------


class MaterialCreateRequest(BaseModel):
    client_id: str
    source_type: Literal["text", "topic"] = "text"
    text: str
    title: str = ""


class MaterialResponse(BaseModel):
    material_id: str
    title: str
    char_count: int


# ---------- 闯关（两段式 SSE） ----------


class ExtractRequest(BaseModel):
    client_id: str
    material_id: str


class GenerateRequest(BaseModel):
    client_id: str
    material_id: str
    goal: StudyGoal = StudyGoal.UNDERSTAND
    difficulty: Difficulty = Difficulty.MEDIUM
    count: Literal[5, 10] = 5
    selected_knowledge_points: list[str] = Field(default_factory=list)


class AnswerRequest(BaseModel):
    client_id: str
    question_index: int = Field(ge=0)
    user_answer: int = Field(ge=0)
    elapsed_ms: int = Field(default=0, ge=0)


class Progress(BaseModel):
    answered: int
    total: int


class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: int
    explanation: str
    knowledge_point: str
    source_excerpt: str = ""
    exp_delta: int = 0
    combo: int = 0
    progress: Progress


# ---------- 报告 ----------


class ReportRequest(BaseModel):
    client_id: str
    quiz_id: str


# ---------- SSE 事件载荷（文档化用途） ----------


class StageEvent(BaseModel):
    stage: Literal["extracting", "generating", "validating"]
    message: str


class SseErrorEvent(BaseModel):
    code: str
    message: str
