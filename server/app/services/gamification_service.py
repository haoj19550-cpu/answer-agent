"""游戏化服务：经验/连击/额度/徽章规则计算（内存存储）。"""

from app.config import Settings
from app.schemas.api import ApiError
from app.schemas.gamification import Badge, GamificationState
from app.stores import memory_store


def ensure_state(client_id: str) -> GamificationState:
    state = memory_store.get_gamification(client_id)
    state.roll_month()
    return state


def check_quota(state: GamificationState, settings: Settings) -> None:
    """生成闯关前检查额度；用尽则拒绝（不进入 LLM 调用）。"""
    if state.quota_used >= settings.monthly_quota:
        raise ApiError(
            code="QUOTA_EXCEEDED",
            message="本月生成额度已用完，下月再来吧",
            status_code=429,
            detail={"monthly_quota": settings.monthly_quota, "used": state.quota_used},
        )


def consume_quota(state: GamificationState) -> None:
    """仅在闯关生成成功后扣 1 次；失败不扣额度。"""
    state.quota_used += 1
    memory_store.save_gamification(state)


def apply_answer(state: GamificationState, correct: bool, settings: Settings) -> tuple[int, int]:
    """答题结算：答对 +exp_per_correct 且连击 +1；答错连击清零。返回 (exp_delta, combo)。"""
    if correct:
        state.exp += settings.exp_per_correct
        state.combo += 1
        state.max_combo = max(state.max_combo, state.combo)
        delta = settings.exp_per_correct
    else:
        state.combo = 0
        delta = 0
    memory_store.save_gamification(state)
    return delta, state.combo


def apply_completion(state: GamificationState, accuracy: float, settings: Settings) -> tuple[int, list[str]]:
    """闯关完成结算：+exp_per_complete，徽章发放。返回 (exp_delta, 新徽章列表)。"""
    state.exp += settings.exp_per_complete
    state.completed_quizzes += 1
    if accuracy >= 1.0:
        state.perfect_quizzes += 1

    new_badges: list[str] = []
    owned = set(state.badges)

    def _grant(badge: str) -> None:
        if badge not in owned:
            owned.add(badge)
            new_badges.append(badge)

    if state.completed_quizzes == 1:
        _grant(Badge.FIRST_QUIZ)
    if state.max_combo >= 3:
        _grant(Badge.COMBO_3)
    if accuracy >= 1.0:
        _grant(Badge.PERFECT)
    if state.completed_quizzes >= 7:
        _grant(Badge.STREAK_7)

    state.badges = sorted(owned)
    memory_store.save_gamification(state)
    return settings.exp_per_complete, new_badges
