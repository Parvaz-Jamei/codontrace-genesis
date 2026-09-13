# Integrated Living World (ILW) — Plan

**Status:** ILW-3 integrated smoke (replay, conservation, edge coverage; no science claim).
**ClaimGate ceiling:** `runtime_observation` (never loosened here).
**Scientific name:** `integrated eco-evolutionary runtime`
(not intelligence / AGI / collective intelligence / Tokyo Type 1 / Avida replacement).

## Problem

4×4 / one-genome / 6-tick pilots are component smoke. They do **not** prove that
toolchain, VM, world, resources, capsules, reproduction, mutation, and lineage
form one integrated system. Keep pilots; do not promote them to a full-world
claim.

## Required chain (one `run_id`, one `WorldSpec`, one scheduler, one ledger)

```text
genome -> toolchain -> VM phenotype -> action -> resource/world consequence
-> experienced event -> capsule with provenance -> transport/accept/apply
-> receiver policy/action change -> survival/reproduction -> mutation/lineage
-> next ecological state
```

Canonical edge list + telemetry: `src/codontrace/genesis/ilw/INTEGRATION_DAG.json`.

Every arrow has:

- unique `edge_id`
- before/after state digests
- separate `attempted` / `accepted` / `applied` counters (never one collapsed counter)
- independent assay + knockout

Forbidden: outcome injection, treatment oracle, fitness shortcut outside VM/world.

## ILW-0 (this milestone) — done when

1. `INTEGRATION_DAG.json` lists required edges, subsystems, knockouts, and
   telemetry fields.
2. Fail-first orphan subsystem registry raises before a full-world claim.
3. Event consumer rejects orphan / unregistered `edge_id` events.
4. Minimal tests cover DAG load, required edges, orphan/missing-edge failure,
   and orphan event rejection.
5. ClaimGate ceiling remains `runtime_observation`; docs make no intelligence claims.

## Later milestones (do not start in ILW-0)

| ID | Scope |
|----|--------|
| ILW-1 | WorldSpec, scheduler, event ledger, shared seed namespace; keep adapters |
| ILW-2 | Full genome→lineage chain in a two-resource environment |
| ILW-3 | Integrated smoke: replay, conservation, edge coverage; no science claim |
| ILW-4 | Prereg patterns, interactions, scale, horizon, seeds, stop rule; then pilot |
| ILW-5 | Factorial / ablation campaign + scale challenge |
| ILW-6 | MODES, phylogeny, novelty+learnability (exploratory only) |

## Smallest vertical cut (ILW-2+)

- Spatial world with ≥2 limited renewable resources and multiple niches
- Mutable genome controlling exploration, harvest, move, emit/read/adopt, reproduction
- Real compute / move / copy / innovation costs
- Capsules from real agent experience (not hand payloads)
- Resource regime shifts so stale information can expire
- Organism phylogeny and capsule genealogy separate but joinable
- Freshness / trust / source-choice as evolvable traits (not hard-coded)

## Scale ladder (lock numbers before seeing outcomes)

- S0: 4×4 / 6 tick — unit only
- S1: integrated smoke (e.g. 16×16, ≥1 birth/death cycle)
- S2: multi-generation pilot (e.g. 32×32, separate seeds)
- S3: research (e.g. 64×64+, tens/hundreds of turnovers)
- S4: ≥3 sizes × ≥3 horizons for finite-size challenge

Report horizon via generation turnover, lineage depth, and regime changes — not
ticks alone.

## Edge knockouts (same world; one edge each; cost/throughput sham/yoked)

- `toolchain_to_action_off`
- `experience_to_capsule_off`
- `capsule_transport_off`
- `capsule_to_policy_off`
- `mutation_off`
- `ecological_feedback_off`
- `lineage_inheritance_off`

OAT alone is insufficient. Prefer Morris screening, then fractional-factorial for
toggles and three-level Definitive Screening for continuous factors. Estimate at
least: `toolchain × capsule`, `capsule × ecology`, `mutation × capsule`,
`heterogeneity × population_size`.

## Multi-pattern gate (Pattern-Oriented Modeling)

ATP mean is not enough. The world must simultaneously:

1. build valid toolchain + phenotype
2. conserve energy/resources
3. persist multi-generation with real turnover
4. show non-token genetic/phenotypic diversity
5. create competition, niches, eco-evolutionary feedback
6. have capsule transfer actually change action and descendant fitness
7. break predictably under null/yoked/edge-off
8. preserve or honestly report effect-direction failure across scales

Do **not** claim cumulative cultural evolution until Mesoudi & Thornton’s four
criteria pass together: innovation, social transmission, performance improvement,
and sequential improvement across generations.

## Required telemetry

```text
run_id, seed, tick, generation, world_spec_digest,
event_id, causal_parent_ids, edge_id,
actor_id, lineage_id, genome_digest,
source_id, capsule_id, capsule_parent_id, payload_digest, provenance_digest,
attempted, accepted, applied, blocked_reason,
state_before_digest, state_after_digest,
energy_delta, resource_delta, fitness_proxy_delta
```

Replay must bitwise rebuild the final digest. Required-edge coverage in an
integrated run must be 100%.

