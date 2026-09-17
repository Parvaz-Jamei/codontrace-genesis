"""HE02 confirmatory rule stays failed while shuffled control is unseparated."""

from codontrace.genesis.he02_contrasts import analyze_committed_research


def test_committed_research_does_not_earn_intervention() -> None:
    report = analyze_committed_research()
    assert report["claim_ceiling"] == "runtime_observation"
    assert report["intervention_supported"] is False
    assert report["decision_rule_passed"] is False
    assert "information_control_not_separated" in report["decision_rule_failures"]
    shuffled = next(
        item
        for item in report["paired_contrasts"]
        if item["baseline_arm"] == "capsules_shuffled"
    )
    assert shuffled["p_holm"] is not None and float(shuffled["p_holm"]) >= 0.05
