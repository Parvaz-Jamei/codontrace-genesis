"""The closure files are measurements, not a repaired old pack.

The locked RQ-1 commit 6187ff4 is not in this repository. Seeds 5706–5708
were therefore run again on the current engine and labelled as such.
Seeds 21061–21063 now have raw. Neither set is allowed to flip a claim.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RQ1 = ROOT / "docs/experiments/2026-09-29/rq1_time_shift/confirmatory/closure_2026-10-03"
RQ3 = ROOT / "docs/experiments/2026-09-29/rq3_adaptation_route/closure_2026-10-03"


def test_rq1_closure_is_three_seeds_and_not_the_old_pack() -> None:
    for seed in (5706, 5707, 5708):
        rec = json.loads((RQ1 / f"seed_{seed}.json").read_text(encoding="utf-8"))
        assert rec["replaces_locked_pack"] is False
        assert rec["locked_commit_absent"] == "6187ff4"
        assert rec["hypothesis_supported"] is False
        assert rec["red_queen_proved"] is False
        assert rec["errors"] == []
        assert set(rec["regimes"]) == {"copassaged", "fixed"}
        for regime in rec["regimes"].values():
            assert set(regime["matrix"]) == {"past", "now", "future"}


def test_rq3_closure_has_raw_and_does_not_win() -> None:
    for seed in (21061, 21062, 21063):
        rec = json.loads((RQ3 / f"seed_{seed}.json").read_text(encoding="utf-8"))
        assert rec["replaces_quoted_table"] is False
        assert rec["hypothesis_supported"] is False
        assert rec["red_queen_proved"] is False
        assert set(rec["arms"]) == {"coevolve", "frozen", "shuffled_labels"}
        assert rec["arms"]["coevolve"]["common_share_last"] == 0.0
        assert rec["arms"]["coevolve"]["common_share_last"] <= rec["arms"]["frozen"]["common_share_last"]
