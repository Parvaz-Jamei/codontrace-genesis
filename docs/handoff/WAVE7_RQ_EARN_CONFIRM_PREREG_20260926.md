# WAVE7 RQ-earn confirmatory prereg — 2026-09-26
**Name:** `HP-ARM01-RQ-EARN-CONFIRM`  
**File role:** sealed design for Genesis Research to code + run after Stage 0 demography pin.  
**Landed scaffold tip:** `fa69913`  
**Wave 6 consensus:** binding (ALife/EcoEvo/Critic/XField).  
**Estimand:** **Fork A** asexual clone Red Queen Dynamics (fluctuating selection with time-lagged host↔parasite class association).  
**Not claimed:** sex maintained by RQ; biological RQ; rewrite of sealed 701–708 hold-class PASS.

Ashby (2020) DOI `10.1111/jeb.13718`: polymorphism / `cycle_candidate` ≠ RQD.  
Dybdahl & Lively (1998) DOI `10.1111/j.1558-5646.1998.tb01833.x`: lagged rare-advantage / tracking.  
Nosek et al. (2018) DOI `10.1073/pnas.1708274114`; Kriegeskorte et al. (2009) DOI `10.1038/nn.2303`.

---

## 0. Prerequisites
1. Stage 0 demography tune (`WAVE7_DEMOGRAPHY_TUNE_PREREG_20260926.md`) completed; winning bolus×patches (and any allowed κ/vir pin) copied **verbatim** into §2 below **before** Stage 1 outcomes.
2. Scaffold P0–P3 present on tip lineage of `fa69913` (or descendant that does not loosen ClaimGate).
3. Sealed FAILS `214df20` / `91ab0c6` / `7171d19` and sealed confirm 701–708 **untouched**.

---

## 1. Seeds, horizon, clocks

| Knob | Lock |
|---|---|
| Seeds | **801, 802, …, 816** (n=**16**) |
| Forbidden reuse | 601–603, 701–708, 751–758, any prior sealed set |
| Generations | **500** |
| Locked windows (hold + floor) | **125, 250, 500** |
| `snap_stride` (dense / lag / phase only) | **25** |
| Parasite class memory L | **8** |
| Lag τ | **4** |
| `lagged_nfds` min_points | **20** |
| `lagged_nfds` threshold | **0.3** (pass iff corr ≤ −threshold and n≥min_points) |

---

## 2. Demography / genetics pins

| Knob | Lock |
|---|---|
| Host N / soft K / parasite N | **64 / 64 / 64** |
| Founders / host bit-flip | **16** distinct / **0.02** |
| Sub-loci | **3×2** graded feature-overlap; **refuse AND-exact** |
| κ / p-mut / vir / steal | **0.5 / 0.25 / 8.0 / 0.15** unless Stage 0 pinned otherwise (then paste Stage 0 winner here before run) |
| Bolus × patches | **Stage 0 winner pinned 2026-09-26: 24.0 × 20** (demography_ok 8/8; grid all 8/8; tie-break lower bolus then fewer patches) |
| Birth ATP / basal / handling | structural confirm defaults |
| `min_viable` floor | **12** (typed `regime_hostile_ne`; **never** hold; **excluded** from lag pass fraction) |
| Primary R_min / ε | **3 / 0.15** |
| Sensitivity (descriptive only) | R_min ∈ {2,3}; ε ∈ {0.15,0.20} on demography-ok seeds — **not** campaign endpoint |

---

## 3. Arms and Pearl passages

**Ecology arms** (census / hold / floor): avirulent, fixed, copassaged.  
**Lag / RQ-earn credit:** **debit-active only** (fixed + copassaged under coevolve genetics). Avirulent never grants RQ-earn credit.

**Pearl do-cuts** (required separate runs per seed; freeze ≠ absent):

| Mode | Expected for seed RQ-earn pass |
|---|---|
| `PASSAGE_COEVOLVE` | `lagged_nfds` all_pass on debit-active arms; optional `debit_backed_cycle=true` |
| `PASSAGE_FROZEN` | lag **fails** (and/or `debit_backed_cycle=false`) — freeze breaks antagonist tracking |
| `PASSAGE_ABSENT` | lag **fails** — no antagonist-driven lag recreation |

Do **not** treat ecology `ARM_FIXED` alone as Pearl `frozen`.

---

## 4. Seed-level conjunctive pass (RQ-earn)

A seed is `rq_earn_seed_pass` iff **all** hold:

