# ILW preregistration v1 (locked before campaign outcomes)

**Product:** CodonTrace Genesis (`codontrace`)  
**Experiment id:** `ilw_integrated_eco_evolutionary_runtime`  
**Prereg version:** `ilw_prereg_v1`  
**Branch context:** `wave-1d-seed-variance` (ILW-4)  
**Status:** LOCKED design + stop rules. **No campaign outcomes in this file.**

**ClaimGate ceiling:** `runtime_observation` (never loosened here).  
**Scientific name:** `integrated eco-evolutionary runtime`  
**Forbidden labels:** `intelligence`, `agi`, `collective_intelligence`,
`proved_collective_intelligence`, `tokyo_type1_passed`, `avida_replacement`.

This document is frozen **before** seeing ILW-5 campaign numbers. Code hooks
live in `src/codontrace/genesis/ilw/prereg.py`. Campaign payloads (ILW-5+) must
record `ilw_prereg_design_digest` and `ilw_prereg_document_digest`.

---

## 1. Question (mechanism, not intelligence)

Does the Integrated Living World causal chain

```text
genome → toolchain → VM phenotype → action → resource/world
→ experience → capsule → transport/accept/apply → policy
→ survival/reproduction → mutation/lineage → next ecological state
```

form one `run_id` / `WorldSpec` / scheduler / ledger system whose
**multi-pattern** signatures (POM) and declared **interactions** survive
edge knockouts, sham/yoked controls, and a locked scale ladder — without
raising ClaimGate above `runtime_observation`?

Null / small / scale-fragile effects are valid findings. They do **not**
unlock a higher claim.

---

## 2. Pattern-Oriented Modeling acceptance patterns

