"""闯关 API：两段式 SSE（提取 / 生成）+ 判分（幂等，答案不出后端）。"""

import json
from typing import AsyncIterable
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.sse import EventSourceResponse

from app.api.deps import ChainRegistry, get_chains, get_owned_material, get_owned_quiz
from app.schemas.api import (
    AnswerRequest,
    AnswerResponse,
    ExtractRequest,
    GenerateRequest,
    Progress,
)
from app.schemas.quiz import AnswerRecord, PublicQuiz, Quiz, QuizConfig, to_public_quiz
from app.services import gamification_service
from app.services.quiz_service import (
    QuizGenerationFailed,
    extract_knowledge,
    filter_knowledge_points,
    generate_quiz,
)
from app.stores import memory_store

router = APIRouter(tags=["quizzes"])


def _frame(event: str, data: str) -> str:
    """手工编码 SSE 帧（EventSourceResponse 仅作 Content-Type 标记，帧格式自控）。

    小程序端按行解析 event:/data: 帧，data 一律为单行 JSON 字符串。
    """
    return f"event: {event}\ndata: {data}\n\n"


def _stage(stage: str, message: str) -> str:
    return _frame("stage", json.dumps({"stage": stage, "message": message}, ensure_ascii=False))


def _error(code: str, message: str) -> str:
    return _frame("error", json.dumps({"code": code, "message": message}, ensure_ascii=False))


def _done() -> str:
    return _frame("done", "[DONE]")


# ---------- 第一段：知识点提取 ----------


@router.post("/quizzes/extract")
async def extract_quiz(req: ExtractRequest, chains: ChainRegistry = Depends(get_chains)):
    async def event_gen() -> AsyncIterable[str]:
        try:
            material = get_owned_material(req.material_id, req.client_id)
        except Exception:
            yield _error("MATERIAL_NOT_FOUND", "学习材料不存在或已过期，请重新提交")
            return
        yield _stage("extracting", "正在提取知识点…")
        try:
            extraction = await extract_knowledge(
                material.id, material.text, chains.extraction_chain, session_id=material.id
            )
        except Exception:
            yield _error("LLM_TIMEOUT", "AI 开小差了，请点击重试")
            return
        yield _frame("knowledge", extraction.model_dump_json())
        yield _done()

    return EventSourceResponse(event_gen())


# ---------- 第二段：按配置与勾选生成题目 ----------


@router.post("/quizzes/generate")
async def generate_quiz_sse(
    req: GenerateRequest, request: Request, chains: ChainRegistry = Depends(get_chains)
):
    settings = request.app.state.settings
    # 额度预检：超限直接 429（不进入 SSE、不调用 LLM）
    state = gamification_service.ensure_state(req.client_id)
    gamification_service.check_quota(state, settings)

    async def event_gen() -> AsyncIterable[str]:
        try:
            material = get_owned_material(req.material_id, req.client_id)
        except Exception:
            yield _error("MATERIAL_NOT_FOUND", "学习材料不存在或已过期，请重新提交")
            return

        config = QuizConfig(
            goal=req.goal,
            difficulty=req.difficulty,
            count=req.count,
            selected_knowledge_points=req.selected_knowledge_points,
        )

        yield _stage("generating", "正在生成题目…")
        # 提取知识点（缓存命中则不消耗 LLM 调用）
        try:
            extraction = await extract_knowledge(
                material.id, material.text, chains.extraction_chain, session_id=material.id
            )
        except Exception:
            yield _error("LLM_TIMEOUT", "AI 开小差了，请点击重试")
            return
        extraction = filter_knowledge_points(extraction, config.selected_knowledge_points)

        # 主题模式：用提取结果扩展有效材料（Grounded 校验针对扩展文本）
        if material.source_type == "topic":
            from app.services.quiz_service import expand_topic_material

            material_text = expand_topic_material(material.text, extraction)
        else:
            material_text = material.text

        quiz_id = f"quiz_{uuid4().hex[:12]}"
        try:
            quiz_set = await generate_quiz(
                material_text, extraction, config, chains.quiz_chain, session_id=quiz_id
            )
        except QuizGenerationFailed:
            yield _error("QUIZ_GENERATION_FAILED", "题目生成失败，建议精简内容后重试（本次不扣额度）")
            return
        except Exception:
            yield _error("LLM_TIMEOUT", "AI 开小差了，请点击重试")
            return

        yield _stage("validating", "正在校验题目质量…")
        quiz = Quiz(
            id=quiz_id,
            material_id=material.id,
            client_id=req.client_id,
            config=config,
            quiz_set=quiz_set,
        )
        memory_store.save_quiz(quiz)
        gamification_service.consume_quota(state)  # 仅成功后扣额度

        public: PublicQuiz = to_public_quiz(quiz_id, quiz_set)
        payload = public.model_dump()
        payload["gamification"] = {
            "exp": state.exp,
            "combo": state.combo,
            "quota_remaining": settings.monthly_quota - state.quota_used,
        }
        yield _frame("quiz", json.dumps(payload, ensure_ascii=False))
        yield _done()

    return EventSourceResponse(event_gen())


# ---------- 获取闯关（不含答案） ----------


@router.get("/quizzes/{quiz_id}", response_model=PublicQuiz)
async def get_quiz(quiz_id: str, client_id: str):
    quiz = get_owned_quiz(quiz_id, client_id)
    return to_public_quiz(quiz.id, quiz.quiz_set)


# ---------- 判分（幂等，答案不出后端） ----------


@router.post("/quizzes/{quiz_id}/answers", response_model=AnswerResponse)
async def submit_answer(
    quiz_id: str, req: AnswerRequest, request: Request
):
    settings = request.app.state.settings
    quiz = get_owned_quiz(quiz_id, req.client_id)
    questions = quiz.quiz_set.questions
    if not 0 <= req.question_index < len(questions):
        from app.schemas.api import ApiError

        raise ApiError(code="QUESTION_NOT_FOUND", message="题目不存在", status_code=404)

    question = questions[req.question_index]
    state = gamification_service.ensure_state(req.client_id)

    existing = memory_store.get_answer(quiz_id, req.question_index)
    if existing is not None:
        # 幂等：同题重复提交返回首次结果，不重复加经验
        answered = len(memory_store.get_answers(quiz_id))
        return AnswerResponse(
            correct=existing.correct,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            knowledge_point=question.knowledge_point,
            source_excerpt=question.source_excerpt,
            exp_delta=0,
            combo=state.combo,
            progress=Progress(answered=answered, total=len(questions)),
        )

    correct = req.user_answer == question.correct_answer
    record = AnswerRecord(
        quiz_id=quiz_id,
        question_index=req.question_index,
        user_answer=req.user_answer,
        correct=correct,
        elapsed_ms=req.elapsed_ms,
    )
    memory_store.save_answer(record)
    exp_delta, combo = gamification_service.apply_answer(state, correct, settings)

    answered = len(memory_store.get_answers(quiz_id))
    if answered == len(questions) and quiz.status != "completed":
        quiz.status = "completed"
        memory_store.save_quiz(quiz)

    return AnswerResponse(
        correct=correct,
        correct_answer=question.correct_answer,
        explanation=question.explanation,
        knowledge_point=question.knowledge_point,
        source_excerpt=question.source_excerpt,
        exp_delta=exp_delta,
        combo=combo,
        progress=Progress(answered=answered, total=len(questions)),
    )
