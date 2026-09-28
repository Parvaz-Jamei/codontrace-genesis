"""De-toy D4: abstract metabolic phenotype from SemanticGenome."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.genesis.host_parasite_abstract_phenotype import (
    SCHEMA,
    decode_abstract_phenotype,
    default_target_phenotype,
    metabolic_error_for_genome,
)
from codontrace.genome import SemanticGenome

ROOT = Path(__file__).resolve().parents[1]
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "4a5987c2ed0f09d1088b3c1bca6d81fe2310f3867fa84f22a33fbeee7b5d7efd",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "b7091921bf00c350fa286caf117fa46af81e9760b1b6d4d135eefd042dabd404",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "2e5193639aad58ceda68ef9bc33943f8eae2c45f042209a060af890c93785079",
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
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
