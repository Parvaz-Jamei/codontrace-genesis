from codontrace.genesis import ClaimRequest, ScientificClaimGate
from codontrace.genesis.swarm_metrics import compute_swarm_metric_report


def test_swarm_metrics_require_controls_not_mean_fitness():
    report = compute_swarm_metric_report([
        {"a": (0, 0), "b": (0, 1)},
        {"a": (1, 0), "b": (1, 1)},
    ], group_task_coverage=1.0, shuffled_agent_control_delta=0.0, single_agent_baseline_delta=1.0, no_communication_baseline_delta=1.0)
    assert not report.claim_eligible


def test_swarm_coordination_claim_requires_all_controls():
    gate = ScientificClaimGate()
    denied = gate.decide(ClaimRequest("swarm_coordination_candidate", {"distributed_task_coverage": True, "decentralized_coordination": True}))
    assert not denied.allowed
    allowed = gate.decide(ClaimRequest("swarm_coordination_candidate", {
        "distributed_task_coverage": True,
        "decentralized_coordination": True,
        "shuffled_agent_control": True,
        "single_agent_baseline": True,
        "no_communication_baseline": True,
        "swarm_report_digest": True,
        "replay_verification": True,
    }))
    assert allowed.allowed
