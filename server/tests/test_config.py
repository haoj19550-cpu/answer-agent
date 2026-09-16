"""配置层测试：真实模型默认值与关键开关（离线）。

对应方案 3.4 / 6.2：模型名以 DeepSeek 官方文档为准（deepseek-chat 已停用）。
"""

from app.config import Settings


def _settings(**kw) -> Settings:
    return Settings(deepseek_api_key="sk-test", **kw)


class TestRealModelDefaults:
    def test_default_model_is_current_deepseek(self):
        assert _settings().deepseek_model == "deepseek-v4-flash"

    def test_default_base_url(self):
        assert _settings().deepseek_base_url == "https://api.deepseek.com/v1"

    def test_structured_output_uses_non_thinking_mode(self):
        # 推理/思考模式与强制 Schema 冲突（方案 3.4 注）
        assert _settings().deepseek_disable_thinking is True


class TestSwitches:
    def test_grounded_strict_default_on(self):
        assert _settings().grounded_strict is True

    def test_conservative_retry_defaults(self):
        s = _settings()
        assert s.chain_max_attempts == 2
        assert s.validate_retry_per_step == 1

    def test_llm_timeout_default(self):
        assert _settings().llm_timeout == 60


class TestEnvOverride:
    def test_env_overrides_model_and_switch(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        monkeypatch.setenv("GROUNDED_STRICT", "0")
        monkeypatch.setenv("CHAIN_MAX_ATTEMPTS", "3")
        s = _settings()
        assert s.deepseek_model == "deepseek-v4-pro"
        assert s.grounded_strict is False
        assert s.chain_max_attempts == 3

    def test_env_overrides_base_url(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://proxy.example.com/v1")
        assert _settings().deepseek_base_url == "https://proxy.example.com/v1"


class TestFakeModeDefault:
    def test_fake_flag_readable(self):
        assert _settings(fake_llm=True).fake_llm is True
        assert _settings(fake_llm=False).fake_llm is False
