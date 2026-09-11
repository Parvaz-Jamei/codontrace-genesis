# Phase I — collective-intelligence evidence harnesses (honest path)

CodonTrace Genesis Phase I closes the next **measurement** gaps after
Phase H ([`PHASE_H_CI_AI_PATH.md`](PHASE_H_CI_AI_PATH.md), PR #13). It is
**evidence engineering**, not a claim unlock. Library-complete beta is not
“done.” ClaimGate stays the authority.

**Claim ceiling:** `runtime_observation` for new harnesses; RAG retrieval is
documentation / measurement design.

**Still blocked:** `collective_intelligence`, `proved_collective_intelligence`,
`intelligence`, `agi`, `open_ended_intelligence`, `tokyo_type1_passed`,
`avida_replacement`.

`collective_intelligence_candidate` remains allowed **only** when the full
ClaimGate flag set is actually present. Phase I can *earn* some of those
flags from research-scale evidence objects. Smoke runs **never** earn flags.
`replay_verification` is **not** earnable from these harnesses alone.
Phase J ([`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md)) attaches an
independent digest re-execution object so that flag can be earned honestly
when captured and replayed campaign digests match.

Index: [`PHASE_INDEX.md`](PHASE_INDEX.md). Honesty:
[`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
Phase L: [`PHASE_L_AVIDA_FIDELITY.md`](PHASE_L_AVIDA_FIDELITY.md).

---

## 1. What shipped

The two-task world is a **heritable preference analog** (Goldsby / Gorelick /
Okasha / Michod), not Avida C++ and not a 50-replicate PNAS experiment.
Complementary tasks A (easy) and B (costlier “dirty work”) pay as a *group*
only when both are present. Organism-only selection favors A specialists.
MLS2-style group replacement can favor mixed specialists.

| Surface | Role | Honesty |
|---|---|---|
| `run_heldout_unfamiliar_partner_experiment` | Evolve a lineage; evaluate with a heldout unfamiliar lineage; distinct partner digests + leakage status | Status `measured_runtime_observation`; smoke does **not** set `heldout_protocol` |
| `run_evolved_division_of_labor_experiment` | Evolved (not assigned) preference + Gorelick-style NMI + all-A ablation | Ablation measurement does **not** auto-set ClaimGate `ablation_result` |
| `run_mls_evolutionary_outcome_experiment` | MLS vs organism-only: which *strategy* wins, not only a fitness delta | Analog of Okasha MLS2; not `DEME_GROUP` C++; `major_transition_in_individuality=False` |
| `build_export_of_fitness_observation` | Isolation vs group competence hooks | Isolation collapse in this toy is **payoff construction**, not evolved autonomy loss; transition stays false |
| `earn_collective_intelligence_candidate_flags` | Map evidence objects → flags | Smoke never earns; does not mutate ClaimGate |
| RAG cites | Gorelick 2004; Okasha 2006; Michod 2007 PNAS | Retrieval is not evidence |

Default Phase A–E digest pins are unchanged. Phase F campaigns still record
`heldout_partner_status=not_run` unless a Phase I (or equivalent) harness is
called.

---

## 2. ClaimGate flags: earnable vs auto-set

`earn_collective_intelligence_candidate_flags(...)` returns a mapping a
researcher *may* pass into `ScientificClaimGate`. It does **not** write
flags onto the gate, and smoke (`smoke=True` or sub-research seed/generation
counts) returns all `False`.

| Flag | Earnable from | Smoke |
|---|---|---|
| `heldout_protocol` | `HeldoutUnfamiliarPartnerCampaign` at research scale, distinct partners, clean leakage | never |
| `familiar_partner_protocol` | same | never |
| `unfamiliar_partner_protocol` | same | never |
| `real_partner_event` | same | never |
| `role_complementarity` | `EvolvedDivisionOfLaborCampaign` (evolved, NMI, ablation drop) | never |
| `collective_coordination` | same | never |
| `non_capsule_cooperation` | same (no capsules in the analog) | never |
| `ablation_result` | evolved-DoL ablation drop, or research-scale communication ablation that pays | never |
| `collective_report_digest` | Phase I campaign digest at research scale | never |
| `replay_verification` | Phase J independent digest re-execution at research scale when captured vs replayed digests match; **not** from Phase I harnesses alone | never |

Even when every earnable flag is True, `collective_intelligence` stays
forbidden. `collective_intelligence_candidate` still needs
`replay_verification` from Phase J (or an equivalent independent digest
match).

Research defaults: `seed_count=12`, `generations=20`. Smoke: `2` seeds,
`6` generations.

---

## 3. RAG pointers added in Phase I

Canonical machine corpus: `src/codontrace/genesis/rag/corpus/seed.jsonl`.

| `doc_id` | Authority | Why it is here |
|---|---|---|
| `gorelick_2004_normalized_mutual_entropy_dol` | Integr Comp Biol 2004 doi:10.1093/icb/44.5.345 | DoL statistic Goldsby used; lifetime samples required |
| `okasha_2006_levels_of_selection` | OUP 2006 | MLS1 bookkeeping vs MLS2 outcome |
| `michod_2007_pnas_export_of_fitness` | PNAS 2007 doi:10.1073/pnas.0701482104 | Export-of-fitness / conflict suppression; scaffold stays false |

Query API is unchanged:

```python
from codontrace.genesis import search_corpus, cite_sources
from codontrace.genesis.phase_i import (
    run_heldout_unfamiliar_partner_experiment,
    run_evolved_division_of_labor_experiment,
    run_mls_evolutionary_outcome_experiment,
    build_export_of_fitness_observation,
    earn_collective_intelligence_candidate_flags,
)

heldout = run_heldout_unfamiliar_partner_experiment(smoke=True)
dol = run_evolved_division_of_labor_experiment(smoke=True)
mls = run_mls_evolutionary_outcome_experiment(smoke=True)
eof = build_export_of_fitness_observation(mls)
flags = earn_collective_intelligence_candidate_flags(
    heldout=heldout, evolved_dol=dol, mls=mls, export_of_fitness=eof, smoke=True
)
assert not any(flags.as_mapping().values())
print(cite_sources(search_corpus("Okasha MLS2 export of fitness Gorelick", k=5)))
```

Print-only smoke: `examples/genesis_phase_i_ci_evidence.py`.

---

## 4. What is still missing for literature-grade CI

1. Avida-scale evolved coordination *instructions* (not a preference gene)
   — Phase K adds a discrete analog ISA on the Phase E buffer; not Avida C++.
2. Goldsby 2012 ~50-replicate CPU-delay specialists + isolation failure that
   is evolved autonomy loss rather than payoff construction — Phase K adds
   the 50-replicate harness; isolation failure is still not automatically
   evolved autonomy loss.
3. Okasha-grade Price-equation covariance terms with a **transmission**
   term and Avida `DEME_GROUP` MLS2. Phase J records a last-generation
   snapshot; Phase K estimates a transmission term and keeps
   `price_equation_complete=False`.
4. Michod/Conlin endogenous conflict suppression and revertant assays —
   Phase K adds hooks; endogenous flags stay False.
5. Replay-verified candidate packs — **Phase J** makes independent digest
   re-execution runnable; literature-scale Avida/Goldsby campaigns remain.
6. Chromaria knock-outs / Channon 2024 Type 1 **pass** / vocabulary+verifier
   gap closure — still later, still blocked as claims.

Keep building until evidence exists. Do not unlock claims by weakening the
gate.

---

## 5. ClaimGate remainder

Allowed when objects exist: `runtime_observation`,
`oee_measurement_only`, `tokyo_type1_measurement_only`,
`collective_intelligence_candidate` (full flags only, including replay).

Forbidden after Phase I harnesses and RAG retrieval: `agi`, `intelligence`,
`collective_intelligence`, `tokyo_type1_passed`, `avida_replacement`,
`open_ended_intelligence`.

Name the project **CodonTrace Genesis**. Package remains `codontrace`.
