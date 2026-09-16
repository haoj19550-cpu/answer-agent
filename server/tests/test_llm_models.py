"""模型抽象层测试：ChatDeepSeek / 通义回退 的参数装配（离线，不发请求）。"""

import pytest

from app.config import Settings
from app.llm.models import LLMConfigurationError, get_fallback_llm, get_primary_llm


class TestPrimaryLLM:
    def test_missing_key_raises_configuration_error(self):
        with pytest.raises(LLMConfigurationError) as exc:
            get_primary_llm(Settings(deepseek_api_key=""))
        assert "DEEPSEEK_API_KEY" in str(exc.value)

    def test_params_wired_from_settings(self):
        s = Settings(
            deepseek_api_key="sk-test-key",
            deepseek_model="deepseek-v4-flash",
            deepseek_base_url="https://api.deepseek.com/v1",
            llm_timeout=42,
            llm_max_retries=1,
        )
        llm = get_primary_llm(s)
        assert llm.model_name == "deepseek-v4-flash"
        assert llm.api_base == "https://api.deepseek.com/v1"
        assert llm.request_timeout == 42
        assert llm.max_retries == 1
        assert llm.temperature == 0.3  # 出题求稳，低温
        assert llm.api_key.get_secret_value() == "sk-test-key"

    def test_custom_base_url_supported(self):
        s = Settings(
            deepseek_api_key="sk-test-key",
            deepseek_base_url="https://my-proxy.local/v1",
        )
        assert get_primary_llm(s).api_base == "https://my-proxy.local/v1"

    def test_thinking_disabled_for_structured_output(self):
        llm = get_primary_llm(Settings(deepseek_api_key="sk-test-key"))
        assert llm.extra_body == {"thinking": {"type": "disabled"}}

    def test_thinking_switch_off(self):
        llm = get_primary_llm(
            Settings(deepseek_api_key="sk-test-key", deepseek_disable_thinking=False)
        )
        assert llm.extra_body is None


class TestFallbackLLM:
    def test_none_without_key(self):
        assert get_fallback_llm(Settings(deepseek_api_key="k", fallback_api_key="")) is None

    def test_qwen_params_wired(self):
        s = Settings(
            deepseek_api_key="k",
            fallback_api_key="sk-qwen",
            fallback_model="qwen-plus",
            fallback_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            llm_timeout=33,
        )
        llm = get_fallback_llm(s)
        assert llm is not None
        assert llm.model_name == "qwen-plus"
        assert llm.openai_api_base == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert llm.request_timeout == 33
