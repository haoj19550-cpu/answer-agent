"""FastAPI 入口：lifespan 装配链、路由挂载、统一错误、限频中间件（方案 6.8 / 8）。"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import gamification, materials, quiz, reports
from app.api.deps import ChainRegistry
from app.chains.quiz import build_extraction_chain, build_quiz_chain, build_report_chain
from app.config import Settings, get_settings
from app.llm.models import LLMConfigurationError, get_fallback_llm, get_primary_llm
from app.schemas.api import ApiError, ErrorResponse
from app.stores import memory_store

logger = structlog.get_logger(__name__)


def llm_mode(settings: Settings) -> str:
    """当前模型装配模式：fake（内置样例）/ real（DeepSeek）。"""
    return "fake" if settings.fake_llm else "real"


def build_chain_registry(settings: Settings) -> ChainRegistry:
    """链装配：FAKE_LLM 模式用内置样例；否则 ChatDeepSeek 主 + 通义备。"""
    if settings.fake_llm:
        from app.llm.fake import make_fake_chains

        extraction_chain, quiz_chain, report_chain = make_fake_chains()
        return ChainRegistry(
            extraction_chain=extraction_chain,
            quiz_chain=quiz_chain,
            report_chain=report_chain,
        )
    if not settings.deepseek_api_key:
        raise LLMConfigurationError(
            "未配置 DEEPSEEK_API_KEY：请在 server/.env 中填入 DeepSeek API Key，"
            "或设置 FAKE_LLM=1 使用内置样例模式"
        )
    primary = get_primary_llm(settings)
    fallback = get_fallback_llm(settings)
    return ChainRegistry(
        extraction_chain=build_extraction_chain(primary, fallback, settings.chain_max_attempts),
        quiz_chain=build_quiz_chain(primary, fallback, settings.chain_max_attempts),
        report_chain=build_report_chain(primary, fallback, settings.chain_max_attempts),
    )


class RateLimitMiddleware:
    """最低限度限频：单 IP 每分钟 N 次（内存滑动窗口）。"""

    def __init__(self, app, limit_per_minute: int = 10):
        self.app = app
        self.limit = limit_per_minute
        self.hits: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return
        client = scope.get("client") or ("unknown", 0)
        now = time.monotonic()
        window = [t for t in self.hits[client[0]] if now - t < 60]
        if len(window) >= self.limit:
            response = JSONResponse(
                status_code=429,
                content=ErrorResponse(
                    code="RATE_LIMITED", message="服务繁忙，请稍后再试"
                ).model_dump(),
            )
            await response(scope, receive, send)
            return
        window.append(now)
        self.hits[client[0]] = window
        await self.app(scope, receive, send)


def create_app(settings: Settings | None = None, chains: ChainRegistry | None = None) -> FastAPI:
    settings = settings or get_settings()
    memory_store.configure(ttl=settings.store_ttl, gamification_ttl=settings.gamification_ttl)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.chains = chains or build_chain_registry(settings)
        logger.info(
            "app_started",
            llm_mode=llm_mode(settings),
            model=settings.deepseek_model,
            base_url=settings.deepseek_base_url,
            fallback=bool(settings.fallback_api_key),
            grounded_strict=settings.grounded_strict,
        )
        yield

    app = FastAPI(title="AI 知识闯关学习平台", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.code, message=exc.message, detail=exc.detail).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(code="INTERNAL_ERROR", message="服务内部错误，请稍后再试").model_dump(),
        )

    app.include_router(materials.router, prefix="/api/v1")
    app.include_router(quiz.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(gamification.router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict:
        """健康检查 + 模型装配可观测（mode/model/fallback/开关）。"""
        return {
            "status": "ok",
            "llm_mode": llm_mode(settings),
            "model": settings.deepseek_model,
            "base_url": settings.deepseek_base_url,
            "fallback": bool(settings.fallback_api_key),
            "grounded_strict": settings.grounded_strict,
            "fake_llm": settings.fake_llm,
        }

    return app


app = create_app()
