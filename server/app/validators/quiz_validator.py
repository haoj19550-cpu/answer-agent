"""Validator：纯代码业务规则校验，不依赖 LLM 自评（方案 5.3）。

校验规则：
- 结构：题数与题型配比正确、单选题 4 选项、判断题 2 选项、选项互不重复、
  correct_answer 在选项下标范围内、题干非空且互不重复
- 语义（Grounded Quiz）：每题 knowledge_point 命中已提取知识点；
  source_excerpt 能在材料原文模糊匹配到
- 难度分布：弱一致信号（有基础题、有进阶题）
"""

import re

import structlog

from app.schemas.quiz import KnowledgeExtraction, QuestionType, QuizSet

logger = structlog.get_logger(__name__)

# 归一化：去空白、标点与省略号（真实模型摘录常带「」引号、…… 与换行）
_PUNCT_RE = re.compile(
    r"[\s　，。、；：？！“”‘’（）《》〈〉「」『』【】…,.;:?!\"'()\[\]<>\-]+"
)


def _normalize(s: str) -> str:
    """归一化：去空白与标点（含省略号），用于模糊匹配。"""
    return _PUNCT_RE.sub("", s)


# 省略号：真实模型摘录常用「……」跳过中间文字，按片段分别校验
_ELLIPSIS_RE = re.compile(r"…+|\.{2,}|·{2,}")


def _match_one(haystack: str, needle: str, fragment: int = 12) -> bool:
    """needle 归一化后整体或首尾片段在 haystack 归一化文本中出现。"""
    h, n = _normalize(haystack), _normalize(needle)
    if not n:
        return False
    if n in h:
        return True
    if len(n) <= fragment:
        return False
    return n[:fragment] in h or n[-fragment:] in h


def _fuzzy_contains(haystack: str, needle: str, fragment: int = 12) -> bool:
    """模糊包含；含省略号时拆成多段，要求每段都能在原文中找到。"""
    parts = [p for p in _ELLIPSIS_RE.split(needle) if p.strip()]
    if not parts:
        return False
    return all(_match_one(haystack, p, fragment) for p in parts)


def validate_quiz(
    quiz: QuizSet,
    extraction: KnowledgeExtraction,
    material: str,
    expected_mix: tuple[int, int, int] | None = None,
    grounded_strict: bool = True,
) -> list[str]:
    """返回错误列表；空列表表示校验通过。

    grounded_strict=False 时，source_excerpt 未命中原文只记录告警（不判失败），
    用于真实模型摘录风格偏改写时的降级运行。
    """
    errors: list[str] = []
    questions = quiz.questions

    # 1. 题数与配比
    if expected_mix is not None:
        exp_count, exp_single, exp_judge, exp_scenario = expected_mix
        if len(questions) != exp_count:
            errors.append(f"题数不符：期望 {exp_count}，实际 {len(questions)}")
        counts = {
            QuestionType.SINGLE_CHOICE: 0,
            QuestionType.TRUE_FALSE: 0,
            QuestionType.SCENARIO: 0,
        }
        for q in questions:
            counts[q.type] += 1
        if (
            counts[QuestionType.SINGLE_CHOICE] != exp_single
            or counts[QuestionType.TRUE_FALSE] != exp_judge
            or counts[QuestionType.SCENARIO] != exp_scenario
        ):
            errors.append(
                "题型配比不符：期望 单选{}/判断{}/场景{}，实际 单选{}/判断{}/场景{}".format(
                    exp_single,
                    exp_judge,
                    exp_scenario,
                    counts[QuestionType.SINGLE_CHOICE],
                    counts[QuestionType.TRUE_FALSE],
                    counts[QuestionType.SCENARIO],
                )
            )

    # 2. 结构规则
    stems: set[str] = set()
    for i, q in enumerate(questions):
        prefix = f"第{i + 1}题"
        if not q.stem.strip():
            errors.append(f"{prefix}：题干为空")
        norm_stem = _normalize(q.stem)
        if norm_stem in stems:
            errors.append(f"{prefix}：题干与其他题重复")
        stems.add(norm_stem)

        if q.type == QuestionType.SINGLE_CHOICE and len(q.options) != 4:
            errors.append(f"{prefix}：单选题必须有 4 个选项，实际 {len(q.options)}")
        if q.type == QuestionType.TRUE_FALSE and len(q.options) != 2:
            errors.append(f"{prefix}：判断题必须有 2 个选项，实际 {len(q.options)}")
        norm_options = [_normalize(o) for o in q.options]
        if len(set(norm_options)) != len(norm_options):
            errors.append(f"{prefix}：选项存在重复")
        if not 0 <= q.correct_answer < len(q.options):
            errors.append(f"{prefix}：correct_answer 下标越界（{q.correct_answer}）")
        if any(not o.strip() for o in q.options):
            errors.append(f"{prefix}：存在空选项")
        if not q.explanation.strip():
            errors.append(f"{prefix}：解析为空")

    # 3. 语义规则（Grounded Quiz）
    kp_names = [kp.name for kp in extraction.knowledge_points]
    for i, q in enumerate(questions):
        prefix = f"第{i + 1}题"
        if not any(_fuzzy_contains(name, q.knowledge_point) or _fuzzy_contains(q.knowledge_point, name) for name in kp_names):
            errors.append(f"{prefix}：knowledge_point「{q.knowledge_point}」未命中已提取知识点")
        if not _fuzzy_contains(material, q.source_excerpt):
            msg = f"{prefix}：source_excerpt 未在材料原文中匹配到（幻觉风险）"
            if grounded_strict:
                errors.append(msg)
            else:
                logger.warning("grounded_excerpt_miss", question=prefix, excerpt=q.source_excerpt)

    # 4. 难度分布（弱一致信号）
    if len(questions) >= 5:
        difficulties = [q.difficulty for q in questions]
        if not any(d <= 2 for d in difficulties):
            errors.append("难度分布不合理：缺少基础题（难度 1-2）")
        if not any(d >= 3 for d in difficulties):
            errors.append("难度分布不合理：缺少进阶题（难度 ≥3）")

    return errors
