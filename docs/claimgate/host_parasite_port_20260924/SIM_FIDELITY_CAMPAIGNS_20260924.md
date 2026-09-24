# Scientific Simulation Fidelity + Differentiation — 2026-09-24

**Project:** CodonTrace Genesis  
**Branch:** `feat/detoy-d0-d1-type2-diagonal`  
**De-toy:** D0+D1 (CiteGate + type-II / diagonal A)  
**Runners:** `host_parasite_sim_fidelity_campaigns.py`, `host_parasite_diff_campaigns.py`  
**Suite:** `tests/test_host_parasite_sim_fidelity.py`  
**Artifact:** `sim_fidelity_campaigns_results.json`  
**pack_digest:** `46184d6d86782344905142c0db06595e20fcddb4bc0be3683be99e5244faa751`

**Architecture locks (unchanged):** ONE `host_parasite` DomainProfile; **cell** =
SemanticGenome / Genesis substrate; microbe / parasite = COU labels only; no
infection physics in `engine.py`; BAIC pins A–C byte-identical; ClaimGate refuse
list not loosened.

**Local time:** authored 2026-09-24 ~05:00 IRST (UTC+3:30).

---

## Methods (brief)

Campaigns ask whether Genesis reproduces a *qualitative* literature signature
(SF) or uniquely refuse / audit claims competitors often skip (DX). Each panel
declares literature prediction, Genesis setup (seeds / modes / nulls), metric,
pre-registered success criterion, ClaimGate ceiling, and SUCCESS / PARTIAL /
FAIL with numbers. Prefer honest FAIL over fake win. Infection stays on the
DomainProfile port (`host_parasite_env.py`); ALife engine remains domain-agnostic.

---

## Matrix A — Simulation fidelity (SF1–SF8)

| SF# | Prediction (short) | DOI | Result | Key metric / note |
|---|---|---|---|---|
| SF1 | Coexistence requires cost-of-generalism | 10.1098/rspb.2012.0769 | **SUCCESS** | extinction_proxy / coexistence / superparasite_dominance |
| SF2 | Biotic vs abiotic entropy / complexity contrast | 10.1371/journal.pbio.1002023 | **SUCCESS** | mean_entropy_delta_vs_baseline (biotic − abiotic; content_null) |
| SF3 | ARD→FSD shift under increased cost-of-generalism | 10.1098/rspb.2014.2297 | **SUCCESS** | transition_observed + early/late cost_of_generalism + labels |
| SF4 | Multi-host type-II / diagonal-A cycling (Sci Rep) | 10.1038/srep10004 | **SUCCESS** | cycling_detected ≥3/5 seeds; red_queen_proved=False |
| SF5 | Dual-genome digest divergence under coevolution  | 10.1371/journal.pbio.1002023 | **SUCCESS** | arms_are_distinct + host≠parasite digests + coevo≠freeze |
| SF6 | Sequential Cornish: obs match / forced success s | arXiv:2301.07210 | **SUCCESS** | observational_match ∧ interventions_executed ∧ ¬intervention_supported |
| SF7 | Replay digest stability — same seed → same publi | internal:ENGINE_REPLAY_CONTRACT | **SUCCESS** | campaign_digest equality across repeats; cross-seed distinctness |
| SF8 | Engine hygiene — infection logic never in engine | internal:ARCHITECTURE_PORTS | **SUCCESS** | zero forbidden infection tokens in engine modules; env has inject API |

**SF tally:** 8 SUCCESS / 0 PARTIAL / 0 FAIL (after De-toy D0+D1).

**De-toy D0+D1:** SF4 retargeted to Sci Rep doi:10.1038/srep10004 (PMC4405699);
ghost BMC Ecol DOI rejected. Port-local type-II FR + diagonally dominant A +
intermediate d / adequate K makes multi-host cycling *structurally testable*.
Under declared capable defaults, 5/5 seeds cycle. Legacy weak NFD proxy still
0/5. SciAdv doi:10.1126/sciadv.1501548 is related comparator only.
`red_queen_proved` remains False forever — SUCCESS ≠ proof.

---

## Matrix B — Differentiation (DX1–DX8) — not another Avida

