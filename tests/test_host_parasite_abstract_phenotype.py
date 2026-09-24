"""De-toy D4: abstract metabolic phenotype from SemanticGenome."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.genesis.host_parasite_abstract_phenotype import (
    SCHEMA,
    decode_abstract_phenotype,
    default_target_phenotype,
    metabolic_error_for_genome,
)
from codontrace.genesis.text_digest import sha256_text_file
from codontrace.genome import SemanticGenome

ROOT = Path(__file__).resolve().parents[1]
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)


def test_phenotype_replay_stable_and_honest() -> None:
    g = SemanticGenome.random(length=12, seed=42)
    a = decode_abstract_phenotype(g)
    b = decode_abstract_phenotype(g)
    assert a["schema"] == SCHEMA
    assert a["phenotype_digest"] == b["phenotype_digest"]
    assert a["aevol_identity"] is False
    assert a["wet_metabolism_claim"] is False
    assert 0.0 <= float(a["metabolic_error"]) <= 1.0
    assert len(a["phenotype"]) == 16


def test_genome_edit_changes_error() -> None:
    g = SemanticGenome.random(length=12, seed=7)
    base = metabolic_error_for_genome(g)
    codons = list(g.to_codons())
    flipped = [("1" + c[1:]) if c.startswith("0") else ("0" + c[1:]) for c in codons]
    g2 = SemanticGenome.from_codons(flipped)
    assert metabolic_error_for_genome(g2) != base


def test_target_deterministic() -> None:
    assert default_target_phenotype() == default_target_phenotype()


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_d4(path: str, expected: str) -> None:
    assert sha256_text_file(ROOT / path) == expected
