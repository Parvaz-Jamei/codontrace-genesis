"""Phase 10 unit: domain-free HookMeter CSV export."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.life_loop.export_csv import (
    SCHEMA_VERSION,
    hook_meter_snapshot_to_rows,
    write_hook_meter_csv,
)
from codontrace.life_loop.hook_meters import HookMeter

REPO = Path(__file__).resolve().parents[3]
EXPORT_SRC = REPO / "src" / "codontrace" / "life_loop" / "export_csv.py"


@pytest.mark.unit
def test_hook_meter_csv_rows_include_digest(tmp_path: Path) -> None:
    meter = HookMeter(meter_id="meter_export_u")
    meter.record_hook("on_contact")
    meter.record_related_total("coupling_total", 0.5)
    snap = meter.snapshot()
    rows = hook_meter_snapshot_to_rows(snap, run_id="r0")
    assert rows
    assert all(r["digest"] == snap.digest for r in rows)
    assert all(r["schema_version"] == SCHEMA_VERSION for r in rows)
    out = tmp_path / "meter.csv"
    written = write_hook_meter_csv(snap, out, run_id="r0")
    assert out.read_text(encoding="utf-8").splitlines()[0].startswith("schema_version")
    assert written == rows


@pytest.mark.unit
def test_life_loop_export_refuses_banned_column_fragment() -> None:
    meter = HookMeter(meter_id="meter_export_ban")
    snap = meter.snapshot()
    with pytest.raises(ConfigurationError, match="banned column"):
        hook_meter_snapshot_to_rows(snap, run_id="clinical_run")


@pytest.mark.unit
def test_life_loop_export_static_no_hp_imports() -> None:
    tree = ast.parse(EXPORT_SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "host_parasite" not in alias.name
                assert "claimgate" not in alias.name.casefold()
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "host_parasite" not in node.module
            assert "claimgate" not in node.module.casefold()
            assert node.module != "codontrace.engine"
