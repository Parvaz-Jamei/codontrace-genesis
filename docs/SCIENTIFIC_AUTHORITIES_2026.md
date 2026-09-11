# Scientific authorities checklist (2026 bugfix mapping)

This document maps the `codontrace==0.3.0b2` eval bugfixes to the literature
those fixes are *aligned with*. Alignment is **software capability** and
**runtime observation / measurement design**. It is **not** proof of
intelligence, AGI, instinct evolution, collective intelligence, evolved
plasticity, Avida replacement, or open-ended evolution (OEE).

ClaimGate remains the authority. Do not cite this file as a Type 1 OEE pass,
an intelligence result, or a comparator-superiority claim.

Cross-links: [`PHASE_D_LITERATURE.md`](PHASE_D_LITERATURE.md) (MODES / Bedau),
[`PHASE_E_LITERATURE.md`](PHASE_E_LITERATURE.md) (plasticity / demes / capsules),
[`../CLAIMS.md`](../CLAIMS.md).

---

## Authorities (use these; keep ClaimGate)

| ID | Authority | What we *may* align with | What we must **not** claim |
|---|---|---|---|
| `modes_2019` | Dolson, Vostinar, Wiser, Ofria 2019 *Artificial Life* (MODES) plus ISAL MODES assessment / prediction-games analyses | Persistence filter informed by coalescence; change / novelty / complexity / ecology **only after persistence** | Open-endedness proved; intelligence; OEE Type 1 passed |
| `channon_2024_tokyo_type1` | Channon 2024 *Artificial Life*: Tokyo Type 1 OEE testing via Bedau evolutionary activity + shadow normalization | Measurement-hook vocabulary `tokyo_type1_measurement_only` (aliases to ClaimGate `oee_measurement_only`) | **Never** `tokyo_type1_passed` / Type 1 OEE passed |
| `avida_2004_cfg_2_14_0` | Ofria & Wilke 2004 *Artificial Life*; live `avida.cfg` `VERSION_ID` 2.14.0 | `BIRTH_METHOD` / `PREFER_EMPTY`, `POPULATION_CAP`, `RECOMBINATION_GROUP` (`RECOMBINATION_PROB`, `MAX_BIRTH_WAIT_TIME`, `SAME_LENGTH_SEX`, `TWO_FOLD_COST_SEX`, `MAX_GLOBAL_BIRTH_CHAMBER_SIZE` 3600), `DEMES_*` / `GERMLINE_*`, `MESSAGE_*` buffers, `ENERGY_*` / sensing | Bit-identical Avida; Avida replacement |
| `plasticity_protocol` | Clune 2007; Lalejini & Ofria 2016; Frontiers 2021 Adaptive Phenotypic Plasticity (Ghalambor four conditions) | Subsequent-action effect under a sensory cue, with ablation | Evolved phenotypic plasticity; associative learning proved |
| `comparators_docs_only` | JaxLife (arXiv 2409.00853, 2024) agentic ALife; Aevol_4b ISAL 2024 bioinformatics bridge; OntoAvida / avidaR *Sci Data* 2023 | Documentation comparators / existing OntoAvida-style export objects | Superiority; implemented JaxLife or Aevol_4b ports in this bugfix |
| `asal_future_only` | ASAL / foundation-model open-endedness (arXiv 2412.17799) | Cite as a **future** measurement option | CLIP / foundation-model OE **not implemented** in this bugfix |

Cheap ClaimGate API for Channon vocabulary: request
`tokyo_type1_measurement_only` (or call `evaluate_tokyo_type1_measurement_claim`).
Final label stays `oee_measurement_only`. `tokyo_type1_passed` and
`tokyo_type1_oee_proved` are forbidden.

---

## Fix → authority mapping

| Fix ID | Bug | What the code now does | Authorities | Honest claim ceiling |
|---|---|---|---|---|
| `sexual_birth_placement_metrics` | Chamber offspring incremented `births` / sexual pairs but `adjacent_or_displaced_births` and `same_cell_births` stayed 0 | Birth-time chamber placement records update the same placement counters as the asexual path | `avida_2004_cfg_2_14_0` (`RECOMBINATION_GROUP` / birth chamber); `modes_2019` (honest birth counts before any persistence filter) | `runtime_observation` |
| `reproduction_mode_validation` | `reproduction_mode='not_a_mode'` stored a raw `str` | Unknown strings raise; valid names coerce to `ReproductionMode` | `avida_2004_cfg_2_14_0` (recombination on/off is a real config, not a free string); ClaimGate discipline | Software capability (configuration error) |
| `phase_e_capsule_wiring` | Capsule writes/reads/substitutions looked empty while deme messaging moved | Last-seen counters; unconstrained seed slot; **subsequent action** under a matching cue; capsules-off ablation differs | `plasticity_protocol`; `avida_2004_cfg_2_14_0` (`ENERGY_*` / sensing, `MESSAGE_*` still separate) | `runtime_observation` — **not** evolved plasticity |
| `life_loop_capacity_footgun` | `capacity = max(pop, 8)` with `pop=8` blocked Darwinian births | For `population >= 8`, capacity exceeds initial *N* and the world is widened so birth can find empty/adjacent room. Historical pop&lt;8 pins stay `capacity=8` on 6×4 | `avida_2004_cfg_2_14_0` (`BIRTH_METHOD` / `PREFER_EMPTY`, `POPULATION_CAP` must not equal current *N*) | `runtime_observation` |
| `summarize_garbage_input` | Summarize helpers returned silent zeros on `None` / garbage | `TypeError` instead of fake zero metrics | Measurement integrity (MODES/ClaimGate: do not treat missing records as zeros) | Error, not a scientific claim |
| `tokyo_type1_measurement_hook` | OEE metrics already existed at `oee_measurement_only` | Expose Channon 2024 vocabulary as an **alias**; reject Type-1-passed labels; no CLIP/ASAL OE | `channon_2024_tokyo_type1`; `modes_2019`; `asal_future_only` (cite only) | `oee_measurement_only` — **Type 1 not passed** |

Default Phase A–E spec / snapshot / tick digest pins for `life_loop_world(seed=7, tick_count=12, population=6)` are unchanged.

---

## Conservative wording (copy into PRs / CLAIMS)

Allowed:

- Chamber offspring now update placement counters like the asexual path (Avida birth-chamber parity of **records**, not an Avida port).
- Capacity for `population >= 8` exceeds initial *N*, in the spirit of not setting Avida `POPULATION_CAP` equal to current population when birth needs empty/replace room.
- Capsule slots can change a later action under a sensory cue; capsules-off ablation yields a different replay digest (plasticity *protocol* instrumentation).
- `tokyo_type1_measurement_only` is a measurement-hook alias for `oee_measurement_only` (Channon 2024 vocabulary).

Blocked:

- Tokyo Type 1 OEE passed.
- Intelligence, AGI, consciousness, collective intelligence.
- Instinct evolution proved; evolved phenotypic plasticity; associative learning proved.
- Open-ended intelligence / unbounded OEE.
- CodonTrace replaces or outperforms Avida, JaxLife, Aevol, OntoAvida, or ASAL.
- CLIP / foundation-model open-endedness scoring is implemented.