| DX# | Differentiation punchline | DOI / authority | Result | Contrast headline |
|---|---|---|---|---|
| DX1 | ClaimLadder theatrical fail-closed — spectacular | internal:CLAIM_LADDER + Pineau checklist spirit | **SUCCESS** | biotic Δentropy=0.444, ARD→FSD cost jump=0.217, yet 17/17 overclaims still blocked |
| DX2 | Okasha Price≠causality gate — descriptive Price  | 10.1098/rstb.2019.0365 | **SUCCESS** | Price covariance=0.147420 available as diagnostic; ClaimGate keeps major_transition_pro... |
| DX3 | Channon/MODES measurement-only — observe without | 10.1162/artl_a_00280 | **SUCCESS** | measurement_only ALLOWED (tokyo_type1_measurement_only); tokyo_type1_passed / modes_pas... |
| DX4 | Replay integrity spectacle — same seed identical | internal:ENGINE_REPLAY_CONTRACT | **SUCCESS** | Identical seeds → identical digests; seed+1 → mismatch; forged intervention_supported a... |
| DX5 | Content-null HE-style trap — treatment looks dra | internal:HE02 dual-null + Floreano honesty | **SUCCESS** | intact mean_score=0.20 vs content_null=1.00; without content_null arm, candidate_eviden... |
| DX6 | Cross-simulator auditor posture — ClaimGate matr | internal:ARCHITECTURE_PORTS + DomainProfile | **SUCCESS** | host_parasite DomainProfile blocks phage_therapy_cleared; other profiles allow the stri... |
| DX7 | Cornish headline — obs 0.2 vs forced ints 1.0/1. | arXiv:2301.07210 | **SUCCESS** | obs_score=0.2 vs intervention_scores=[1.0, 1.0, 1.0] — looks fixed; ClaimGate intervent... |
| DX8 | Engine boundary hard lock — infection/virulence  | internal:ARCHITECTURE_PORTS | **SUCCESS** | engine.py: zero infection tokens; host_parasite_env.py: inject APIs present |

**DX tally:** 8 SUCCESS / 0 FAIL.

### Most eye-catching contrasts

1. **DX1:** biotic Δentropy ≈ 0.444 and ARD→FSD cost jump ≈ 0.22, yet **17/17**
   overclaims (intelligence, Red Queen, MODES-passed, phage therapy, …) stay blocked.
2. **DX7:** observational score **0.2** vs forced interventions **[1.0, 1.0, 1.0]** —
   still `intervention_supported=False` (Cornish).
3. **DX5:** intact mean_score **0.20** vs content_null **1.00**; without the null arm,
   `candidate_evidence` raises `ConfigurationError`.
4. **DX3:** `tokyo_type1_measurement_only` ALLOWED; `tokyo_type1_passed` / `modes_passed*`
   REFUSED (Channon measurement without pass-washing).
5. **DX2:** Price covariance ≈ 0.147 present as diagnostic; `major_transition_proved`
   remains False (Okasha).

---

## ClaimGate ceilings (pack-wide)

Refused forever on this port (spot-checked): `red_queen_proved`,
`intelligence_proved`, `modes_passed_proved`, `tokyo_type1_passed`,
`phage_therapy_cleared`, `intervention_supported`, `complexity_emergence_proved`,
`gene_identity_proved`, `crispr_identity_proved`, `oee_modes_passed`,
`virulence_optimized_for_humans`, `major_transition_proved`,
`biosafety_level_certified`, `clinical_pathogen_model`.

Ladder unchanged on attach (`claimgate_audit.ladder_unchanged=True`).

---

## Honest answer: can Genesis do real simulation?

**Yes, with ceilings.** Under stated digital setups, CodonTrace Genesis reproduces
several qualitative host–parasite / digital-evolution signatures (cost-of-generalism
coexistence, biotic vs abiotic entropy contrast, ARD→FSD cost-rise labels,
dual-genome digest divergence, Cornish intervention refuse, replay stability,
engine hygiene). It does **not** reproduce multi-host Red Queen perpetual cycles
(SF4 SUCCESS under capable type-II defaults — still not red_queen_proved). Differentiation tests show the product is not
“another Avida”: spectacular runtime metrics do not promote claims; Price is not
causality; OEE can be measured without pass-washing; content-null is mandatory for
candidate evidence; ClaimGate is DomainProfile-scoped; infection physics stay out
of `engine.py`.

---

## References (grounded)

| Topic | Citation |
|---|---|
| Coevolution → complexity (Avida) | Zaman et al. 2014 *PLOS Biology* doi:10.1371/journal.pbio.1002023 |
| Mixing → ARD | Gómez, Ashby & Buckling 2015 *Proc R Soc B* doi:10.1098/rspb.2014.2297 |
| Cost of generalism / mode of interaction | Quigley et al. 2012 *Proc R Soc B* doi:10.1098/rspb.2012.0769 (arXiv:1210.2320) |
| Multi-host Red Queen cycles | Rabajante et al. 2015 *Sci Rep* doi:10.1038/srep10004 (PMC4405699); SciAdv doi:10.1126/sciadv.1501548 related only |
| Price ≠ causality | Okasha line, *Phil Trans R Soc B* doi:10.1098/rstb.2019.0365 |
| MODES | Dolson et al. 2019 *Artificial Life* doi:10.1162/artl_a_00280 |
| Tokyo Type 1 measurement procedure | Channon 2024 *Artificial Life* doi:10.1162/artl_a_00430 |
| Observational ≠ interventional | Cornish et al. arXiv:2301.07210 |

---

## Pins

| Artifact | SHA256 |
|---|---|
| `docs/hard_experiment_01/results_v7.json` | `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6` |
| `docs/claimgate/risk_bar.json` | `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7` |
| `docs/claimgate/biomedical_study.json` | `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce` |
