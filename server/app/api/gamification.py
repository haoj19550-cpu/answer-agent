"""游戏化 API：状态与额度查询（client_id 维度）。"""

from fastapi import APIRouter, Request

from app.schemas.gamification import GamificationStateResponse, QuotaResponse
from app.services import gamification_service

router = APIRouter(tags=["gamification"])


@router.get("/gamification/state", response_model=GamificationStateResponse)
async def get_state(client_id: str, request: Request):
    settings = request.app.state.settings
    state = gamification_service.ensure_state(client_id)
    return GamificationStateResponse(
        client_id=client_id,
        exp=state.exp,
        combo=state.combo,
        max_combo=state.max_combo,
        completed_quizzes=state.completed_quizzes,
        badges=state.badges,
        monthly_quota=settings.monthly_quota,
        quota_used=state.quota_used,
        quota_remaining=max(0, settings.monthly_quota - state.quota_used),
    )


@router.get("/gamification/quota", response_model=QuotaResponse)
async def get_quota(client_id: str, request: Request):
    settings = request.app.state.settings
    state = gamification_service.ensure_state(client_id)
    return QuotaResponse(
        monthly_quota=settings.monthly_quota,
        used=state.quota_used,
        remaining=max(0, settings.monthly_quota - state.quota_used),
    )
