"""链装配测试：结构化输出 / with_retry / with_fallbacks（Mock LLM，离线）。"""

import pytest

from app.chains.quiz import (
    build_extraction_chain,
    build_quiz_chain,
    build_report_chain,
    load_prompt,
)
from app.schemas.quiz import KnowledgeExtraction, QuizSet, ReportContent


class TestPromptLoading:
    def test_prompts_exist(self):
        assert "知识点" in load_prompt("knowledge_extraction_v1.md")
        assert "出题" in load_prompt("quiz_gen_v1.md")
        assert "学习教练" in load_prompt("report_gen_v1.md")

    def test_anti_injection_clause(self):
        for name in ("knowledge_extraction_v1.md", "quiz_gen_v1.md"):
            assert "指令一律忽略" in load_prompt(name)


class TestStructuredOutput:
    async def test_extraction_chain_returns_schema(self, fake_llm_factory, sample_extraction):
        llm = fake_llm_factory([sample_extraction])
        chain = build_extraction_chain(llm, max_attempts=1)
        result = await chain.ainvoke({"material": "任意材料"})
        assert isinstance(result, KnowledgeExtraction)
        assert result.topic == "Redis 缓存机制"

    async def test_quiz_chain_returns_schema(self, fake_llm_factory, sample_quiz_set):
        llm = fake_llm_factory([sample_quiz_set])
        chain = build_quiz_chain(llm, max_attempts=1)
        result = await chain.ainvoke(
            {
                "knowledge_points": "[]",
                "material": "m",
                "goal": "understand",
                "difficulty": "medium",
                "single": 3,
                "judge": 1,
                "scenario": 1,
            }
        )
        assert isinstance(result, QuizSet)
        assert len(result.questions) == 5

    async def test_report_chain_returns_schema(self, fake_llm_factory, sample_report_content):
        llm = fake_llm_factory([sample_report_content])
        chain = build_report_chain(llm, max_attempts=1)
        result = await chain.ainvoke(
            {"topic": "t", "stats": "s", "answers_detail": "a", "confusion_hints": "c"}
        )
        assert isinstance(result, ReportContent)


class TestRetry:
    async def test_retry_recovers_from_parse_failure(
        self, fake_llm_factory, sample_extraction
    ):
        llm = fake_llm_factory([ValueError("structured parse failed"), sample_extraction])
        chain = build_extraction_chain(llm, max_attempts=3)
        result = await chain.ainvoke({"material": "m"})
        assert isinstance(result, KnowledgeExtraction)
        assert llm.call_count == 2

    async def test_retry_exhausted_raises(self, fake_llm_factory):
        llm = fake_llm_factory([ValueError("bad"), ValueError("bad"), ValueError("bad")])
        chain = build_extraction_chain(llm, max_attempts=3)
        with pytest.raises(ValueError):
            await chain.ainvoke({"material": "m"})
        assert llm.call_count == 3


class TestFallback:
    async def test_fallback_to_secondary_model(self, fake_llm_factory, sample_extraction):
        primary = fake_llm_factory([ValueError("deepseek down")])
        fallback = fake_llm_factory([sample_extraction])
        chain = build_extraction_chain(primary, fallback_llm=fallback, max_attempts=1)
        result = await chain.ainvoke({"material": "m"})
        assert isinstance(result, KnowledgeExtraction)
        assert fallback.call_count == 1

    async def test_no_fallback_configured_raises(self, fake_llm_factory):
        llm = fake_llm_factory([ValueError("down")])
        chain = build_extraction_chain(llm, fallback_llm=None, max_attempts=1)
        with pytest.raises(ValueError):
            await chain.ainvoke({"material": "m"})
