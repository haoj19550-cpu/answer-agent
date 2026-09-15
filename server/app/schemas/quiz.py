"""核心 Pydantic 模型：链输出与 API 响应复用（方案 6.4 / 7.1）。"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------- 知识点提取（链1 输出） ----------


class KnowledgePoint(BaseModel):
    name: str
    definition: str
    importance: int = Field(ge=1, le=5)
    confusion_with: list[str] = Field(default_factory=list)


class KnowledgeExtraction(BaseModel):
    topic: str
    summary: str
    knowledge_points: list[KnowledgePoint] = Field(min_length=3, max_length=10)


# ---------- 题目生成（链2 输出） ----------


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    TRUE_FALSE = "true_false"
    SCENARIO = "scenario"


class Question(BaseModel):
    type: QuestionType
    stem: str
    options: list[str] = Field(min_length=2, max_length=4)
    correct_answer: int  # 正确选项下标（0 基）
    explanation: str
    knowledge_point: str
    difficulty: int = Field(ge=1, le=5)
    source_excerpt: str  # 材料原文依据（Grounded Quiz）


class QuizSet(BaseModel):
    title: str
    questions: list[Question] = Field(min_length=3, max_length=10)


# ---------- 展示版（不含答案，可下发前端） ----------


class PublicQuestion(BaseModel):
    index: int
    type: QuestionType
    stem: str
    options: list[str]
    difficulty: int
    knowledge_point: str


class PublicQuiz(BaseModel):
    quiz_id: str
    title: str
    questions: list[PublicQuestion]


def to_public_quiz(quiz_id: str, quiz: QuizSet) -> PublicQuiz:
    return PublicQuiz(
        quiz_id=quiz_id,
        title=quiz.title,
        questions=[
            PublicQuestion(
                index=i,
                type=q.type,
                stem=q.stem,
                options=q.options,
                difficulty=q.difficulty,
                knowledge_point=q.knowledge_point,
            )
            for i, q in enumerate(quiz.questions)
        ],
    )


# ---------- 学习配置 ----------


class StudyGoal(str, Enum):
    UNDERSTAND = "understand"  # 理解概念
    MEMORIZE = "memorize"  # 记忆背诵
    EXAM = "exam"  # 应对考试
    INTERVIEW = "interview"  # 准备面试
    QUICK = "quick"  # 快速过一遍


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADAPTIVE = "adaptive"


class QuizConfig(BaseModel):
    goal: StudyGoal = StudyGoal.UNDERSTAND
    difficulty: Difficulty = Difficulty.MEDIUM
    count: Literal[5, 10] = 5
    selected_knowledge_points: list[str] = Field(default_factory=list)


# 题量 → 题型配比（单选/判断/场景）
def mix_for_count(count: int) -> tuple[int, int, int]:
    if count == 10:
        return (6, 2, 2)
    return (3, 1, 1)


def reduction_ladder(count: int) -> list[tuple[int, int, int]]:
    """降级梯子：(count, single, judge, scenario)。"""
    if count == 10:
        return [(10, 6, 2, 2), (8, 5, 2, 1), (5, 3, 1, 1), (3, 2, 1, 0)]
    return [(5, 3, 1, 1), (3, 2, 1, 0)]


# ---------- 报告生成（链3 输出） ----------


class ErrorAnalysis(BaseModel):
    question_index: int
    error_type: Literal["概念不清", "概念混淆", "不会应用", "记忆不牢", "粗心"]
    analysis: str


class ReportContent(BaseModel):
    performance_summary: str
    error_analyses: list[ErrorAnalysis]
    confusion_pairs: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(min_length=1, max_length=5)


# ---------- 运行时结构（第七章） ----------


class Material(BaseModel):
    id: str
    client_id: str
    source_type: Literal["text", "topic", "pdf"]
    title: str
    text: str
    char_count: int
    created_at: datetime = Field(default_factory=utcnow)


class Quiz(BaseModel):
    """完整闯关（含答案），仅存服务端。"""

    id: str
    material_id: str
    client_id: str
    config: QuizConfig
    quiz_set: QuizSet
    status: Literal["in_progress", "completed"] = "in_progress"
    created_at: datetime = Field(default_factory=utcnow)


class AnswerRecord(BaseModel):
    quiz_id: str
    question_index: int
    user_answer: int
    correct: bool
    elapsed_ms: int = 0
    answered_at: datetime = Field(default_factory=utcnow)


class WrongQuestion(BaseModel):
    index: int
    stem: str
    error_type: str = ""
    analysis: str = ""


MasteryLevel = Literal["good", "fair", "weak"]


class Report(BaseModel):
    quiz_id: str
    client_id: str
    title: str = ""
    score: int  # 0-100
    accuracy: float
    duration_ms: int
    mastery_levels: dict[str, MasteryLevel]
    wrong_questions: list[WrongQuestion] = Field(default_factory=list)
    performance_summary: str = ""
    confusion_pairs: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    ai_generated: bool = True  # 文案是否来自 LLM（False = 模板兜底）
    badges: list[str] = Field(default_factory=list)
    exp_gained: int = 0
    created_at: datetime = Field(default_factory=utcnow)
