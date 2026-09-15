"""报告 API：规则计算 + 链3 文案 + 模板降级，报告永不 500。"""

from fastapi import APIRouter, Depends, Request

from app.api.deps import ChainRegistry, get_chains, get_owned_quiz
from app.schemas.api import ApiError, ReportRequest
from app.schemas.quiz import Report
from app.services import gamification_service
from app.services.report_service import build_report
from app.stores import memory_store

router = APIRouter(tags=["reports"])


@router.post("/reports", status_code=201, response_model=Report)
async def create_report(
    req: ReportRequest, request: Request, chains: ChainRegistry = Depends(get_chains)
):
    settings = request.app.state.settings
    quiz = get_owned_quiz(req.quiz_id, req.client_id)

    existing = memory_store.get_report(req.quiz_id)
    if existing is not None:
        return existing

    records = memory_store.get_answers(req.quiz_id)
    total = len(quiz.quiz_set.questions)
    if len(records) < total:
        raise ApiError(
            code="QUIZ_NOT_FINISHED",
            message=f"还有 {total - len(records)} 题未完成，答完再生成报告吧",
            status_code=409,
            detail={"answered": len(records), "total": total},
        )

    report = await build_report(quiz, records, chains.report_chain, session_id=req.quiz_id)

    # 闯关完成结算：经验 + 徽章
    state = gamification_service.ensure_state(req.client_id)
    correct_count = sum(1 for r in records if r.correct)
    exp_delta, new_badges = gamification_service.apply_completion(state, report.accuracy, settings)
    report.exp_gained = correct_count * settings.exp_per_correct + exp_delta
    report.badges = new_badges

    memory_store.save_report(report)
    return report


@router.get("/reports/{quiz_id}", response_model=Report)
async def get_report(quiz_id: str, client_id: str):
    get_owned_quiz(quiz_id, client_id)
    report = memory_store.get_report(quiz_id)
    if report is None:
        raise ApiError(code="REPORT_NOT_FOUND", message="报告不存在，请先生成", status_code=404)
    return report
