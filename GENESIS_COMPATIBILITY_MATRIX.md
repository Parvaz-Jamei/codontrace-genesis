# GENESIS Compatibility Matrix — v0.3.0a1 unified-runtime

CodonTrace is not yet a proof of artificial life, AGI, consciousness, or open-ended autonomous discovery. It is a GENESIS-aligned research-alpha foundation engine.

| GENESIS Concept | Current API | Status | Operational Level | Missing / Limitation | Evidence / Tests | Claim Allowed? |
|---|---|---:|---|---|---|---|
| Genome | `SemanticGenome`, `GenomeSpec` | implemented | tested primitive | no endogenous emergence | phase 1 regression | design/tested |
| CodonTable | `GenesisCodonTable`, `CodonTable` | implemented | tested primitive | limited default vocabulary | ribosome tests | design/tested |
| Ribosome | `Ribosome`, `CompiledBrain` | implemented | runtime | variable-length decoder is longest-match scaffold | phase 1 ADF tests | design/tested |
| ADF | `ADFMacro`, dynamic vocabulary helpers, action-token dispatch | partial | executable action-token scaffold | variable-width ADF codons decode and dispatch; automatic macro expansion is not enabled unless the caller registers a handler/policy | phase 1 ADF runtime + polish manifest tests | limited |
| Organism | `GenesisOrganism` | implemented | runtime | small-world organism, not biological life | organism tests | foundation organism |
| ATP_runtime | `GenesisATPState.runtime` | implemented | runtime ledger | simple accounting model | ATP/organism tests | accounting |
| ATP_learning | `GenesisATPState.learning` | implemented | runtime ledger | not cognition proof | phase 2 causal tests | accounting |
| AliveGate | `evaluate_alive` | implemented | audit gate | not life proof | liveness tests | survival gate |
| Reproduction | `reproduce`, `ReproductionConfig` | partial | controlled | not open-ended evolution | population tests | controlled reproduction |
| Population | `PopulationRunner`, `step_population` | implemented | sequential tick | limited scheduler modes | population tests | controlled population |
| Selection | `EvolutionConfig`, selection policies | partial | capacity selection | no full natural selection ecosystem | phase 3 selection tests | selection pressure scaffold |
| World2D | `World2D` | implemented | deterministic grid | simple 2D world | world tests | deterministic substrate |
| ElementGrid | `ElementGrid`, `world2d_to_element_grid`, `element_grid_to_world2d`, `GenesisExperimentSpec.element_grid` | partial | bridge scaffold | `GenesisEngine` remains World2D-based with ElementGrid source/mirror bridge; not full unified substrate-organism physics | substrate + phase 3 polish bridge tests | scaffold |
| Substrate physics | `SubstrateRule`, configs | scaffold | rule application | many fields metadata-only | substrate docs/tests | limited |
| CausalGraph | `CausalGraph`, `causal_runtime` | partial | evidence graph | not Pearl-grade causal discovery | phase 2 tests | evidence/prediction scaffold |
| Memory | `EpisodicMemory` | implemented | bounded memory | no long-term semantic memory | memory tests | bounded memory |
| Capsule | `CausalCapsule`, `CapsuleStore` | partial | transfer scaffold | not proof of knowledge transfer | phase 1/2 tests | scaffold |
| Nexus/Stigmergy | `NexusStigmergyLayer` | partial | local layer | PopulationRunner/GenesisEngine integrate EMIT_NEXUS with capsule/stigmergy; direct GenesisOrganism.step remains organism-local unless a future layer hook is supplied | capsule population tests | scaffold |
| QD | `QDArchive`, engine QD update | partial | archive + engine hook | no full MAP-Elites search loop | phase 3 QD test | QD integration scaffold |
| Discovery/D0 | `DiscoveryDetector`, D0 runner contract | scaffold | candidate/review-needed | no proof without D0/ablation/multiseed | phase 3 discovery tests | candidate only |
| Evidence/Claim audit | artifacts, claim audit modules | partial | evidence pack + manifest | no publication proof | artifact tests | evidence-ready |
| LLM review API | `LLMReviewRequest`, `LLMReviewResult` | implemented | provider-neutral schema | no provider integration | phase 3 review tests | review API only |
| Rule proposal API | `RuleProposal`, `RuleValidator` | implemented | validation + approval gate | no code execution, no direct runtime mutation | phase 3 rule tests | guarded proposal API |
| Replay/Artifact | `RunManifest`, `ReplayBundle`, `verify_replay_bundle` | partial | deterministic metadata + digest verification | replay bundle verifies manifest/snapshot/generation digests; it is not a full simulation re-execution engine yet | phase 3/post-review replay tests | replay metadata verified |
| UI readiness | `GenesisEngine`, docs | partial | library API ready | no UI included | full connection smoke | API-ready |
| Open-endedness | n/a | not-claimed | none | needs future evidence | claim control docs | no |
| Full GENESIS Engine claim | n/a | not-claimed | none | many missing scientific claims | matrix + README | no |
| Multi-seed experiments | `MultiSeedExperimentRunner` | partial | deterministic aggregate runner | descriptive stats only; not publication proof by itself | science gate multiseed tests | limited scientific protocol |
| ODD reporting | `GenesisODDReport`, `build_odd_report` | implemented | ABM report exporter | report contract only, not model validation | science gate ODD tests | documentation evidence |
| Active QD descriptors | `QDDescriptorConfig`, `QDDescriptorRegistry`, `select_population_with_qd_feedback` | partial | user-defined descriptors + novelty feedback | not a full MAP-Elites/OEE engine | science gate QD descriptor tests | QD scaffold |
| Discovery gate | `DiscoveryGate` | partial | D0/shadow/persistence/ablation claim gate | requires external/protocol evidence for stronger claims | discovery gate tests | candidate/support only |
| Causal intervention | `InterventionProtocol` | scaffold | ground-truth/control/intervention reports | not true causal discovery | causal intervention tests | prediction support only |
| Statistical report | `StatisticalExperimentReport`, `BootstrapCI` | scaffold | deterministic uncertainty report | lightweight CI scaffold, not full statistical suite | statistical report tests | descriptive evidence |
| Benchmark suite | `BenchmarkScenarioSuite` | scaffold | stable baseline/ablation scenarios | small default scenarios | benchmark suite tests | comparable runs |
| Scientific claim gate | `ScientificClaimGate` | implemented | overclaim blocker | heavy claims rejected/downgraded by default | claim gate tests | claim control |

