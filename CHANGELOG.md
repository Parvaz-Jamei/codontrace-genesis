# Changelog

## Unreleased

### Fixed

- Sexual life-loop placement counters (`adjacent_or_displaced_births` / `same_cell_births`) now update from birth-time chamber placement records. Chamber offspring that selection later drops still count. This is a runtime observation fix, not an intelligence claim.
- `reproduction_mode` rejects unknown strings (`ValueError`) and non-string types (`TypeError`) instead of storing a raw `str`. Valid names such as `"sexual_crossover"` still coerce to `ReproductionMode`.
- `phase_e_substrate_world` capsule observation now aggregates last-seen write/read/substitution counters across the run (not only final survivors). Seed priors are unconstrained so matching cues produce measurable substitution under fixed seeds; capsules-off ablation still differs. Not associative-learning proof.
- `life_loop_world` capacity stays `max(pop, 8)` for the historical pop<8 presets (pinned Phase A–E spec/snapshot/tick digests unchanged). For `population >= 8`, capacity is `max(pop*2, 16)` and the world is widened so COPY_SELF is not immediately blocked at capacity or by packed adjacent cells.
- Summarize helpers (`summarize_life_loop_observation`, `summarize_phase_e_observation`, `summarize_dynamic_environment_observation`) raise `TypeError` on `None` / objects without `ticks` instead of returning silent zeros.

## 0.3.0b2 — Science-gate hardening and Phase A–E substrates (2026-09-11)

Public beta identity for science-gate hardening plus the Phase A–E library surfaces that landed on `main` after `0.3.0b1`. Package version remains `0.3.0b2` (not bumped to b3). This is not an Avida replacement and does not prove OEE, instinct evolution, AGI, collective intelligence, evolved plasticity, or phenotypic plasticity.

### Release identity

- Kept package version `0.3.0b2` (`pyproject.toml`, `codontrace.__version__`, `CITATION.cff`).
- Aligned `RELEASE_LABEL` / `RELEASE_ARTIFACT_NAME` (and aliases), README / CLAIMS / RELEASE_EVIDENCE / BibTeX pins, and citation `date-released` with that same identity.

### Notes (claim policy)

- Phase A–C and Phase E are **opt-in substrates** (life-loop ecology; sexual recombination; dynamic/fluctuating environment; capsule/memory/role/deme). Research defaults stay unchanged unless a caller selects those presets.
- Phase D is an **opt-in measurement** layer (`MultiGenerationEvidencePack`). Metric deltas are runtime observations. `instinct_improved` is ClaimGate-gated; OEE stays `oee_measurement_only` unless existing research-grade thresholds are met.
- ClaimGate keeps `collective_intelligence`, `evolved_plasticity`, and `avida_replacement` blocked. Do not claim OEE proof, instinct/intelligence proof, or AGI.
- No loosening of scientific claims from the science-gate hardening below. GENESIS remains research-beta software.

### Phase E — capsule/memory/role/collective substrate

#### Added

- Opt-in `PhaseESubstrateConfig` (omitted from default serialization so Phase A–D presets and pinned digests stay stable).
- Organism-local / lineage capsule memory with **real** subsequent effects: action substitution, ATP bonus, and COPY_SELF task gating under a matching sensory cue (Am Nat 2020 / odometry mapping). Ablation with capsules disabled yields a different replay digest.
- Role / differentiation tags (`soma` / `germline` / `messenger`) that can gate reproduction or messaging (Avida GermlineReplication / GECCO 2008 analog).
- Deme/group containers, Goldsby-style messaging buffer (`send_message`, `retrieve_message`, `broadcast_message`, `block_propagation`), and a minimal mean-fitness deme-replication trigger with recorded events (`DEMES_*` analog).
- `PlasticityProtocolSpec` plus `read_environment_cue()` over Phase C regimes/local patches, including the Ghalambor/Clune four-condition experimental-design checklist (not evolved-plasticity proof).
- OntoAvida-inspired `PhenotypeTranscriptomeEvidence` export and `AvidaParityProtocolSpec` head-to-head recipe (software capability only).
- `GenesisRuntimeProfile.phase_e_substrate_world()`, `build_phase_e_evidence_pack`, `examples/genesis_phase_e_substrate.py`, `tests/test_genesis_phase_e_substrate.py`, and `docs/PHASE_E_LITERATURE.md`.
- ClaimGate blocked aliases for `proved_collective_intelligence`, `evolved_plasticity`, `avida_replacement`, and `associative_learning_proved`. Ceiling remains `runtime_observation`.

