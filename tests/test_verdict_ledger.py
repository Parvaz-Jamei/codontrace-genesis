"""The standing verdicts in the index must be the ledger, not a second opinion."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "docs/experiments/2026-09-29/VERDICT_LEDGER_V1.json"
INDEX_PATH = ROOT / "docs/experiments/2026-09-29/INDEX.md"
CI_PATH = ROOT / ".github/workflows/ci.yml"
STATUS_PATH = ROOT / "docs/campaigns/discovery_questions_20260928/TESTS_DONE_STATUS_2026-09-29.md"
HARNESS_PATH = ROOT / "docs/experiments/2026-09-29/rq3_adaptation_route/rq3_harness.py"
ALLOWED = {
    "SUPPORTED_IN_MODEL",
    "FALSIFIED_IN_MODEL",
    "INCONCLUSIVE",
    "BLOCKED_MEASUREMENT",
}
RQ3_RUNS = ROOT / "docs/experiments/2026-09-29/rq3_adaptation_route/runs"


def _first_code(text: str) -> str:
    start = text.find("`")
    end = text.find("`", start + 1)
    if start < 0 or end < 0:
        raise AssertionError(f"no code span in {text!r}")
    return text[start + 1 : end]


def _standing_verdict(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Standing verdict"):
            return _first_code(line)
    raise AssertionError(f"{path} has no standing-verdict line")


def _job_blocks(workflow: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    name: str | None = None
    lines: list[str] = []
    for line in workflow.splitlines():
        token = line.strip()
        header = line.startswith("  ") and not line.startswith("   ") and token.endswith(":")
        if header and " " not in token[:-1]:
            if name is not None:
                blocks[name] = "\n".join(lines)
            name = token[:-1]
            lines = [line]
        elif name is not None:
            lines.append(line)
    if name is not None:
        blocks[name] = "\n".join(lines)
    return blocks


def _index_verdicts() -> dict[str, str]:
    found: dict[str, str] = {}
    for line in INDEX_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Experiment", "---"}:
            continue
        verdict = cells[2]
        if "`" not in verdict:
            continue
        found[cells[0]] = _first_code(verdict)
    return found


def test_every_standing_verdict_is_one_label_and_matches_the_index() -> None:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    assert ledger["hypothesis_supported"] is False
    assert ledger["red_queen_proved"] is False
    assert ledger["confirmatory_campaign"]["opened"] is False
    assert ledger["confirmatory_campaign"]["verdict"] == "BLOCKED_MEASUREMENT"
    index = _index_verdicts()
    for record in ledger["records"]:
        verdict = record["standing_verdict"]
        assert verdict in ALLOWED
        assert record["hypothesis_supported"] is False
        assert record["red_queen_proved"] is False
        assert index[record["id"]] == verdict
        decision = record.get("decision_path")
        if decision is not None:
            assert _standing_verdict(ROOT / decision) == verdict


def test_d2_falsified_is_history_and_rq3_quoted_seeds_have_no_roster() -> None:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    by_id = {record["id"]: record for record in ledger["records"]}
    d2 = by_id["d2_recovery_window"]
    assert d2["standing_verdict"] == "BLOCKED_MEASUREMENT"
    assert d2["historical"][0]["verdict"] == "FALSIFIED_IN_MODEL"
    assert d2["historical"][0]["role"] != "standing"
    rq3 = by_id["rq3_adaptation_route"]
    assert rq3["data_status"] == "INCOMPLETE"
    names = " ".join(path.name for path in RQ3_RUNS.iterdir())
    for seed in rq3["missing_raw_seeds"]:
        assert f"s{seed}" not in names
    assert "21001" in names and "21011" in names


def test_status_table_uses_the_same_standing_labels() -> None:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    by_id = {record["id"]: record["standing_verdict"] for record in ledger["records"]}
    labels = {"RQ-1": "rq1_time_shift", "RQ-3": "rq3_adaptation_route", "D-2": "d2_recovery_window"}
    seen: set[str] = set()
    in_standing = False
    for line in STATUS_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Test | Standing result"):
            in_standing = True
            continue
        if not in_standing or not line.startswith("| **"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        for prefix, record_id in labels.items():
            if cells[0].startswith(f"**{prefix}**"):
                assert _first_code(cells[1]) == by_id[record_id]
                seen.add(record_id)
    assert seen == set(labels.values())
    status = STATUS_PATH.read_text(encoding="utf-8")
    assert "D-2 `FALSIFIED_IN_MODEL` on the calibration tier" not in status
    assert "infection_cost=0.4" in status
    assert "400 generations" in status
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    sex = next(record for record in ledger["records"] if record["id"] == "sex_cost")
    assert sex["standing_verdict"] == "INCONCLUSIVE"
    assert "infection_cost=0.4" in sex["scope"]
    assert "generations=400" in sex["scope"]
    assert "two-fold" in sex["scope"]
    index = INDEX_PATH.read_text(encoding="utf-8")
    assert "infection_cost=0.4" in index
    assert "400 generations" in index


def test_mypy_is_optional_and_the_ledger_gate_is_not() -> None:
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    blocks = _job_blocks(CI_PATH.read_text(encoding="utf-8"))
    assert ledger["mypy"]["required"] is False
    assert "continue-on-error: true" in blocks["lint-type"]
    assert "continue-on-error" not in blocks["verdict-ledger"]
    assert "continue-on-error" not in blocks["published-manifests"]
    assert "tests/test_published_manifests.py" in blocks["published-manifests"]
    assert "test_property_balance_identity_and_parents" in blocks["published-manifests"]
    for relative in (
        "tests/test_fork_checkpoint.py",
        "tests/test_antagonist_energy_accounting.py",
        "tests/closed_loop/test_rq_metric_split.py",
        "tests/closed_loop/test_d2_recovery_v2.py",
        "tests/test_verdict_ledger.py",
    ):
        assert (ROOT / relative).is_file()


def test_archive_harness_imports_this_checkout_and_passes_rng_by_keyword() -> None:
    text = HARNESS_PATH.read_text(encoding="utf-8")
    assert "E:\\" not in text
    assert "REPO = ROOT.parents[3]" in text
    assert (HARNESS_PATH.parent.parents[3] / "src" / "codontrace").is_dir()
    assert "rng=self.rng.fork" in text
