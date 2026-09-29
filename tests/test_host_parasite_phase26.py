"""Phase 26: Phase 11×21 entropy × contingency bridge (Wave 6 earn-in)."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_entropy_contingency_bridge,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_entropy_contingency_bridge import (
    HYPOTHESIS,
    run_entropy_contingency_bridge,
)
from codontrace.genesis.text_digest import sha256_text_file

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


def test_entropy_contingency_bridge_falsifies_joint_universal_rise() -> None:
    result = run_entropy_contingency_bridge(
        seeds=(1, 2, 3, 4),
        steps=2,
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert result.failure_reason
    assert result.complexity_emergence_proved is False
    assert result.red_queen_proved is False
    assert result.seed_digests_are_distinct is True
    assert all(not o.joint_rise for o in result.seed_outcomes)


def test_bridge_requires_three_seeds() -> None:
    with pytest.raises(ConfigurationError, match="at least 3 seeds"):
        run_entropy_contingency_bridge(seeds=(1, 2))


def test_attach_bridge_requires_prereg_and_keeps_ladder() -> None:
    bridge = run_entropy_contingency_bridge(seeds=(5, 6, 7), steps=2)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do entropy and contingency jointly rise under parasites?",
        context_of_use="Phase 26 bridge; complexity emergence unproved.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_entropy_contingency_bridge(bundle, bridge)
    prereg = host_parasite_preregistration(
        question_of_interest="Do entropy and contingency jointly rise under parasites?",
        context_of_use="Phase 26 bridge; complexity emergence unproved.",
        arms=("entropy_contingency_bridge",),
        success_metrics=("campaign_digest", "seed_digests_are_distinct"),
        forbidden_claims=("red_queen_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_entropy_contingency_bridge(ready, bridge)
    record = attached.extra["entropy_contingency_bridge"]
    assert record["complexity_emergence_proved"] is False
    assert record["raises_claim_ladder"] is False
    assert audit_bundle(attached).achieved_level == before


def test_baic_pins_byte_identical_phase26() -> None:
    for rel, expected in PIN_SPECS:
        digest = sha256_text_file(ROOT / rel)
        assert digest == expected, rel
