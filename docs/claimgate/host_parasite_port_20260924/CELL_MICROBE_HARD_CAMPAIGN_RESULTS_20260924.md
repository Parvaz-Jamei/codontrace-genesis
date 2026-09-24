# Cell↔microbe hard campaign results — 2026-09-24

**Project:** CodonTrace Genesis  
**Branch:** `exp/cell-microbe-hard-campaigns` (stacked on open #53 hard regressions)  
**Runner:** `src/codontrace/genesis/host_parasite_cell_microbe_hard_campaigns.py`  
**Suite:** `tests/test_host_parasite_cell_microbe_hard_campaigns.py`  
**Artifact:** `cell_microbe_hard_campaigns_results.json`  
**pack_digest:** `bd384b651e074478ef2c8fa904dbc19a40c02021294c193a8aaf4cf8ad6663fc`

**Architecture locks (unchanged):** ONE `host_parasite` DomainProfile; **cell** =
SemanticGenome / Genesis substrate (not a DomainProfile); microbe / bacterium /
virus / parasite = COU semantic labels only; no infection physics in `engine.py`;
BAIC pins A–C byte-identical; ClaimGate refuse list not loosened.

**Local time:** authored 2026-09-24 ~04:30 IRST (UTC+3:30).

---

## Why these campaigns (anti-fake)

Wave-6 journal smoke already attaches happy-path digests. These campaigns are
**harder**: larger / contingency-aware seed packs, dual-null separations with
measured magnitudes, supporting-edge honesty (support ≠ prove), and fail-closed
ClaimGate attach on one bundle. Every panel has a falsification path. Prefer
surprising negatives and seed contingency over hyped positives.

Framing: cell substrate × parasite/microbe **labels** on the same digital
host–parasite frame — not wet microbial cell biology, not phage therapy, not BSL.

---

## Campaign results

### CM1 — Multi-seed contingency (Zaman S1 honesty)

| Field | Detail |
|---|---|
| **Setup** | Mixed seeds `[3, 6, 7, 8, 9, 11, 12, 13]` parasite_present vs parasite_absent; edge pack `[1, 2, 4]`. |
| **Why hard** | Zaman S1 honesty: mixed seeds include contingent collapses and rising seeds; supporting-edge pack still never unlocks complexity emergence. |
| **Falsifier** | parasite_absent dual-null + contingent seed collapses |
| **Measured** | mixed `hypothesis_supported=False`; edge `hypothesis_supported=True`; cross-seed variance=1.1428571429; rising=2, failing=6; mean Δ present=0.5, absent=0.625. |
| **Honesty** | Support on edge seeds ≠ complexity_emergence_proved; mixed pack falsifies universal rise law. `complexity_emergence_proved=False`. |
| **Digests** | mixed `56c8fc8db2b2ccb7fc47b010…`; edge `7e44ba94d64806506cc5723a…` |

**Parasite-present seed heat**

| seed | richness_delta | contingent | outcome_score |
|---|---|---|---|
| 3 | 0 | True | 0.0 |
| 6 | 0 | True | 0.0 |
| 7 | 3 | False | 0.2 |
| 8 | 0 | True | 0.0 |
| 9 | 0 | True | 0.0 |
| 11 | 0 | True | 0.0 |
| 12 | 0 | True | 0.0 |
| 13 | 1 | False | 0.2 |

**References:** Zaman et al. 2014 doi:10.1371/journal.pbio.1002023; challenge S1;
Dolson et al. 2019 MODES doi:10.1162/artl_a_00280 (comparator, not a pass claim).

---

### CM2 — Dual-genome Zaman (cell host vs microbe parasite labels)

| Field | Detail |
|---|---|
| **Setup** | Seeds `[101, 202, 303, 404]`, steps=5; freeze / replay / reciprocal arms. |
| **Why hard** | Host SemanticGenome (cell substrate) and parasite SemanticGenome (microbe label) digests must separate across freeze/replay/reciprocal arms without claiming Red Queen or complexity emergence. |
| **Falsifier** | arm digest distinctness; frozen parasite trajectory flat |
| **Measured** | `arms_are_distinct=True`; per-arm host≠parasite final digests for all seeds. |
| **Honesty** | Digital genome analogue only; CRISPR / gene identity unproved. `red_queen_proved=False`, `complexity_emergence_proved=False`. |
| **Digest** | `bd384b651e074478ef2c8fa904dbc19a…` |

**Arm digests:**  
- `freeze_parasites`: `fa5ffc05a3f8f94022073112…`
- `reciprocal_coevolution`: `015e657c2618163fbd19746d…`
- `replay_parasite_schedule`: `7c6c10a9e1e9f0947cdac863…`

**References:** Zaman 2014 doi:10.1371/journal.pbio.1002023; Acosta & Zaman 2022
doi:10.3389/fevo.2021.750772 (CPU-theft comparator stays *outside* engine).

---

### CM3 — Codon entropy / Hamming dual-null

| Field | Detail |
|---|---|
| **Setup** | Seeds `[11, 22, 33, 44, 55]`; arms biotic_intact / content_null / structure_null / abiotic_stress. |
| **Why hard** | Hypothesis parasites_always_raise_codon_entropy must fail under abiotic / content-null / structure-null while biotic intact separates. |
| **Falsifier** | content_null + structure_null + abiotic_stress deltas ≤ 0 |
| **Measured** | `hypothesis_supported=False`; biotic−content_null entropy Δ = **0.4440262302**. |
| **Honesty** | HE02 dual-null genotype observables; not wet CRISPR identity. |
| **Digest** | `dfbbd551f1c0e3a478b4dbf087bcf3b7…` |

| arm | mean entropy Δ vs baseline | mean Hamming | mean entropy |
|---|---|---|---|
| `abiotic_stress` | 0.0 | 0.000000 | 2.418726 |
| `biotic_intact` | 0.4440262302 | 0.387963 | 2.862753 |
| `content_null` | 0.0 | 0.000000 | 2.418726 |
| `structure_null` | 0.0 | 0.000000 | 2.418726 |

**References:** Floreano et al. 2007 doi:10.1016/j.cub.2007.01.058; Knoester et al.
2008 doi:10.1145/1389095.1389130; HE02 dual-null lineage; Scanlan/Buckling
humility analogue (digital only).

---

### CM4 — ARD→FSD + cost-of-generalism

| Field | Detail |
|---|---|
| **Setup** | Seeds `[11, 22, 33]`, n_slices=8; parasite_coevolution vs structure_null vs abiotic_only. |
| **Why hard** | Time-sliced range trajectories must show ARD-like→FSD-like labels under parasite coevolution while dual-null arms stay undeclared; universal 'always ARD' law falsifies. |
| **Falsifier** | structure_null_shuffled + abiotic_only dual-null |
| **Measured** | `transition_observed=True`; `hypothesis_supported=False` (transition_or_dual_null_falsifies_dynamics_always_ard_under_parasitism). |
| **Honesty** | Digital transition protocol only; Red Queen dynamics unproved. `wet_ard_fsd_identity=False`. |
| **Digest** | `ca7f340f448a4126a74784628446a0b4…` |

**Cost spotlight (seed 11)**

| slice | label | mean_cost_of_generalism |
|---|---|---|
| `parasite_coevolution:early:seed11` | ard_like | 0.2389837287 |
| `parasite_coevolution:late:seed11` | fsd_like | 0.4555775429 |
| `structure_null_shuffled:early:seed11` | undeclared | 0.0092652134 |
| `structure_null_shuffled:late:seed11` | undeclared | 0.0092652134 |
| `abiotic_only:early:seed11` | undeclared | 0.0116414145 |
| `abiotic_only:late:seed11` | undeclared | 0.0568771011 |

**References:** Hall et al. 2011; Koskella & Brockhurst 2014
doi:10.1016/j.tree.2014.04.002; Lopez Pascua et al. 2014 (resource / coevolution
context). Digital transition protocol only — not wet ARD/FSD identity.

---

### CM5 — Sequential Cornish multi-intervention

| Field | Detail |
|---|---|
| **Setup** | Seeds `[11, 22, 33, 44]`; observational baseline then remove_parasites / content_null / steal ablation. |
| **Why hard** | Ordered interventions on cell-level outcome scores can all be effect-distinct after observational match and still must refuse intervention_supported (Cornish rule). |
| **Falsifier** | later intervention order; ClaimGate attach refuse |
| **Measured** | obs score=0.2; intervention scores=[1.0, 1.0, 1.0]; `observational_match=True`; `intervention_supported=False`. |
| **Honesty** | Observational twin match alone never grants intervention_supported; not clinical decision support. |
| **Digest** | `5647d342ee876b2d920333dd46b21612…` |

| step | kind | score | effect_distinct | intervention_supported |
|---|---|---|---|---|
| obs_baseline | observational | 0.2 | False | False |
| int_remove_parasites | intervention | 1.0 | True | False |
| int_content_null | intervention | 1.0 | True | False |
| int_steal_ablation | intervention | 1.0 | True | False |

**References:** Cornish et al. JMLR 27(152) 2026 / arXiv:2301.07210.

---

### CM6 — Scanlan mutator dual-null

| Field | Detail |
|---|---|
| **Setup** | Seeds `[11, 22, 33]`; coevolution×mutation crossed with abiotic + content-null. |
| **Why hard** | Elevated mutation under coevolution must not always improve abiotic fitness vs abiotic-elevated / content-null arms (Scanlan constraint). |
| **Falsifier** | abiotic_elevated + content_null_elevated dual-null |
| **Measured** | `hypothesis_supported=False`; abiotic_elevated − coevo_elevated fitness = **0.1157407407**. |
| **Honesty** | Digital mutator honesty map; wet mutator-gene identity unproved. `gene_identity_proved=False`. |
| **Digest** | `68f1d47bda93dea02e53d20e1c82ba7a…` |

| arm | mut_factor | mean abiotic fitness | mean entropy | mean Hamming |
|---|---|---|---|---|
| `abiotic_elevated_mutation` | 4.0 | 0.657407 | 2.729255 | 0.212963 |
| `coevolution_baseline_mutation` | 1.0 | 0.486111 | 2.680831 | 0.141975 |
| `coevolution_elevated_mutation` | 4.0 | 0.541667 | 2.858915 | 0.410494 |
| `content_null_elevated_mutation` | 4.0 | 0.486111 | 2.883502 | 0.459877 |

**References:** Scanlan et al. 2015 doi:10.1093/molbev/msv032.

---

### CM7 — Task–gene dual-null panel (declared phenotype link)

| Field | Detail |
|---|---|
| **Setup** | cell_host_substrate / microbe_parasite_label / content_null_proxy seeds. |
| **Why hard** | Same declared phenotype-link API must produce distinct digests for cell-host substrate, microbe-parasite label, and content-null proxy without unlocking gene identity. |
| **Falsifier** | content_null_proxy map digest must differ from intact cell map |
| **Measured** | `map_digests_pairwise_distinct=True`. |
| **Honesty** | Declared digital phenotype link only; not CRISPR / wet locus proof. |

| label | seed | map_digest | windows | gene_identity |
|---|---|---|---|---|
| `cell_host_substrate` | 42 | `785233770d414cb4…` | 6 | False |
| `content_null_proxy` | 819 | `96f0299a30e0130c…` | 6 | False |
| `microbe_parasite_label` | 10049 | `da8055d53b109cb6…` | 6 | False |

---

## ClaimGate pack audit

| Check | Result |
|---|---|
| Ladder before → after | `0` → `0` (unchanged=True) |
| Blocked spot-check | all True for red_queen / phage_therapy / BSL / clinical / CRISPR / complexity / gene_identity / intervention_supported / OEE-MODES / intelligence aliases |
| Ceiling cap | `candidate_evidence` |
| Engine infection | `not_in_engine_core` |

---

## Are the results “cool” or modest? (honesty)

**Impressive (real):** contingency seed heat (rising + failing together);
biotic−null entropy Δ ≈ 0.444;
ARD→FSD cost climb under parasite with flat nulls; Cornish score jump
0.2→[1.0, 1.0, 1.0] still refuses support; Scanlan
fitness constraint gap ≈ 0.116.

**Modest / not overclaimed:** all scientific hypotheses here **falsify** or stay
at runtime/candidate ceilings; no Red Queen, no complexity emergence, no gene
identity, no clinical path. That is the point — cool contrasts without الکی
(fake) claim inflation.

---

## Pins / engine / tests

| Check | Status |
|---|---|
| `results_v7.json` SHA256 `35bb5936…21cbd6` | OK |
| `risk_bar.json` SHA256 `4dbe4aa3…771cd7` | OK |
| `biomedical_study.json` SHA256 `9685f2fb…f5ddce` | OK |
| `engine.py` free of infection / HostParasiteEnv | OK |
| New suite | 15 tests |
| Replay policy registers `CellMicrobeHardCampaignPack` | OK |

---

## Code touch

- New runner: `host_parasite_cell_microbe_hard_campaigns.py`
- Replay registration for pack digest
- No ClaimGate refuse-list loosening; no BAIC pin edits; no `population/`
