"""Every published experiment manifest has to match the tree.

A new file that is not listed, or an old hash on a changed file, fails.
Historical raw bytes are not rewritten to force a match.
"""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.archive_io import verify_manifest

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "docs" / "experiments"


def test_every_published_experiment_manifest_matches_the_tree() -> None:
    manifests = sorted(EXPERIMENTS.rglob("manifest_*.sha256"))
    assert manifests
    errors = [f"{path.relative_to(ROOT)}: {verify_manifest(path)}" for path in manifests if verify_manifest(path)]
    assert errors == []
    covered = {path.parent for path in manifests}
    for directory in covered:
        assert (directory / "manifest_lf.sha256").is_file()
        assert (directory / "manifest_raw.sha256").is_file()
