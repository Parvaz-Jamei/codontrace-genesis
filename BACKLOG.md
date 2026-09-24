# Backlog

## Next research-library phases

1. `v0.3.0a1`: Release Candidate hardening around hosted CI evidence, pip-audit, TestPyPI/PyPI gate decisions, citation validation, and supply-chain evidence.
2. `v0.3.0a1`: Scientific Evidence Pack planning for owner-side empirical validation, with no proof claims and no heavy runner inside core.
3. Later: optional heavy experiment runners, validation notebooks, and reports outside the dependency-free core, if needed.
4. Phase B (implemented, opt-in): Sexual recombination substrate — CodonTrace birth chamber + positional continuous corresponding recombination, digest-backed dual-parent records, opt-in `diploid_meiosis` homolog-reduction analog and `TWO_FOLD_COST_SEX` (optional knobs peer-compatible with `avida.cfg` `RECOMBINATION_GROUP`). Research defaults stay asexual. Mating types / lekking remain stubs.
5. Phase C (implemented, opt-in): chemostat / periodic / fluctuating environments on top of the Phase A ecology preset. Avida `RESOURCE` initial/inflow/outflow, Avida-ED periodic or seeded regimes, global and/or local patches, digest-backed env trajectory replay. Default life-loop stays static. Plasticity-evolved claims deferred.
6. Phase D (implemented, opt-in measurement): multi-generation fitness/behavior evidence pack, persistence-filtered MODES-style axes with explicit `persistence_window_t` coalescence-window semantics, Bedau activity surfaces, same-seed cohort comparison, Channon 2024 Tokyo Type 1 *measurement* protocol, opt-in Python Empirical-style shadow adapter, multi-seed Tokyo campaign / window-sweep suite, and ClaimGate-honest `instinct_improved` / `oee_measurement_only` / `tokyo_type1_measurement_only` labels. Default A/B/C presets unchanged. OEE/Tokyo Type 1 pass / intelligence proof remains blocked.
7. Phase E (implemented, opt-in substrate): capsule/memory with real subsequent action/ATP/task-eligibility effects, role/propagule gates, deme messaging (Goldsby subset) plus GermlineReplication-style deme payoff + contribution ledger, plasticity protocol object over Phase C cues, OntoAvida-style phenotype export (action-execution transcriptome proxy), `AvidaParityProtocolSpec`, opt-in Logic-9 reaction coupling, and learning causal payoff protocol. Defaults off. Collective intelligence / evolved-plasticity / associative-learning-proved / Avida-replacement claims remain blocked.
8. Phase G (implemented, opt-in substrate): named `MaterialSpec` chemistry-effect overlay (energy yield, toxicity, viscosity/diffusion, permeability, signaling, scarcity), named-material chemostat, simple stoichiometric CRN, cellularity/membrane uptake gate, ChEBI/KEGG schema hooks without a GEM/MD solver. Defaults off. Realistic-chemistry / wet-lab-equivalent claims remain blocked.
9. Scientific authorities 2026 map (`docs/SCIENTIFIC_AUTHORITIES_2026.md`) plus honesty note `docs/WHY_NOT_INTELLIGENCE_YET.md`: literature vs CodonTrace Genesis reality. Completeness of *measurement and documentation*, not a claim that CodonTrace Genesis replaces those systems or is close to AGI. JaxLife NN and ASAL CLIP stay docs-only.
10. Phase F (implemented, opt-in measurement): multi-seed collective deme payoff campaigns, deme mean-fitness ranking, division-of-labor *metrics*. Still ClaimGate-blocks `collective_intelligence` / `proved_collective_intelligence`. Not a major transition in individuality.
11. Phase H (implemented, opt-in measurement + literature RAG): research corpus/retriever; communication ablation harness; group-vs-individual effect sizes (`seed_count` library default 12 = exploratory; research-grade 30); Goldsby 2012 task-switching cost hook; candidate checklist printer. ClaimGate still blocks `collective_intelligence` / `intelligence` / AGI. Library-complete beta is not “done.”
12. Phase I (implemented, opt-in CI evidence harnesses): heldout unfamiliar-partner generalization; evolved (not assigned) DoL + Gorelick NMI + ablation; MLS vs organism-only evolutionary *outcome*; export-of-fitness scaffold with `major_transition_in_individuality=False`. ClaimGate flags can be earned from research-scale evidence objects only — never auto-set from smokes. `collective_intelligence` still blocked.
13. Phase J (implemented, opt-in replay-verified CI candidate packs): independent campaign digest re-execution so `replay_verification` can be earned honestly when digests match; Price-equation / Okasha MLS1 covariance scaffold (snapshot, no transmission term). Research-scale full flags may allow `collective_intelligence_candidate`. `collective_intelligence` / AGI / Tokyo Type 1 passed / Avida replacement still blocked. No version bump.
14. Phase K (implemented, opt-in CI-depth measurements): evolved send/retrieve/broadcast instruction analog that can pay under ablation; Goldsby-scale CPU-delay specialist harness (research default 50 replicates); multi-generation Price with a transmission term; Michod/Conlin conflict-suppression hooks. Smoke never earns flags. Bare `collective_intelligence` / intelligence / AGI / `tokyo_type1_passed` still blocked. No version bump.
15. Phase L (implemented, opt-in Avida-fidelity analogs): closer ORGANISM_MESSAGING (per-organism FIFO, faced-neighbor send, block_propagation) and DEME_GROUP (maybe_replicate_demes) semantics — still analog, not a C++ port; Goldsby 2012-aligned specialist measurement (not the PNAS experiment); optional Phase K coordination-ablation evidence feed that does not auto-set ClaimGate flags. Smoke never earns. Bare `collective_intelligence` / intelligence / AGI / `tokyo_type1_passed` still blocked. No version bump.
16. Hard experiment 01 (implemented, measurement paper): capsule source-bias vs next-generation fitness (library default 12 seeds = exploratory; research-grade n=30), with source-fitness ablation and capsules-off controls, effect size, and replay digests. Claim ceiling `runtime_observation`. Not a Phase M. Further engine.py splits can continue if A–E pins stay stable.
17. Wave 2 (implemented): simulator-agnostic ClaimGate auditor (`codontrace.claimgate`). Public 0–5 only. Avida/MABE2 adapters are skeletons. HE01 v2 stays `runtime_observation`. Not Wave 3 / tag / PyPI / Phase M+.

