"""The RQ-1 runner must stop before any seed when the checkout is not the pin."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = (
    ROOT
    / "docs/experiments/2026-09-29/rq1_time_shift/confirmatory/confirmatory_rq1.py"
)


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_missing_checkout_stops(tmp_path: Path) -> None:
    proc = _run(
        [
            "--reference-checkout",
            str(tmp_path / "absent"),
            "--output",
            str(tmp_path / "out"),
            "--expect-commit",
            "6187ff4",
        ]
    )
    assert proc.returncode != 0
    assert "does not exist" in proc.stderr
    assert not (tmp_path / "out").exists()


def test_commit_mismatch_stops(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "gate@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "gate"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "note").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "note"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "not the pin"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    proc = _run(
        [
            "--reference-checkout",
            str(repo),
            "--check-only",
            "--expect-commit",
            "6187ff4",
        ]
    )
    assert proc.returncode != 0
    assert "commit mismatch" in proc.stderr
    assert "check_only" not in proc.stdout