1. Floor OK on both debit arms at every locked window under coevolve (else `regime_hostile_ne`; seed **out** of lag fraction; not RQ).
2. Conjunctive polymorphism hold on both debit arms at mid+terminal under coevolve.
3. `score_lagged_nfds_on_debit_arms(...).pass_prelim is True` under coevolve (both debit arms; not oscillation-flip wrapper).
4. Pearl: coevolve lag pass; frozen breaks; absent does not recreate.
5. Replay digests equal for the seed record.

Typed outcomes (non-exhaustive):  
`rq_earn_seed_pass` | `polymorphism_hold` | `cycle_candidate` (obs-only) | `lag_fail` | `pearl_fail` | `regime_hostile_ne` | `parasite_extinct` | `horizon_insufficient`

---

## 5. Campaign accept / reject

| Label | Rule |
|---|---|
| **SUCCESS** (may justify Critic P4 review) | `rq_earn_seed_pass` ≥ **12/16** |
| Mixed (no SUCCESS) | 8–11/16 — report counts; no RQ-proved language |
| FAIL | ≤7/16 — honest FAIL preferred |
| `red_queen_proved` on digests | **false** until separate Critic-signed P4 allowlist commit after SUCCESS |
| `biological_red_queen_proved` | **false** always this campaign |
| Ceiling | ≤`runtime_observation` until SUCCESS evidence recorded → then ≤`candidate_evidence` per Critic; proved still false without P4 |

---

## 6. Implementation map (Research)

| Work | Module |
|---|---|
| NEW confirm runner | `closed_loop_hp_arm01_rq_earn_confirm.py` (suggested) calling structural arm builder + Pearl passages + `score_lagged_nfds_on_debit_arms` + `pearl_contrast_stubs` / live contrasts |
| Clocks | `measurements/rq_frequency_clocks.py` (no proved flags) |
| Hold / floor | reuse structural confirm conjunctive + min_viable logic |
| Design digest | pin this prereg path + numeric table in `rq_earn_confirm_design_dict()` |
| Tests | assert `red_queen_proved is False` on SUCCESS smoke; assert hostile_ne excluded; assert avi ignored for lag credit; assert freeze≠absent |
| `engine.py` | **general / domain-free only** — may be edited for life-loop fidelity; no HP/infection physics in kernel (see `OWNER_ENGINE_MODULE_UPDATE_POLICY_20260926.md`) |

---

## 7. Critic P4 conditions (sign-off checklist — allowlist not flipped here)

P4 may proceed only if Critic affirms ALL of:

- [ ] Sealed 701–708 / sealed FAILS untouched  
- [ ] SUCCESS ≥12/16 on fresh 801–816  
- [ ] Lagged NFDS ≠ `_oscillation_on_arm` alias  
- [ ] Pearl freeze ≠ absent demonstrated on pass seeds  
- [ ] Debit-active only; hostile_ne excluded from lag fraction  
- [ ] No SPC/Cuscore accept path  
- [ ] No sex-by-RQ / Slowinski / two-fold claim  
- [ ] Public prose ordinary research English  
- [ ] Replay OK  

Until then ClaimGate must still raise on `assert_claim_allowed("red_queen_proved")`.

---

## 8. Explicit REJECTS
Soft-green sealed results; rewrite 701–708 into RQ; lower floor/bar/R_min/ε post-peek; raise K as Ne; OR hold clause; infection in `engine.py`; second registry; invented DOIs; packaging `cycle_candidate` or hold-class PASS as `red_queen_proved`.

---

## 9. Status
**TEST DESIGN READY** (ALife freeze). EcoEvo/Critic/XField may tighten refuse language without widening soft-pass. Research: run Stage 0 → paste pins → implement Stage 1 runner → execute 801–816 → RESULTS handoff → Critic P4 gate.

---

## 10. EcoEvo fold (Role B — ecology refuse tightenings)

Agree ALife freeze. No competing design. Additional ecology locks:

1. `lagged_nfds` = **paired** host and parasite match-class frequency series with explicit τ; refuse any wrapper that only counts dominant-class flips (`_oscillation_on_arm`).
2. RQ-earn lag credit on **debit-active arms only**; avirulent never grants RQ-earn credit (control only).
3. Pearl passages are **true** `PASSAGE_COEVOLVE` / `PASSAGE_FROZEN` / `PASSAGE_ABSENT`; ecology arm `fixed` is not Pearl frozen.
4. Seeds typed `regime_hostile_ne` are **excluded** from lagged_nfds pass fraction and cannot be `rq_earn_seed_pass`.
5. Fork A only: no Slowinski invasion score; no sex-maintained-by-RQ prose (Ashby 2020 DOI `10.1111/jeb.13718`; Morran 2011 DOI `10.1126/science.1206360` contrast is arm ecology, not sex unlock).
6. Stage 0 demography FAILURE ⇒ do **not** open Stage 1 by dropping floor/bar (Nosek 2018 DOI `10.1073/pnas.1708274114`).
7. Sealed 701–708 / sealed FAILS untouched; `biological_red_queen_proved=false`; `red_queen_proved=false` until Critic P4.

