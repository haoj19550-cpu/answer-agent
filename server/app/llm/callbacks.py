"""Token 用量统计（方案 6.7）。

每条链调用携带独立 UsageMetadataCallbackHandler，按 quiz_id 聚合到内存；
单局预算超阈值打日志告警。
"""

import threading

import structlog
from langchain_core.callbacks import UsageMetadataCallbackHandler

logger = structlog.get_logger(__name__)

# 单局预算（经验值，按实测校准）
SINGLE_SESSION_TOKEN_BUDGET = 8000

_lock = threading.Lock()
_usage_by_session: dict[str, dict[str, dict[str, int]]] = {}


def new_usage_callback() -> UsageMetadataCallbackHandler:
    return UsageMetadataCallbackHandler()


def record_usage(session_id: str, usage_cb: UsageMetadataCallbackHandler) -> None:
    """把一次链调用的用量聚合到会话，并做预算告警。"""
    with _lock:
        bucket = _usage_by_session.setdefault(session_id, {})
        for model, usage in usage_cb.usage_metadata.items():
            slot = bucket.setdefault(model, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
            slot["input_tokens"] += usage.get("input_tokens", 0)
            slot["output_tokens"] += usage.get("output_tokens", 0)
            slot["total_tokens"] += usage.get("total_tokens", 0)
        total = sum(s["total_tokens"] for s in bucket.values())
    if total > SINGLE_SESSION_TOKEN_BUDGET:
        logger.warning("token_budget_exceeded", session_id=session_id, total_tokens=total)


def get_session_usage(session_id: str) -> dict[str, dict[str, int]]:
    with _lock:
        return {m: dict(u) for m, u in _usage_by_session.get(session_id, {}).items()}


def clear_usage() -> None:
    with _lock:
        _usage_by_session.clear()
