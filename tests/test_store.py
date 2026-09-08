import pytest
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
