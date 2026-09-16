"""接口级测试：TestClient 全链路（材料 → 提取 → 生成 → 判分 → 报告 → 游戏化）。

链用 FakeStructuredChatModel 注入，离线可跑。
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.deps import ChainRegistry
from app.chains.quiz import build_extraction_chain, build_quiz_chain, build_report_chain
from app.config import Settings
from app.main import create_app
from tests.conftest import SAMPLE_MATERIAL

CLIENT_ID = "test-client-001"


@pytest.fixture
def settings() -> Settings:
    return Settings(deepseek_api_key="", monthly_quota=3, rate_limit_per_minute=1000)


@pytest.fixture
def chains(fake_llm_factory, sample_extraction, sample_quiz_set, sample_report_content):
    return ChainRegistry(
        extraction_chain=build_extraction_chain(fake_llm_factory([sample_extraction]), max_attempts=1),
        quiz_chain=build_quiz_chain(fake_llm_factory([sample_quiz_set]), max_attempts=1),
        report_chain=build_report_chain(fake_llm_factory([sample_report_content]), max_attempts=1),
    )


@pytest.fixture
def client(settings, chains):
    app = create_app(settings=settings, chains=chains)
    with TestClient(app) as c:
        yield c


def parse_sse(text: str) -> list[tuple[str, str]]:
    """解析 SSE 帧为 (event, data) 列表。"""
    events = []
    event, data_lines = None, []
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line == "" and event is not None:
            events.append((event, "\n".join(data_lines)))
            event, data_lines = None, []
    if event is not None:
        events.append((event, "\n".join(data_lines)))
    return events


def create_material(client) -> str:
    resp = client.post(
        "/api/v1/materials",
        json={"client_id": CLIENT_ID, "source_type": "text", "text": SAMPLE_MATERIAL},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["material_id"]


def run_generate(client, material_id: str) -> dict:
    resp = client.post(
        "/api/v1/quizzes/generate",
        json={"client_id": CLIENT_ID, "material_id": material_id, "count": 5},
    )
    assert resp.status_code == 200, resp.text
    events = parse_sse(resp.text)
    stages = [json.loads(d)["stage"] for e, d in events if e == "stage"]
    assert stages == ["generating", "validating"]
    quiz_events = [d for e, d in events if e == "quiz"]
    assert len(quiz_events) == 1
    assert any(e == "done" for e, _ in events)
    return json.loads(quiz_events[0])


# ---------- 健康检查与材料 ----------


class TestHealthAndMaterials:
    def test_health(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["llm_mode"] in ("fake", "real")
        assert body["model"]
        assert body["fallback"] is False

    def test_create_material(self, client):
        resp = client.post(
            "/api/v1/materials",
            json={"client_id": CLIENT_ID, "source_type": "text", "text": SAMPLE_MATERIAL},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["material_id"].startswith("mat_")
        assert body["char_count"] > 0

    def test_material_too_short(self, client):
        resp = client.post(
            "/api/v1/materials", json={"client_id": CLIENT_ID, "source_type": "text", "text": "短"}
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "MATERIAL_TOO_SHORT"

    def test_upload_rejects_non_pdf(self, client):
        resp = client.post(
            "/api/v1/materials/upload",
            data={"client_id": CLIENT_ID},
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "UNSUPPORTED_FILE_TYPE"


# ---------- 第一段 SSE：知识点提取 ----------


class TestExtract:
    def test_extract_event_sequence(self, client):
        material_id = create_material(client)
        resp = client.post(
            "/api/v1/quizzes/extract",
            json={"client_id": CLIENT_ID, "material_id": material_id},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = parse_sse(resp.text)
        assert events[0][0] == "stage"
        assert json.loads(events[0][1])["stage"] == "extracting"
        knowledge = [d for e, d in events if e == "knowledge"]
        assert len(knowledge) == 1
        payload = json.loads(knowledge[0])
        assert payload["topic"] == "Redis 缓存机制"
        assert len(payload["knowledge_points"]) == 4
        assert events[-1][0] == "done"

    def test_extract_material_not_found(self, client):
        resp = client.post(
            "/api/v1/quizzes/extract",
            json={"client_id": CLIENT_ID, "material_id": "mat_nonexistent"},
        )
        events = parse_sse(resp.text)
        assert any(e == "error" and json.loads(d)["code"] == "MATERIAL_NOT_FOUND" for e, d in events)


# ---------- 第二段 SSE：题目生成 ----------


class TestGenerate:
    def test_generate_event_sequence_and_no_answers_leaked(self, client):
        material_id = create_material(client)
        quiz_payload = run_generate(client, material_id)
        assert quiz_payload["quiz_id"].startswith("quiz_")
        assert len(quiz_payload["questions"]) == 5
        for q in quiz_payload["questions"]:
            assert "correct_answer" not in q  # 答案不出后端
            assert "explanation" not in q
            assert "source_excerpt" not in q
        assert quiz_payload["gamification"]["quota_remaining"] == 2  # 成功扣 1 次

    def test_get_quiz(self, client):
        material_id = create_material(client)
        quiz_payload = run_generate(client, material_id)
        resp = client.get(f"/api/v1/quizzes/{quiz_payload['quiz_id']}", params={"client_id": CLIENT_ID})
        assert resp.status_code == 200
        assert len(resp.json()["questions"]) == 5

    def test_get_quiz_wrong_client(self, client):
        material_id = create_material(client)
        quiz_payload = run_generate(client, material_id)
        resp = client.get(f"/api/v1/quizzes/{quiz_payload['quiz_id']}", params={"client_id": "other"})
        assert resp.status_code == 404
        assert resp.json()["code"] == "SESSION_EXPIRED"

    def test_quota_exceeded(self, client):
        material_id = create_material(client)
        for _ in range(3):  # monthly_quota = 3
            run_generate(client, material_id)
        resp = client.post(
            "/api/v1/quizzes/generate",
            json={"client_id": CLIENT_ID, "material_id": material_id, "count": 5},
        )
        assert resp.status_code == 429
        assert resp.json()["code"] == "QUOTA_EXCEEDED"


class TestGenerateFailure:
    @pytest.fixture
    def failing_chains(self, fake_llm_factory, sample_extraction, sample_report_content, sample_quiz_set):
        bad = sample_quiz_set.model_copy(
            update={
                "questions": [
                    q.model_copy(update={"source_excerpt": "不存在的幻觉内容xyz"})
                    for q in sample_quiz_set.questions
                ]
            }
        )
        return ChainRegistry(
            extraction_chain=build_extraction_chain(fake_llm_factory([sample_extraction]), max_attempts=1),
            quiz_chain=build_quiz_chain(fake_llm_factory([bad]), max_attempts=1),
            report_chain=build_report_chain(fake_llm_factory([sample_report_content]), max_attempts=1),
        )

    @pytest.fixture
    def failing_client(self, settings, failing_chains):
        app = create_app(settings=settings, chains=failing_chains)
        with TestClient(app) as c:
            yield c

    def test_generation_failed_error_event_and_no_quota_deducted(self, failing_client):
        material_id = create_material(failing_client)
        resp = failing_client.post(
            "/api/v1/quizzes/generate",
            json={"client_id": CLIENT_ID, "material_id": material_id, "count": 5},
        )
        events = parse_sse(resp.text)
        errors = [json.loads(d) for e, d in events if e == "error"]
        assert errors and errors[0]["code"] == "QUIZ_GENERATION_FAILED"
        # 失败不扣额度
        quota = failing_client.get("/api/v1/gamification/quota", params={"client_id": CLIENT_ID}).json()
        assert quota["used"] == 0


# ---------- 判分 ----------


class TestAnswers:
    def test_answer_flow_and_idempotency(self, client):
        material_id = create_material(client)
        quiz_payload = run_generate(client, material_id)
        quiz_id = quiz_payload["quiz_id"]

        resp = client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"client_id": CLIENT_ID, "question_index": 0, "user_answer": 0, "elapsed_ms": 8000},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["correct"] is True
        assert body["correct_answer"] == 0
        assert body["explanation"]
        assert body["knowledge_point"] == "缓存穿透"
        assert body["source_excerpt"]
        assert body["exp_delta"] == 20
        assert body["combo"] == 1
        assert body["progress"] == {"answered": 1, "total": 5}

        # 幂等：同题重复提交返回首次结果，不重复加经验
        resp2 = client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"client_id": CLIENT_ID, "question_index": 0, "user_answer": 1, "elapsed_ms": 100},
        )
        body2 = resp2.json()
        assert body2["correct"] is True  # 仍是首次结果
        assert body2["exp_delta"] == 0

    def test_wrong_answer_resets_combo(self, client):
        material_id = create_material(client)
        quiz_id = run_generate(client, material_id)["quiz_id"]
        client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"client_id": CLIENT_ID, "question_index": 0, "user_answer": 0, "elapsed_ms": 5000},
        )
        resp = client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"client_id": CLIENT_ID, "question_index": 1, "user_answer": 0, "elapsed_ms": 5000},
        )
        body = resp.json()
        assert body["correct"] is False
        assert body["combo"] == 0
        assert body["exp_delta"] == 0

    def test_answer_invalid_index(self, client):
        material_id = create_material(client)
        quiz_id = run_generate(client, material_id)["quiz_id"]
        resp = client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"client_id": CLIENT_ID, "question_index": 99, "user_answer": 0},
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "QUESTION_NOT_FOUND"


# ---------- 报告 ----------


def _finish_quiz(client, quiz_id: str, answers: dict[int, int]):
    for index, answer in answers.items():
        client.post(
            f"/api/v1/quizzes/{quiz_id}/answers",
            json={"client_id": CLIENT_ID, "question_index": index, "user_answer": answer, "elapsed_ms": 8000},
        )


class TestReports:
    def test_full_loop_report(self, client):
        material_id = create_material(client)
        quiz_id = run_generate(client, material_id)["quiz_id"]
        # 标准答案：0,1,0,0,1（conftest 样例），错第 2、5 题
        _finish_quiz(client, quiz_id, {0: 0, 1: 0, 2: 0, 3: 0, 4: 0})

        resp = client.post("/api/v1/reports", json={"client_id": CLIENT_ID, "quiz_id": quiz_id})
        assert resp.status_code == 201, resp.text
        report = resp.json()
        assert report["score"] == 60
        assert report["accuracy"] == 0.6
        assert report["ai_generated"] is True
        assert len(report["wrong_questions"]) == 2
        assert report["mastery_levels"]["缓存击穿"] == "weak"
        assert report["exp_gained"] == 3 * 20 + 40
        assert "first_quiz" in report["badges"]

        # 重复生成返回同一份
        resp2 = client.post("/api/v1/reports", json={"client_id": CLIENT_ID, "quiz_id": quiz_id})
        assert resp2.json()["quiz_id"] == quiz_id

        # GET 已生成报告
        resp3 = client.get(f"/api/v1/reports/{quiz_id}", params={"client_id": CLIENT_ID})
        assert resp3.status_code == 200

    def test_report_requires_all_answered(self, client):
        material_id = create_material(client)
        quiz_id = run_generate(client, material_id)["quiz_id"]
        _finish_quiz(client, quiz_id, {0: 0, 1: 1})
        resp = client.post("/api/v1/reports", json={"client_id": CLIENT_ID, "quiz_id": quiz_id})
        assert resp.status_code == 409
        assert resp.json()["code"] == "QUIZ_NOT_FINISHED"

    def test_report_not_found(self, client):
        material_id = create_material(client)
        quiz_id = run_generate(client, material_id)["quiz_id"]
        resp = client.get(f"/api/v1/reports/{quiz_id}", params={"client_id": CLIENT_ID})
        assert resp.status_code == 404
        assert resp.json()["code"] == "REPORT_NOT_FOUND"


# ---------- 游戏化接口 ----------


class TestGamificationApi:
    def test_state_and_quota(self, client):
        material_id = create_material(client)
        quiz_id = run_generate(client, material_id)["quiz_id"]
        _finish_quiz(client, quiz_id, {i: 0 for i in range(5)})
        client.post("/api/v1/reports", json={"client_id": CLIENT_ID, "quiz_id": quiz_id})

        state = client.get("/api/v1/gamification/state", params={"client_id": CLIENT_ID}).json()
        assert state["exp"] == 3 * 20 + 40
        assert state["completed_quizzes"] == 1
        assert "first_quiz" in state["badges"]
        assert state["quota_used"] == 1
        assert state["quota_remaining"] == 2

        quota = client.get("/api/v1/gamification/quota", params={"client_id": CLIENT_ID}).json()
        assert quota == {"monthly_quota": 3, "used": 1, "remaining": 2}