## First acceptance milestone (ILW-3 target; not ILW-0)

- One command + one spec runs the whole world
- Toolchain and capsule share the same agents and `run_id`
- Experience→capsule→distinct action→resource/energy→reproduction/ancestry linked
- Multiple generation turnovers without fixture outcomes
- Replay, conservation, and all assays pass
- Every required edge has non-zero telemetry and a valid knockout
- Smoke issues no ladder promotion

## Red lines

No new standalone pilots-as-world-claims, theatrical network inflation, config
cherry-pick, ATP-only claims, treatment oracles, weakened tests, Phase A–E pin
breaks, tag/PyPI, or ClaimGate raises. Ceiling stays `runtime_observation`.

## Code map (ILW-0 / ILW-1 / ILW-2 / ILW-3)

| Path | Role |
|------|------|
| `src/codontrace/genesis/ilw/INTEGRATION_DAG.json` | Required edges / subsystems / knockouts / telemetry |
| `src/codontrace/genesis/ilw/dag.py` | Load + validate DAG |
| `src/codontrace/genesis/ilw/orphan.py` | Fail-first orphan subsystem registry |
| `src/codontrace/genesis/ilw/event_consumer.py` | Reject orphan / unregistered events |
| `src/codontrace/genesis/ilw/world_spec.py` | Shared digest-stable WorldSpec |
| `src/codontrace/genesis/ilw/seed_namespace.py` | Run-scoped deterministic seed namespaces |
| `src/codontrace/genesis/ilw/scheduler.py` | Tick scheduler bound to one run_id |
| `src/codontrace/genesis/ilw/event_ledger.py` | Append-only causal event ledger |
| `src/codontrace/genesis/ilw/adapter_honesty.py` | No fixture/oracle outcome injection |
| `tests/test_ilw0_integration_dag.py` | Minimal ILW-0 tests |
| `tests/test_ilw1_world_runtime.py` | ILW-1 WorldSpec / ledger / scheduler / seeds |
| `src/codontrace/genesis/ilw/dual_resource_world.py` | Dual limited renewable resources + niches |
| `src/codontrace/genesis/ilw/knockouts.py` | Per-edge knockout config (one cut set each) |
| `src/codontrace/genesis/ilw/chain_runtime.py` | ILW-2 integrated causal chain under one run_id |
| `tests/test_ilw2_causal_chain.py` | ILW-2 chain / coverage / knockout tests |
| `src/codontrace/genesis/ilw/conservation.py` | Resource/energy conservation assays |
| `src/codontrace/genesis/ilw/integrated_smoke.py` | ILW-3 integrated smoke + replay |
| `tests/test_ilw3_integrated_smoke.py` | ILW-3 replay / conservation / coverage / no-claim |

## ILW-1 (this milestone) — done when

1. Shared `WorldSpec` is digest-stable (frozen/slots; `canonical_digest`).
2. Scheduler advances ticks under one `run_id` only.
3. Event ledger is append-only with `edge_id` + causal parent checks.
4. Seed namespace is deterministic and does not leak across runs.
5. Adapters stay honest (no fixture outcome injection); ClaimGate ceiling remains `runtime_observation`.


## ILW-2 (this milestone) — done when

1. Full causal chain genome→…→next ecological state runs under one `run_id`,
   one `WorldSpec`, one scheduler, and one event ledger.
2. Dual limited renewable resources + niches form the minimal vertical world.
3. Every required DAG edge emits telemetry with `edge_id`, before/after digests,
   and separate `attempted` / `accepted` / `applied`.
4. Capsule path (experience→capsule→transport/accept/apply→policy) and lineage
   path (survival/reproduction→mutation→inheritance) are recordable on one run.
5. At least one edge-off knockout severs apply (fail-first blocked telemetry);
   no outcome injection; ClaimGate ceiling remains `runtime_observation`.


## ILW-3 (this milestone) — done when

1. Integrated smoke runs at S1-ish scale (larger than 4×4 / 6 tick) under one
   `run_id` / WorldSpec / scheduler / ledger.
2. Independent replay bitwise-rebuilds `final_digest`.
3. Conservation checks pass for resources (harvest+renewal reconciliation) and
   energy non-negativity / harvest conversion.
4. Required-edge coverage is 100% on the integrated run.
5. `attempted` / `accepted` / `applied` remain separate fields (never one counter).
6. At least one birth and one death occur when dynamics allow (honest; no fixture).
7. Smoke emits **no** ClaimGate ladder promotion / scientific claim; ceiling stays
   `runtime_observation`.

## Primary references

- Pattern-Oriented Modeling: https://doi.org/10.1098/rstb.2011.0180
- Global sensitivity / OAT weakness: https://doi.org/10.1016/j.envsoft.2010.04.012
- Definitive Screening Designs: https://doi.org/10.1080/00224065.2011.11917841
- MODES Toolbox: https://doi.org/10.1162/artl_a_00280
- Cumulative cultural evolution: https://doi.org/10.1098/rspb.2018.0712
- Social learning strategies: https://doi.org/10.1126/science.1184719
- Phylotrack: https://doi.org/10.48550/arXiv.2405.09389
- Model docking: https://doi.org/10.1007/BF01299065
