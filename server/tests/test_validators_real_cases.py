"""真实模型输出形态下的 Grounded Quiz 校验（离线用例）。

真实 LLM 的 source_excerpt 常带「」引号、省略号、换行与全半角差异；
GROUNDED_STRICT=1 时逐字摘录不匹配即判失败（触发降级重生成），
=0 时仅记录告警不阻塞。
"""

from app.schemas.quiz import (
    KnowledgeExtraction,
    KnowledgePoint,
    Question,
    QuestionType,
    QuizSet,
)
from app.validators.quiz_validator import validate_quiz

MATERIAL = (
    "Redis 缓存是后端性能优化的核心手段。"
    "缓存穿透是指查询一个数据库中根本不存在的数据，缓存和数据库都miss。"
    "解决方案是使用布隆过滤器拦截非法key，或对空结果进行短时间的空值缓存。"
)

EXTRACTION = KnowledgeExtraction(
    topic="Redis 缓存",
    summary="缓存三大问题与解法",
    knowledge_points=[
        KnowledgePoint(name="缓存穿透", definition="查询不存在的数据", importance=5),
        KnowledgePoint(name="布隆过滤器", definition="拦截非法key", importance=3),
        KnowledgePoint(name="空值缓存", definition="缓存空结果", importance=3),
    ],
)

MIX = (3, 3, 0, 0)  # QuizSet 最少 3 题：目标题 + 2 道填充题


def _q(stem: str, kp: str, excerpt: str, answer: int = 0) -> Question:
    return Question(
        type=QuestionType.SINGLE_CHOICE,
        stem=stem,
        options=["选项一", "选项二", "选项三", "选项四"],
        correct_answer=answer,
        explanation="见材料原文。",
        knowledge_point=kp,
        difficulty=2,
        source_excerpt=excerpt,
    )


def _quiz(excerpt: str, kp: str = "缓存穿透") -> QuizSet:
    return QuizSet(
        title="Redis 闯关",
        questions=[
            _q("缓存穿透的成因是？", kp, excerpt),
            _q("布隆过滤器的作用是？", "布隆过滤器", "解决方案是使用布隆过滤器拦截非法key", 1),
            _q("空值缓存用于缓解？", "空值缓存", "或对空结果进行短时间的空值缓存", 2),
        ],
    )


def _errors_for(excerpt: str, kp: str = "缓存穿透", **kw) -> list[str]:
    return validate_quiz(_quiz(excerpt, kp), EXTRACTION, MATERIAL, MIX, **kw)


class TestRealExcerptForms:
    def test_verbatim_excerpt_passes(self):
        assert _errors_for("缓存穿透是指查询一个数据库中根本不存在的数据") == []

    def test_cjk_quotes_and_brackets_tolerated(self):
        assert _errors_for("「缓存穿透是指查询一个数据库中根本不存在的数据」") == []

    def test_ellipsis_inside_excerpt_tolerated(self):
        assert _errors_for("缓存穿透是指……根本不存在的数据") == []

    def test_newline_and_spaces_tolerated(self):
        assert _errors_for("缓存穿透是指查询一个\n  数据库中根本不存在的数据") == []

    def test_whitespace_only_excerpt_is_error(self):
        assert any("source_excerpt" in e for e in _errors_for("   "))


class TestGroundedStrictSwitch:
    def test_strict_rejects_paraphrased_excerpt(self):
        errors = _errors_for("查询压根没有的数据导致缓存失效")
        assert any("source_excerpt" in e for e in errors)

    def test_strict_is_default(self):
        assert _errors_for("查询压根没有的数据导致缓存失效") != []

    def test_loose_mode_only_warns(self):
        assert _errors_for("查询压根没有的数据导致缓存失效", grounded_strict=False) == []

    def test_structural_errors_still_fail_in_loose_mode(self):
        quiz = _quiz("缓存穿透是指查询一个数据库中根本不存在的数据")
        quiz.questions[0].correct_answer = 9  # 下标越界
        errors = validate_quiz(quiz, EXTRACTION, MATERIAL, MIX, grounded_strict=False)
        assert any("correct_answer" in e for e in errors)

    def test_knowledge_point_mismatch_fails_in_both_modes(self):
        for strict in (True, False):
            errors = _errors_for(
                "缓存穿透是指查询一个数据库中根本不存在的数据",
                kp="量子纠缠",
                grounded_strict=strict,
            )
            assert any("knowledge_point" in e for e in errors)