#### Notes

Phase E is an opt-in **substrate**. Default life-loop, sexual, dynamic-environment, and Phase D measurement APIs keep their pinned digests. Phase D MODES/Bedau packs can observe Phase E when it is enabled because action/ATP/birth records actually change. This is not proof of learning, collective intelligence, evolved plasticity, OEE, or Avida-replacement status.

### Phase D — multi-generation instinct/behavior evidence

#### Added

- First-class `MultiGenerationEvidencePack` (JSON + digest) measuring multi-generation fitness, survival, births, ATP, and resource intake from existing life-loop records.
- Descriptive instinct/behavior trajectories (genome→action phenotype summaries) plus same-seed ancestor vs descendant cohort comparison and optional mutation-off ablation/control hooks.
- Persistence-filtered MODES-inspired axes (change, novelty, complexity, ecological potential; Dolson et al. 2019) and Bedau-style novelty/diversity/activity surfaces as library objects.
- ClaimGate labels `runtime_observation` / `instinct_improved` (downgrades without multi-seed + ablation) and blocked `open_ended_intelligence` / instinct-evolution-proved aliases. OEE remains `oee_measurement_only` unless existing research-grade thresholds are met.
- `examples/genesis_multi_generation_evidence.py`, `tests/test_genesis_phase_d_multigen_evidence.py`, and `docs/PHASE_D_LITERATURE.md`.

#### Notes

Phase D is an opt-in **measurement** layer. Phase A/B/C default presets, research defaults, and pinned spec/run digests stay stable (`phase_d_instinct_claim_metrics` metadata remains `hooks_only_not_implemented` on those specs). Metric deltas are runtime observations. This is not proof of OEE, AGI, collective intelligence, or instinct evolution, and not an Avida replacement.

### Phase C — dynamic / fluctuating environment

#### Added

- Opt-in `EnvironmentConfig` / `EnvironmentSchedule` / `ResourceSpec` (omitted from default serialization so asexual and sexual research digests stay stable).
- Avida `RESOURCE` chemostat parity: per-resource `initial`, `inflow` per tick, `outflow` fraction of unused resource (Ofria & Wilke 2004; Cooper/Ofria ~1% outflow).
- Periodic / seasonal schedules (Avida-ED periodic; period < 1 is non-periodic) and seeded regime-switch ticks.
- Two selectable fluctuating regimes (high-food vs low-food, or two niche reward maps) as a substrate for later plasticity studies — not a claim that plasticity evolved.
- Spatial options: global pool, local patches, or both, with deterministic von Neumann diffusion/decay hooks aligned with ElementGrid neighbor geometry.
- Digest-backed `EnvironmentState`, per-tick `EnvironmentSnapshot`, `EnvironmentEvent` log, and `WorldEvent` records (`environment_inflow` / `outflow` / `regime_switch` / `periodic_toggle` / `hazard_changed`).
- `EnvironmentSchedule` object API plus `verify_environment_trajectory_replay()` for env trajectory digests.
- `GenesisRuntimeProfile.dynamic_environment_world()` and `life_loop_world(environment=...)`; organisms still eat/starve/reproduce while food availability follows the schedule.
- `tests/test_genesis_phase_c_dynamic_environment.py` and `examples/genesis_dynamic_environment.py`.

#### Deferred

- Evolved phenotypic plasticity measurement (environment substrate only).
- Avida reaction/task-resource coupling (logic tasks as metabolic reactions).

#### Notes

Phase C is a time-varying environment *substrate*, not an Avida replacement and not a claim of evolved plasticity or intelligence. Claim language stays software capability / runtime observation only. Grounded in Ofria & Wilke 2004, Cooper/Ofria limited-resource ecosystems, Avida-ED resource modes, and Avida fluctuating-environment / plasticity literature used only as experimental design context.

### Phase B — sexual recombination substrate

#### Added

