# Changelog

## Unreleased

### DomainProfile — ports, not a second engine

ClaimGate domain labels live on `DomainProfile` (`alife` / `biomedical` /
`hardware`). The Genesis engine stays domain-agnostic. Biomedical is one
port, not a medical engine: `samd_certified`, `fda_cleared`,
`clinical_validated`, and `asme_vv40_passed` raise `ConfigurationError`.
Runtime `__version__` reads `[project].version` from pyproject (no hardcoded
identity). README / CLAIMS / CITATION now name the published PyPI tip
`0.3.0b6` and say `main` may be ahead of tag `v0.3.0b6` without recutting.
`sign_flip_permutation_detail` reports exhaustive / Monte Carlo /
meet-in-the-middle and will not hide a censored p-floor; default
`exact_sign_flip_permutation_p` is unchanged so published campaign pins stay
stable. `bootstrap_ci_paired(..., method="studentized")` is opt-in
percentile-t; default BCa is unchanged. Meet-in-the-middle sign-flip
uses a relative float match so all-positive n=30 deltas count as 2/2^n;
the default p path and HE01 `results_v7.json` are unchanged. BAIC
manuscript in `paper/baic/` combines the honest revision (claim audit,
composite intervention, missing calibration artifact) with the fuller
tables, without recutting campaign numbers or claiming SaMD. JOSS no longer calls the default sign-flip “exact” for all n, and
the ESP32 line is an engineering stub. BAIC 2026 source lives in
`paper/baic/` (evidence-audit analog; not SaMD). Biomedical port now
records declared SiMD/SaMD kind, IEC 62304 class, IMDRF N12 category,
and FDA 2023 evidence cats 1–8 (`bundle_from_device_model_cou`). Labels
do not raise the ladder; new blocked aliases include `simd_certified`,
`iec_62304_certified`, `in_silico_trial_validated`. No version bump. Phase A–E
pins unchanged. ClaimGate not loosened.

### HARD_EXPERIMENT_02 — honest pilot clear + research null

CodonTrace Genesis. Identity `0.3.0b4.dev0`. ClaimGate not loosened beyond
earned evidence. Phase A–E pins unchanged.

- Wiring: harvest-at-nav-target for E1 selective value; shuffled-arm MI
  records gated to `shuffle_mode=off` (adoption path matches emit).
- Pilot seeds 1000–1009 clear assay / oracle / MI gates
  (`cleared_for_research=true`).
- Research 30 seeds (2000–2029) committed to
  `docs/hard_experiment_02/results_v1.json` with Holm null — ceiling stays
  `runtime_observation` (not `intervention_supported`).
- Research ticks/pop locked to smoke-calibrated 8/8 after host OOM at 24/12
  (prereg TBD-after-smoke).
- HE03 research remains deferred.

## [0.3.0b4] — 2026-09-17

