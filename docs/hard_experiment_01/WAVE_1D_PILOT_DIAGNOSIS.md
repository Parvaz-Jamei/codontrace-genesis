# WAVE 1D PILOT DIAGNOSIS

**Status:** calibration FAIL root-cause analysis (throwaway; Amd 02 untouched).
**HEAD:** `d3a9ce5` branch `wave-1d-seed-variance`
**Scope:** pilot seeds 1000–1009 only; **do not touch seeds 11–40**; **do not amend Amd 02 in-repo**.

## 1. Per-seed capsules_off outcomes (pilot JSON)

| seed | capsules_off | oracle | source_bias_on | source_bias_off |
|-----:|-------------:|-------:|---------------:|----------------:|
| 1000 | 28.0 | 19.975 | 20.675 | 23.925 |
| 1001 | 28.0 | 19.725 | 21.475 | 28.85 |
| 1002 | 28.0 | 21.475 | 34.4375 | 29.55 |
| 1003 | 28.0 | 22.6125 | 26.8875 | 30.95 |
| 1004 | 28.0 | 19.125 | 26.45 | 27.175 |
| 1005 | 28.0 | 21.525 | 28.325 | 30.2 |
| 1006 | 28.0 | 21.875 | 29.3625 | 28.475 |
| 1007 | 28.0 | 22.375 | 32.825 | 25.925 |
| 1008 | 28.0 | 19.0625 | 25.5375 | 26.3125 |
| 1009 | 28.0 | 24.3 | 30.25 | 27.3625 |

All 10 capsules_off equal 28.0: **True** (unique=[28.0]).
Oracle mean=21.205 < capsules_off 28.0 (assay gate `assay_failed_positive_control_did_not_move_outcome`).

## 2. Overlay compare: v3-style vs v4 (seeds 1000, 1001 × off/oracle)

v3-style = fixed `index%4` roles + every-cell food + `draws=population`. v4 = Amd 02 permute + sparse coverage + `draws=pop//4`.

| seed | arm | mode | coverage | n_food | draws | roles Counter | receivers |
|-----:|-----|------|---------:|-------:|------:|---------------|----------:|
| 1000 | capsules_off | v3 | 1.0 | 64 | 16 | `{'good_emitter': 4, 'poor_emitter': 4, 'receiver': 8}` | 8 |
| 1000 | capsules_off | v4 | 0.703125 | 45 | 4 | `{'good_emitter': 4, 'poor_emitter': 4, 'receiver': 8}` | 8 |
| 1000 | oracle_capsule | v3 | 1.0 | 64 | 16 | `{'good_emitter': 8, 'receiver': 8}` | 8 |
| 1000 | oracle_capsule | v4 | 0.703125 | 45 | 4 | `{'good_emitter': 8, 'receiver': 8}` | 8 |
| 1001 | capsules_off | v3 | 1.0 | 64 | 16 | `{'good_emitter': 4, 'poor_emitter': 4, 'receiver': 8}` | 8 |
| 1001 | capsules_off | v4 | 0.703125 | 45 | 4 | `{'poor_emitter': 4, 'good_emitter': 4, 'receiver': 8}` | 8 |
| 1001 | oracle_capsule | v3 | 1.0 | 64 | 16 | `{'good_emitter': 8, 'receiver': 8}` | 8 |
| 1001 | oracle_capsule | v4 | 0.703125 | 45 | 4 | `{'good_emitter': 8, 'receiver': 8}` | 8 |

### Notes from overlay

- Food layout **does** vary by seed under v4 (same coverage 45/64=0.703125 for 1000 and 1001 in this draw, but cell sets differ).
- Role permutation **does** vary by seed; oracle remaps poor→good **before** permute → 8 good emitters + 8 receivers (vs 4/4/8 off).
- `respawn_draws` v4=4 vs v3=16; `max_resources` stays full lattice (64) in both.

## 3. Run outcomes: v3-style vs v4 (terminal receiver mean ATP)

| seed | arm | mode | receiver_mean | n_food | draws | adoptions | bias | food_end | recv_atp unique |
|-----:|-----|------|--------------:|-------:|------:|----------:|-----:|---------:|-----------------|
| 1000 | capsules_off | v3 | 28.0 | 64 | 16 | 0 | 0 | 64 | [28.0] |
| 1000 | capsules_off | v4 | 28.0 | 45 | 4 | 0 | 0 | 64 | [28.0] |
| 1000 | oracle_capsule | v3 | 78.375 | 64 | 16 | 559 | 412 | 64 | [77.4, 78.7] |
| 1000 | oracle_capsule | v4 | 19.975 | 45 | 4 | 559 | 404 | 52 | [13.4, 16.1, 16.7, 20.1, 20.7, 23.4, 28.7] |
| 1001 | capsules_off | v3 | 28.0 | 64 | 16 | 0 | 0 | 64 | [28.0] |
| 1001 | capsules_off | v4 | 28.0 | 45 | 4 | 0 | 0 | 64 | [28.0] |
| 1001 | oracle_capsule | v3 | 78.375 | 64 | 16 | 559 | 412 | 64 | [77.4, 78.7] |
| 1001 | oracle_capsule | v4 | 19.725 | 45 | 4 | 585 | 404 | 52 | [12.7, 14.7, 18.1, 20.7, 22.1, 22.7, 26.1] |

