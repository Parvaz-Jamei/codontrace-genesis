"""Phase 24: Wave 6 journal packet integration smoke (Phases 18–23)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_wave6_journal_smoke,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_attach_registry import (
    WAVE6_ATTACH_CALLABLES,
    WAVE6_ATTACH_KEYS,
    assert_wave6_attach_surface_wired,
)
from codontrace.genesis.host_parasite_wave6_smoke import (
    ATTACH_ORDER,
    run_wave6_journal_smoke,
)

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


def test_wave6_journal_smoke_attaches_phases_18_to_23_without_ladder_rise() -> None:
    result = run_wave6_journal_smoke(seeds=(101, 202, 303))
    assert result.attached_keys == ATTACH_ORDER
    assert result.ladder_unchanged is True
    assert result.raises_claim_ladder is False
    assert result.red_queen_proved is False
    assert result.complexity_emergence_proved is False
    assert result.intervention_supported is False
    assert result.gene_identity_proved is False
    assert result.soft_complete_wave5_surface is True
    assert all(blocked for _, blocked in result.blocked_spot_check)
    assert len(result.campaign_digests) == 6


def test_wave6_smoke_requires_three_seeds() -> None:
    with pytest.raises(ConfigurationError, match="at least 3 seeds"):
        run_wave6_journal_smoke(seeds=(1, 2))


def test_attach_wave6_smoke_requires_prereg_and_keeps_ladder() -> None:
    smoke = run_wave6_journal_smoke(seeds=(11, 22, 33))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do Phases 18–23 stay ClaimGate-honest on one bundle?",
        context_of_use="Wave 6 Phase 24 journal smoke hygiene only.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.15,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_wave6_journal_smoke(bundle, smoke)
    prereg = host_parasite_preregistration(
        question_of_interest="Do Phases 18–23 stay ClaimGate-honest on one bundle?",
        context_of_use="Wave 6 Phase 24 journal smoke hygiene only.",
        arms=ATTACH_ORDER,
        success_metrics=("smoke_digest", "ladder_unchanged"),
        forbidden_claims=("red_queen_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_wave6_journal_smoke(ready, smoke)
    record = attached.extra["wave6_journal_smoke"]
    assert record["ladder_unchanged"] is True
    assert record["raises_claim_ladder"] is False
    assert record["soft_complete_wave5_surface"] is True
    assert audit_bundle(attached).achieved_level == before
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_wave6_journal_smoke(attached, smoke)


def test_wave6_attach_surface_wired() -> None:
    assert_wave6_attach_surface_wired()
    assert set(WAVE6_ATTACH_KEYS) == set(WAVE6_ATTACH_CALLABLES)
    assert "attach_wave6_journal_smoke" in WAVE6_ATTACH_CALLABLES.values()


def test_baic_pins_byte_identical_phase24() -> None:
    for rel, expected in PIN_SPECS:
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, rel
