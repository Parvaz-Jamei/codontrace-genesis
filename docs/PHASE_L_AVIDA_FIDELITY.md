# Phase L — Avida ORGANISM_MESSAGING / DEME_GROUP fidelity (honest path)

CodonTrace Genesis Phase L deepens **analog fidelity** after Phase K
([`PHASE_K_CI_DEPTH.md`](PHASE_K_CI_DEPTH.md), `2614ec4`). It is
**evidence engineering**, not a claim unlock and **not an Avida C++ port**.
ClaimGate stays the authority. No version bump.

**Claim ceiling:** `runtime_observation` for new measurement objects; RAG
retrieval is documentation / measurement design.

**Still blocked:** `collective_intelligence`, `proved_collective_intelligence`,
`intelligence`, `agi`, `open_ended_intelligence`, `tokyo_type1_passed`,
`avida_replacement`.

`collective_intelligence_candidate` remains allowed **only** when the full
ClaimGate flag set is actually present, including honest
`replay_verification`. Phase L does **not** earn those flags from smoke.
The optional Phase K coordination-ablation **feed** never auto-sets
ClaimGate flags. Digests are never faked. Default Phase A–E digest pins
are unchanged.

Index: [`PHASE_INDEX.md`](PHASE_INDEX.md). Honesty:
[`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).

Cross-links: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md),
[`PHASE_K_CI_DEPTH.md`](PHASE_K_CI_DEPTH.md),
[`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md),
[`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md),
[`PHASE_H_CI_AI_PATH.md`](PHASE_H_CI_AI_PATH.md),
[`rag/README.md`](rag/README.md),
[`SOCIAL_COLLECTIVE_INTELLIGENCE_PROTOCOL.md`](SOCIAL_COLLECTIVE_INTELLIGENCE_PROTOCOL.md),
[`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md),
[`../CLAIMS.md`](../CLAIMS.md).

---

## 1. What shipped

| Surface | Role | Honesty |
|---|---|---|
| `evaluate_organism_messaging_group` / `run_organism_messaging_fidelity_experiment` | Per-organism FIFO inbox; faced-neighbor `send_message`; `broadcast_message`; `block_propagation`; `rotate_cw`; Phase E `DemeState` audit; optional `maybe_replicate_demes` | Analog ISA, not Avida C++; ring facing ≠ grid neighborhood |
| `measure_goldsby_aligned_specialists` / `run_goldsby_aligned_specialist_campaign` | Behavioral vs genotypic specialists; clonal-group DoL; colony-quota analog; ancestral vs evolved isolation; delay dose-response | `is_goldsby_2012_pnas_experiment=False`; isolation failure ≠ evolved autonomy loss |
| `feed_phase_k_coordination_ablation_evidence` | Optional Phase K ablation → evidence object; may *propose* `ablation_result` only when opted in at research scale with a payoff drop | Does **not** mutate ClaimGate; smoke never earns |

Default Phase A–E digest pins are unchanged. Phase K campaign schemas are
not rewritten.

---

## 2. ORGANISM_MESSAGING analog (closer, still not a port)

Avida `ORGANISM_MESSAGING` (devosoft/avida instruction set / wiki) treats
communication as CPU instructions:

- `send-msg` delivers a labeled message to the **faced** neighbor
- `retrieve-msg` **pops** the organism's own inbox (FIFO)
- broadcast fans out to the neighborhood
- `block_propagation` suppresses forwarding
- facing is changed by rotate instructions

Phase K used a **shared deme latest-message** retrieve on
`send_message` / `retrieve_message` / `broadcast_message` only.

Phase L keeps the Phase E buffer as an audit trail and adds:

1. per-organism FIFO inboxes (retrieve consumes)
2. faced-neighbor send on a **ring** (documented substitute for Avida's
   grid neighborhood)
3. `rotate_cw`
4. `block_propagation` (later broadcasts from that organism do not enter
   peer inboxes)
5. label + data on inbox items (`A` / `B` / `cue`)

This is how communication *pays* in the analog when a retrieve pops a
peer message. It is still not Avida hardware, not evolved language, and
not `collective_intelligence`.

Library default `seed_count=12` is exploratory; research-grade n is 30.
`generations=20` stays the library default. Smoke: `2`
seeds, `6` generations.

---

## 3. DEME_GROUP analog (closer, still not a port)