- Optional `ReproductionMode.SEXUAL_CROSSOVER` on `ReproductionConfig` (omitted from default serialization so asexual research digests stay stable).
- `SexualRecombinationConfig` mirroring Avida `avida.cfg` `RECOMBINATION_GROUP`: `recombination_prob`, `same_length_only`, `two_fold_cost_sex`, `max_birth_wait_ticks`, `chamber_capacity`, timeout policy, plus stubs for mating types / lekking.
- Birth-chamber pairing queue (`BirthChamberState` / `IncipientOffspring`) with capacity and wait-timeout (`fail` or `asexual_fallback`). Empty chambers are omitted from population snapshots so asexual digests stay stable.
- Avida-style positional continuous corresponding segment exchange (`apply_positional_segment_exchange`, `recombine_positional_segment_pair`) with a dedicated deterministic RNG fork for chamber pairing (`genesis/population/birth_chamber`) and crossover breakpoints (`recombination/<slot>/<slot>`).
- Dual recombinant products by default; `two_fold_cost_sex` places only one. Mutation still runs after recombination.
- Two-parent lineage / birth / child-genome fields (`second_parent_id`, `parent_ids`) that appear only on sexual births.
- Direct `reproduce(..., mate=...)` remains a one-child library API; population sexual mode uses the chamber.
- `GenesisRuntimeProfile.life_loop_world(reproduction_mode=...)` opt-in; default life-loop remains asexual COPY_SELF → mutate → child.
- Sexual path reuses Phase A AliveGate, ATP, capacity, and placement gates.
- `tests/test_genesis_phase_b_sexual_recombination.py` and `examples/genesis_sexual_recombination.py`.

#### Deferred

- Diploid meiosis / selfing (Aevol Eukaryote) as Phase B.1.
- Full `MATING_TYPES` / `LEKKING` (config stubs only).
- Modular random-region swap when `CONT_REC_REGS=0` (Phase B ships continuous corresponding regions).

#### Notes

Phase B is a recombination *substrate*, not an Avida replacement and not a claim of sexual selection or intelligence. Claim language stays software capability / runtime observation only. Grounded in Misevic, Ofria, Lenski 2006 Proc B and `devosoft/avida` `avida.cfg` `RECOMBINATION_GROUP`.

### Phase A — Darwinian life-loop

#### Added

- `GenesisRuntimeProfile.life_loop_world()`: explicit ecology / life-loop preset with limited depletable food, partial deterministic respawn, basal metabolism, starvation death records, adjacent offspring placement, AliveGate + ATP reproduction gates, fitness-proportional capacity selection, and asexual parent→mutate→child inheritance.
- Opt-in `MetabolicConfig` basal ATP drain (default off so existing research presets/digests stay stable).
- `DeathMonitoringConfig` starvation floor + consecutive-tick threshold with explicit `starvation` removal reason (omitted from default config serialization).
- `OffspringPlacementPolicy.REPLACE_OCCUPIED`: optional Avida-like overwrite-neighbor policy; not the research or life-loop default.
- `LifeLoopObservation` / `summarize_life_loop_observation()`: Phase D hook for runtime counts only, including eater/waiter births, starvation deaths, and remaining resource cells (not instinct/intelligence claims).
- `examples/genesis_life_loop.py` and `tests/test_genesis_phase_a_life_loop.py` for the eat → survive → reproduce loop, depletable resources, spatial capacity, differential reproductive success, and fixed-seed replay digest stability.
- Restored `codontrace.genesis.engine` as a re-export of the core engine implementation so the public Genesis import path works.

#### Notes

Phase A is literature-complete as a Darwinian life-loop *substrate* (Avida limited resources + energy-budget ALife). It is not an Avida replacement. Phase B (sexual crossover) and Phase C (fluctuating/seasonal environments) are opt-in substrates. Phase D (multi-generation evidence metrics) is an opt-in post-hoc measurement API that does not change these presets. Research defaults such as `ReproductionConfig.offspring_placement=SAME_CELL` and `ResourceConfig.density=0` are unchanged unless a caller selects the life-loop or dynamic-environment preset. Claim language remains software capability / runtime observation only.

### Scientific evidence-gate hardening (capsule / memory / generalization)

#### Added