## 4. Hypothesis: why capsules_off sd=0

### Mechanism

Receivers use genome `000000000` (WAIT×3). With capsules **off**, WAIT is never substituted. Per-tick drain = basal `0.4` + WAIT action cost `0.1` = `0.5`. Over 40 ticks: `48.0 − 40*0.5 = 28.0` → **exactly 28.0** for every receiver.

Food layout and role permutation therefore **cannot** move the primary outcome on `capsules_off`: receivers never EAT, never adopt, never pay EAT's 0.8 action cost. Emitters do interact with food (good emitters reach ~39 ATP; poor ~18.6), and under v4 `max_resources=64` + `respawn_draws=4` the lattice often **refills to 64** by mid-run when only 4 good emitters eat — but that is invisible to the estimand.

### Rejected alternatives

- **Not** 'food cells identical across seeds': placement differs (and coverage can differ).
- **Not** 'max_resources/respawn making effective food identical *for receivers*': food is irrelevant to WAIT-only receivers; effective food can even saturate to full lattice.
- **Yes**: energy path saturates to the same ATP because **all receivers WAIT**.

## 5. Hypothesis: why oracle < capsules_off

### Seed 1000 v4 comparison

| arm | mean | roles | adoptions | bias | payloads | rejected | food_end |
|-----|-----:|-------|----------:|-----:|----------|---------:|---------:|
| capsules_off | 28.0 | `{'good_emitter': 4, 'poor_emitter': 4, 'receiver': 8}` | 0 | 0 | `{}` | 0 | 64 |
| oracle_capsule | 19.975 | `{'good_emitter': 8, 'receiver': 8}` | 559 | 404 | `{'EAT_LUMEN': 404}` | 0 | 52 |
| source_bias_on | 20.675 | `{'good_emitter': 4, 'poor_emitter': 4, 'receiver': 8}` | 559 | 392 | `{'EAT_LUMEN': 392}` | 443 | 52 |

### Mechanism (supported)

1. **Oracle remaps poor→good then permutes** → 8× `EAT_LUMEN` emitters + 8 receivers (vs 4 good / 4 poor / 8 receivers on off).
2. Capsules on → receivers adopt; bias events apply payload `EAT_LUMEN` (seed 1000: 404 bias / 559 adoptions).
3. **EAT_LUMEN action cost = 0.8** vs WAIT 0.1. Successful eat credits `resource_amount=2.0` ATP, but under sparse + `respawn_draws=4` many attempts hit `no_lumen` → pay 0.8 with **zero** credit.
4. More concurrent EAT consumers (8 emitters + up to 8 eating receivers) compete on the same sparse patches → failed eats dominate → receiver mean falls **below** the WAIT baseline (28). In v3 (every cell + draws=16) nearly every EAT succeeds → oracle **beats** off (v3: 78.4 > 28).
5. Extinction is **not** the story (final_pop=16). Adoptions fire; the positive control moves the channel, but in the **wrong direction** for the assay gate `oracle > capsules_off`.

