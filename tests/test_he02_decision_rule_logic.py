"""Synthetic HE02 decision-rule cases. Does not raise ClaimGate."""

from codontrace.genesis.he02_contrasts import decision_from_contrasts


def _row(baseline: str, *,
    dz: float,
    p_holm: float,
) -> dict[str, float | str]:
    return {
        "treatment_arm": "treatment",
        "baseline_arm": baseline,
        "dz": dz,
        "p_holm": p_holm,
        "p_raw": p_holm,
        "n_pairs": 30,
    }


def test_rule_fails_when_shuffled_is_not_separated() -> None:
    rows = [
        _row("content_null", dz=1.1, p_holm=0.001),
        _row("channel_off", dz=1.1, p_holm=0.001),
        _row("capsules_shuffled", dz=0.2, p_holm=0.37),
    ]
    report = decision_from_contrasts(rows)
    assert report["decision_rule_passed"] is False
    assert "information_control_not_separated" in report["decision_rule_failures"]
    assert report["intervention_supported"] is False
    assert report["claim_ceiling"] == "runtime_observation"


def test_rule_can_pass_without_raising_claimgate() -> None:
    rows = [
        _row("content_null", dz=1.1, p_holm=0.001),
        _row("channel_off", dz=1.1, p_holm=0.001),
        _row("capsules_shuffled", dz=0.8, p_holm=0.01),
    ]
    report = decision_from_contrasts(rows)
    assert report["decision_rule_passed"] is True
    assert report["decision_rule_failures"] == []
    assert report["intervention_supported"] is False
