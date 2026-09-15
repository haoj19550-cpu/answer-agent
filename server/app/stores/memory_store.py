"""内存数据存储：TTLCache，无数据库（方案 7.2）。

访问接口定义为简单函数，未来如需持久化，替换实现即可。
"""

import threading

from cachetools import TTLCache

from app.schemas.gamification import GamificationState
from app.schemas.quiz import AnswerRecord, KnowledgeExtraction, Material, Quiz, Report

_STORE_TTL = 7200  # 2 小时
_GAMIFICATION_TTL = 30 * 86400  # 30 天

_lock = threading.RLock()

materials: TTLCache = TTLCache(maxsize=1000, ttl=_STORE_TTL)
extractions: TTLCache = TTLCache(maxsize=1000, ttl=_STORE_TTL)  # key = material_id
quizzes: TTLCache = TTLCache(maxsize=1000, ttl=_STORE_TTL)
reports: TTLCache = TTLCache(maxsize=1000, ttl=_STORE_TTL)  # key = quiz_id
answers: TTLCache = TTLCache(maxsize=1000, ttl=_STORE_TTL)  # key = quiz_id -> dict[index, AnswerRecord]
gamification: TTLCache = TTLCache(maxsize=10000, ttl=_GAMIFICATION_TTL)  # key = client_id


def configure(ttl: int = _STORE_TTL, gamification_ttl: int = _GAMIFICATION_TTL) -> None:
    """按配置重建存储（应用启动时调用一次；测试可调整 TTL）。"""
    global materials, extractions, quizzes, reports, answers, gamification
    with _lock:
        materials = TTLCache(maxsize=1000, ttl=ttl)
        extractions = TTLCache(maxsize=1000, ttl=ttl)
        quizzes = TTLCache(maxsize=1000, ttl=ttl)
        reports = TTLCache(maxsize=1000, ttl=ttl)
        answers = TTLCache(maxsize=1000, ttl=ttl)
        gamification = TTLCache(maxsize=10000, ttl=gamification_ttl)


# ---------- Material ----------


def save_material(m: Material) -> None:
    with _lock:
        materials[m.id] = m


def get_material(material_id: str) -> Material | None:
    return materials.get(material_id)


# ---------- KnowledgeExtraction（按 material_id 缓存复用，省 LLM 调用） ----------


def save_extraction(material_id: str, ext: KnowledgeExtraction) -> None:
    with _lock:
        extractions[material_id] = ext


def get_extraction(material_id: str) -> KnowledgeExtraction | None:
    return extractions.get(material_id)


# ---------- Quiz ----------


def save_quiz(q: Quiz) -> None:
    with _lock:
        quizzes[q.id] = q


def get_quiz(quiz_id: str) -> Quiz | None:
    return quizzes.get(quiz_id)


# ---------- AnswerRecord（幂等：同题重复提交返回首次记录） ----------


def save_answer(record: AnswerRecord) -> AnswerRecord:
    """幂等写入：已存在同题记录时返回首次记录，不覆盖。"""
    with _lock:
        bucket: dict[int, AnswerRecord] = answers.get(record.quiz_id) or {}
        if record.question_index in bucket:
            return bucket[record.question_index]
        bucket[record.question_index] = record
        answers[record.quiz_id] = bucket
        return record


def get_answer(quiz_id: str, question_index: int) -> AnswerRecord | None:
    bucket = answers.get(quiz_id) or {}
    return bucket.get(question_index)


def get_answers(quiz_id: str) -> list[AnswerRecord]:
    bucket = answers.get(quiz_id) or {}
    return [bucket[i] for i in sorted(bucket)]


# ---------- Report ----------


def save_report(r: Report) -> None:
    with _lock:
        reports[r.quiz_id] = r


def get_report(quiz_id: str) -> Report | None:
    return reports.get(quiz_id)


# ---------- Gamification ----------


def get_gamification(client_id: str) -> GamificationState:
    with _lock:
        state = gamification.get(client_id)
        if state is None:
            state = GamificationState(client_id=client_id)
            gamification[client_id] = state
        return state


def save_gamification(state: GamificationState) -> None:
    with _lock:
        gamification[state.client_id] = state


def clear_all() -> None:
    """测试辅助：清空全部存储。"""
    with _lock:
        for cache in (materials, extractions, quizzes, reports, answers, gamification):
            cache.clear()
