"""DeepSeek 连通性自检脚本（真实 API，需 DEEPSEEK_API_KEY）。

用法（在 server/ 目录下）：
    .venv\\Scripts\\python scripts/check_deepseek.py

检查三步：
  1. 配置体检：模式（fake/real）、Key 脱敏、模型名、Base URL
  2. GET /models：列出账号可用模型（验证 Key 有效 + 模型名是否存在）
  3. 结构化输出：跑一次知识点提取链，验证 with_structured_output 可用并统计用量

失败时按 401 / 404 / 429 / 超时 / 连接错误 分类给出处理建议。
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from langchain_core.callbacks import UsageMetadataCallbackHandler  # noqa: E402
from openai import (  # noqa: E402
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

from app.chains.quiz import build_extraction_chain  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.llm.models import LLMConfigurationError, get_fallback_llm, get_primary_llm  # noqa: E402
from app.schemas.quiz import KnowledgeExtraction  # noqa: E402

SAMPLE = (
    "Redis 缓存三大问题：缓存穿透是指查询数据库中根本不存在的数据，缓存和数据库都miss，"
    "可用布隆过滤器拦截非法key或空值缓存解决；缓存击穿是热点key过期瞬间大量并发打到数据库，"
    "用互斥锁或逻辑过期解决；缓存雪崩是大量key同时过期或实例宕机，用随机过期时间、"
    "高可用集群与降级熔断解决。"
)


def mask(key: str) -> str:
    if not key:
        return "<空>"
    return f"{key[:6]}***{key[-4:]}（长度 {len(key)}）"


def check_settings() -> bool:
    s = get_settings()
    print("== 1/3 配置体检 ==")
    print(f"  模式        : {'FAKE（内置样例，不会调用 DeepSeek）' if s.fake_llm else 'REAL（真实 DeepSeek）'}")
    print(f"  API Key     : {mask(s.deepseek_api_key)}")
    print(f"  模型        : {s.deepseek_model}")
    print(f"  Base URL    : {s.deepseek_base_url}")
    print(f"  超时/重试   : {s.llm_timeout}s / {s.llm_max_retries} 次")
    print(f"  链级重试    : {s.chain_max_attempts}（每档 {s.validate_retry_per_step} 次）")
    print(f"  回退模型    : {'已配置 ' + s.fallback_model if s.fallback_api_key else '未配置'}")
    print(f"  Grounded    : {'严格（摘录不匹配即判失败）' if s.grounded_strict else '宽松（仅告警）'}")
    if s.fake_llm:
        print("\n[提示] FAKE_LLM=1，本脚本只做配置体检。真实联调请在 .env 设 FAKE_LLM=0")
        return False
    if not s.deepseek_api_key:
        print("\n[错误] FAKE_LLM=0 但未配置 DEEPSEEK_API_KEY，请在 server/.env 中填写")
        return False
    return True


def check_models() -> list[str]:
    """列出账号可用模型；失败返回空列表（不阻断，第 3 步会实测）。"""
    s = get_settings()
    print("\n== 2/3 查询可用模型 ==")
    url = f"{s.deepseek_base_url.rstrip('/')}/models"
    try:
        resp = httpx.get(
            url, headers={"Authorization": f"Bearer {s.deepseek_api_key}"}, timeout=15
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        print(f"  [失败] HTTP {code}: {exc.response.text[:300]}")
        if code == 401:
            print("  → API Key 无效或已失效，请到 DeepSeek 平台重新生成并写入 .env")
        elif code == 429:
            print("  → 触发限流，稍后重试")
        return []
    except httpx.HTTPError as exc:
        print(f"  [失败] 网络错误：{exc}")
        print("  → 检查服务器能否访问 api.deepseek.com（代理/防火墙）")
        return []

    models = [m.get("id", "") for m in resp.json().get("data", [])]
    print(f"  可用模型：{models}")
    if s.deepseek_model in models:
        print(f"  [通过] {s.deepseek_model} 可用")
    else:
        print(f"  [警告] {s.deepseek_model} 不在列表中（列表可能不完整，第 3 步会实测）")
    return models


async def check_structured_output(available_models: list[str]) -> bool:
    s = get_settings()
    print("\n== 3/3 结构化输出（知识点提取链）==")
    try:
        primary = get_primary_llm(s)
        fallback = get_fallback_llm(s)
    except LLMConfigurationError as exc:
        print(f"  [失败] {exc}")
        return False

    chain = build_extraction_chain(primary, fallback, s.chain_max_attempts)
    cb = UsageMetadataCallbackHandler()
    started = time.perf_counter()
    try:
        result = await chain.ainvoke({"material": SAMPLE}, config={"callbacks": [cb]})
    except AuthenticationError:
        print("  [失败] 401：API Key 无效")
        return False
    except NotFoundError:
        print(f"  [失败] 404：模型 {s.deepseek_model} 不存在或账号无权限")
        if available_models:
            print(f"  → 请把 .env 的 DEEPSEEK_MODEL 改为：{' / '.join(available_models)}")
        return False
    except RateLimitError:
        print("  [失败] 429：触发限流/余额不足，请稍后重试或充值")
        return False
    except APITimeoutError:
        print(f"  [失败] 请求超时（>{s.llm_timeout}s），可调大 LLM_TIMEOUT")
        return False
    except APIConnectionError as exc:
        print(f"  [失败] 连接错误：{exc}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  [失败] {type(exc).__name__}: {exc}")
        return False
    elapsed = time.perf_counter() - started

    assert isinstance(result, KnowledgeExtraction)
    print(f"  主题      : {result.topic}")
    print(f"  知识点    : {len(result.knowledge_points)} 个 -> "
          + "、".join(kp.name for kp in result.knowledge_points[:6]))
    print(f"  耗时      : {elapsed:.1f}s")
    print(f"  Token用量 : {cb.usage_metadata}")
    print("  [通过] with_structured_output 正常（DeepSeek 走 function calling 实现）")
    return True


async def check_fallback() -> bool:
    """备用模型（通义/OpenAI 兼容端点）自检：列模型 + 一次结构化输出。"""
    s = get_settings()
    print("\n== 4/4 备用模型（回退链）==")
    if not s.fallback_api_key:
        print("  未配置 FALLBACK_API_KEY：不装配回退（主模型故障时无兜底）")
        return True
    print(f"  模型     : {s.fallback_model}")
    print(f"  Base URL : {s.fallback_base_url}")
    try:
        resp = httpx.get(
            f"{s.fallback_base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {s.fallback_api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        models = [m.get("id", "") for m in resp.json().get("data", [])]
        print(f"  可用模型 : {models[:20]}")
        if models and s.fallback_model not in models:
            print(f"  [警告] {s.fallback_model} 不在列表中，请核对 FALLBACK_MODEL")
    except Exception as exc:  # noqa: BLE001
        print(f"  [跳过] /models 不可用：{type(exc).__name__}: {str(exc)[:150]}")

    try:
        llm = get_fallback_llm(s)
        structured = llm.with_structured_output(KnowledgeExtraction)
        started = time.perf_counter()
        result = await structured.ainvoke(
            [("system", "你是课程内容分析师，用中文提取知识点。"), ("human", SAMPLE)]
        )
        elapsed = time.perf_counter() - started
    except Exception as exc:  # noqa: BLE001
        print(f"  [失败] {type(exc).__name__}: {str(exc)[:250]}")
        print("  → 备用模型不可用：回退虽然装配，但主模型故障时会一起失败")
        return False
    print(f"  主题     : {result.topic}（{len(result.knowledge_points)} 个知识点，{elapsed:.1f}s）")
    print("  [通过] 备用模型可用，with_fallbacks 回退链生效")
    return True


async def main() -> int:
    if not check_settings():
        return 1
    models = check_models()
    ok = await check_structured_output(models)
    if ok:
        ok = await check_fallback()
    if ok:
        print("\n全部通过：后端已连通 DeepSeek，可启动服务 `FAKE_LLM=0 uvicorn app.main:app`")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
