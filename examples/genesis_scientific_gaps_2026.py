"""Opt-in scientific-gaps 2026 smoke (shadow, Tokyo campaign, Logic-9, payoffs).

Print-only. Does not write files, start a UI, or claim Tokyo Type 1 passed,
OEE, intelligence, AGI, associative learning, collective intelligence, or
Avida replacement.
"""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.genesis.benchmark_suite import run_channon_avida_modes_shadow_suite
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.empirical_systematics import (
    EmpiricalSystematicsShadowConfig,
    build_empirical_systematics_shadow,
)
from codontrace.genesis.logic9 import Logic9ReactionConfig, build_logic9_reaction_pack
from codontrace.genesis.multi_generation import build_multi_generation_evidence_pack
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.collective_deme import run_collective_deme_payoff_campaign
from codontrace.genesis.learning_payoff import build_learning_causal_payoff_pack
from codontrace.genesis.tokyo_type1 import (
    build_tokyo_type1_measurement_protocol,
    evaluate_tokyo_type1_pass_claim,
    run_multi_seed_tokyo_measurement_campaign,
)


def main() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=8, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    shadow = build_empirical_systematics_shadow(
        result,
        EmpiricalSystematicsShadowConfig(enabled=True, seed=7, persistence_window_t=2),
    )
    protocol = build_tokyo_type1_measurement_protocol(
        pack,
        shadow_digest=shadow.shadow_digest,
        empirical_systematics_shadow_run=True,
    )
    campaign = run_multi_seed_tokyo_measurement_campaign(seeds=(3, 7), tick_count=6, population=4)
    suite = run_channon_avida_modes_shadow_suite(
        seed=7, tick_count=6, population=4, windows=(1, 2)
    )
    logic9 = build_logic9_reaction_pack(result, Logic9ReactionConfig(enabled=True))
    learning = build_learning_causal_payoff_pack(seeds=(7, 11), tick_count=4, population=3)
    collective = run_collective_deme_payoff_campaign(
        seeds=(3, 7), tick_count=4, population=4
    )
    gate = ScientificClaimGate()

    print("life_loop_digest_prefix", spec.digest()[:16])
    print("shadow_run", shadow.empirical_systematics_shadow_run)
    print("tokyo_step4", protocol.shadow_normalization_status)
    print("tokyo_type1_passed", protocol.tokyo_type1_passed)
    print("campaign_seeds", len(campaign.seeds))
    print("campaign_passed", campaign.tokyo_type1_passed)
    print("suite_windows", list(suite.windows))
    print("suite_passed", suite.tokyo_type1_passed)
    print("logic9_ceiling", logic9.claim_ceiling)
    print("learning_ceiling", learning.claim_ceiling)
    print("learning_instinct_status", learning.instinct_improved_status)
    print("collective_ceiling", collective.claim_ceiling)
    print("collective_heldout", collective.heldout_partner_status)
    print("collective_ablation", collective.communication_ablation_status)
    print("collective_mls", collective.multilevel_selection_experiment)
    print("collective_intelligence_flag", collective.to_dict()["collective_intelligence"])
    print("pass_allowed", evaluate_tokyo_type1_pass_claim(protocol).allowed)
    print("agi_allowed", gate.decide(ClaimRequest("agi", {})).allowed)
    print(
        "collective_allowed",
        gate.decide(ClaimRequest("collective_intelligence", collective.to_dict())).allowed,
    )
    print("avida_replacement_allowed", gate.decide(ClaimRequest("avida_replacement", {})).allowed)


if __name__ == "__main__":
    main()
