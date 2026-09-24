"""Phase 10 unit: refuse-safe genesis export JSON/CSV."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_export import (
    SCHEMA_SUMMARY,
    meter_snapshot_rows,
    metric_summary_row,
    world_summary_row,
    write_csv_rows,
    write_json,
)
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld


@pytest.mark.unit
def test_metric_summary_and_world_export_honesty(tmp_path: Path) -> None:
    world = HostParasiteWorld(
        HostParasiteProfile(profile_id="export_world_u", seed=0, coupling_amount=0.2)
    )
    world.run(1)
    summary = world.metric_summary(claim_role="smoke")
    row = metric_summary_row(summary)
    assert row["schema_version"] == SCHEMA_SUMMARY
    assert row["digest"] == summary.digest
    assert row["red_queen_proved"] is False
    assert row["intervention_supported"] is False
    world_row = world_summary_row(world.summary(), run_id="w0")
    assert world_row["world_digest"] == world.summary()["world_digest"]
    assert world_row["red_queen_proved"] is False
    path = tmp_path / "summary.csv"
    cols = write_csv_rows([row], path)
    assert "digest" in cols
    assert "red_queen_proved" in cols
    text = path.read_text(encoding="utf-8")
    assert "False" in text or "false" in text.casefold()


@pytest.mark.unit
def test_export_refuses_proved_true_and_clinical_column() -> None:
    world = HostParasiteWorld(HostParasiteProfile(profile_id="export_refuse", seed=1))
    world.run(1)
    snap = world.meter.snapshot()
    rows = meter_snapshot_rows(snap, run_id="ok")
    bad = dict(rows[0])
    bad["red_queen_proved"] = True
    with pytest.raises(ConfigurationError, match="refuses"):
        write_csv_rows([bad], Path("/tmp/should_not_write_phase10.csv"))
    with pytest.raises(ConfigurationError, match="refused export fragment|banned"):
        write_csv_rows(
            [rows[0]],
            Path("/tmp/should_not_write_phase10b.csv"),
            fieldnames=list(rows[0].keys()) + ["clinical_claim"],
        )


@pytest.mark.unit
def test_write_json_stable(tmp_path: Path) -> None:
    world = HostParasiteWorld(HostParasiteProfile(profile_id="export_json", seed=2))
    payload = world.summary()
    d1 = write_json(payload, tmp_path / "a.json")
    d2 = write_json(payload, tmp_path / "b.json")
    assert d1 == d2
    assert (tmp_path / "a.json").read_text(encoding="utf-8") == (
        tmp_path / "b.json"
    ).read_text(encoding="utf-8")
