"""Phase 20: resource × coevolution-dynamics factorial."""

from __future__ import annotations

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_resource_dynamics_factorial,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_resource_dynamics import (
    HYPOTHESIS,
    run_resource_dynamics_factorial,
)


def test_resource_factorial_falsifies_higher_resources_always_increase_fsd() -> None:
    result = run_resource_dynamics_factorial(
        seeds=(1, 2),
        request_claim_ceiling="candidate_evidence",
    )
    assert result.hypothesis == HYPOTHESIS
    assert result.hypothesis_supported is False
    assert result.failure_reason
    assert result.cells_are_distinct is True
    assert result.red_queen_proved is False
    payload = result.to_dict()
    assert payload["wet_resource_virulence_proof"] is False
    assert len(result.cells) == 8  # 2 seeds × 2 resource × 2 biotic
    labels = {(c.resource_level, c.biotic_level, c.dynamics_label) for c in result.cells}
    assert labels


def test_attach_resource_dynamics_requires_prereg() -> None:
    factorial = run_resource_dynamics_factorial(seeds=(4,))
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do resource levels modulate dynamics labels digitally?",
        context_of_use="Lopez Pascua honesty map; no wet replication claim.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.2,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_resource_dynamics_factorial(bundle, factorial)
    prereg = host_parasite_preregistration(
        question_of_interest="Do resource levels modulate dynamics labels digitally?",
        context_of_use="Lopez Pascua honesty map; no wet replication claim.",
        arms=("low_absent", "low_present", "high_absent", "high_present"),
        success_metrics=("factorial_digest", "cells_are_distinct"),
        forbidden_claims=("red_queen_proved", "virulence_optimized_for_humans"),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_resource_dynamics_factorial(ready, factorial)
    record = attached.extra["resource_dynamics_factorial"]
    assert record["wet_resource_virulence_proof"] is False
    assert record["raises_claim_ladder"] is False
    assert audit_bundle(attached).achieved_level == before