Phase A life-loop literature items (basal metabolism, starvation reason, limited depletable resources, spatial capacity, differential reproductive-success observation) are implemented on the ecology preset only.

## Wave 0 lint-type (CI `continue-on-error`)

Job `lint-type` is **not blocking**. Recorded inventory below is the 2026-09-11 snapshot
on `0.3.0b4.dev0` after PR #19. That snapshot is **not** a claim that those
findings were later deleted from the tree.

### Policy as of 2026-09-17 (`0.3.0b5` line)

`[tool.ruff.lint] ignore = ["E501"]` only. Line-length is deferred. The other
codes from the snapshot are **visible** again; they are not ignored as a block.
No dedicated `ruff check --fix` pass has landed, so I001 / F401 / UP042 / F811
and the rest of the non-E501 set are still open. `mypy --strict src` is unchanged.

Cleared in this wave: none of the 1273 snapshot rows by code edit.
Changed: display policy (E501 hidden; remainder no longer hidden).

### Ruff snapshot 2026-09-11 — 1273 findings (`ruff check src tests`, no ignores)

| Code | Count | Rule | Status 2026-09-17 |
|---|---:|---|---|
| E501 | 955 | line-too-long | ignored in `pyproject.toml`; not wrapped |
| I001 | 87 | unsorted-imports | open |
| F811 | 48 | redefined-while-unused | open |
| UP042 | 37 | replace-str-enum | open |
| F401 | 33 | unused-import | open |
| B017 | 27 | assert-raises-exception | open |
| E402 | 21 | module-import-not-at-top-of-file | open |
| UP037 | 12 | quoted-annotation | open |
| B009 | 11 | get-attr-with-constant | open |
| E701 | 6 | multiple-statements-on-one-line-colon | open |
| F841 | 6 | unused-variable | open |
| B023 | 5 | function-uses-loop-variable | open |
| E702 | 5 | multiple-statements-on-one-line-semicolon | open |
| SIM102 | 4 | collapsible-if | open |
| SIM114 | 3 | if-with-same-arms | open |
| other | 13 | UP017, SIM113, SIM401, SIM108, SIM210, F402, SIM118, SIM103, SIM105, F821, UP012, SIM300, B905 (1 each) | open |

About 189 are auto-fixable with `ruff check --fix` (not run on this line).
After E501 ignore, expected remaining visible ruff count is ~318 plus any
new findings since the snapshot. A later CI log on `ba03621` reported 1336
before the E501-only ignore landed; that is the same backlog plus drift, not
a new science failure.

### Mypy (`mypy --strict src`) — 263 errors in 37 files (2026-09-11 snapshot)

| Code | Count |
|---|---:|
| arg-type | 83 |
| attr-defined | 38 |
| dict-item | 29 |
| assignment | 29 |
| misc | 26 |
| union-attr | 24 |
| operator | 17 |
| unused-ignore | 5 |
| var-annotated | 3 |
| type-var | 3 |
| call-arg | 2 |
| no-untyped-def, no-redef, no-any-return, name-defined | 1 each |

Heaviest files: `genesis/__init__.py` (37), `engine.py` (35),
`genesis/population.py` (25), `actions.py` (20), `genesis/fitness.py` (14),
`genesis/birth.py` (13), `genesis/logic9.py` (12).

Do not treat a green `continue-on-error` job as a type-safe release gate.

## Non-goals that remain active

- No UI, dashboard, CLI product, report writer, database, web server, cloud service, or config-file framework in core.
- No runtime dependency additions.
- No AGI, artificial-life, open-ended discovery, causal-learning, knowledge-transfer, or benchmark-superiority proof claims.