So Amd 02's sparse food + reduced draws inverted the positive-control inequality that Amendment 01's assay requires, while failing to give `capsules_off` any across-seed variance (because that arm's estimand units never touch food/capsules).

## 6. Ablation micro-check (Amd 03 direction)

| Mode | Roles | Food / draws |
|------|-------|--------------|
| **A** | seed-permuted | every cell + `draws=population` (v3 food) |
| **B** | fixed `index%4` | sparse Amd02 + `draws=pop//4` |
| **C** | seed-permuted | sparse Amd02 + `draws=pop//4` (current v4) |

| mode | seed | arm | mean | n_food | draws | roles receivers | adoptions |
|------|-----:|-----|-----:|-------:|------:|----------------:|----------:|
| A | 1000 | capsules_off | 28.0 | 64 | 16 | 8 | 0 |
| A | 1000 | oracle_capsule | 78.375 | 64 | 16 | 8 | 559 |
| A | 1001 | capsules_off | 28.0 | 64 | 16 | 8 | 0 |
| A | 1001 | oracle_capsule | 78.7 | 64 | 16 | 8 | 585 |
| B | 1000 | capsules_off | 28.0 | 45 | 4 | 8 | 0 |
| B | 1000 | oracle_capsule | 19.65 | 45 | 4 | 8 | 559 |
| B | 1001 | capsules_off | 28.0 | 45 | 4 | 8 | 0 |
| B | 1001 | oracle_capsule | 22.025 | 45 | 4 | 8 | 559 |
| C | 1000 | capsules_off | 28.0 | 45 | 4 | 8 | 0 |
| C | 1000 | oracle_capsule | 19.975 | 45 | 4 | 8 | 559 |
| C | 1001 | capsules_off | 28.0 | 45 | 4 | 8 | 0 |
| C | 1001 | oracle_capsule | 19.725 | 45 | 4 | 8 | 585 |

### Summary

- **A**: capsules_off=[28.0, 28.0] (identical across seeds? True); oracle=[78.375, 78.7]; oracle>off on both seeds? **True**
- **B**: capsules_off=[28.0, 28.0] (identical across seeds? True); oracle=[19.65, 22.025]; oracle>off on both seeds? **False**
- **C**: capsules_off=[28.0, 28.0] (identical across seeds? True); oracle=[19.975, 19.725]; oracle>off on both seeds? **False**

## 7. Root cause(s) ranked

1. **Primary — `capsules_off` estimand is food/role-invariant under WAIT-only genomes.** Amd 02's variance knobs (food coverage, role permute, respawn draws) never enter the receiver ATP path when capsules are disabled. Arm sd stays 0 by construction; matching v3's 28.0 is expected, not a bug in RNG.
2. **Primary — sparse food + low respawn draws + oracle's doubled EAT consumers inverts the positive control.** EAT cost 0.8 with frequent `no_lumen` drains receivers below WAIT baseline; assay requires oracle > off.
3. **Secondary — role permute alone cannot fix capsules_off sd** (ablation B/C both keep off=28; only food abundance restores oracle≫off, and even then off may stay flat unless receivers somehow vary — which they cannot without capsules or non-WAIT genomes).
4. **Secondary — analysis arms with capsules on *do* get sd>0** (pilot: on/off/shuffled all sd>0; primary sd_delta>0). Variance restore partially worked where adoption couples receivers to the environment; it failed where that coupling is cut.

## 8. Recommended Amd 03 direction

Ablation snapshot (seeds 1000 & 1001):
- **A** (roles permute + v3 every-cell food + draws=pop): off=[28.0, 28.0]; oracle=[78.375, 78.7]; **oracle≫off**
- **B** (roles fixed + sparse Amd02): off=[28.0, 28.0]; oracle=[19.65, 22.025]; oracle<off
- **C** (current v4 both): off=[28.0, 28.0]; oracle=[19.975, 19.725]; oracle<off

**Recommended: (A) roles-only permute + v3 food/draws.**

One-line rationale: ablation A is the only tested knob set that restores the Amendment 01 positive-control inequality (`oracle ≈ 78 > off = 28`) while keeping seed-permuted roles for capsule-on spatial/adoption variance; sparse food (B/C) is what inverted the assay.

### Option ranking

1. **(A) — best supported.** Revert food/draws to v3 abundance; keep Fisher–Yates role permute. Fixes assay. Capsule-on arms retain role-driven variance (oracle already differs 78.375 vs 78.7 across 1000/1001 under A). **Does not** give `capsules_off` sd>0 (structural WAIT path). Amd 03 text must therefore either exempt `capsules_off` from the arm-sd gate or change the estimand/negative-control design — food knobs cannot fix that gate.
2. **(C) hybrid — runner-up** if Amd 03 insists on residual food-map stochasticity: keep role permute **and** raise coverage/draws high enough that successful EAT dominates the 0.8 action cost (near-v3 floor, not [0.5,0.8]/draws=pop//4). Untested mid-floor; would need a new pilot 1000–1009 after hashing.
3. **(B) raise coverage/draws alone (roles fixed) — not supported** as the sole move: without permute, capsule-on arms risk collapsing back toward v3's across-seed sd=0; sparse-or-partial raise without permute also leaves the spatial-adoption variance goal unmet.

### Capsules_off sd gate (required Amd 03 decision)

None of A/B/C produce capsules_off ≠ 28 across seeds. Prefer: **amend the calibration gate** to require sd>0 on capsule-coupled analysis arms (`source_bias_on/off`, `capsules_shuffled`) and treat `capsules_off` as a structural constant baseline under the frozen receiver-WAIT estimand — rather than inventing a receiver energy path that would change the DAG.

### Explicit constraints

- Do **NOT** touch analysis seeds 11–40.
- Do **NOT** amend Amd 02 in-repo; write a hashed Amd 03 sibling before re-pilot.
- This file and `_wave1d_pilot_diagnosis.py` are handoff diagnostics only.