ATP mean alone is **not** acceptance (Grimm & Railsback, 2012,
https://doi.org/10.1098/rstb.2011.0180). The world must be judged on these
patterns **together** (ILW plan §گیت چندالگویی / multi-pattern gate):

| ID | Pattern |
|----|---------|
| `pom_1_toolchain_phenotype` | Toolchain and phenotype are valid under the integrated run. |
| `pom_2_conservation` | Energy/resource conservation assays pass. |
| `pom_3_multigen_turnover` | Multi-generation persistence with real turnover (not fixture). |
| `pom_4_diversity` | Non-token genetic/phenotypic diversity is observable. |
| `pom_5_eco_evo_feedback` | Competition, niches, and eco-evolutionary feedback emerge. |
| `pom_6_capsule_causal` | Capsule transfer changes action and descendant fitness proxy. |
| `pom_7_null_yoked_break` | Path breaks predictably under null/yoked/edge-off controls. |
| `pom_8_scale_direction` | Effect direction retained across scales, or failure reported honestly. |

**Pilot gate:** patterns must be *recorded* (pass/fail/inconclusive) at S2
before confirmatory seeds. Recording is not a science claim.

### Cumulative cultural evolution (do not claim yet)

Do **not** claim CCE until **all four** Mesoudi & Thornton (2018) core
criteria pass together (https://doi.org/10.1098/rspb.2018.0712):

1. Innovation (behavioural novelty or modification)
2. Social transmission
3. Performance improvement (fitness-proxy)
4. Sequential improvement across generations

ILW-4 does not authorize a CCE claim.

---

## 3. Interactions to estimate

One-factor-at-a-time (OAT) is insufficient (Saltelli & Annoni, 2010,
https://doi.org/10.1016/j.envsoft.2010.04.012). At minimum estimate:

1. `toolchain × capsule`
2. `capsule × ecology`
3. `mutation × capsule`
4. `heterogeneity × population_size`

---

## 4. Scale ladder S0–S4 (numbers locked pre-outcome)

| Scale | Role | Grid | Tick horizon | Pop cap | Niches | Min turnovers |
|-------|------|------|--------------|---------|--------|---------------|
| S0 | unit | 4×4 | 6 | 8 | 2 | 0 |
| S1 | integrated smoke | 16×16 | 32 | 24 | 4 | ≥1 |
| S2 | multi-gen pilot | 32×32 | 128 | 64 | 4 | ≥3 |
| S3 | research | 64×64 | 512 | 128 | 6 | ≥10 |
| S4 | finite-size challenge | widths/heights ∈ {32,64,96}; horizons ∈ {128,256,512}; pop caps ∈ {64,128,192} | — | — | 6 | ≥3 per cell |

S0/S1 never promote to a science claim. S2 is pilot-only. S3/S4 require
pilot gates (below). S4 reports effect-direction retention or honest failure.

### Stop rules (explicit)

1. `stop_escalate_if_replay_fails`
2. `stop_escalate_if_conservation_fails`
3. `stop_escalate_if_required_edge_coverage_lt_1`
4. `stop_escalate_if_pom_patterns_incomplete_at_current_scale`
5. `stop_confirmatory_if_pilot_gates_fail`
6. `stop_campaign_if_claim_ceiling_would_rise`
7. `stop_s4_cell_if_finite_size_effect_direction_reverses_without_prereg_amendment`
8. `never_promote_s0_or_s1_to_science_claim`

---

## 5. Horizon definitions

Report **all four**, not ticks alone:

| Metric | Definition |
|--------|------------|
| `ticks` | Scheduler tick count under one `run_id` / WorldSpec. |
| `generation_turnover` | Completed birth→death cycles (unique organism ids that both appeared via reproduction and later died), averaged per seed. |
| `lineage_depth` | Max ancestry-chain length from a living organism to the oldest recorded ancestor. |
| `regime_changes` | Count of discrete resource-regime shifts (stale information may expire). |

---

## 6. Seed policy

| Role | Seeds | Use |
|------|-------|-----|
| Pilot | `3100..3107` | S2 pilot / exploratory; POM recording; gate checks |
| Smoke | `{3100}` subset of pilot | Cheap CI / local stub |
| Confirmatory held-out | `4100..4107` | **ILW-5 only after pilot gates**; never used in pilot analysis |

**Hard rule:** `PILOT_SEEDS ∩ CONFIRMATORY_HELD_OUT_SEEDS = ∅`.  
Pilot harness stub **refuses** confirmatory seeds until gates pass (fail-first).

---

## 7. Edge knockouts + sham/yoked controls

Same world; **one edge (cut set) per knockout**:

- `toolchain_to_action_off`
- `experience_to_capsule_off`
- `capsule_transport_off`
- `capsule_to_policy_off`
- `mutation_off`
- `ecological_feedback_off`
- `lineage_inheritance_off`

Controls:

- **Sham cost-match:** preserve compute/move/copy cost when an edge is off so
  cost/throughput alone cannot explain differences.
- **Yoked timing:** preserve attempt timing/rate while severing informational
  content (no oracle fitness shortcut).
- **No outcome injection:** fixture/oracle/treatment-oracle/fitness-shortcut
  remain forbidden (`adapter_honesty`).

---

## 8. DoE plan: Morris → fractional-factorial / DSD

### Phase 1 — Morris elementary-effects screening

- Method: Morris EE trajectories (reject OAT-only inference).
- Cite: Saltelli & Annoni (2010) https://doi.org/10.1016/j.envsoft.2010.04.012
- Supporting EE revision: Campolongo, Cariboni & Saltelli (2007)
  https://doi.org/10.1016/j.envsoft.2006.10.004
- Minimum trajectories: 4 (budget permitting 4–10).
- Outputs: μ*, σ, factor ranking.

### Phase 2a — Fractional-factorial on toggles

- 2-level fractional factorial on edge knockouts / toggles.
- Target interactions listed in §3.

### Phase 2b — Definitive Screening Design (continuous)

- Three-level DSD for continuous knobs (mutation rate, adopt threshold,
  renewal rate, heterogeneity, population size, regime-shift interval, …).
- Cite: Jones & Nachtsheim (2011)
  https://doi.org/10.1080/00224065.2011.11917841

ILW-4 locks this plan only. **Do not run the large campaign here (ILW-5).**

---

## 9. Pilot gates (before confirmatory)

All must be true before any confirmatory held-out seed may run:

1. `replay_ok` — independent replay bitwise-matches `final_digest`
2. `conservation_ok` — resource/energy assays pass
3. `edge_coverage_ok` — required-edge coverage = 100%
4. `pom_patterns_recorded` — all eight POM rows recorded at pilot scale
5. `no_claim_promotion` — smoke/pilot issued no ladder promotion
6. `claim_ceiling_ok` — ceiling still `runtime_observation`

---

## 10. Literature refresh (DOIs not invented)

Verified against public records for this prereg (2026-09-13):

| Topic | Citation | DOI |
|-------|----------|-----|
| POM | Grimm & Railsback, *Phil. Trans. R. Soc. B* (2012) 367:298–310 | [10.1098/rstb.2011.0180](https://doi.org/10.1098/rstb.2011.0180) |
| OAT weakness / SA practice | Saltelli & Annoni, *Env. Model. Softw.* (2010) 25:1508–1517 | [10.1016/j.envsoft.2010.04.012](https://doi.org/10.1016/j.envsoft.2010.04.012) |
| Morris EE (revised) | Campolongo, Cariboni & Saltelli, *Env. Model. Softw.* (2007) 22:1509–1518 | [10.1016/j.envsoft.2006.10.004](https://doi.org/10.1016/j.envsoft.2006.10.004) |
| DSD | Jones & Nachtsheim, *J. Qual. Technol.* (2011) 43:1–15 | [10.1080/00224065.2011.11917841](https://doi.org/10.1080/00224065.2011.11917841) |
| CCE criteria | Mesoudi & Thornton, *Proc. R. Soc. B* (2018) 285:20180712 | [10.1098/rspb.2018.0712](https://doi.org/10.1098/rspb.2018.0712) |

Additional ILW plan refs (unchanged; not re-derived here): MODES
(`10.1162/artl_a_00280`), social learning strategies
(`10.1126/science.1184719`), Phylotrack (`10.48550/arXiv.2405.09389`),
model docking (`10.1007/BF01299065`).

---

## 11. Digests & next milestone

- Design digest: `ilw_prereg_design_digest()` in `prereg.py` (canonical JSON).
- Document digest: SHA-256 of this file’s UTF-8 bytes
  (`ilw_prereg_document_digest()`).
- **Next:** ILW-5 factorial/ablation campaign + scale challenge **only after**
  pilot gates pass. No Colab. No ClaimGate loosening. No CCE/intelligence claim.
