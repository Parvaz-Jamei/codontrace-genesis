# Scientific authorities map (2026)

This document maps CodonTrace Genesis **software surfaces** to world-authority
digital-evolution, OEE-measurement, plasticity, and modern-comparator literature.
It is a completeness and honesty checklist after Phase A–E on `main`
(`0.3.0b2`) plus the opt-in Phase G materials overlay. It does **not** claim
intelligence, AGI, proved open-ended evolution, Tokyo Type 1 *passed*, instinct
evolution proved, collective intelligence, evolved phenotypic plasticity,
realistic chemistry, wet-lab equivalence, or that CodonTrace Genesis replaces Avida,
Aevol, JaxLife, MABE, or Empirical.

**Claim ceiling for this map:** software capability / `runtime_observation` /
`oee_measurement_only` / `tokyo_type1_measurement_only`.

**Blocked:** `tokyo_type1_passed`, `tokyo_type1_proved`, `channon_2024_passed`,
`proved_open_endedness`, `open_ended_intelligence`, `avida_replacement`, AGI,
and related aliases in `ScientificClaimGate`. Type 1 not passed.

ClaimGate remains the authority. Do not cite this file as a Type 1 OEE pass,
an intelligence result, or a comparator-superiority claim.

Cross-links: [`PHASE_D_LITERATURE.md`](PHASE_D_LITERATURE.md) (MODES / Bedau),
[`PHASE_E_LITERATURE.md`](PHASE_E_LITERATURE.md) (plasticity / demes / capsules),
[`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md) (literature vs
CodonTrace Genesis reality; not close to AGI),
[`PHASE_H_CI_AI_PATH.md`](PHASE_H_CI_AI_PATH.md) (Phase H RAG + CI pathway),
[`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md) (Phase I CI evidence harnesses),
[`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md) (Phase J honest replay + Price scaffold),
[`PHASE_K_CI_DEPTH.md`](PHASE_K_CI_DEPTH.md) (Phase K CI-depth measurements),
[`PHASE_G_MATERIALS_LITERATURE.md`](PHASE_G_MATERIALS_LITERATURE.md) (named materials),
[`../CLAIMS.md`](../CLAIMS.md).

Phase A–E default preset **spec digest pins stay stable**. New measurement
objects are opt-in library APIs.

---

## 1. Mandatory authorities (cite + map)

### 1.1 Core digital evolution

| Authority | What it is | CodonTrace Genesis mapping | Status |
|---|---|---|---|
| Ofria & Wilke 2004, *Artificial Life* — Avida platform | Spatial digital organisms, instruction genomes, ecology | Life-loop ecology preset; instruction/genome substrate; audit/replay layer | **partial** (Python library, not C++ Avida ISA clone) |
| Lenski, Ofria, Pennock, Adami 2003 *Nature* — complex features | Evolution of complex features from simpler building blocks | Measurement of fitness/behavior trajectories (Phase D); not a replication of the 2003 experiment | **deferred** as a paper-grade replication; **landed** as substrate + metrics |
| Live `devosoft/avida` `avida.cfg` `VERSION_ID` 2.14.0 config groups | Authoritative knob names for reproduction, sex, demes, messaging, energy, sensing, resources, Logic-9 reactions | See [§2 Avida.cfg group map](#2-avidacfg-2140-group-map) | mixed: **landed / partial / deferred** per group |
| BMC Evol Biol 2021 metabolic signaling in Avida | Resource × population × mutation as interacting experimental axes | Recorded as design axes on `Logic9ReactionPack.resource_population_mutation`; not a paper replication | **partial** (axes recorded; not that paper's experiment) |

### 1.2 OEE measurement (measurement-only)

| Authority | What it is | CodonTrace Genesis mapping | Status |
|---|---|---|---|
| Dolson, Vostinar, Wiser, Ofria 2019 *Artificial Life* — MODES toolbox | Change, novelty, complexity, ecological potential **after a persistence filter** | `ModesAssessment`, `filter_persistent_lineages`, explicit `persistence_window_t` | **partial** (Python analog, not bit-identical C++ MODES) |
| Empirical MODES / systematics integration notes | Persistence filter is sensitive to coalescence window; full phylogenetic systematics + shadow runs are the careful path | Opt-in Python shuffled-parentage adapter `build_empirical_systematics_shadow` produces a real `shadow_digest` for Tokyo step_4; default off; never auto-passes Type 1 | **partial** (Python analog, not Empirical C++ systematics); **landed** as opt-in adapter |
| Bedau evolutionary activity statistics | Novelty, diversity, (cumulative) activity of components | `BedauActivitySurface` | **partial** |
| Channon 2024 *A Procedure for Testing for Tokyo Type 1 Open-Ended Evolution* (*Artificial Life*) | Measurement-step vocabulary: activity, novelty, shadow/normalization, multi-replicate decision procedure | `TokyoType1MeasurementProtocol` with claim ceiling `tokyo_type1_measurement_only`; pack-level hook aliases to `oee_measurement_only` unless Channon steps are recorded; `tokyo_type1_passed` **blocked** | **landed** as measurement protocol; **blocked** as a pass verdict |
| Packard et al. 2019 Tokyo types overview | Type taxonomy (Type 1 = ongoing generation of adaptive novelty, etc.) | Cited in protocol literature refs; types 2–3 not implemented as pass tests | **cite / partial** (Type 1 measurement steps only) |
| Borg et al. 2023 cultural OEE | Cultural/open-endedness in human/cultural systems | Cite only — CodonTrace Genesis is not a cultural-evolution engine | **deferred** (cite only) |

### 1.3 Plasticity / memory / collective

| Authority | What it is | CodonTrace Genesis mapping | Status |
|---|---|---|---|
| Clune 2007; Lalejini & Ofria 2016 | Phenotypic plasticity in digital evolution / fluctuating environments | Phase C fluctuating env + Phase E `sense-react` / `read_environment_cue` | **partial** (substrate + protocol, not evolved-plasticity proof) |
| Frontiers 2021 Adaptive Phenotypic Plasticity | Four Ghalambor conditions as experimental-design checklist | `PlasticityProtocolSpec` / `GHALAMBOR_CLUNE_CONDITIONS` | **landed** as checklist object |
| Goldsby messaging / GermlineReplication / `DEME_GROUP` | `send_message`, `retrieve_message`, `broadcast_message`, `block_propagation`; soma vs germline; deme replicate-on-mean-fitness | Phase E deme messaging + role gates + opt-in `CollectiveDemePayoffPack` + Phase F campaign + Phase H communication-ablation / effect-size harnesses + Phase I heldout-partner / evolved-DoL / MLS-outcome analogs | **partial** (group fitness / `runtime_observation`; Phase F heldout `not_run`; Phase I heldout/DoL/MLS harnesses are measurement-only and do not auto-set ClaimGate flags from smoke; `collective_intelligence` blocked) |
| GECCO 2008 digital germlines | Cooperative networks / germline replication | Role / propagule-eligibility tags; germline copy on deme replicate when enabled | **partial** (gates + recorded payoff, not evolved division of labor) |
| Am Nat 2020 associative learning | Learning in Avida | Capsule/memory slots with **real** subsequent action/ATP/task effects; opt-in `LearningCausalPayoffPack` (cue→action→ATP, ablation, ≥2 seeds) | **partial** (protocol instrumentation; `instinct_improved` stays gated; not proved learning) |
| PLOS One odometry case study | Navigation / odometry in digital organisms | Same capsule/memory mapping via the learning-payoff protocol | **partial** (hooks vs proved learning) |

### 1.4 Modern comparators (gap analysis, not copy)

| Comparator | What it is | What CodonTrace Genesis deliberately is | Gap / status |
|---|---|---|---|
| JaxLife 2024 (arXiv 2409.00853) | Embodied neural-network agents; culture/tech accumulation | Instruction/genome ecology + **audit/replay/claim-gate** evidence layer | CodonTrace Genesis is **not** an embodied NN culture engine. JaxLife-style culture/tech accumulation is **deferred**. Basal energy-budget *inspiration* is **landed** on the life-loop preset. |
| Aevol_4b ISAL 2024 | Genome encoding / bioinformatics bridge | Semantic/instruction genomes with digest-backed lineage | Bioinformatics-grade genome export / Aevol encoding parity is **deferred**. Variable-genome tokens are **partial**. |
| OntoAvida / avidaR 2023 (Sci Data; PeerJ CS) | Phenotype / transcriptome export for analysis | `PhenotypeTranscriptomeEvidence` JSON+digest (genome + action-execution counts + fitness/ATP/role) | **partial** — analysis-ready export, not a biological transcriptome simulator |
| ASAL 2024/25 foundation-model OE search (arXiv 2412.17799) | Foundation-model / CLIP open-ended search | Out of scope for the dependency-free core | **deferred**; CLIP / foundation-model OE **not implemented**; do **not** add heavy FM dependencies |

---

## 2. Avida.cfg 2.14.0 group map

Authoritative live tree: [`devosoft/avida`](https://github.com/devosoft/avida)
`avida.cfg` groups (`VERSION_ID` 2.14.0). Mapping is **semantic**, not a C++ port.

| Avida group / knob family | Avida role | CodonTrace Genesis status | Surface |
|---|---|---|---|
| `REPRODUCTION` / `BIRTH_METHOD` / `PREFER_EMPTY` | How offspring are placed; prefer empty cells | **landed** (life-loop default `ADJACENT_FREE`; `SAME_CELL` and `REPLACE_OCCUPIED` explicit) | `OffspringPlacementPolicy`, `ReproductionConfig` |
| World / `POPULATION_CAP` > founders | Room to birth (grid not filled at t=0; do not set `POPULATION_CAP` equal to current *N*) | **landed** (pop&lt;8 keeps historical `capacity=8` on 6×4; `population >= 8` uses `max(pop*2, 16)` and a widened world) | `GenesisRuntimeProfile.life_loop_world` |
| `RECOMBINATION_GROUP` (`RECOMBINATION_PROB`, `SAME_LENGTH_SEX`, `TWO_FOLD_COST_SEX`, `MAX_BIRTH_WAIT_TIME`) | Sexual recombination / birth chamber | **landed** (opt-in) | `ReproductionMode.SEXUAL_CROSSOVER`, `SexualRecombinationConfig` |
| `DEME_GROUP` / `GERMLINE` / GermlineReplication | Group/deme replication; germline vs soma | **partial** | Phase E `DemeConfig`, `RoleKind`, deme-replication event |
| `ORGANISM_MESSAGING` | Send/retrieve/broadcast/block | **partial** | Phase E Goldsby-style buffer |
| `ENERGY` | Energy/ATP metabolism | **partial** | Dual ATP + basal drain on life-loop preset |
| `SENSING` | Environmental cues | **partial** | Phase C snapshots + Phase E `read_environment_cue` |
| `RESOURCE` chemostat (`initial` / `inflow` / `outflow`) | Limited resources; Avida-ED chemostat/periodic literature | **landed** (opt-in Phase C); named-material extension **landed** (opt-in Phase G) | `ResourceSpec`, `EnvironmentConfig`; `MaterialSpec` / `MaterialsConfig` |
| Logic-9 / reaction–task metabolic coupling | Tasks as reactions consuming resources (`res{TASK}`) and awarding merit | **landed** opt-in semantic analog (not a NAND CPU) | `Logic9ReactionConfig`, `build_logic9_reaction_pack`; claim ceiling `runtime_observation` |
| Named materials / chemistry-effect overlay | Energy yield, toxicity, permeability, intracellular profiles | **partial** (effect coefficients + ontology-id schema hooks; GEM/MD deferred) | `materials_world`, `MaterialBindingSchema` |
| Full Avida ISA / hardware | Instruction-level CPU | **deferred** (deliberately different genome/ISA) | — |

---

## 3. Feature × authority matrix

Status key: **landed** = callable library surface with tests; **partial** = analog
or subset; **deferred** = documented non-goal or future.

| Feature | Avida / avida.cfg | MODES 2019 | Channon 2024 | JaxLife 2024 | Aevol_4b 2024 | CodonTrace Genesis |
|---|---|---|---|---|---|---|
| Spatial eat/survive/reproduce loop | landed analog | n/a | n/a | energy-budget inspiration only | n/a | **landed** (`life_loop_world`) |
| Capacity > initial population (room to birth) | `PREFER_EMPTY` + unfilled grid / `POPULATION_CAP` | n/a | n/a | n/a | n/a | **landed** (regression-tested) |
| Sexual recombination / birth chamber | `RECOMBINATION_GROUP` | n/a | n/a | n/a | diploid meiosis analog opt-in | **landed** opt-in; `diploid_meiosis` + `TWO_FOLD_COST_SEX` default off |
| Chemostat / fluctuating resources | `RESOURCE` + Avida-ED | n/a | n/a | n/a | n/a | **landed** opt-in Phase C |
| Named materials / chemistry-effect overlay | resource/reaction analog + ontology-id hooks | n/a | n/a | energy-budget inspiration only | n/a | **landed** opt-in Phase G; GEM/MD **deferred**; wet-lab **blocked** |
| Persistence-filtered change/novelty/complexity/ecology | post-hoc analyze | **partial** analog | feeds Type 1 activity/novelty steps | n/a | n/a | **landed** Phase D + coalescence-window docs |
| Empirical systematics shadow phylogeny | n/a | **partial** analog | opt-in `shadow_digest` for step_4; never a pass | n/a | n/a | **landed** opt-in Python adapter (`empirical_systematics_shadow_run` default False) |
| Multi-seed Tokyo measurement campaign | n/a | Bedau/MODES inputs | **landed** `TokyoType1MeasurementCampaign` (`seed_count≥2`) | n/a | n/a | **landed**; `tokyo_type1_passed` **blocked** |
| Logic-9 reaction→resource→merit | `RESOURCE` / LOGIC tasks | n/a | n/a | n/a | n/a | **landed** opt-in semantic analog; `avida_replacement` blocked |
| Learning causal payoff (cue→action→ATP) | learning/odometry papers | n/a | n/a | n/a | n/a | **landed** opt-in protocol; `instinct_improved` gated |
| Collective deme payoff / germline replicate | Goldsby / GECCO 2008 / GermlineReplication | n/a | n/a | n/a | n/a | **landed** opt-in ledger; `collective_intelligence` blocked |
| Channon/Avida/MODES/shadow suite | n/a | `persistence_window_t` sweep | Tokyo JSON per window | n/a | n/a | **landed** `run_channon_avida_modes_shadow_suite`; Type 1 not passed |
| Bedau activity surface | n/a | complementary | **landed** as activity step | n/a | n/a | **landed** |
| Tokyo Type 1 *measurement* protocol | n/a | inputs | **landed** step labels | n/a | n/a | **landed**; pass claim **blocked** |
| Tokyo Type 1 *passed* | n/a | n/a | procedure exists in literature | n/a | n/a | **blocked** (`tokyo_type1_passed`) |
| Capsule/memory subsequent effects | learning/odometry papers | n/a | n/a | n/a | n/a | **landed** opt-in Phase E |
| Deme messaging / germline roles | Goldsby / GECCO 2008 / wiki | n/a | n/a | n/a | n/a | **partial** |
| Ghalambor four-condition checklist | plasticity literature | n/a | n/a | n/a | n/a | **landed** checklist |
| Phenotype/transcriptome export | OntoAvida/avidaR | n/a | n/a | n/a | bioinformatics bridge **deferred** | **partial** (strengthened Phase E export) |
| Embodied NN + culture/tech | n/a | n/a | n/a | JaxLife core | n/a | **deferred** (CodonTrace Genesis is genome/instruction ecology + audit) |
| Foundation-model OE search | n/a | n/a | n/a | n/a | n/a | **deferred** (ASAL / CLIP; no FM deps) |
| Avida replacement / superiority | — | — | — | — | — | **blocked** |

---

## 4. Eval bugfix → authority mapping

These rows map the `0.3.0b2` eval bugfixes (squash-merged from PR #7) onto the
same authorities. Alignment is **software capability** and **runtime
observation / measurement design**.

| Fix ID | Bug | What the code now does | Authorities | Honest claim ceiling |
|---|---|---|---|---|
| `sexual_birth_placement_metrics` | Chamber offspring incremented `births` / sexual pairs but `adjacent_or_displaced_births` and `same_cell_births` stayed 0 | Birth-time chamber placement records update the same placement counters as the asexual path | `avida.cfg` 2.14.0 (`RECOMBINATION_GROUP` / birth chamber); MODES 2019 (honest birth counts before any persistence filter) | `runtime_observation` |
| `reproduction_mode_validation` | `reproduction_mode='not_a_mode'` stored a raw `str` | Unknown strings raise; valid names coerce to `ReproductionMode` | `avida.cfg` 2.14.0 (recombination on/off is a real config, not a free string); ClaimGate discipline | Software capability (configuration error) |
| `phase_e_capsule_wiring` | Capsule writes/reads/substitutions looked empty while deme messaging moved | Last-seen counters; unconstrained seed slot; **subsequent action** under a matching cue; capsules-off ablation differs | Clune 2007 / Ghalambor plasticity protocol; `avida.cfg` (`ENERGY_*` / sensing, `MESSAGE_*` still separate) | `runtime_observation` — **not** evolved plasticity |
| `life_loop_capacity_footgun` | `capacity = max(pop, 8)` with `pop=8` blocked Darwinian births | For `population >= 8`, capacity exceeds initial *N* and the world is widened so birth can find empty/adjacent room. Historical pop&lt;8 pins stay `capacity=8` on 6×4 | `BIRTH_METHOD` / `PREFER_EMPTY`; `POPULATION_CAP` must not equal current *N* | `runtime_observation` |
| `summarize_garbage_input` | Summarize helpers returned silent zeros on `None` / garbage | `TypeError` instead of fake zero metrics | Measurement integrity (MODES/ClaimGate: do not treat missing records as zeros) | Error, not a scientific claim |
| `tokyo_type1_measurement_hook` | OEE metrics already existed at `oee_measurement_only` | Expose Channon 2024 vocabulary; pack-level request aliases to `oee_measurement_only` unless Channon steps are recorded; reject Type-1-passed labels; no CLIP/ASAL OE | Channon 2024; MODES 2019; ASAL (cite only) | `oee_measurement_only` / protocol `tokyo_type1_measurement_only` — **Type 1 not passed** |

Default Phase A–E spec / snapshot / tick digest pins for `life_loop_world(seed=7, tick_count=12, population=6)` are unchanged.

---

## 5. MODES persistence filter — coalescence-window semantics

Dolson et al. 2019 count change/novelty/complexity/ecological potential **only
for types that persist**. Empirical's systematics notes make the subtlety
explicit: the filter is a **forward window** of `t` updates. If `t` is near
the coalescence time of the extant population, most historical types drop out
even if they were successful for a long stretch. A full Empirical phylogeny
plus shadow/null systematics run is the careful publication path.

CodonTrace Genesis Phase D implements an **organism-id descendant graph** evaluated at
`generation + persistence_window_t`:

- An ancestor persists if it, or any descendant, is alive at the horizon.
- Self-survival counts as lineage continuation (the lineage did not go extinct).
- If the horizon census is missing, the filter returns no persistent ids
  (window not observed).
- Longer `t` is a stricter coalescence window: lineages that die out before
  the horizon are removed.

**Limitations (always recorded):**

- `coalescence_window_organism_id_graph_not_full_phylogeny`
- `no_empirical_systematics_shadow_run` unless a caller supplies a real shadow digest (opt-in `build_empirical_systematics_shadow` is a Python shuffled-parentage analog, not Empirical C++)
- `not_a_bit_identical_modes_cpp_port`
- `window_longer_than_mrca_filters_more_historical_types`

API: `persistence_window_t` is the explicit window (alias of
`persistence_window_generations` / `window_t`). See
`describe_modes_persistence_semantics()` and `PersistentLineageFilter`.

This is **measurement design**, not proof of open-endedness.

---

## 6. Channon 2024 Tokyo Type 1 — measurement protocol only

Channon (2024, *Artificial Life*) publishes a **procedure for testing** Tokyo
Type 1 OEE (Packard et al. 2019 taxonomy: ongoing generation of adaptive
novelty). CodonTrace Genesis implements the *measurement steps vocabulary* as
`TokyoType1MeasurementProtocol`:

| Step label | What is recorded | Pass claim |
|---|---|---|
| `step_1_activity_components` | Component/activity set from Bedau/MODES surfaces | never |
| `step_2_evolutionary_activity` | Novelty, diversity, cumulative activity series | never |
| `step_3_adaptive_novelty` | Persistence-filtered novelty/change | never |
| `step_4_shadow_normalization` | Shadow/null hook if a real digest is supplied; otherwise `unavailable` | never |
| `step_5_multi_seed_aggregation` | Seed count; `< 2` stays single-seed measurement | never |
| `step_6_claim_gate` | Ceiling `tokyo_type1_measurement_only` | `tokyo_type1_passed` **blocked** |

Two ClaimGate entry points, one forbidden pass:

- **Protocol:** `evaluate_tokyo_type1_measurement_claim(protocol)` with
  `channon_2024_steps_recorded` may keep ceiling `tokyo_type1_measurement_only`.
- **Pack cheap hook:** `evaluate_tokyo_type1_measurement_claim(pack)` requests
  `tokyo_type1_measurement_only` and aliases to `oee_measurement_only` unless
  those steps are recorded.
- **Forbidden:** `tokyo_type1_passed` (and related aliases). Measurement ≠ pass.

Anything **above** `tokyo_type1_measurement_only` requires a multi-seed
protocol object **and** is still not a pass: the gate rejects `tokyo_type1_passed`.
Borg et al. 2023 is cited only (cultural OEE is out of scope). CLIP / ASAL
foundation-model OE (arXiv 2412.17799) is **not** implemented.

---

## 7. Deliberate product identity vs comparators

CodonTrace Genesis is a **deterministic, replay/audit-first Python research
library** for instruction/genome digital-evolution experiments. Relative to:

- **Avida:** overlapping ecology/sex/resource/deme *semantics*, different ISA,
  first-class Python evidence objects, ClaimGate. Not a replacement.
- **JaxLife:** they accumulate culture/tech with embodied NN agents; we audit
  genome/instruction ecology. Complementary, not a port.
- **Aevol:** they bridge genome encoding to bioinformatics; we expose digest-backed
  genomes/lineage. Encoding-parity **deferred**.
- **OntoAvida/avidaR:** they export phenotype/transcriptome tables; we export
  digest-backed `PhenotypeTranscriptomeEvidence` (action-execution counts as a
  transcriptome *proxy*).
- **ASAL:** foundation-model / CLIP open-ended search is a future research option
  outside the core dependency set. CLIP / foundation-model OE is **not implemented**.

---

## 8. Scientific-gaps 2026 surfaces (opt-in)

These library APIs close remaining measurement/engineering gaps after PR #7+#8.
All are **opt-in**. Phase A–E default spec/snapshot/tick digest pins stay
stable. ClaimGate is not weakened.

| Surface | Literature | Status | Claim ceiling | Never claims |
|---|---|---|---|---|
| `build_empirical_systematics_shadow` | Empirical systematics/shadow notes; MODES 2019; Bedau; Channon 2024 step_4 | **landed** Python shuffled-parentage analog; default `enabled=False` | `oee_measurement_only` | Tokyo Type 1 passed; Empirical C++ port |
| `run_multi_seed_tokyo_measurement_campaign` | Channon 2024 multi-replicate decision procedure; Bedau; MODES | **landed** `seed_count≥2` | `tokyo_type1_measurement_only` | `tokyo_type1_passed` |
| `Logic9ReactionConfig` / `build_logic9_reaction_pack` | Ofria & Wilke 2004; avida.cfg 2.14.0 RESOURCE/LOGIC; BMC Evol Biol 2021 axes | **landed** semantic analog; default off | `runtime_observation` | Avida replacement; metabolic intelligence |
| `build_learning_causal_payoff_pack` | Am Nat 2020; PLOS One odometry; Clune/Lalejini/Frontiers 2021 | **landed** cue→action→ATP + ablation + multi-seed | `runtime_observation` | associative learning proved; `instinct_improved` stays gated |
| `build_collective_deme_payoff_pack` | Avida `DEME_GROUP` / GERMLINE; Goldsby messaging / DoL; GECCO 2008 germlines; Michod / Szathmáry major transitions | **landed** replicate-on-mean-fitness + contribution ledger | `runtime_observation` | `collective_intelligence` |
| `run_collective_deme_payoff_campaign` | Goldsby; `DEME_GROUP` multilevel selection; GECCO 2008; Michod / Szathmáry | **landed** ≥2-seed ranking + DoL metrics + group-vs-individual contrast; heldout/ablation `not_run`; MLS `scaffold_only` | `runtime_observation` | `collective_intelligence` / `proved_collective_intelligence` |
| `run_heldout_unfamiliar_partner_experiment` | Goldsby heldout / familiar vs unfamiliar; ClaimGate partner protocol | **landed** Phase I two-task analog; research-scale can earn heldout flags; smoke never earns | `runtime_observation` | `collective_intelligence` |
| `run_evolved_division_of_labor_experiment` | Goldsby 2012; Gorelick 2004 NMI | **landed** evolved preference + ablation; not assigned tags; not 50-replicate PNAS | `runtime_observation` | `collective_intelligence` |
| `run_mls_evolutionary_outcome_experiment` | Okasha 2006 MLS2; `DEME_GROUP` | **landed** majority-strategy contrast vs organism-only; not a rank table | `runtime_observation` | `collective_intelligence`; major transition |
| `build_export_of_fitness_observation` | Michod 2007 PNAS; Szathmáry & Maynard Smith | **landed** scaffold; isolation collapse marked as payoff construction; `major_transition_in_individuality=False` | `runtime_observation` | major transition; `collective_intelligence` |
| `build_replay_verified_ci_candidate_pack` | ClaimGate `replay_verification`; independent digest re-execution | **landed** Phase J; smoke never earns; same-object replay rejected | `runtime_observation`; `collective_intelligence_candidate` only with full earned flags | `collective_intelligence` |
| `run_price_equation_covariance_scaffold` | Price 1970; Okasha 2006 MLS1 | **landed** last-generation between/within snapshot; no transmission term | `runtime_observation` | full Price paper; major transition; `collective_intelligence` |
| `run_channon_avida_modes_shadow_suite` | Channon 2024; MODES `persistence_window_t`; Empirical shadow | **landed** window sweep + MODES digest + Tokyo JSON | `tokyo_type1_measurement_only` | Type 1 passed |
| `SexualRecombinationConfig.diploid_meiosis` | avida.cfg `RECOMBINATION_GROUP` / `TWO_FOLD_COST_SEX`; Aevol-style homolog reduction | **landed** opt-in; default off | `runtime_observation` | Aevol-grade meiosis; biological diploidy |
| `build_multi_generation_evidence_pack` hygiene | measurement integrity | **landed** `TypeError` on `None`/garbage; `reproduction_mode=None` coerces to asexual | error / software capability | silent zero metrics |

JaxLife NN agents and ASAL CLIP remain **docs-only comparators** and are not
ported into core.

---

## 9. PR checklist (scientific completeness)

Use this on the completeness PR. All items must stay **honest**.

- [x] `docs/SCIENTIFIC_AUTHORITIES_2026.md` cites Ofria & Wilke 2004; Lenski et al. 2003; live avida.cfg groups; Dolson et al. 2019; Empirical persistence-filter subtlety; Bedau; Channon 2024; Packard et al. 2019; Borg et al. 2023 (cite only); Clune 2007; Lalejini & Ofria 2016; Frontiers 2021 Ghalambor four conditions; Goldsby / demes wiki / GECCO 2008; Am Nat 2020; PLOS One odometry; BMC Evol Biol 2021 metabolic signaling (axes only); JaxLife 2024 arXiv 2409.00853; Aevol_4b ISAL 2024; OntoAvida/avidaR 2023; ASAL arXiv 2412.17799.
- [x] Feature × Avida / MODES / Channon2024 / JaxLife / Aevol matrix with landed / partial / deferred.
- [x] Eval bugfix IDs mapped (`sexual_birth_placement_metrics`, `reproduction_mode_validation`, `phase_e_capsule_wiring`, `life_loop_capacity_footgun`, `summarize_garbage_input`, `tokyo_type1_measurement_hook`).
- [x] Phase D MODES persistence filter documents coalescence-window semantics and exposes `persistence_window_t`; Empirical shadow is an opt-in Python analog, never a silent Type 1 pass.
- [x] Tests cover coalescence-window filtering (longer `t` drops extinct lineages).
- [x] `TokyoType1MeasurementProtocol` uses Channon-2024 step labels; ceiling `tokyo_type1_measurement_only`; `tokyo_type1_passed` blocked.
- [x] Multi-seed campaign (`TokyoType1MeasurementCampaign`) requires ≥2 seeds; pass claim still blocked.
- [x] Opt-in Empirical systematics shadow adapter produces a real `shadow_digest` for Tokyo step_4; default off.
- [x] Opt-in Logic-9 reaction→resource→merit coupling (digest-backed); `avida_replacement` blocked.
- [x] Opt-in learning causal payoff with ablation + multi-seed; `instinct_improved` stays gated.
- [x] Opt-in collective deme payoff + contribution ledger; Phase F campaign with group-vs-individual contrast, DoL metrics, multi-deme ranking; `collective_intelligence` blocked.
- [x] `run_channon_avida_modes_shadow_suite` pins `persistence_window_t` sweeps + MODES + Tokyo JSON.
- [x] `build_multi_generation_evidence_pack` raises `TypeError` on garbage; `reproduction_mode=None` is consistently asexual.
- [x] Opt-in `diploid_meiosis` + existing `TWO_FOLD_COST_SEX`; default sexual digest pins unchanged.
- [x] Default life-loop capacity strictly greater than initial population; regression test; A–E spec digest pins unchanged.
- [x] Phase E phenotype/transcriptome export includes genome, action-execution counts, fitness/ATP/role (OntoAvida-style proxy, not biology).
- [x] `CLAIMS.md` / `README.md` / `CHANGELOG.md` Unreleased updated with honest ceilings.
- [x] ClaimGate stronger, not weaker: union of forbidden Tokyo Type 1 pass aliases; pack alias does not unlock a pass.
- [x] Example smoke prints blocked pass claim.
- [x] No intelligence / AGI / OEE-proved / Avida-replacement / Tokyo-Type-1-passed language.
- [x] `docs/WHY_NOT_INTELLIGENCE_YET.md` maps Nature MI 2021 / Chromaria / Stanley / Channon 2024 / arXiv 2607.09560 / JaxLife / Goldsby–demes–major-transitions onto CodonTrace Genesis has-vs-lacks; does **not** claim the project is close to AGI.

---

## 10. What this document does not claim

- CodonTrace Genesis is not Avida, Empirical, JaxLife, Aevol, or a foundation-model OE search engine.
- Measuring MODES-style axes or running Channon-2024 *steps* is not passing Tokyo Type 1.
- Persistence filtering is not a full phylogenetic systematics proof. The Python shadow adapter is not Empirical C++.
- Capsule/memory effects and the learning-payoff protocol are not proved associative learning.
- Deme messaging and the collective deme payoff ledger are not collective intelligence.
- Logic-9 reaction coupling is not an Avida NAND-CPU port and not metabolic intelligence.
- Opt-in `diploid_meiosis` is not Aevol-grade meiosis or biological diploidy.
- Plasticity checklists are not evolved phenotypic plasticity.
- Phenotype/transcriptome JSON is not a biological transcriptome.
- Named materials / ontology ids are not realistic chemistry, wet-lab
  equivalence, or a KEGG/BiGG GEM solver.
- CLIP / foundation-model open-endedness scoring is **not** implemented.

See `CLAIMS.md`, `docs/PHASE_D_LITERATURE.md`, `docs/PHASE_E_LITERATURE.md`,
`docs/PHASE_G_MATERIALS_LITERATURE.md`, `docs/PHASE_H_CI_AI_PATH.md`,
`docs/PHASE_I_CI_EVIDENCE.md`, `docs/PHASE_J_REPLAY_CI.md`, `docs/PHASE_K_CI_DEPTH.md`, `docs/WHY_NOT_INTELLIGENCE_YET.md`,
and `ScientificClaimGate`.
