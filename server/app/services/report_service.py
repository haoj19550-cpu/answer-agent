"""报告服务：规则统计 + 链3 文案 + 模板兜底（方案 5.5）。

数字由代码计算，文案由 LLM 生成；链3 失败时回退纯规则模板报告，报告永不 500。
"""

import structlog
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.runnables import Runnable

from app.llm.callbacks import record_usage
from app.schemas.quiz import AnswerRecord, Quiz, Report, ReportContent, WrongQuestion
from app.stores import memory_store

logger = structlog.get_logger(__name__)


def compute_stats(quiz: Quiz, records: list[AnswerRecord]) -> dict:
    """规则计算：总分/正确率/用时/各知识点得分率。数字绝不让 LLM 算。"""
    questions = quiz.quiz_set.questions
    total = len(questions)
    correct_count = sum(1 for r in records if r.correct)
    accuracy = correct_count / total if total else 0.0

    # 知识点得分率
    kp_stats: dict[str, list[int]] = {}
    by_index = {r.question_index: r for r in records}
    for i, q in enumerate(questions):
        rec = by_index.get(i)
        slot = kp_stats.setdefault(q.knowledge_point, [0, 0])
        slot[1] += 1
        if rec and rec.correct:
            slot[0] += 1

    mastery: dict[str, str] = {}
    for kp, (hit, cnt) in kp_stats.items():
        rate = hit / cnt if cnt else 0.0
        mastery[kp] = "good" if rate >= 0.8 else ("fair" if rate >= 0.5 else "weak")

    return {
        "total": total,
        "correct_count": correct_count,
        "accuracy": accuracy,
        "score": round(accuracy * 100),
        "duration_ms": sum(r.elapsed_ms for r in records),
        "mastery_levels": mastery,
        "kp_stats": kp_stats,
        "wrong_indices": [i for i in range(total) if i in by_index and not by_index[i].correct],
    }


def _build_template_report(quiz: Quiz, records: list[AnswerRecord], stats: dict) -> Report:
    """纯规则模板报告（链3 失败的兜底）。"""
    wrong = [
        WrongQuestion(
            index=i,
            stem=quiz.quiz_set.questions[i].stem,
            error_type="待分析",
            analysis="本次报告由模板生成，错因分析不可用，建议对照解析复习。",
        )
        for i in stats["wrong_indices"]
    ]
    weak_kps = [kp for kp, lv in stats["mastery_levels"].items() if lv == "weak"]
    suggestions = [f"重点复习薄弱知识点：{kp}" for kp in weak_kps[:2]] or ["保持当前节奏，尝试更高难度"]
    suggestions.append("重新挑战一次闯关，检验掌握情况")
    return Report(
        quiz_id=quiz.id,
        client_id=quiz.client_id,
        title=quiz.quiz_set.title,
        score=stats["score"],
        accuracy=stats["accuracy"],
        duration_ms=stats["duration_ms"],
        mastery_levels=stats["mastery_levels"],
        wrong_questions=wrong,
        performance_summary=(
            f"本次闯关共 {stats['total']} 题，答对 {stats['correct_count']} 题，"
            f"正确率 {stats['accuracy']:.0%}。"
        ),
        confusion_pairs=[],
        suggestions=suggestions,
        ai_generated=False,
    )


async def build_report(
    quiz: Quiz,
    records: list[AnswerRecord],
    report_chain: Runnable | None = None,
    session_id: str = "",
) -> Report:
    """规则统计 + 链3 文案；链3 缺失或失败时回退模板报告。"""
    stats = compute_stats(quiz, records)
    questions = quiz.quiz_set.questions
    by_index = {r.question_index: r for r in records}

    if report_chain is None:
        return _build_template_report(quiz, records, stats)

    answers_detail = "\n".join(
        f"第{i + 1}题[{q.knowledge_point}]：{'答对' if by_index[i].correct else '答错'}"
        f"（用户选 {q.options[by_index[i].user_answer] if i in by_index and by_index[i].user_answer < len(q.options) else '?'}，"
        f"正确为 {q.options[q.correct_answer]}）"
        for i, q in enumerate(questions)
        if i in by_index
    )
    stats_text = (
        f"总分 {stats['score']}/100；正确率 {stats['accuracy']:.0%}；"
        f"用时 {stats['duration_ms'] // 1000} 秒；"
        f"各知识点得分率："
        + "，".join(
            f"{kp} {hit}/{cnt}" for kp, (hit, cnt) in stats["kp_stats"].items()
        )
    )
    confusion_hints = "；".join(
        f"{kp.name} vs {'、'.join(kp.confusion_with)}"
        for kp in _get_confusion_hints(quiz)
    ) or "无"

    usage_cb = UsageMetadataCallbackHandler()
    try:
        content: ReportContent = await report_chain.ainvoke(
            {
                "topic": quiz.quiz_set.title,
                "stats": stats_text,
                "answers_detail": answers_detail,
                "confusion_hints": confusion_hints,
            },
            config={"callbacks": [usage_cb]},
        )
    except Exception as exc:
        logger.warning("report_chain_failed_fallback_template", error=str(exc))
        return _build_template_report(quiz, records, stats)
    finally:
        record_usage(session_id or quiz.id, usage_cb)

    analysis_by_index = {ea.question_index: ea for ea in content.error_analyses}
    wrong = [
        WrongQuestion(
            index=i,
            stem=questions[i].stem,
            error_type=analysis_by_index[i].error_type if i in analysis_by_index else "待分析",
            analysis=analysis_by_index[i].analysis if i in analysis_by_index else "",
        )
        for i in stats["wrong_indices"]
    ]
    return Report(
        quiz_id=quiz.id,
        client_id=quiz.client_id,
        title=quiz.quiz_set.title,
        score=stats["score"],
        accuracy=stats["accuracy"],
        duration_ms=stats["duration_ms"],
        mastery_levels=stats["mastery_levels"],
        wrong_questions=wrong,
        performance_summary=content.performance_summary,
        confusion_pairs=content.confusion_pairs,
        suggestions=content.suggestions,
        ai_generated=True,
    )


def _get_confusion_hints(quiz: Quiz):
    """从缓存的知识点提取结果中收集易混淆提示（尽力而为）。"""
    ext = memory_store.get_extraction(quiz.material_id)
    if ext is None:
        return []
    return [kp for kp in ext.knowledge_points if kp.confusion_with]
