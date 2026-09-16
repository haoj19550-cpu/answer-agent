"""启动装配与可观测性测试：FAKE/真实模式切换、缺 Key 提示、/health 字段（离线）。"""

import pytest
from fastapi.testclient import TestClient
from langchain_core.runnables import RunnableLambda

from app.config import Settings
from app.llm.models import LLMConfigurationError
from app.main import build_chain_registry, create_app, llm_mode


def _fake_settings() -> Settings:
    return Settings(deepseek_api_key="", fake_llm=True)


class TestChainRegistry:
    def test_fake_mode_builds_fake_chains(self):
        reg = build_chain_registry(_fake_settings())
        assert isinstance(reg.extraction_chain, RunnableLambda)
        assert isinstance(reg.quiz_chain, RunnableLambda)
        assert isinstance(reg.report_chain, RunnableLambda)

    def test_real_mode_builds_lcel_chains(self):
        reg = build_chain_registry(Settings(deepseek_api_key="sk-test", fake_llm=False))
        assert not isinstance(reg.quiz_chain, RunnableLambda)
        assert hasattr(reg.quiz_chain, "ainvoke")

    def test_real_mode_without_key_raises_actionable_error(self):
        with pytest.raises(LLMConfigurationError) as exc:
            build_chain_registry(Settings(deepseek_api_key="", fake_llm=False))
        assert "DEEPSEEK_API_KEY" in str(exc.value)


class TestLLMMode:
    def test_mode_labels(self):
        assert llm_mode(_fake_settings()) == "fake"
        assert llm_mode(Settings(deepseek_api_key="sk-test", fake_llm=False)) == "real"


class TestHealth:
    def test_health_reports_llm_wiring(self):
        settings = _fake_settings()
        app = create_app(settings=settings, chains=build_chain_registry(settings))
        with TestClient(app) as client:
            body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["llm_mode"] == "fake"
        assert body["model"] == settings.deepseek_model
        assert body["fallback"] is False
        assert body["grounded_strict"] is True

    def test_health_reports_real_mode_and_fallback(self):
        settings = Settings(
            deepseek_api_key="sk-test", fallback_api_key="sk-qwen", fake_llm=False
        )
        app = create_app(settings=settings, chains=build_chain_registry(settings))
        with TestClient(app) as client:
            body = client.get("/health").json()
        assert body["llm_mode"] == "real"
        assert body["fallback"] is True
