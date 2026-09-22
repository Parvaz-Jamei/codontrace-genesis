"""Nine-pack ladder validation is generated from the live auditor."""

from __future__ import annotations

from codontrace.claimgate.ladder_packs import (
    PAPER_TABLE3_LEVELS,
    audit_ladder_packs,
    ladder_validation_payload,
)


def test_live_auditor_matches_paper_table3_levels() -> None:
    rows = audit_ladder_packs()
    assert len(rows) == 9
    by_id = {row["pack_id"]: row for row in rows}
    for pack_id, level in PAPER_TABLE3_LEVELS.items():
        assert by_id[pack_id]["auditor_level"] == level, pack_id


def test_validation_payload_is_canonical() -> None:
    payload = ladder_validation_payload()
    assert payload["schema"] == "claimgate_ladder_validation_v1"
    assert payload["n_packs"] == 9
    assert payload["not_a_population_error_rate"] is True
    assert payload["external_raters"] is False
    assert isinstance(payload["digest"], str) and len(payload["digest"]) == 64
