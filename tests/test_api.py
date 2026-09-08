import time

from fastapi.testclient import TestClient
from sentinel import api
from sentinel.store import Store


def test_api_requires_distinct_roles_and_human_review(monkeypatch, tmp_path):
    api.store = Store(tmp_path / "api.db")

    async def fake_investigate(case_id, scenario):
        return {
            "adjustment_minor": 1500,
            "currency": "INR",
            "eligible": True,
            "expires_at": time.time() + 300,
            "policy_version": "test",
            "evidence": {"payment_id": "PAY-TEST", "reference": "test"},
            "analysis": "synthetic test",
            "action": "record_simulated_adjustment",
            "timeline": [],
        }

    monkeypatch.setattr("sentinel.workflow.investigate", fake_investigate)
    client = TestClient(api.app)
    operator = {"Authorization": "Bearer demo-operator"}
    reviewer = {"Authorization": "Bearer demo-reviewer"}

    page = client.get("/")
    assert page.status_code == 200
    assert "Settlement Sentinel" in page.text
    assert "Approve simulation" in page.text
    missing_auth = client.get("/api/cases")
    assert missing_auth.status_code == 401
    assert missing_auth.headers["www-authenticate"] == "Bearer"
    assert client.get("/api/cases", headers=reviewer).status_code == 403
    created = client.post("/api/cases", headers=operator, json={"scenario": "fee_mismatch"})
    assert created.status_code == 201
    case = created.json()
    assert case["state"] == "awaiting_approval"
    assert client.post(f"/api/cases/{case['id']}/decision", headers=operator, json={"version": case["version"], "decision": "approve"}).status_code == 403

    approved = client.post(f"/api/cases/{case['id']}/decision", headers=reviewer, json={"version": case["version"], "decision": "approve"})
    assert approved.status_code == 200
    assert approved.json()["state"] == "executed_simulation"
    assert approved.json()["ledger_entries"] == 1


def test_failure_is_persisted_without_exposing_upstream_detail(monkeypatch, tmp_path):
    api.store = Store(tmp_path / "failed.db")

    async def fail_investigation(case_id, scenario):
        raise RuntimeError("secret-key=must-not-leak")

    monkeypatch.setattr("sentinel.workflow.investigate", fail_investigation)
    client = TestClient(api.app)
    operator = {"Authorization": "Bearer demo-operator"}

    response = client.post("/api/cases", headers=operator, json={"scenario": "duplicate"})

    assert response.status_code == 502
    assert "must-not-leak" not in response.text
    case_id = response.json()["detail"]["case_id"]
    case = client.get(f"/api/cases/{case_id}", headers=operator).json()
    assert case["state"] == "failed"
    assert case["ledger_entries"] == 0


def test_security_headers_are_applied(tmp_path):
    api.store = Store(tmp_path / "headers.db")
    client = TestClient(api.app)

    response = client.get("/health")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
