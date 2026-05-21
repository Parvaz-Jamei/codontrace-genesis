from codontrace.genesis.contribution_ledger import (
    build_contribution_ledger,
    contribution_from_execution_record,
    contribution_ledger_from_dict,
    eligibility_trace_credit,
    paired_micro_ablation_score,
)
from codontrace.genesis.innovation_protection import (
    InnovationProtectionConfig,
    build_innovation_record,
    enforce_innovation_protection_limit,
    is_innovation_protected,
)
from codontrace.genesis.ribosome import BrainTokenSource, CodonExecutionRecord


def _exec(pos=0, atp_after=2.0):
    return CodonExecutionRecord(
        "org",
        1,
        pos,
        BrainTokenSource(pos, "000"),
        "EAT_LUMEN",
        "executed",
        1.0,
        atp_after,
        "ctx",
        f"e{pos}",
    )


def test_contribution_ledger_from_execution_records_and_digest_validation():
    records = [contribution_from_execution_record(_exec(0, 3.0), generation=2)]
    ledger = build_contribution_ledger("org", 2, records)
    assert ledger.aggregate_by_codon[0][1] > 0
    assert contribution_ledger_from_dict(ledger.to_dict()).digest == ledger.digest


def test_eligibility_trace_delayed_reward_and_micro_ablation():
    records = [
        contribution_from_execution_record(_exec(0)),
        contribution_from_execution_record(_exec(1)),
    ]
    credited = eligibility_trace_credit(records, 10.0, gamma=0.5)
    assert credited[1].descendant_success_discounted > credited[0].descendant_success_discounted
    assert paired_micro_ablation_score(5.0, 3.0) == 2.0


def test_innovation_protection_respects_max_protected_fraction_and_scope():
    cfg = InnovationProtectionConfig(max_protected_fraction=0.25, protection_scope="niche")
    records = tuple(
        build_innovation_record(
            f"i{i}", "adf_macro", 0, f"L{i}", cfg, novelty_score=float(i), niche_id="n"
        )
        for i in range(8)
    )
    limited = enforce_innovation_protection_limit(
        records, population_size=8, config=cfg, scope_id="n"
    )
    assert sum(1 for r in limited if r.status == "protected") == 2
    assert any(is_innovation_protected(r, 1) for r in limited)
