from pathlib import Path

from tools.audit_closure_evidence import inventory


def test_aggregate_closures_do_not_become_complete_raw_packs():
    result = inventory(Path(__file__).resolve().parents[2])
    assert len(result["records"]) == 6
    assert not result["claim_eligible"]
    for record in result["records"]:
        assert record["summary_present"]
        assert not record["raw_pack_complete"]
        assert record["record_role"] == "current_engine_aggregate_summary"
        assert not record["replaces_historical_raw"]
