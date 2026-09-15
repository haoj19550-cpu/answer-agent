"""服务层测试：降级流水线 / 提取缓存 / 报告兜底 / 游戏化规则。"""

import pytest

from app.chains.quiz import build_extraction_chain, build_quiz_chain, build_report_chain
from app.config import Settings
from app.schemas.api import ApiError
from app.schemas.gamification import Badge
from app.schemas.quiz import Quiz, QuizConfig, StudyGoal, Difficulty
from app.services import gamification_service
from app.services.quiz_service import (
    QuizGenerationFailed,
    extract_knowledge,
    filter_knowledge_points,
    generate_quiz,
)
from app.services.report_service import build_report, compute_stats
from app.stores import memory_store


def _settings(**kw) -> Settings:
    return Settings(deepseek_api_key="", **kw)


# ---------- 知识点过滤与缓存 ----------


class TestKnowledgeFilter:
    def test_no_selection_returns_all(self, sample_extraction):
        assert len(filter_knowledge_points(sample_extraction, []).knowledge_points) == 4

    def test_filter_by_selected_names(self, sample_extraction):
        result = filter_knowledge_points(sample_extraction, ["缓存穿透", "缓存击穿"])
        assert [kp.name for kp in result.knowledge_points] == ["缓存穿透", "缓存击穿"]

    def test_unknown_selection_returns_all(self, sample_extraction):
        assert len(filter_knowledge_points(sample_extraction, ["不存在"]).knowledge_points) == 4


class TestExtractionCache:
    async def test_second_call_uses_cache(self, fake_llm_factory, sample_extraction):
        llm = fake_llm_factory([sample_extraction])
        chain = build_extraction_chain(llm, max_attempts=1)
        r1 = await extract_knowledge("mat1", "材料", chain)
        r2 = await extract_knowledge("mat1", "材料", chain)
        assert r1 is r2
        assert llm.call_count == 1  # 缓存命中，省 1 次 LLM 调用


# ---------- 出题降级流水线 ----------


class TestGeneratePipeline:
    async def test_success_first_try(
        self, fake_llm_factory, sample_quiz_set, sample_extraction, sample_material
    ):
        llm = fake_llm_factory([sample_quiz_set])
        chain = build_quiz_chain(llm, max_attempts=1)
        quiz = await generate_quiz(sample_material, sample_extraction, QuizConfig(), chain)
        assert len(quiz.questions) == 5
        assert llm.call_count == 1

    async def test_validator_failure_then_retry_success(
        self, fake_llm_factory, sample_quiz_set, sample_extraction, sample_material
    ):
        bad = sample_quiz_set.model_copy(
            update={
                "questions": [
                    q.model_copy(update={"source_excerpt": "材料中不存在的幻觉内容段落xyz"})
                    for q in sample_quiz_set.questions
                ]
            }
        )
        llm = fake_llm_factory([bad, sample_quiz_set])
        chain = build_quiz_chain(llm, max_attempts=1)
        quiz = await generate_quiz(sample_material, sample_extraction, QuizConfig(), chain)
        assert len(quiz.questions) == 5
        assert llm.call_count == 2

    async def test_all_fail_raises(self, fake_llm_factory, sample_extraction, sample_material, sample_quiz_set):
        bad = sample_quiz_set.model_copy(
            update={
                "questions": [
                    q.model_copy(update={"source_excerpt": "不存在的幻觉内容xyz"})
                    for q in sample_quiz_set.questions
                ]
            }
        )
        llm = fake_llm_factory([bad])
        chain = build_quiz_chain(llm, max_attempts=1)
        with pytest.raises(QuizGenerationFailed):
            await generate_quiz(sample_material, sample_extraction, QuizConfig(), chain)

    async def test_chain_exception_moves_to_reduced_count(
        self, fake_llm_factory, sample_extraction, sample_material
    ):
        llm = fake_llm_factory([RuntimeError("model exploded")])
        chain = build_quiz_chain(llm, max_attempts=1)
        with pytest.raises(QuizGenerationFailed):
            await generate_quiz(sample_material, sample_extraction, QuizConfig(), chain)


# ---------- 报告服务 ----------


def _make_quiz_and_records(sample_quiz_set, answers: dict[int, tuple[int, bool]]):
    from app.schemas.quiz import AnswerRecord

    quiz = Quiz(
        id="quiz_t1",
        material_id="mat1",
        client_id="c1",
        config=QuizConfig(),
        quiz_set=sample_quiz_set,
    )
    records = [
        AnswerRecord(
            quiz_id="quiz_t1",
            question_index=i,
            user_answer=ua,
            correct=ok,
            elapsed_ms=8000,
        )
        for i, (ua, ok) in answers.items()
    ]
    return quiz, records


