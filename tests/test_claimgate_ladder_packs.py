"""Nine-pack ladder validation is generated from the live auditor."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate.ladder_packs import (
    PAPER_TABLE3_LEVELS,
    audit_ladder_packs,
    ladder_validation_payload,
)
from codontrace.genesis.text_digest import sha256_text_file


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


def test_committed_ladder_validation_matches_live_auditor() -> None:
    committed = json.loads(
        Path("docs/claimgate/ladder_validation.json").read_text(encoding="utf-8")
    )
    live = ladder_validation_payload()
    assert committed["digest"] == live["digest"]
    assert committed["n_packs"] == 9
    assert [row["auditor_level"] for row in committed["rows"]] == [
        row["auditor_level"] for row in live["rows"]
    ]


def test_text_digest_normalizes_crlf() -> None:
    path = Path("docs/claimgate/README.md")
    lf = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    assert sha256_text_file(path) == __import__("hashlib").sha256(lf).hexdigest()
