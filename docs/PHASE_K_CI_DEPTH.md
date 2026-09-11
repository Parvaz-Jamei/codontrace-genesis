# Phase K — literature-grade CI depth (honest path)

CodonTrace Genesis Phase K deepens **measurement** after Phase J
([`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md), `899addc`). It is
**evidence engineering**, not a claim unlock. ClaimGate stays the authority.
No version bump.

**Claim ceiling:** `runtime_observation` for new measurement objects; RAG
retrieval is documentation / measurement design.

**Still blocked:** `collective_intelligence`, `proved_collective_intelligence`,
`intelligence`, `agi`, `open_ended_intelligence`, `tokyo_type1_passed`,
`avida_replacement`.

`collective_intelligence_candidate` remains allowed **only** when the full
ClaimGate flag set is actually present, including honest
`replay_verification`. Phase K does **not** earn those flags. Smoke runs
**never** earn flags. Digests are never faked.

Index: [`PHASE_INDEX.md`](PHASE_INDEX.md). Honesty:
[`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).
Phase L: [`PHASE_L_AVIDA_FIDELITY.md`](PHASE_L_AVIDA_FIDELITY.md).

---

## 1. What shipped

| Surface | Role | Honesty |
|---|---|---|
| `evaluate_coordination_group` / `run_evolved_coordination_instruction_experiment` | Discrete send/retrieve/broadcast/work genomes on the Phase E buffer; MLS evolution; messaging ablation | Analog ISA, not Avida C++; not evolved language; ablation does **not** set ClaimGate `ablation_result` |
| `run_goldsby_cpu_delay_specialist_campaign` | 0/25/50-cycle switch-delay treatments; research default **50** replicates; isolation vs group dual-task competence | Not the PNAS 2012 paper; analog CPU budget; `is_goldsby_2012_pnas_experiment=False` |
| `run_multi_generation_price_analysis` | Multi-generation Price with a **transmission** term from realized parent–offspring Δz; Phase J last-generation MLS1 snapshot retained | `transmission_term_estimated=True`; `price_equation_complete=False` |
| `build_conflict_suppression_observation` | Within-group variance, cheater-invasion hook, Conlin-style revertant isolation | `conflict_suppression_endogenous=False`; `major_transition_in_individuality=False` |

Default Phase A–E digest pins are unchanged.

---

## 2. Evolved coordination instructions

Phase I evolved a **preference gene**. Phase K evolves a short instruction
genome on the Goldsby/Ofria ISA subset:

`send_message`, `retrieve_message`, `broadcast_message`, `work_a`, `work_b`,
`nop`.

Execution is lockstep. Send/broadcast write the Phase E deme inbox.
Retrieve reads a *peer* unblocked message. Coordination payoff is added only
when retrieve succeeds; complementary retrieve (A-token then work B, or the
reverse) pays extra. Ablation sets `can_message=False` on the same genomes.

This is how communication *pays* in the analog. It is still not Avida
hardware, not evolved language, and not `collective_intelligence`.

Library default `seed_count=12` is exploratory; research-grade n is 30.
`generations=20` stays the library default. Smoke: `2` seeds,
`6` generations.

---

## 3. Goldsby-scale CPU-delay specialist harness

Goldsby et al. PNAS 2012 used 0 / 25 / 50 CPU-cycle switch delays and ~50
replicates, then asked whether isolation competence collapsed.

Phase K:

- Research default `GOLDSBY_RESEARCH_REPLICATE_COUNT = 50`
- Smoke `4` replicates
- Literature delays `(0, 25, 50)` mapped onto analog extra CPU
  (`0 / 2 / 4` on an 8-cycle budget)
- Isolation = both work types executed in one lifetime
- Missing complementary `work_*` is recorded; instruction-loss vs ancestor
  can be `True` without flipping `isolation_collapse_is_evolved_autonomy_loss`

`is_goldsby_2012_pnas_experiment` cannot be set True. Isolation failure is
**not** automatically evolved autonomy loss. The complementary-task pair
bonus is still an analog, not a colony resource quota.

---

## 4. Multi-generation Price with transmission

Phase J recorded a last-generation MLS1 snapshot and forbade
`transmission_term_estimated=True`.

Phase K traces parent→offspring preference after mutation. Realized
offspring *counts* are the fitness that makes the discrete Price identity
hold under truncation selection:

`Δz̄ = Cov(w, z)/w̄ + E[w Δz]/w̄`

The last-generation Phase J partition is attached and still has
`transmission_term_estimated=False`. Phase K marks transmission estimated
and keeps `price_equation_complete=False`: mutation-as-transmission on the
two-task analog is not a Price 1970/1972 empirical paper.

---

## 5. Michod/Conlin conflict-suppression hooks

`build_conflict_suppression_observation` records:

- within-group personal-fitness variance under MLS vs organism-only
- a cheater-invasion assay (A-only specialist inserted; group-fitness drop
  can look like suppression **by group replacement**, not an evolved
  suppressor)
- a revertant/unicell isolation assay (Conlin-style hook; collapse in the
  preference analog remains payoff construction; `entrenchment_of_multicellularity=False`)

Endogenous conflict suppression, germline sequestration, export-of-fitness
detected, and major transition stay **False**. The constructor refuses
otherwise.

---

## 6. RAG pointers added or updated in Phase K

Canonical machine corpus: `src/codontrace/genesis/rag/corpus/seed.jsonl`.

| `doc_id` | Authority | Why it is here |
|---|---|---|
| `price_1972_extension_covariance_selection` | Ann Hum Genet 1972 doi:10.1111/j.1469-1809.1972.tb00796.x | Transmission / extension of the covariance selection math |
| `goldsby_ofria_avida_messaging_germline` | updated | Phase K evolved instruction analog on the Phase E buffer |
| `goldsby_2012_pnas_task_switching` | updated | 50-replicate CPU-delay *harness* (not the PNAS experiment) |
| `price_1970_selection_and_covariance` | updated | Multi-generation transmission scaffold |
| `michod_2007_pnas_export_of_fitness` / `conlin_2023_dol_multicellularity_avida` | updated | Conflict / revertant **hooks** |

```python
from codontrace.genesis import search_corpus, cite_sources
from codontrace.genesis.phase_k import (
    run_evolved_coordination_instruction_experiment,
    run_goldsby_cpu_delay_specialist_campaign,
    run_multi_generation_price_analysis,
    build_conflict_suppression_observation,
)

coord = run_evolved_coordination_instruction_experiment(smoke=True)
goldsby = run_goldsby_cpu_delay_specialist_campaign(smoke=True)
price = run_multi_generation_price_analysis(smoke=True)
hooks = build_conflict_suppression_observation()
assert coord.claim_gate_flags_auto_set is False
assert goldsby.is_goldsby_2012_pnas_experiment is False
assert price.price_equation_complete is False
assert hooks.major_transition_in_individuality is False
print(cite_sources(search_corpus("Goldsby messaging CPU delay Price transmission", k=5)))
```

Print-only smoke: `examples/genesis_phase_k_ci_depth.py`.

---

## 7. What is still missing for literature-grade CI

1. Avida C++ ORGANISM_MESSAGING / `DEME_GROUP` at literature scale (Phase K
   is a discrete analog ISA; Phase L adds FIFO / facing / block / deme
   replicate analogs — still not a C++ port).
2. The actual Goldsby 2012 PNAS experiment (Avida CPU, clonal groups,
   colony quota, 50× hardware). Phase L records aligned *measurements*
   (`is_goldsby_2012_pnas_experiment=False`).
3. A published multi-generation Price paper; Avida `DEME_GROUP` MLS2.
4. Endogenous conflict suppression, germline sequestration, and Conlin
   revertants that are not payoff construction.
5. Chromaria knock-outs / Channon 2024 Type 1 **pass** / vocabulary+verifier
   gap closure — still later, still blocked as claims.

Keep building until evidence exists. Do not unlock claims by weakening the
gate.

---

## 8. ClaimGate remainder

Allowed when objects exist: `runtime_observation`,
`oee_measurement_only`, `tokyo_type1_measurement_only`,
`collective_intelligence_candidate` (full flags only, including honest
replay from Phase J).

Forbidden after Phase K instruction/Goldsby/Price/conflict surfaces and RAG
retrieval: `agi`, `intelligence`, `collective_intelligence`,
`tokyo_type1_passed`, `avida_replacement`, `open_ended_intelligence`.

Name the project **CodonTrace Genesis**. Package remains `codontrace`.
