"""Validator 全规则单测（方案 5.3）。"""

from app.schemas.quiz import QuestionType, QuizSet
from app.validators.quiz_validator import validate_quiz
from tests.conftest import SAMPLE_MATERIAL, make_question


class TestValidQuiz:
    def test_sample_quiz_passes(self, sample_quiz_set, sample_extraction, sample_material):
        errors = validate_quiz(sample_quiz_set, sample_extraction, sample_material, (5, 3, 1, 1))
        assert errors == []

    def test_passes_without_expected_mix(self, sample_quiz_set, sample_extraction, sample_material):
        assert validate_quiz(sample_quiz_set, sample_extraction, sample_material) == []


class TestStructure:
    def test_wrong_count(self, sample_quiz_set, sample_extraction, sample_material):
        errors = validate_quiz(sample_quiz_set, sample_extraction, sample_material, (10, 6, 2, 2))
        assert any("题数不符" in e for e in errors)

    def test_wrong_mix(self, sample_quiz_set, sample_extraction, sample_material):
        errors = validate_quiz(sample_quiz_set, sample_extraction, sample_material, (5, 2, 2, 1))
        assert any("配比不符" in e for e in errors)

    def test_single_choice_must_have_4_options(self, sample_quiz_set, sample_extraction, sample_material):
        q = sample_quiz_set.questions[0].model_copy(update={"options": ["A", "B", "C"]})
        quiz = QuizSet(title="t", questions=[q] + sample_quiz_set.questions[1:])
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("4 个选项" in e for e in errors)

    def test_duplicate_options(self, sample_quiz_set, sample_extraction, sample_material):
        q = sample_quiz_set.questions[0].model_copy(
            update={"options": ["相同", "相同", "C", "D"]}
        )
        quiz = QuizSet(title="t", questions=[q] + sample_quiz_set.questions[1:])
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("选项存在重复" in e for e in errors)

    def test_answer_index_out_of_range(self, sample_quiz_set, sample_extraction, sample_material):
        q = sample_quiz_set.questions[0].model_copy(update={"correct_answer": 4})
        quiz = QuizSet(title="t", questions=[q] + sample_quiz_set.questions[1:])
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("下标越界" in e for e in errors)

    def test_duplicate_stems(self, sample_quiz_set, sample_extraction, sample_material):
        dup = sample_quiz_set.questions[0].model_copy(
            update={"type": QuestionType.SINGLE_CHOICE}
        )
        quiz = QuizSet(title="t", questions=[dup] + sample_quiz_set.questions)
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("重复" in e for e in errors)


class TestGroundedness:
    def test_knowledge_point_not_in_extraction(self, sample_quiz_set, sample_extraction, sample_material):
        q = sample_quiz_set.questions[0].model_copy(update={"knowledge_point": "量子计算"})
        quiz = QuizSet(title="t", questions=[q] + sample_quiz_set.questions[1:])
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("未命中已提取知识点" in e for e in errors)

    def test_source_excerpt_not_in_material(self, sample_quiz_set, sample_extraction, sample_material):
        q = sample_quiz_set.questions[0].model_copy(
            update={"source_excerpt": "材料中完全不存在的虚构内容段落，用于模拟幻觉输出"}
        )
        quiz = QuizSet(title="t", questions=[q] + sample_quiz_set.questions[1:])
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("幻觉风险" in e for e in errors)

    def test_source_excerpt_fuzzy_match_with_punctuation(self, sample_quiz_set, sample_extraction, sample_material):
        """摘录带了不同标点/截断仍应模糊命中。"""
        q = sample_quiz_set.questions[0].model_copy(
            update={"source_excerpt": "缓存穿透是指查询一个数据库中根本不存在的数据……缓存和数据库都miss"}
        )
        quiz = QuizSet(title="t", questions=[q] + sample_quiz_set.questions[1:])
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert not any("幻觉风险" in e for e in errors)


class TestDifficulty:
    def test_all_easy_rejected_for_5_questions(self, sample_extraction, sample_material):
        quiz = QuizSet(
            title="t",
            questions=[
                make_question(
                    QuestionType.SINGLE_CHOICE, f"基础题{i}缓存穿透是什么？",
                    ["查询不存在的数据", "热点失效", "集中过期", "宕机"], 0, "缓存穿透", 1,
                    "缓存穿透是指查询一个数据库中根本不存在的数据",
                )
                for i in range(3)
            ]
            + [
                make_question(
                    QuestionType.TRUE_FALSE, "布隆过滤器拦截非法key。", ["正确", "错误"], 0,
                    "布隆过滤器", 1, "使用布隆过滤器拦截非法key",
                ),
                make_question(
                    QuestionType.SCENARIO, "场景：缓存穿透发生了该怎么办？",
                    ["布隆过滤器", "删库", "重启", "扩容"], 0, "缓存穿透", 1,
                    "解决方案是使用布隆过滤器拦截非法key",
                ),
            ],
        )
        errors = validate_quiz(quiz, sample_extraction, sample_material)
        assert any("缺少进阶题" in e for e in errors)