- `codontrace.genesis.capsule_utility`: pure outcome-based capsule utility evaluator (`capsule_outcome_utility_v2`). Utility is measured selection-fitness delta only; synthetic fixed rewards (e.g. `task_delta = 1.0`) are forbidden. `claim_eligible` requires adoption + measured positive delta + trusted source status (`measured` / `last_known`).
- `codontrace.genesis.memory_evidence`: pure delayed-reward evidence classifier. Write→later reward without read is `temporal_correlation` only. Causal claim requires read-linked evidence plus ablation `control_digest`.
- Science unit tests:
  - `tests/test_capsule_utility_science.py`
  - `tests/test_memory_delayed_evidence_science.py`
  - `tests/test_generalization_protocol_science.py`

#### Changed

- `engine.capsule_utility_records` now delegates to the pure evaluator (single source of truth).
- `engine.memory_use_records` classifies delayed-reward chains via the evidence ladder (`observed_write` → `temporal_correlation` → `read_linked` → `causal_support`).
- `engine.generalization_records` no longer emits first/last-tick digest proxies. Without a real heldout protocol, status is `protocol_not_run` with digests `not_run:*` and `claim_eligible=False`.
- `SignalActionLink` / `MemoryUseEvidence` schema → v2 evidence fields (`evidence_status`, `causal_status`, `control_digest`, `claim_eligible`).
- `GeneralizationResult` schema → v2 with hard gate against `protocol_not_run` and identical train/heldout digests.

#### Claim policy

No loosening of scientific claims. Changes tighten evidence surfaces so ClaimGate cannot treat correlation or synthetic rewards as causal success. GENESIS remains research-beta software; it does not claim AGI, consciousness, proven collective intelligence, or peer-reviewed superiority.

## 0.3.0b1 — Studio-readiness beta release

### Changed

- Promoted current package identity from `0.3.0a2` alpha to `0.3.0b1` beta.
- Updated package metadata, runtime `codontrace.__version__`, citation metadata, release evidence, README install pins, and current release artifact identity.
- Kept historical `added_in`/compatibility provenance fields intact where they describe APIs introduced during the alpha line.

### Added

- Added `docs/STUDIO_PHASE1_EXECUTION_SPEC.html` as the repo-ready Phase 1 Studio execution handoff.
- Added `docs/STUDIO_BOUNDARY.md` to lock the library/UI boundary before Studio work begins.
- Added `docs/PERFORMANCE_PHASE1.md` as a safe profiling and optimization plan for live execution without changing scientific semantics.

### Notes

This beta promotion does not make CodonTrace a UI product and does not loosen the claim boundary. The core remains a dependency-free research library; Studio/API/Desktop work belongs in a separate consumer repository.

## 0.3.0a2 — AGPL metadata correction alpha release

### Changed

- Updated release identity from `0.3.0a1` to `0.3.0a2`.
- Updated package, citation, and runtime version metadata for the AGPL public alpha line.
- Removed deprecated license classifier from `pyproject.toml` to comply with modern Python packaging license-expression behavior.
- Kept `AGPL-3.0-or-later` as the package license expression.

### Notes

This release is a metadata/legal-packaging correction release. It does not change the scientific claim boundary: CodonTrace Genesis remains alpha research software and does not claim final peer-reviewed benchmark results, AGI, consciousness, or proven collective intelligence.

## 0.3.0a1 — Alpha research release

This release prepares CodonTrace Genesis for public alpha distribution as a deterministic research-software library.

### Added

- Causal mechanism surfaces for capsule ablation, capsule outcome windows, signal-memory-action links, skill-compression ablation, and child-outcome audits.
- Role, territory, collective-task, role-ablation, heldout-partner, multi-agent contribution, source-reputation, counterfactual-replay, and extended OEE schema surfaces.
- Runtime-wiring manifest digests for the new causal mechanism policies.
- Integration audit helpers for public API, replay-policy coverage, evidence consistency, package hygiene, and reference hygiene.
- CI and PyPI Trusted Publishing workflow templates.

### Changed

- Release identity is aligned to `0.3.0a1`.
- Public documentation was rewritten for release-facing clarity and claim control.

### Claim policy

This is an alpha research-software release. It exposes deterministic primitives and evidence structures; it does not claim AGI, consciousness, artificial life, benchmark superiority, causal certainty, or autonomous open-ended discovery.