`avida.cfg` `DEME_GROUP` / `DEMES_GROUP_REPLICATE` / `GERMLINE` and the
[devosoft/avida wiki Deme-introduction](https://github.com/devosoft/avida/wiki/Deme-introduction)
copy a deme when mean fitness clears a threshold and may export a
germline/propagule, leaving a target deme.

Phase L calls Phase E `maybe_replicate_demes` with
`replicate_on_mean_fitness` and optional `replicate_copy_germline`.
Events and `extra_target_deme_preserved` are recorded.

This is **not** Avida C++ deme hardware, not MLS2 at literature scale,
and not a major transition. Germline parent identity is fitness-max or
an explicit index — not an evolved soma/germline network.

---

## 4. Goldsby 2012-aligned specialist measurement

Goldsby, Dornhaus, Kerr, and Ofria (PNAS 2012,
doi:10.1073/pnas.1202233109) used 0 / 25 / 50 CPU-cycle switch delays,
~50 replicates, a colony resource quota, Gorelick mutual information,
isolation tests, and noted that **clonal** groups can still differentiate
behaviorally.

Phase L records those *kinds* of measurement on the existing analog:

- genotypic specialist fraction (XOR `work_a` / `work_b` in the genome)
- behavioral specialist fraction (only one task executed in group)
- generalist residual
- Gorelick NMI analog
- colony-quota analog (both task yields must clear a fraction of group
  size × yield) — **not** Avida resources
- clonal-group assay (identical genomes on the messaging analog)
- ancestral vs evolved isolation competence
- delay dose-response observation (whether specialist fraction is
  non-decreasing with delay)

`is_goldsby_2012_pnas_experiment` cannot be set True.
`isolation_collapse_is_evolved_autonomy_loss` cannot be set True.
Research default remains 50 replicates; smoke uses 4.

---

## 5. Phase K coordination ablation → evidence (optional, honest)

Phase K's `run_evolved_coordination_instruction_experiment` already
measures messaging on vs off. Phase L adds:

- `phase_k_coordination_to_communication_ablation` — reshape numbers as
  a Phase H-shaped object (`claim_gate_ablation_result_set=False`)
- `feed_phase_k_coordination_ablation_evidence` — package an evidence
  object
- `earn_collective_intelligence_candidate_flags(coordination=...)` —
  duck-typed; may propose `ablation_result` only at research scale with
  a payoff drop and successful retrieves

Defaults: `propose_candidate_flags=False`, `smoke=True` → all proposed
flags False. Constructing the evidence object does **not** write
ClaimGate state. Smoke never earns.

---

## 6. RAG pointers added or updated in Phase L

Canonical machine corpus: `src/codontrace/genesis/rag/corpus/seed.jsonl`.

| `doc_id` | Authority | Why it is here |
|---|---|---|
| `avida_cfg_organism_messaging` | **new** | Avida ORGANISM_MESSAGING / send-msg / retrieve-msg / broadcast / block |
| `avida_cfg_deme_group` | **new** | avida.cfg `DEME_GROUP` / `DEMES_*` / GERMLINE + wiki Deme-introduction |
| `goldsby_ofria_avida_messaging_germline` | updated | Phase L FIFO / facing / block / DEME_GROUP analog |
| `goldsby_2012_pnas_task_switching` | updated | Phase L aligned specialist *measurement* (not the PNAS experiment) |

```python
from codontrace.genesis import search_corpus, cite_sources
from codontrace.genesis.phase_l import (
    run_organism_messaging_fidelity_experiment,
    run_goldsby_aligned_specialist_campaign,
    feed_phase_k_coordination_ablation_evidence,
)
from codontrace.genesis.phase_k import run_evolved_coordination_instruction_experiment

msg = run_organism_messaging_fidelity_experiment(smoke=True)
goldsby = run_goldsby_aligned_specialist_campaign(smoke=True)
feed = feed_phase_k_coordination_ablation_evidence(
    run_evolved_coordination_instruction_experiment(smoke=True)
)
assert msg.is_avida_cpp_port is False
assert goldsby.is_goldsby_2012_pnas_experiment is False
assert feed.claim_gate_flags_auto_set is False
print(cite_sources(search_corpus("Avida ORGANISM_MESSAGING DEME_GROUP", k=5)))
```

Print-only smoke: `examples/genesis_phase_l_avida_fidelity.py`.

---

## 7. What is still missing for literature-grade CI

1. Avida C++ ORGANISM_MESSAGING / `DEME_GROUP` at literature scale (Phase L
   is a closer analog: FIFO + facing ring + block + deme replicate).
2. The actual Goldsby 2012 PNAS experiment (Avida CPU, spatial colonies,
   colony resource quota, 50× hardware). Isolation failure here is still
   not evolved autonomy loss.
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

Forbidden after Phase L messaging/DEME_GROUP/Goldsby-aligned surfaces,
the optional ablation feed, and RAG retrieval: `agi`, `intelligence`,
`collective_intelligence`, `tokyo_type1_passed`, `avida_replacement`,
`open_ended_intelligence`.

Name the project **CodonTrace Genesis**. Package remains `codontrace`.
