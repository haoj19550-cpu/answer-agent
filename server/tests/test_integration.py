"""真实 DeepSeek 集成测试（@pytest.mark.integration）。

默认跳过；配置 DEEPSEEK_API_KEY 后手动跑：
    pytest -m integration
"""

import os

import pytest

from app.chains.quiz import build_extraction_chain, build_quiz_chain, build_report_chain
from app.config import get_settings
from app.llm.models import get_fallback_llm, get_primary_llm
from app.schemas.quiz import KnowledgeExtraction, QuizConfig, QuizSet
from app.services.quiz_service import generate_quiz
from app.validators.quiz_validator import validate_quiz
from tests.conftest import SAMPLE_MATERIAL

pytestmark = pytest.mark.integration

needs_key = pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"), reason="需要 DEEPSEEK_API_KEY"
)


@needs_key
async def test_real_extraction_chain():
    settings = get_settings()
    chain = build_extraction_chain(
        get_primary_llm(settings), get_fallback_llm(settings), settings.chain_max_attempts
    )
    result = await chain.ainvoke({"material": SAMPLE_MATERIAL})
    assert isinstance(result, KnowledgeExtraction)
    assert len(result.knowledge_points) >= 3


@needs_key
async def test_real_generate_quiz_passes_validator():
    settings = get_settings()
    primary = get_primary_llm(settings)
    fallback = get_fallback_llm(settings)
    ext_chain = build_extraction_chain(primary, fallback, settings.chain_max_attempts)
    quiz_chain = build_quiz_chain(primary, fallback, settings.chain_max_attempts)

    extraction = await ext_chain.ainvoke({"material": SAMPLE_MATERIAL})
    quiz = await generate_quiz(SAMPLE_MATERIAL, extraction, QuizConfig(count=5), quiz_chain)
    assert isinstance(quiz, QuizSet)
    # 全量校验通过（Grounded Quiz 幻觉防线）
    assert validate_quiz(quiz, extraction, SAMPLE_MATERIAL, (5, 3, 1, 1)) == []


@needs_key
async def test_real_report_chain():
    settings = get_settings()
    chain = build_report_chain(
        get_primary_llm(settings), get_fallback_llm(settings), settings.chain_max_attempts
    )
    result = await chain.ainvoke(
        {
            "topic": "Redis 缓存机制",
            "stats": "总分 60/100；正确率 60%；各知识点得分率：缓存穿透 1/1，缓存击穿 1/2",
            "answers_detail": "第1题[缓存穿透]：答对\n第2题[缓存击穿]：答错（用户选 给过期时间加随机值，正确为 使用互斥锁保证只有一个线程回源）",
            "confusion_hints": "缓存击穿 vs 缓存穿透、缓存雪崩",
        }
    )
    assert result.performance_summary
    assert 1 <= len(result.suggestions) <= 5