PyPI research-beta cut. Tag `v0.3.0b4`. Includes HE01 SCHEMA v7 (PR #35),
discovery ClaimGate waves A–D, ESP32 engineering stub, and prior H–L work.
Install: `pip install codontrace==0.3.0b4`.

### HARD_EXPERIMENT_01 SCHEMA v7 — seed-contingent food amounts + lock digest

CodonTrace Genesis. Identity `0.3.0b4`. Estimand unchanged. ClaimGate not
loosened by the lock text alone. Phase A–E pins unchanged (HE01 overlay only).

- Single prereg lock: `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK.md` (no
  sixth soft numbered amendment pile-on).
- Every-cell food coverage retained (Amd 03 lesson); initial resource amounts
  drawn per seed from discrete multipliers `{0.75, 1.0, 1.25}` × base
  (`hard_experiment_01/food_amounts`) so analysis seeds are distinct environment
  realizations (Avida spatial-heterogeneity / Taylor-style seed contingency).
- Confirmatory negative control remains `capsules_content_null`; legacy
  `capsules_shuffled` sensitivity-only (peer-rotation may beat off).
- Assay gate: `assay_failed_treatment_seed_variance_zero` if treatment outcomes
  are seed-invariant.
- Artifacts: `docs/hard_experiment_01/pilot_v7.json`,
  `docs/hard_experiment_01/results_v7.json`. Ceiling at most
  `intervention_supported` when the full rule + healthy control hold; else
  honest `assay_invalid` / zero / `runtime_observation`.
- ESP32 Moj-ه demoted in CLAIMS/CHANGELOG/README to **engineering stub only**
  (`SimEsp32Bridge`), not a scientific research surface.
- Avida/MABE ClaimGate adapters remain **skeletons** until audited published
  `.dat` / DataFile CSV campaigns exist (no literature-compatibility overclaim).
- HE03 research results remain deferred (docs only); HE02 research landed with Holm null.

### Discovery-wire + ESP32 Moj-ه thin bridge (engineering stub — not research surface)

CodonTrace Genesis. Identity `0.3.0b4.dev0`. ClaimGate not loosened.
Phase A–E pins unchanged when `discovery_wire` is default-off.
ESP32 is an **engineering stub** (`SimEsp32Bridge`); not a scientific research surface.
**Zero claim that physical robots ran.**

- Optional `DiscoveryWireConfig` on `QDSearchConfig` (default OFF): every N
  generations, `NoveltyProposer.propose` → cheap S1 `run_discovery_pipeline` →
  admit to QD archive / innovation_protection only when ClaimGate ceiling is
  `discovery_witness_candidate`. Omitted from digests when disabled.
- ESP32 Moj-ه thin adapter `claimgate/adapters/esp32_bridge.py`:
  `move` / `read_sensor`, Pydantic untrusted boundary, `SimEsp32Bridge`,
  Serial/MQTT stubs fail closed (no secrets), STR-disparity helper + §11 stop
  criterion. Firmware sketches under `firmware/esp32/` with safety comments.
- Docs: `docs/design/ESP32_BRIDGE_v0.1.md` (Koos/Mouret/Doncieux 2013;
  OMNI-EPIC arXiv:2405.15568; ARE 2024 STR-disparity honesty).
- Replay digest policy registration for `DiscoveryWireEvent` + `STRDisparityResult`.
- No AGI / collective-intelligence / fabricated hardware-campaign claims.

### Open-ended discovery ClaimGate pipeline (waves الف–د)

CodonTrace Genesis. Identity `0.3.0b4.dev0`. ClaimGate not loosened.
Phase A–E pins unchanged. Zero ESP32 / Moj-ه code.

- Goal doc: `docs/design/OPEN_ENDED_DISCOVERY_CLAIMGATE_PIPELINE_v2.md`
  (ASAL Kumar et al. arXiv:2412.17799; Flageat et al. IEEE TEVC 2026 /
  arXiv:2409.13315; MAP-Elites; QD; OMNI-EPIC; HE01 three-negative lesson).
- Wave الف: `run_discovery_pipeline(candidate, *, scale=...) -> DiscoveryAuditReport`
  with digest-bearing accept/reject and unit tests on ≥3 hand-crafted candidates.
- Wave ب: `NoveltyProposer` Protocol + `RandomProposer` + `ExternalModelStubProposer`
  (callable without paid API) + Pydantic boundary `parse_external_proposal`.
- Wave ج: `CandidateSpec` / `DiscoveryAuditReport` / `NegativeControlResult` as
  `@dataclass(frozen=True, slots=True)`; witness sha256 matches content.
- Wave د: campaign 3–5 proposals with all three negatives
  (`proposer_random`, `proposer_shuffled_archive`, `archive_no_op`); ceiling
  above `runtime_observation` only if meaningfully better than all three;
  honest accept/reject rates (100% reject is valid data).
- Hypothesis: `paired_effect_size` never returns NaN when variance is 0.
- Replay digest policy registration for new public digest dataclasses.
- No AGI / collective-intelligence claims.

### HARD_EXPERIMENT_03 — E3 TaskSwitchCost + gorelick_nmi + IsolationAssay

CodonTrace Genesis. Identity `0.3.0b4.dev0`. ClaimGate not loosened.
Phase A–E pins unchanged.

- Default-off `TaskSwitchCostConfig` (Goldsby 0 / ~25 / ~50 cycle → ATP
  analogues 0 / 0.25 / 0.50) with conditional `to_dict`, digests,
  ConfigurationError validation, and pin+runtime tests.
- Confirmatory `gorelick_nmi` at `codontrace.genesis.metrics.division_of_labor`
  (Gorelick NMI/NME); non-NMI DoL proxies stay **legacy**.
- `IsolationAssay` secondary solo-vs-group drop (not collective intelligence).
- Campaign module `hard_experiment_03` with prereg arms, honest
  `runtime_observation` ceiling, pilot seeds 1000–1009.
- ClaimGate adapter `bundle_from_hard_experiment_03`; replay digest policy
  registration for HE02/HE03 public digest dataclasses.
- Docs: `HARD_EXPERIMENT_03.md`; CLAIMS ceiling starts at
  `runtime_observation`. No fabricated research `results_v1.json`.

### HARD_EXPERIMENT_02 — E1+E2+E5 after prereg

CodonTrace Genesis. Identity `0.3.0b4.dev0`. ClaimGate not loosened.
Phase A–E pins unchanged.

- Default-off knobs: `FoodPatchSignalConfig`, `DemeSelectionConfig`,
  `SteppingStoneRewardConfig` with conditional `to_dict`, digests,
  ConfigurationError validation, and pin+runtime tests.
- `MOVE_TOWARD_CAPSULE_TARGET` on HE02 action registries only.
- Campaign module `hard_experiment_02` with prereg arms, manipulation
  checks (`assay_invalid` when not realized), pilot seeds 1000–1009,
  research 30-seed path, ClaimGate adapter.
- Docs: `HARD_EXPERIMENT_02.md`; CLAIMS ceiling starts at
  `runtime_observation`.


### Wave 2 — simulator-agnostic ClaimGate auditor

CodonTrace Genesis standalone evidence auditor. **Does not** claim
intelligence, collective intelligence, Tokyo Type 1 passed, or Avida
replacement. Identity stays `0.3.0b4.dev0`. Phase A–E pins stay
stable. ClaimGate is not loosened.

- New package `codontrace.claimgate`: `claimgate_bundle_v1` +
  `audit_bundle` → public 0–5 (`CLAIMS.md` §5 + §8). CLI
  `python -m codontrace.claimgate audit bundle.json`.
- `StrongClaimLadderResult.public_level` maps the nine internal rungs
  through `docs/CLAIM_LADDER_MAP.md`. Digest payload unchanged.
- Adapters: complete CodonTrace Genesis HARD_EXPERIMENT_01 v2;
  Avida `.dat` and MABE2 DataFile CSV **skeletons** only.
- HARD_EXPERIMENT_01 v2 still grades `runtime_observation` / public
  level 1, labeled `assay_invalid` (bitwise-identical fitness across
  arms; manipulation not realized), not a scientific null. MODES /
  Tokyo Type 1 remain measurement neighbors, not a pass. ASME V&V 40
  is context-of-use, not a numeric score.
- Docs: `docs/CLAIMGATE_STANDALONE.md`, collapsed
  `docs/CLAIM_LADDER.md`, `docs/design/*` literature notes.

### HARD_EXPERIMENT_01 Wave 1b — survival calibration + assay gate

CodonTrace Genesis harden of the same Wave 1 question. **Does not**
claim intelligence, collective intelligence, Tokyo Type 1 passed, or
Avida replacement. Identity stays `0.3.0b4.dev0`. Phase A–E pins stay
stable. ClaimGate is not loosened.

- Root-cause: research v1 (`30 / 40 / 16`) was an invalid null — every
  arm extinct by tick 10, zero `EMIT_NEXUS`, zero adoptions. Energy
  budget vs `COPY_SELF`, two food cells vs pop 16, no emit codon.
- Overlay-only calibration (food inflow, ATP, basal cost, death
  patience, initial genomes) so the existing capsule channel can fire.
  Estimand / arms / seeds / analysis unchanged.
- Assay gate: `assay_failed` when treatment mean adoptions ≈ 0 or
  extinction ≈ 1; ceiling stays `runtime_observation`.
- Research v2 (`docs/hard_experiment_01/results_v2.json`): treatment
  adoptions 169, extinction 0, assay passed; primary dz = 0,
  CI `[0,0]`, Holm p = 1.0; ceiling `runtime_observation`. Interpretable
  null after the channel fired.

### HARD_EXPERIMENT_01 Wave 1 — preregistered causal design

CodonTrace Genesis confirmatory measurement on the Wave 0 helpers.
**Does not** claim intelligence, collective intelligence, Tokyo Type 1
passed, or Avida replacement. Identity stays `0.3.0b4.dev0`. Phase A–E
pins stay stable. ClaimGate is not loosened.

- Preregistration `docs/HARD_EXPERIMENT_01_PREREG.md` is committed
  *before* campaign numbers. Campaigns record `prereg_digest`.
- Four arms: `source_bias_on`, `source_bias_off`, `capsules_off`,
  `capsules_shuffled` (`CapsuleShuffleMode.CONTENT`). Explicit DAG
  (Okasha & Otsuka 2020) states which edge each arm cuts.
- Dose-response `min_source_fitness ∈ {0,1,2,4}` with `FITNESS_WEIGHTED`
  and a seed-fixed Spearman permutation trend (Goldsby 2012 pattern).
- Paired dz + BCa 95% CI (10000) + sign-flip p; Holm across three
  primary contrasts; `PairedComparisonResult.claim_downgraded` when CI
  includes 0; missing outcomes dropped, never zero-filled.
- Smoke (12 / 6 / 4) stays in CI at `runtime_observation`. Research
  (30 / 40 / 16) may request existing `intervention_supported` only if
  the preregistered decision rule holds and ClaimGate allows it.
- Research v1 (`docs/hard_experiment_01/results_v1.json`) is a null
  finding: dz = 0, CI `[0, 0]`, Holm p = 1.0, ceiling
  `runtime_observation`. Replay matched. Capsule adoptions were 0.

### Advisor hygiene + hard experiment 01

CodonTrace Genesis hygiene and one measurement paper. **Does not** claim
intelligence, collective intelligence, Tokyo Type 1 passed, or Avida
replacement. Development identity `0.3.0b4.dev0`. Phase A–E default digest
pins stay stable.

- Deleted probe leftovers from the published tree:
  `.grok_write_probe2.txt`, `.grok_write_probe3.txt`, `.size_test_10k.txt`.
  Added `.gitignore` and `MANIFEST.in` excludes so they are never packaged.
- Default PR CI now runs full `pytest tests` on Ubuntu × Python 3.11–3.14.
  Cross-OS jobs keep the release-critical smoke subset (timeout split).
- Started `engine.py` decomposition: `codontrace.engine_digest` (replay
  hashes) and `codontrace.engine_results` (tick/snapshot/run identity).
  Historical imports unchanged. Contract:
  `docs/ENGINE_REPLAY_CONTRACT.md`.
- Hard experiment 01 (`codontrace.genesis.hard_experiment_01`): 12-seed
  paired source-bias on vs source-bias off vs capsules off; effect size;
  independent replay digests; ClaimGate ceiling `runtime_observation`.
  Example `examples/genesis_hard_experiment_01.py`. Write-up
  `docs/HARD_EXPERIMENT_01.md`.
- Phase H–L “not intelligence” pointers folded into
  `docs/PHASE_INDEX.md`. Canonical honesty doc remains
  `docs/WHY_NOT_INTELLIGENCE_YET.md`.
- Full-suite honesty: register Phase H–L / RAG / hard-experiment digest
  dataclasses in the replay policy sweep (measurement/reference, not
  claim-granting). Remove the core `print()` from
  `print_collective_intelligence_candidate_checklist` (examples may
  print the rendered checklist). These tests were never in the old CI
  subset.
- Working-tree identity is `0.3.0b4.dev0` (`pyproject.toml`,
  `codontrace.__version__`, `CITATION.cff`, release-label aliases). The
  public PyPI tip remains `0.3.0b3`.
- Contributor naming lives in `CONTRIBUTING.md` / `STYLE.md`. README opens
  with a plain 30-second intro instead of an internal naming-order note.
- Hard experiment 01 maps each arm to an explicit
  `CapsuleTransferConfig` intervention (`hard_experiment_01_interventions`).

### Phase L — Avida ORGANISM_MESSAGING / DEME_GROUP fidelity

CodonTrace Genesis measurement-first follow-on after Phase K (`2614ec4`).
**Does not** claim intelligence, collective intelligence, Tokyo Type 1
passed, or Avida replacement. ClaimGate unchanged in the strict
direction. No version bump. Phase A–E default digest pins stay stable.

- ORGANISM_MESSAGING analog
  (`evaluate_organism_messaging_group` /
  `run_organism_messaging_fidelity_experiment`): per-organism FIFO
  retrieve, faced-neighbor send, `rotate_cw`, `block_propagation`, Phase E
  `DemeState` audit. Analog ISA, not Avida C++.
- `DEME_GROUP` analog: optional `maybe_replicate_demes` with extra target
  deme / germline copy recorded. Not avida.cfg hardware.
- Goldsby 2012-aligned specialist measurement
  (`run_goldsby_aligned_specialist_campaign`): behavioral vs genotypic
  specialists, clonal-group DoL, colony-quota analog, ancestral vs evolved
  isolation, delay dose-response. `is_goldsby_2012_pnas_experiment=False`.
- Optional Phase K coordination-ablation evidence feed
  (`feed_phase_k_coordination_ablation_evidence`): never auto-sets
  ClaimGate flags; smoke never earns.
- RAG corpus: `avida_cfg_organism_messaging`, `avida_cfg_deme_group`;
  Goldsby messaging / 2012 digests updated.
- Docs: `docs/PHASE_L_AVIDA_FIDELITY.md`.
- Example: `examples/genesis_phase_l_avida_fidelity.py`.

### Phase K — literature-grade CI depth

CodonTrace Genesis measurement-first follow-on after Phase J (`899addc`).
**Does not** claim intelligence, collective intelligence, Tokyo Type 1
passed, or Avida replacement. ClaimGate unchanged in the strict
direction. No version bump. Phase A–E default digest pins stay stable.

- Evolved coordination instructions
  (`run_evolved_coordination_instruction_experiment`): discrete
  send/retrieve/broadcast/work genomes on the Phase E buffer; messaging
  ablation can drop coordination payoff. Analog ISA, not Avida C++.
- Goldsby-scale CPU-delay specialist harness
  (`run_goldsby_cpu_delay_specialist_campaign`): 0/25/50-cycle analog
  treatments; research default **50** replicates; isolation vs group
  dual-task hooks. `is_goldsby_2012_pnas_experiment=False`.
- Multi-generation Price analysis
  (`run_multi_generation_price_analysis`): transmission term from
  realized parent–offspring Δz; `price_equation_complete=False`.
- Michod/Conlin conflict-suppression hooks
  (`build_conflict_suppression_observation`): within-group variance,
  cheater invasion, revertant isolation. Endogenous / transition flags
  stay False.
- RAG corpus: Price 1972 transmission digest; Goldsby / Michod / Conlin
  / Okasha / Price 1970 updated.
- Docs: `docs/PHASE_K_CI_DEPTH.md`.
- Example: `examples/genesis_phase_k_ci_depth.py`.

### Phase J — replay-verified CI candidate packs

CodonTrace Genesis measurement-first follow-on after Phase I (PR #14 @
`6a0fe1a`). **Does not** claim intelligence, collective intelligence, Tokyo
Type 1 passed, or Avida replacement. ClaimGate unchanged in the strict
direction. No version bump. Phase A–E default digest pins stay stable.

- Replay-verified CI candidate pack
  (`build_replay_verified_ci_candidate_pack`): runs Phase I research-scale
  earnable campaigns, independently re-executes them, and earns
  `replay_verification` only when campaign digests match. Same-object
  “replay” is rejected. Smoke never earns flags.
- When every candidate flag is honestly earned at research scale,
  ClaimGate **allows** `collective_intelligence_candidate`. Bare
  `collective_intelligence` / proved CI stay forbidden.
- Price-equation / Okasha covariance scaffold
  (`run_price_equation_covariance_scaffold`): last-generation MLS1
  between/within partition on the two-task analog; transmission term not
  estimated; `major_transition_in_individuality=False`.
- RAG corpus: Price 1970 Nature; Okasha 2006 digest updated.
- Docs: `docs/PHASE_J_REPLAY_CI.md`.
- Example: `examples/genesis_phase_j_replay_ci.py`.

### Phase I — collective-intelligence evidence harnesses

CodonTrace Genesis measurement-first follow-on after Phase H (PR #13).
**Does not** claim intelligence, collective intelligence, Tokyo Type 1
passed, or Avida replacement. ClaimGate unchanged in the strict direction.
No version bump. Phase A–E default digest pins stay stable.

- Heldout unfamiliar-partner generalization
  (`run_heldout_unfamiliar_partner_experiment`): familiar vs heldout lineage,
  distinct partner digests, leakage status. Smoke does **not** earn
  ClaimGate `heldout_protocol`.
- Evolved (not assigned) division of labor
  (`run_evolved_division_of_labor_experiment`): heritable two-task preference,
  Gorelick-style NMI, all-A ablation. Does **not** auto-set `ablation_result`.
- MLS evolutionary *outcome* vs organism-only
  (`run_mls_evolutionary_outcome_experiment`): majority strategy contrast
  (Okasha MLS2 analog), not a rank table.
- Export-of-fitness scaffold (`build_export_of_fitness_observation`): isolation
  vs group competence; isolation collapse marked as payoff construction;
  `major_transition_in_individuality=False`.
- `earn_collective_intelligence_candidate_flags`: research-scale evidence
  objects may earn candidate flags; smoke never earns;
  `replay_verification` is not earnable from Phase I.
- RAG corpus: Gorelick 2004; Okasha 2006; Michod 2007 PNAS.
- Docs: `docs/PHASE_I_CI_EVIDENCE.md`; WHY_NOT / PHASE_H cross-links.
- Example: `examples/genesis_phase_i_ci_evidence.py`.

### Phase H — literature RAG + collective-intelligence pathway scaffolding

CodonTrace Genesis measurement-first kickoff toward CI then broader AI/OEE.
**Does not** claim intelligence, collective intelligence, Tokyo Type 1 passed,
or Avida replacement. ClaimGate unchanged in the strict direction. No version
bump. Phase A–E default digest pins stay stable.

- Literature RAG substrate (`codontrace.genesis.rag`): JSONL+markdown corpus
  of citable digests (Nature MI 2021; Goldsby PNAS 2012; Goldsby/Ofria
  messaging/germline; Channon 2024; Chromaria; Stanley open-endedness;
  Szathmáry/Michod; JaxLife; arXiv 2607.09560; arXiv 2604.00810; bioRxiv
  2023.03.15.532780) with has/lacks/next-experiment maps. Retriever:
  `ingest_document`, `search_corpus(query, k)`, `cite_sources`. Deterministic
  TF-IDF + feature-hash; replay digest. Example:
  `examples/genesis_rag_query.py`.
- Communication ablation harness (`run_communication_ablation_experiment`):
  messaging on vs off, multi-seed, Cohen's *d*. Status
  `measured_runtime_observation`. Does **not** set ClaimGate `ablation_result`.
- Group-vs-individual effect-size campaign (research default `seed_count=12`,
  smoke 2) with explicit `mean_delta` / `cohens_d` fields.
- Goldsby 2012 task-switching cost hook on DoL metrics
  (`TaskSwitchingCostConfig`, `apply_task_switching_cost_to_dol`).
- `collective_intelligence_candidate` checklist printer lists missing flags
  and never auto-sets them.
- Docs: `docs/PHASE_H_CI_AI_PATH.md`, `docs/rag/`, honesty updates to
  `docs/WHY_NOT_INTELLIGENCE_YET.md`.

## 0.3.0b3 — Phase F scientific gaps, Phase G materials, ClaimGate honesty (2026-09-11)

Public beta bump from `0.3.0b2`. Includes Phase F+#9 scientific-gap measurement, Phase G+#10 named-materials substrate, and post-F/G suite ClaimGate honesty hygiene (#11 @ `0a5ce17`). Product name **CodonTrace Genesis**. Package/import remains `codontrace`. License `AGPL-3.0-or-later`. This is not an Avida replacement and does not prove intelligence, collective intelligence, AGI, OEE, Tokyo Type 1, realistic chemistry, or wet-lab equivalence.

### Release identity

- Package version `0.3.0b3` (`pyproject.toml`, `codontrace.__version__`, `CITATION.cff`).
- Aligned `RELEASE_LABEL` / `RELEASE_ARTIFACT_NAME` (and aliases), README / CLAIMS / RELEASE_EVIDENCE / BibTeX pins with that identity.

### Notes (claim policy)

- ClaimGate is unchanged in the strict direction. Bare `intelligence` is unknown/not whitelisted; `collective_intelligence` remains a forbidden overclaim alias.
- Phase F/G are opt-in measurement/substrate layers. Research defaults stay unchanged unless a caller selects those presets.
- No intelligence, collective-intelligence, or chemistry-proved claims.

### Docs / tests — honest claim ceilings after Phase F+#9 and Phase G+#10

CodonTrace Genesis full-suite drift after those merges: tests expected strong
pilot claims that runtime correctly denies. ClaimGate is unchanged.

- Official default memory delayed-reward and capsule-usefulness pilots still
  emit records, but tests now expect `pilot_fixture_not_strong_memory_claim`
  / `no_positive_behavioral_utility` instead of fabricated strong claims.
- `RELEASE_EVIDENCE.md` lists example-generated official pilot JSON names
  without committing fake pilot payloads.
- Restored the legacy `World2D.resources` amount-only semantics note. License
  metadata tests match `AGPL-3.0-or-later`.

### Scientific gaps 2026 (opt-in measurement/engineering completeness)

Honest completeness pass for remaining scientific/engineering gaps after
PR #7+#8 (`1f408d9`). This does **not** claim intelligence, AGI, proved OEE,
Tokyo Type 1 passed, associative learning, collective intelligence, or
Avida replacement. Phase A–E default spec digest pins stay stable.
ClaimGate is unchanged in the strict direction.

#### Added

- Opt-in Empirical-style shadow/null phylogeny adapter
  (`build_empirical_systematics_shadow`) producing a real `shadow_digest` for
  Channon 2024 Tokyo Type 1 step_4. Default off. Python shuffled-parentage
  analog, not Empirical C++.
- `TokyoType1MeasurementCampaign` / `run_multi_seed_tokyo_measurement_campaign`
  (≥2 seeds, Bedau/MODES aggregation). Still forbids `tokyo_type1_passed`.
- Opt-in Logic-9 / NAND-style reaction→resource→merit/ATP coupling
  (`Logic9ReactionConfig`, `build_logic9_reaction_pack`). Semantic analog of
  Ofria & Wilke 2004 / avida.cfg 2.14.0 RESOURCE/LOGIC; BMC Evol Biol 2021
  resource×population×mutation axes recorded, not that paper replicated.
  Claim ceiling `runtime_observation`.
- Opt-in learning causal payoff protocol (`build_learning_causal_payoff_pack`):
  cue→action→ATP/task reward with ablation and multi-seed. `instinct_improved`
  stays ClaimGate-gated. Am Nat 2020 / PLOS One odometry / Clune–Lalejini–
  Frontiers 2021 instrumentation only.
- Opt-in collective deme payoff (`build_collective_deme_payoff_pack`):
  GermlineReplication-style replicate-on-mean-fitness plus contribution
  ledger (Goldsby messaging; GECCO 2008 germlines). `collective_intelligence`
  blocked.
- `run_channon_avida_modes_shadow_suite` pins `persistence_window_t` sweeps +
  MODES digest + Tokyo JSON. Type 1 remains unpassed.
- Opt-in `SexualRecombinationConfig.diploid_meiosis` homolog-reduction analog
  (Avida `TWO_FOLD_COST_SEX` already placed one recombinant product).
- `docs/WHY_NOT_INTELLIGENCE_YET.md`: literature-vs-reality barrier map
  (Nature MI 2021 Miikkulainen & Forrest / Banzhaf computational-evolution
  agenda; Soros & Stanley Chromaria; Stanley open-endedness as a creative-
  intelligence component; Channon 2024 measurement ≠ pass; arXiv 2607.09560
  vocabulary+verifier gaps; JaxLife complementary ecology vs NN culture;
  Goldsby / GECCO 2008 / demes / Michod–Szathmáry major transitions). Does
  **not** claim CodonTrace Genesis is close to AGI.
- Phase F `run_collective_deme_payoff_campaign`: ≥2-seed deme ranking +
  division-of-labor *metrics* + contribution ledger + paired
  group-vs-individual contrast. Gap flags stay explicit
  (`heldout_partner_status=not_run`, `communication_ablation_status=not_run`,
  `multilevel_selection_experiment=scaffold_only`). Group fitness remains
  `runtime_observation`; `collective_intelligence` /
  `proved_collective_intelligence` blocked. Docs name the project
  **CodonTrace Genesis** (PyPI package remains `codontrace`).
- `examples/genesis_scientific_gaps_2026.py` prints blocked pass/intelligence
  claims.

#### Fixed

- `build_multi_generation_evidence_pack` raises `TypeError` on `None` / objects
  without `ticks` or `digest` instead of silent empty packs.
- `reproduction_mode=None` is documented and consistently coerced to asexual
  (never stored as `None`).

#### Claim policy

- Allowed: `runtime_observation`, `oee_measurement_only`,
  `tokyo_type1_measurement_only` (measurement steps / campaigns recorded).
- Blocked: `tokyo_type1_passed`, AGI, `avida_replacement`,
  `associative_learning_proved`, `collective_intelligence`,
  `open_ended_intelligence`, `realistic_chemistry_proved`,
  `wet_lab_equivalent` (unchanged / Phase G).
- JaxLife NN agents and ASAL CLIP remain docs-only comparators, not ports.

### Phase G — named materials / chemistry-effect substrate

CodonTrace Genesis adds an opt-in `MaterialsWorld` overlay so later experiments can bind real substance
tables. This is **not** an Earth chemistry simulator, KEGG/BiGG GEM solver,
molecular-dynamics engine, or wet-lab equivalent. Phase A–E default spec
digest pins stay stable.

#### Added

- `MaterialSpec` / `MaterialState` / `MaterialsConfig`: named materials with
  energy yield, toxicity, viscosity/diffusion, permeability, signaling potency,
  scarcity; optional `external_ontology_id` (ChEBI/KEGG/BiGG schema hook),
  `units`, and `effect_coefficients`. `biological_accuracy_claimed` is always
  false.
- World pools and optional spatial grids: consume / transform / excrete;
  simple stoichiometric CRN subset; chemostat inflow/outflow on named materials
  (Novick & Szilard 1950; Phase C `apply_chemostat_step`); diffusion/decay
  hooks (viscosity reduces diffusion).
- Organism–material coupling: eat/absorb → ATP + recorded merit coefficient;
  toxins → ATP drain / lethal threshold; catalysts enable reactions; membrane
  permeability (cellularity knob) gates uptake.
- `GenesisRuntimeProfile.materials_world()` and
  `life_loop_world(materials=...)`; digest-backed trajectory replay.
- Optional 2–3 material autocatalytic cycle demo (`A + B → 2A`) with spatial
  coexistence *measurement* (npj Complexity 2025 ACE cited as design note only).
- `MaterialBindingSchema` export for a future real-substance table bind. GEM
  and MD flags are hardcoded false.
- ClaimGate blocked aliases: `realistic_chemistry_proved`, `wet_lab_equivalent`,
  `kegg_solver_equivalent`, `bigg_gem_equivalent`,
  `molecular_dynamics_equivalent`, `earth_chemistry_simulator`,
  `biological_accuracy_proved`. Ceiling remains `runtime_observation`.
- `examples/genesis_materials_world.py`, `tests/test_genesis_phase_g_materials.py`,
  and `docs/PHASE_G_MATERIALS_LITERATURE.md`.
- ClaimGate keeps chemistry aliases blocked **and** `collective_intelligence`
  blocked.

### Fixed

- Sexual life-loop placement counters (`adjacent_or_displaced_births` / `same_cell_births`) now update from birth-time chamber placement records. Chamber offspring that selection later drops still count. This is a runtime observation fix, not an intelligence claim.
- `reproduction_mode` rejects unknown strings (`ValueError`) and non-string types (`TypeError`) instead of storing a raw `str`. Valid names such as `"sexual_crossover"` still coerce to `ReproductionMode`.
- `phase_e_substrate_world` capsule observation now aggregates last-seen write/read/substitution counters across the run (not only final survivors). Seed priors are unconstrained so matching cues produce measurable substitution under fixed seeds; capsules-off ablation still differs. Not associative-learning proof.
- `life_loop_world` capacity stays `max(pop, 8)` for the historical pop<8 presets (pinned Phase A–E spec/snapshot/tick digests unchanged). For `population >= 8`, capacity is `max(pop*2, 16)` and the world is widened so COPY_SELF is not immediately blocked at capacity or by packed adjacent cells.
- Summarize helpers (`summarize_life_loop_observation`, `summarize_phase_e_observation`, `summarize_dynamic_environment_observation`) raise `TypeError` on `None` / objects without `ticks` instead of returning silent zeros.

### Scientific authorities 2026 (measurement/docs completeness)

Honest completeness pass against world-authority digital-evolution and OEE
*measurement* literature after Phase A–E (`0.3.0b2`). This does **not** claim
intelligence, AGI, proved OEE, Tokyo Type 1 passed, or Avida replacement.
Phase A–E default spec digest pins stay stable.

#### Added

- `docs/SCIENTIFIC_AUTHORITIES_2026.md`: feature × Avida / MODES / Channon 2024 /
  JaxLife / Aevol matrix (landed / partial / deferred), live `avida.cfg` 2.14.0
  group map, eval-bugfix → authority mapping, and a PR honesty checklist.
- `TokyoType1MeasurementProtocol` (Channon 2024 measurement-step vocabulary:
  activity, novelty, shadow/normalization hooks). Claim ceiling
  `tokyo_type1_measurement_only` when Channon steps are recorded.
  `tokyo_type1_passed` is blocked by construction and ClaimGate. Multi-seed is
  required for any status above measurement_only and still does not pass Type 1.
- Pack-level cheap hook: `evaluate_tokyo_type1_measurement_claim(pack)` requests
  `tokyo_type1_measurement_only` and ClaimGate aliases it to `oee_measurement_only`
  unless `channon_2024_steps_recorded` is set. CLIP / ASAL OE (arXiv 2412.17799)
  is **not** implemented.
- Explicit `persistence_window_t` on the Phase D MODES persistence filter, plus
  coalescence-window semantics and recorded limitations
  (`no_empirical_systematics_shadow_run`).
- OntoAvida-style phenotype/transcriptome export fields: fitness, genome length,
  instruction-execution counts as a transcriptome *proxy* (not biology).
- `examples/genesis_tokyo_type1_measurement.py` prints blocked pass claims.

#### Claim policy

- Allowed: `tokyo_type1_measurement_only` (measurement steps recorded); pack-level
  Channon vocabulary without those steps aliases to `oee_measurement_only`.
- Blocked: `tokyo_type1_passed`, `tokyo_type1_proved`, `channon_2024_passed`,
  `tokyo_type1_oee_proved`, `avida_replacement`, AGI, open-ended intelligence
  (unchanged / stronger).
- JaxLife culture/tech accumulation, Aevol bioinformatics encoding parity, and
  ASAL / CLIP foundation-model OE search remain documented gaps, not ports.
- Capacity for `population >= 8` exceeds initial *N* in the Avida spirit of
  `BIRTH_METHOD` / `PREFER_EMPTY` (do not set `POPULATION_CAP` == current
  population). Capsule wiring requires a subsequent-action effect under a sensory
  cue, with ablation. Chamber offspring update placement counters like the
  asexual path.

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

This beta promotion does not make CodonTrace Genesis a UI product and does not loosen the claim boundary. The core remains a dependency-free research library; Studio/API/Desktop work belongs in a separate consumer repository.

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
