"""游戏化模型：经验/连击/额度/徽章（内存存储，TTL 30 天）。"""

from datetime import date

from pydantic import BaseModel, Field


class Badge:
    FIRST_QUIZ = "first_quiz"  # 首次完成闯关
    COMBO_3 = "combo_3"  # 三连击
    PERFECT = "perfect"  # 满分
    STREAK_7 = "streak_7"  # 累计 7 次闯关

    ALL = {FIRST_QUIZ, COMBO_3, PERFECT, STREAK_7}


class GamificationState(BaseModel):
    client_id: str
    exp: int = 0
    combo: int = 0  # 当前连击（连续答对）
    max_combo: int = 0
    completed_quizzes: int = 0
    perfect_quizzes: int = 0
    badges: list[str] = Field(default_factory=list)
    quota_month: str = ""  # 额度所属月份 YYYY-MM
    quota_used: int = 0

    def roll_month(self, today: date | None = None) -> None:
        month = (today or date.today()).strftime("%Y-%m")
        if self.quota_month != month:
            self.quota_month = month
            self.quota_used = 0


class QuotaResponse(BaseModel):
    monthly_quota: int
    used: int
    remaining: int


class GamificationStateResponse(BaseModel):
    client_id: str
    exp: int
    combo: int
    max_combo: int
    completed_quizzes: int
    badges: list[str]
    monthly_quota: int
    quota_used: int
    quota_remaining: int
