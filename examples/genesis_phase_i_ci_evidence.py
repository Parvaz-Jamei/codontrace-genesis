"""CodonTrace Genesis Phase I CI evidence smoke.

Print-only. Runs heldout-partner, evolved-DoL, and MLS-outcome harnesses at
smoke scale, prints the export-of-fitness scaffold, and shows which ClaimGate
candidate flags can be earned only from research-scale evidence objects.
Does not write files, start a UI, set ClaimGate flags, or claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
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

from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_i import (
    EARNABLE_FLAG_SOURCES,
    build_export_of_fitness_observation,
    earn_collective_intelligence_candidate_flags,
    phase_i_candidate_checklist,
    run_evolved_division_of_labor_experiment,
    run_heldout_unfamiliar_partner_experiment,
    run_mls_evolutionary_outcome_experiment,
)
from codontrace.genesis.rag import cite_sources, search_corpus


def main() -> None:
    gate = ScientificClaimGate()
    print("product", "CodonTrace Genesis")
    print("phase", "I")
    hits = search_corpus("heldout unfamiliar partners MLS2 export of fitness Gorelick DoL", k=6)
    print("ranked_cites")
    for index, citation in enumerate(cite_sources(hits), start=1):
        print(f"  {index}. {citation}")
    heldout = run_heldout_unfamiliar_partner_experiment(smoke=True)
    dol = run_evolved_division_of_labor_experiment(smoke=True)
    mls = run_mls_evolutionary_outcome_experiment(smoke=True)
    eof = build_export_of_fitness_observation(mls)
    smoke_flags = earn_collective_intelligence_candidate_flags(
        heldout=heldout, evolved_dol=dol, mls=mls, export_of_fitness=eof, smoke=True
    )
    print("heldout_status", heldout.heldout_partner_status)
    print("heldout_distinct", all(row.distinct_partners for row in heldout.seed_records))
    print("evolved_dol_nmi", dol.mean_nmi)
    print("evolved_dol_ablation_drop", dol.mean_ablation_drop)
    print("mls_outcome_changed_fraction", mls.outcome_changed_fraction)
    print("major_transition_in_individuality", eof.major_transition_in_individuality)
    print("export_of_fitness_detected", eof.export_of_fitness_detected)
    print("smoke_earned_any", any(smoke_flags.as_mapping().values()))
    print("earnable_flag_sources")
    for name, source in EARNABLE_FLAG_SOURCES:
        print(f"  {name}: {source}")
    checklist = phase_i_candidate_checklist(
        heldout=heldout, evolved_dol=dol, mls=mls, smoke=True
    )
    print("gap_checklist")
    for line in checklist.render().splitlines():
        print(" ", line)
    payload = heldout.to_dict()
    print(
        "collective_intelligence_allowed",
        gate.decide(ClaimRequest("collective_intelligence", payload)).allowed,
    )
    print("intelligence_allowed", gate.decide(ClaimRequest("intelligence", payload)).allowed)
    print(
        "candidate_allowed",
        gate.decide(ClaimRequest("collective_intelligence_candidate", payload)).allowed,
    )
    print("agi_allowed", gate.decide(ClaimRequest("agi", {})).allowed)


if __name__ == "__main__":
    main()