class TestReportStats:
    def test_stats_computed_by_code(self, sample_quiz_set):
        quiz, records = _make_quiz_and_records(
            sample_quiz_set, {0: (0, True), 1: (0, False), 2: (0, True), 3: (0, True), 4: (0, False)}
        )
        stats = compute_stats(quiz, records)
        assert stats["score"] == 60
        assert stats["correct_count"] == 3
        assert stats["duration_ms"] == 40000
        assert stats["wrong_indices"] == [1, 4]
        assert stats["mastery_levels"]["缓存穿透"] == "good"
        assert stats["mastery_levels"]["缓存击穿"] == "weak"


class TestReportBuild:
    async def test_report_with_llm_content(self, fake_llm_factory, sample_quiz_set, sample_report_content):
        quiz, records = _make_quiz_and_records(
            sample_quiz_set, {0: (0, True), 1: (0, False), 2: (0, True), 3: (0, True), 4: (0, False)}
        )
        llm = fake_llm_factory([sample_report_content])
        chain = build_report_chain(llm, max_attempts=1)
        report = await build_report(quiz, records, chain)
        assert report.ai_generated is True
        assert report.score == 60
        assert report.performance_summary.startswith("本次闯关")
        assert report.wrong_questions[0].error_type == "概念混淆"
        assert len(report.suggestions) == 3

    async def test_report_chain_failure_falls_back_to_template(self, fake_llm_factory, sample_quiz_set):
        quiz, records = _make_quiz_and_records(
            sample_quiz_set, {0: (0, True), 1: (0, False), 2: (0, True), 3: (0, True), 4: (0, False)}
        )
        llm = fake_llm_factory([RuntimeError("report chain down")])
        chain = build_report_chain(llm, max_attempts=1)
        report = await build_report(quiz, records, chain)
        assert report.ai_generated is False
        assert report.score == 60  # 数字仍准确
        assert report.suggestions

    async def test_report_without_chain_is_template(self, sample_quiz_set):
        quiz, records = _make_quiz_and_records(sample_quiz_set, {0: (0, True)})
        report = await build_report(quiz, records, None)
        assert report.ai_generated is False


# ---------- 游戏化 ----------


class TestGamification:
    def test_quota_check_and_consume(self):
        settings = _settings(monthly_quota=2)
        state = gamification_service.ensure_state("c1")
        gamification_service.check_quota(state, settings)
        gamification_service.consume_quota(state)
        gamification_service.consume_quota(state)
        with pytest.raises(ApiError) as exc:
            gamification_service.check_quota(state, settings)
        assert exc.value.code == "QUOTA_EXCEEDED"
        assert exc.value.status_code == 429

    def test_quota_rolls_over_month(self):
        settings = _settings(monthly_quota=1)
        state = gamification_service.ensure_state("c2")
        gamification_service.consume_quota(state)
        import datetime

        state.roll_month(datetime.date(2099, 1, 1))
        gamification_service.check_quota(state, settings)  # 不抛异常

    def test_answer_exp_and_combo(self):
        settings = _settings(exp_per_correct=20)
        state = gamification_service.ensure_state("c3")
        delta, combo = gamification_service.apply_answer(state, True, settings)
        assert (delta, combo) == (20, 1)
        delta, combo = gamification_service.apply_answer(state, True, settings)
        assert (delta, combo) == (20, 2)
        delta, combo = gamification_service.apply_answer(state, False, settings)
        assert (delta, combo) == (0, 0)
        assert state.max_combo == 2

    def test_completion_badges(self):
        settings = _settings(exp_per_complete=40)
        state = gamification_service.ensure_state("c4")
        gamification_service.apply_answer(state, True, settings)
        gamification_service.apply_answer(state, True, settings)
        gamification_service.apply_answer(state, True, settings)
        exp_delta, badges = gamification_service.apply_completion(state, 1.0, settings)
        assert exp_delta == 40
        assert Badge.FIRST_QUIZ in badges
        assert Badge.COMBO_3 in badges
        assert Badge.PERFECT in badges
        # 重复完成不再重复发徽章
        _, badges2 = gamification_service.apply_completion(state, 0.6, settings)
        assert badges2 == []

    def test_state_persists_in_store(self):
        settings = _settings()
        state = gamification_service.ensure_state("c5")
        gamification_service.apply_answer(state, True, settings)
        again = gamification_service.ensure_state("c5")
        assert again.exp == 20