## Advanced scientific validation patch

| Capability | Current API | Status | Claim control |
|---|---|---:|---|
| Causal validation | `codontrace.genesis.causal_validation` | scaffold/implemented | Separates temporal precedence, association, conditional association, intervention, and ground-truth recovery; never claims true causality by graph alone. |
| ADF macro validation | `adf_runtime`, `adf_validation` | scaffold/implemented | ADF decode and macro expansion are operational; language emergence is not claimed without null models and ablation. |
| Active QD search loop | `qd_search` | scaffold/implemented | Archive can feed parent selection/emission; still research-alpha, not full OEE proof. |
| Capsule transfer validation | `capsule_validation` | scaffold/implemented | Adoption counters alone are not transfer proof; ON/OFF or before/after effect needed. |
| Discovery experiment protocol | `discovery_protocol` | scaffold/implemented | D0/shadow/persistence/ablation/multiseed/replay gates downgrade unsupported claims. |
| Scientific manifest strictness | `validate_scientific_manifest` | scaffold/implemented | Flags missing or placeholder hashes for paper-grade runs. |
| Rule compatibility | `validate_rule_compatibility` | scaffold/implemented | Checks structured proposal compatibility with registry/table/spec; no code execution. |
| Scientific claim gate | `ScientificClaimGate` | implemented | Rejects/downgrades full GENESIS, artificial-life, OEE, and strong causal claims by default. |

## Strong Library Phase 2 additions

| GENESIS Concept | Current API | Status | Operational Level | Missing / Limitation | Claim Allowed? |
|---|---|---:|---|---|---|
| Variable genome | `GenomeProgram`, `StructuralMutationRecord` | partial | codon-token structural mutation | not unbounded OEE | `variable_genome_supported` |
| Executable ADF macro | `ADFMacroRegistry.expand` | partial | bounded subroutine expansion | no semantic closure/language emergence claim | `adf_macro_supported` |
| Contribution ledger | `ContributionLedger` | scaffold | attribution estimate | not true gene causality | `lineage_attribution_supported` |
| Innovation protection | `InnovationProtectionConfig` | scaffold | max protected fraction/scope guard | no full innovation ecology | metadata/evidence only |
| EventGraph | `EventGraph` | partial | temporal association canonical graph | CausalGraph remains compatibility alias | `temporal_association` |
| Predictive probe | `PredictiveProbeResult` | scaffold | lagged/conditional predictive evidence | not intervention evidence | `lagged_predictive_support` |
| Intervention result | `InterventionResult` | scaffold | paired-seed effect object | full causal runner still benchmark-dependent | `intervention_supported` if ClaimGate passes |
| OEE measurement | `OEEMetricsReport` | scaffold | metrics/thresholds/shadow requirement | never proof of open-endedness | `oee_measurement_only`, `oee_candidate` |
| Translation profile | `TranslationProfile` | experimental | adaptive GP-map proxy | not semantic closure | `adaptive_gp_map_proxy` |
