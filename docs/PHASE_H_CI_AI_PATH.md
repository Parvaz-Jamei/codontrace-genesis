# Phase H — collective intelligence then broader AI/OEE (honest path)

CodonTrace Genesis Phase H is **engineering toward evidence**, not a claim
that collective intelligence or artificial intelligence has been achieved.
Library-complete beta is not “done.” ClaimGate stays the authority.

**Claim ceiling:** `runtime_observation` for new harnesses; RAG retrieval is
documentation / measurement design.

**Still blocked:** `collective_intelligence`, `proved_collective_intelligence`,
`intelligence`, `agi`, `open_ended_intelligence`, `tokyo_type1_passed`,
`avida_replacement`.

`collective_intelligence_candidate` remains allowed **only** when the full
ClaimGate flag set is actually present. Phase H printers list missing flags
and **do not set them**.

Cross-links: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md),
[`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md) (Phase I evidence harnesses),
[`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md) (Phase J honest replay + Price scaffold),
[`PHASE_K_CI_DEPTH.md`](PHASE_K_CI_DEPTH.md) (Phase K CI-depth measurements),
[`PHASE_L_AVIDA_FIDELITY.md`](PHASE_L_AVIDA_FIDELITY.md) (Phase L Avida-fidelity analogs),
[`rag/README.md`](rag/README.md),
[`SOCIAL_COLLECTIVE_INTELLIGENCE_PROTOCOL.md`](SOCIAL_COLLECTIVE_INTELLIGENCE_PROTOCOL.md),
[`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md),
[`../CLAIMS.md`](../CLAIMS.md).

---

## 1. What shipped

| Surface | Role | Honesty |
|---|---|---|
| Literature RAG (`codontrace.genesis.rag`) | Ingest + keyword/TF-IDF/hash search over citable digests | Retrieving a paper is not evidence |
| Communication ablation harness | Messaging on vs off, multi-seed, Cohen's *d* | Status `measured_runtime_observation`; does **not** set `ablation_result` |
| Group-vs-individual effect-size campaign | Configurable `seed_count` (research default **12**, smoke **2**) | Delta is group fitness, not intelligence |
| Task-switching cost hook | Goldsby 2012 analog reweights DoL fitness shares | Not a 50-replicate PNAS experiment; not evolved DoL |
| Candidate checklist printer | Lists missing ClaimGate flags | Printing ≠ unlocking |

Default Phase A–E digest pins are unchanged.

---

## 2. RAG pointers (papers ingested)

Canonical machine corpus: `src/codontrace/genesis/rag/corpus/seed.jsonl`.
Human copies: [`rag/corpus/`](rag/corpus/). Query API:

```python
from codontrace.genesis import search_corpus, cite_sources
from codontrace.genesis.phase_h import format_collective_intelligence_candidate_checklist

hits = search_corpus("how to get collective intelligence evidence", k=8)
print(cite_sources(hits))
print(format_collective_intelligence_candidate_checklist())
```

Print-only smoke: `examples/genesis_rag_query.py`.

| `doc_id` | Authority | CodonTrace Genesis has | Lacks / next |
|---|---|---|---|
| `miikkulainen_forrest_2021_nature_mi` | Nature MI 2021 EC vs biology | Life-loop, QD, measurement | Biological-scale *N*, weak selection, evolved G→P, major transitions |
| `goldsby_2012_pnas_task_switching` | PNAS 2012 task-switching → DoL | Phase K/L analog harness + aligned specialist *measurement* | The PNAS experiment itself; evolved autonomy loss |
| `goldsby_ofria_avida_messaging_germline` | Messaging / GermlineReplication / GECCO 2008 | Buffer + Phase K/L instruction analog + ablation | Avida C++; evolved germline networks |
| `avida_cfg_organism_messaging` | Avida ORGANISM_MESSAGING inst-set | Phase L FIFO / facing / block analog | C++ hardware; grid neighborhood |
| `avida_cfg_deme_group` | avida.cfg `DEME_GROUP` / wiki Deme-introduction | Phase L `maybe_replicate_demes` analog | C++ deme hardware; MLS2 |
| `channon_2024_tokyo_type1` | Channon 2024 procedure | Measurement steps | Type 1 **pass** |
| `soros_stanley_2014_chromaria` | Chromaria OEE conditions | AliveGate / spatial / Phase C | Four-condition knock-out; unbounded phenotype |
| `stanley_2017_open_endedness_creative_intelligence` | Open-endedness as creative-intelligence component | MODES/Bedau/QD instruments | Creative intelligence as a result |
| `szathmary_maynard_smith_michod_transitions` | Major transitions; export-of-fitness | Deme tags + group fitness | New Darwinian individual |
| `jaxlife_2024` | JaxLife NN culture/tech | Complementary ecology + audit | NN agents; not a port |
| `cao_yang_2026_vocabulary_verifier_gaps` | arXiv 2607.09560 | ADF proposals; external ClaimGate | Endogenous vocabulary; co-evolving verifier |
| `chaturvedi_2026_role_mls` | arXiv 2604.00810 MLS roles | Group-vs-individual effect sizes | Coupled channels; dynamic endogenous roles |
| `conlin_2023_dol_multicellularity_avida` | bioRxiv 2023.03.15.532780 | Germline/soma *tags* | Entrenchment / revertant assays |

---

## 3. Build plan toward CI, then broader AI/OEE

Keep going until **evidence** exists. Do not unlock claims by weakening the gate.

### 3.1 Collective-intelligence evidence (still missing)

These are the literature-grade bars. Phase H makes the first three *runnable
measurements*; they remain insufficient for `collective_intelligence`.

1. **Communication must pay** — messaging on vs off drops group payoff at
   research seed counts, with effect size. Harness: `run_communication_ablation_experiment`.
   Still missing: literature-scale *N*, evolved instructions (not a buffer).
2. **Group-over-individual evolutionary outcome** — deme-level selection
   changes lineage outcome vs organism-only, ≥12 seeds, effect size.
   Harness: `run_group_vs_individual_effect_size_campaign` (research default 12).
   Still missing: true MLS treatment vs ranking; heldout partners.
3. **Task-switching costs drive DoL** — Goldsby 2012 sweep. Hook:
   `apply_task_switching_cost_to_dol`. Still missing: evolved specialists and
   isolation failure under high cost.
4. **Heldout unfamiliar partners** — ClaimGate `heldout_protocol` /
   familiar vs unfamiliar. Status remains `not_run`.
5. **Non-capsule cooperation + role complementarity** — not capsule transfer;
   not round-robin tags.
6. **Export-of-fitness / transition in individuality** — Michod; Szathmáry &
   Maynard Smith. `major_transition_in_individuality` stays False.

Only when those flags are *true from experiments* may a researcher request
`collective_intelligence_candidate`. `collective_intelligence` stays forbidden
until the project explicitly revises ClaimGate with new evidence policy —
this Phase does **not** do that.

### 3.2 Broader AI / OEE (after CI instrumentation, not instead of honesty)

- Chromaria four-condition knock-outs (Soros & Stanley).
- Channon 2024 procedure with pre-registered pass criteria — still do not
  claim a pass from implementing steps.
- Vocabulary + verifier gaps (arXiv 2607.09560): macros that change the search
  frame *and* a verifier that is not a weakened ClaimGate.
- Nature MI 2021: large-*N* weak selection; developmental G→P; major
  transitions as results.
- JaxLife / ASAL stay complementary / out of core.

Stanley’s point remains: without open-endedness as a **result**, CodonTrace
Genesis has not got that component of creative intelligence.

---

## 4. ClaimGate remainder

Allowed when objects exist: `runtime_observation`,
`oee_measurement_only`, `tokyo_type1_measurement_only`,
`collective_intelligence_candidate` (full flags only).

Forbidden after Phase H harnesses and RAG retrieval: `agi`, `intelligence`,
`collective_intelligence`, `tokyo_type1_passed`, `avida_replacement`,
`open_ended_intelligence`.

Name the project **CodonTrace Genesis**. Package remains `codontrace`.

---

## 5. Phase I continues the evidence path

Phase I ([`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md)) makes heldout
unfamiliar-partner generalization, evolved (not assigned) DoL, and MLS
*outcome* (not only a fitness delta) runnable, plus an export-of-fitness
scaffold that keeps `major_transition_in_individuality=False`. ClaimGate
flags can be *earned* from research-scale evidence objects and are **never**
auto-set from smokes. `collective_intelligence` stays blocked.

---

## 6. Phase J continues the evidence path

Phase J ([`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md)) makes
`replay_verification` earnable from independent campaign digest
re-execution (never faked; smoke never earns) and adds a Price-equation /
Okasha MLS1 covariance **snapshot**. When every candidate flag is honestly
present at research scale, ClaimGate may allow
`collective_intelligence_candidate`. Bare `collective_intelligence` stays
forbidden.

---

## 7. Phase K continues the evidence path

Phase K ([`PHASE_K_CI_DEPTH.md`](PHASE_K_CI_DEPTH.md)) adds evolved
send/retrieve/broadcast instruction genomes that can *pay* under ablation,
a Goldsby-scale CPU-delay specialist harness (research default 50
replicates), multi-generation Price with a transmission term, and
Michod/Conlin conflict-suppression hooks. Smoke never earns flags. Bare
`collective_intelligence` stays forbidden.
