import pytest
import time
from sentinel.store import Store


def proposed_case(id="case-1"):
    return {
        "id": id,
        "adjustment_minor": 1500,
        "currency": "INR",
        "eligible": True,
        "expires_at": 4_000_000_000,
        "action": "record_simulated_adjustment",
    }


def test_approval_is_atomic_and_idempotent(tmp_path):
    store = Store(tmp_path / "cases.db")
    store.create({"id": "case-1", "scenario": "fee_mismatch"})
    store.finish("case-1", proposed_case())
    version = store.get("case-1")["version"]

    executed = store.decide("case-1", version, "approve", "reviewer")

    assert executed["state"] == "executed_simulation"
    assert executed["ledger_entries"] == 1
    with pytest.raises(ValueError, match="Stale or already reviewed"):
        store.decide("case-1", version, "approve", "reviewer")
    assert store.get("case-1")["ledger_entries"] == 1


def test_rejection_never_writes_simulated_ledger(tmp_path):
    store = Store(tmp_path / "cases.db")
    store.create({"id": "case-2", "scenario": "duplicate"})
    store.finish("case-2", proposed_case("case-2"))

    result = store.decide("case-2", store.get("case-2")["version"], "reject", "reviewer")

    assert result["state"] == "rejected"
    assert result["ledger_entries"] == 0


def test_expired_proposal_is_closed_and_never_executed(tmp_path):
    store = Store(tmp_path / "cases.db")
    case = proposed_case("case-expired")
    case["expires_at"] = time.time() - 1
    store.create({"id": "case-expired", "scenario": "fee_mismatch"})
    store.finish("case-expired", case)

    with pytest.raises(ValueError, match="Proposal expired"):
        store.decide("case-expired", store.get("case-expired")["version"], "approve", "reviewer")

    expired = store.get("case-expired")
    assert expired["state"] == "expired"
    assert expired["ledger_entries"] == 0
    assert expired["audit"][-1]["event"] == "expired"