**EcoEvo: TEST DESIGN READY (fold).**

---

## 11. ClaimCritic fold (Role C — refuse / P4 conditions)

Agree ALife freeze + EcoEvo ecology refuse. No competing design. CausalHonesty locks:

1. **Packaging (C01):** Campaign SUCCESS means `rq_earn_seed_pass` ≥ **12/16** only. Forbid narrating hold-class PASS, `cycle_candidate` counts, or polymorphism alone as RQ-earn SUCCESS or as `red_queen_proved` (Ashby 2020 DOI `10.1111/jeb.13718`). Wave 5 RESULT packaging (hold=0 / cycle×7) is a cautionary anti-pattern.
2. **Lag (C04):** `lagged_nfds` requires paired host+parasite match-class series + explicit τ — never alias `_oscillation_on_arm`.
3. **Pearl (C05):** True `PASSAGE_COEVOLVE` / `PASSAGE_FROZEN` / `PASSAGE_ABSENT`; ecology `fixed` ≠ Pearl frozen; freeze≠absent both required on pass seeds.
4. **Debit-active only; `regime_hostile_ne` excluded** from lag pass fraction and from `rq_earn_seed_pass`.
5. **Ceiling:** ≤`runtime_observation` until SUCCESS evidence recorded → ≤`candidate_evidence`; `red_queen_proved=false` and `biological_red_queen_proved=false` until **separate Critic-signed P4 allowlist commit** after §7 checklist audit. Runner/helpers must keep proved flags false on SUCCESS smoke.
6. **Stage 0 FAIL:** honest FAIL — do not cut floor/bar/R_min/ε or raise soft K to unlock Stage 1 (Nosek 2018 DOI `10.1073/pnas.1708274114`).
7. **Sealed:** 701–708 and FAILS `214df20`/`91ab0c6`/`7171d19` untouched; no sex-by-RQ / Slowinski claim (Fork A).
8. **P4:** Critic signs only after Stage 1 RESULTS meet §7 checklist; allowlist change is **not** part of Stage 1 implement PR.

**Critic: TEST DESIGN READY (fold).** Per-round: `WAVE7_ROUND{1,2}_CRITIC_20260926.md`.

---

## 12. XFieldInnov fold (Role D/I — sampling / Floquet / process refuse)

Agree ALife freeze + EcoEvo ecology + Critic P4 refuse. No competing design. Process locks:

1. **Dense sampling (X1):** `snap_stride=25` feeds lag/phase / Floquet-style scores only; hold + floor evaluate **only** locked windows 125/250/500 with the **conjunctive** clause (Phil. Trans. B DOI `10.1098/rstb.2022.0006`; Ashby & Boots 2017 DOI `10.1111/ele.12734`).
2. **Lag ≠ oscillation (X2):** `lagged_nfds` = paired host+parasite match-class series + explicit τ — refuse any wrapper of `_oscillation_on_arm` dominant flips (Dybdahl & Lively 1998 DOI `10.1111/j.1558-5646.1998.tb01833.x`).
3. **Parasite memory ring (X3):** length L=8 in **HP env/plugin** only — no infection imports in `engine.py`; no second registry (Zaman et al. 2014 DOI `10.1371/journal.pbio.1002023` peer analog).
4. **Cuscore/SPC (X4):** observation-only fail-closed **after** ecology clocks — **REJECT** as hold or `rq_earn_seed_pass` / `red_queen_proved` accept (Box & Ramírez 1992 DOI `10.1002/qre.4680080105`).
5. **Demography-first (X5):** Stage 0 feast–famine / bolus×patches tune before Stage 1 numerics lock; soft K stays **64**; floor stays **12**; Stage 0 FAIL ⇒ no floor/bar cut unlock (Elena & Lenski 2003 DOI `10.1038/nrg1088`; Nosek 2018 DOI `10.1073/pnas.1708274114`).
6. **Pearl process (X6):** true `PASSAGE_COEVOLVE` / `PASSAGE_FROZEN` / `PASSAGE_ABSENT`; ecology `fixed` ≠ Pearl frozen.
7. **Packaging:** SUCCESS = `rq_earn_seed_pass` ≥12/16 only; sealed 701–708 untouched; `red_queen_proved=false` until Critic-signed P4 after §7.

**XFieldInnov: TEST DESIGN READY (fold).** Per-round: `WAVE7_ROUND{1,2}_XFIELD_20260926.md`.
