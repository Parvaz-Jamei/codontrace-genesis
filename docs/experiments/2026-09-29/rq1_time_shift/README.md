# RQ-1 — time-shifted antagonism, confirmatory pack (2026-09-29)

**Archive entry:** `docs/experiments/2026-09-29/rq1_time_shift/`
**Test:** RQ-1 of the 2026-09-29 discovery program (bundle A, Red Queen tests)
**Verdict on the imported archive:** `INCONCLUSIVE`, and the pack is **not complete**.
**No discovery is claimed:** `hypothesis_supported = false`, `red_queen_proved = false`.

## Archive integrity (2026-10-02)

The owner draft below describes an 8/8 confirmatory pack. The files actually imported into this tree do not support that completion claim.

| Seed | events | population | summary | `seed_<N>.json` |
|---|---|---|---|---|
| 5701–5705 | `.jsonl.gz` | `.jsonl.gz` | plain `.jsonl` | present |
| 5706 | plain `.jsonl` | `.jsonl.gz` | plain `.jsonl` | **absent** |
| 5707, 5708 | **absent** | **absent** | **absent** | **absent** |

`confirmatory/analysis_confirmatory.json` is the historical partial record: `status=partial`, `seeds_completed=[5701, 5702]`. It is left in place. A fresh rebuild writes only to the directory given by `--output`.

Numbers in the later sections that cite seeds 5707 and 5708, including wall times and the 8/8 intervals, are the owner draft. They are not recomputed from raw files in this repository. Completion requires a population file, a summary, an events file and `seed_<N>.json` for every locked seed, plus a rebuild that matches.

## 1. Question and hypothesis

Does the realised pressure an antagonist exerts on a host depend on the **time gap** between them — contemporary or slightly lagged antagonists pressing harder on the host that was recently common, with a drop on the old host and no uniform increase? That pattern would indicate fluctuating selection. A uniform increase in every cell would instead be consistent with a directional arms race and must not be reported as fluctuating selection.

The sealed stage-0 record (`DISCOVERY_PROGRAM_STAGE0_20260929.md`) issued `BLOCKED_MEASUREMENT` for RQ-1 on the **Idea-2 engine** route, whose antagonist is a scalar counter. That is route-specific; the route used here has a genotype antagonist population. The addendum recording this is `docs/campaigns/discovery_questions_20260928/DISCOVERY_PROGRAM_STAGE0_ADDENDUM_20260929_RQ1_ROUTE.md`.

### References (dated, nearest work)

| # | Work | Relation |
|---|---|---|
| 1 | Decaestecker et al. (2007), *Nature* 450, 870–873, doi:10.1038/nature06291 | Original time-shift design: past antagonists assayed against present and past hosts |
| 2 | Gaba & Ebert (2009), *TREE* 24, 226–232, doi:10.1016/j.tree.2008.11.008 | The method and its interpretation limits |
| 3 | Brockhurst et al. (2014), *Proc. R. Soc. B* 281, 20141382, doi:10.1098/rspb.2014.1382 | A directional shift is not fluctuating selection |
| 4 | Gibson et al. (2020), *Biology Letters* 16, 20200210, doi:10.1098/rsbl.2020.0210 | Rare-versus-common host genotypes, the question this assay mirrors digitally |
| 5 | Buckingham & Ashby (2022), *J. Evol. Biol.* 35, 205–224, doi:10.1111/jeb.13981 | Short time-shift windows can look directional under fluctuating selection; hence an interaction estimand |
| 6 | Blount, Lenski & Losos (2018), *Science* 362, eaam5979, doi:10.1126/science.aam5979 | Replay/fork requirement inherited by the design |

RQ-1's design is the standard time-shift assay (refs 1–2); no novelty is claimed for it. The contribution here is measurement hygiene (an interaction on realised pressure, never a frequency change) plus the negative controls in section 7.

## 2. Design (locked before any seed)

| Item | Value |
|---|---|
| Seeds (unseen, locked) | `5701 5702 5703 5704 5705 5706 5707 5708` |
| Generations per seed | **200** (never shortened) |
| Regimes per seed | `copassaged` (coevolve), `fixed` (frozen antagonist) |
| Arms reported | `contemporary`, `lagged`, `frozen` |
| Time slots | `past = 90`, `now = 100`, `future = 110` (lag 10) |
| Contact | equal exposure, `contact_mode = full_matrix`, `kappa = 1.2`, reserve infinite |
| Estimator | host-time × antagonist-time interaction contrast |
| Controls | frozen arm exactly 0; six shuffled antagonist time labels |
| Interval | 95% paired t, `causal_validation._paired_interval` |
| Flags held false | `hypothesis_supported`, `red_queen_proved` |

No seed, threshold, arm, estimator or generation count changed after any result. The horizon is inside the program's ceilings (80 / 150 / 200).

### 2.1 Estimand

```
pi_cell(ti, tj) = sum_h w_h(ti) * mean_{a in A(tj)} pi(h, a)
pi(h, a)        = min(R, kappa * A(h, a))      (R = infinity here)
I(ti, tj)       = pi(ti,tj) - row_mean(ti) - col_mean(tj) + grand_mean
contemporary    = I(now, now);   lagged = mean( I(now, past), I(future, now) )
```

`w_h(ti)` is the host class frequency at `ti` (raw `host_joint_class_frequencies`); `A(tj)` are the antagonist classes present at `tj` (raw `antagonist_class_frequencies`); `A(h, a)` is the repository's graded affinity over the 3 × 2-bit recognition window, with class strings `"aa|bb|cc"` mapping 1:1 onto the 6-bit window `aabbcc`; `kappa = virulence × steal_fraction = 8.0 × 0.15 = 1.2`; `full_matrix` gives equal exposure, every host class meeting every antagonist class exactly once. A uniform increase in every cell is a main effect (arms race) and is not counted as support.

### 2.2 What "the frozen arm is exactly 0" means

In the `fixed` regime the antagonist stock is restored to the same ancestral 16-window cycle every generation, so it cannot adapt. Structurally every host class then faces the same antagonist multiset, mean affinity is identical for all classes, every cell of the frozen matrix is the same value, and the interaction is exactly zero. This is the pre-declared negative control: had the frozen arm reproduced the pattern, the verdict would be `FALSIFIED_IN_MODEL`. It did not (section 7).

## 3. Instrument and interval method

The dated history comes from `StructuralRQArm` (`src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py`), a live life-loop host/antagonist coevolutionary arm: host match windows are genomes under bit-flip mutation; the antagonist is a stock of 64 recognition windows, partly kept (`parasite_keep_fraction = 0.5`) and partly re-drawn each generation from that generation's **matched** windows and mutated (`parasite_mutation = 0.25`) — heritable, mutating, selected. Per generation it archives host joint match class counts, antagonist class counts and the realised pressure per host class; `window_snapshot(generation)` exposes them, and the raw JSONL is built from it.

Reference arms are `copassaged` (coevolve), `fixed` (frozen) and `avirulent` (host-only). This pack reports `contemporary` and `lagged` from the coevolve history and `frozen` from the frozen history; both regimes boot from the same seed and the same initial state per seed (identical founder genome digest and identical initial parasite-window digest), verified in `raw/seed_<N>.json`.

`causal_validation._paired_interval` returns a 95% Student-t interval for the mean paired delta from the three-decimal lookup `_T975_BY_DF`. With eight seeds (df = 7) the table value is `2.365`; the exact quantile is `2.364624251592784`. The endpoint shift at n = 8 is ~1e-6:

| contrast | repo lo / hi | exact-quantile shift |
|---|---|---|
| contemporary vs frozen | 0.0007107158 / 0.0122036492 | +9.13e-07 / −9.13e-07 |
| lagged vs frozen | −0.0072590741 / −0.0019639842 | +4.21e-07 / −4.21e-07 |
| contemporary vs lagged | 0.0034049586 / 0.0187324648 | +1.22e-06 / −1.22e-06 |

For reference the `df = 1` row (`12.706`) versus the exact `12.706204736174694` differs by `2.05e-04`; that row is not used here (n = 8) but is recorded so the archived copy carries exact values. Full detail: `analysis_confirmatory.json` → `interval_exact_quantile`. **The locked verdict uses the repository function**; the exact quantile only quantifies the shift.

## 4. Protocol and provenance

| Item | Value |
|---|---|
| Commit pin | `6187ff4` |
| Pin source | isolated extraction `docs/experiments/2026-09-29/verification/full6187ff4` (git archive, 1318 files) |
| Config digest | `rq1_confirmatory:d44a70140eeef5876ea68c838ca442de38f5e05cfeaeabd71bab2be38479c807` |
| Harness | `confirmatory_rq1.py` (run), `analysis_confirmatory_rq1.py` (derived analysis) |
| Workers | 1 sequential worker; one seed at a time, two regimes per seed |
| Python | 3.14.4, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` |
| Live output | `raw/events_seed<N>.jsonl` and `raw/population_seed<N>.jsonl` per generation; `raw/summary_seed<N>.jsonl` every 10 |
| Resumability | a seed is skipped when `raw/seed_<N>.json` exists; partial JSONL is truncated before a seed restart |

The owner draft said all eight seeds ran against one pinned extraction, so the 5701–5702 and 5703–5708 groups would be comparable. That sentence is not an archive result: seed JSON for 5706–5708 is not in this tree, so those seeds cannot be placed on the pin from the imported files. The engine commits after the pin (`40138c9`, `913f18e`, `02cc725`) are recorded in the draft as absent from the extraction.

## 5. What ran

Owner draft. The wall times for 5706–5708 are not backed by `raw/seed_<N>.json` in this tree. Do not treat this table as the archive result. The provable rebuild is `confirmatory/rebuild/`.

8 seeds × 2 regimes × 200 generations = **3200 arm-generations**. Each seed is one independent population history contributing three paired arm values. Wall time per seed in seconds, from `raw/seed_<N>.json` → `regimes[*].wall_s`:

| seed | coevolve | frozen | total |
|---|---|---|---|
| 5701 | 380.4 | 312.9 | 693.3 |
| 5702 | 473.4 | 383.0 | 856.4 |
| 5703 | 448.2 | 358.7 | 806.8 |
| 5704 | 776.3 | 448.8 | 1225.0 |
| 5705 | 606.3 | 749.0 | 1355.3 |
| 5706 | 516.0 | 266.0 | 782.0 |
| 5707 | 281.3 | 230.0 | 511.3 |
| 5708 | 684.8 | 631.5 | 1316.2 |
| **total** | | | **7546.5 s ≈ 2.10 h** |

Every seed passed its gates: identical initial state across regimes, host classes ≥ 2 and antagonist classes ≥ 2 at all three slots, non-zero census and antagonist count (`raw/seed_<N>.json` → `seed_gates_ok = true`).

## 6. Raw data files

Owner draft of the intended 32-file pack. The checksum rows for `population_seed5708.jsonl` and `seed_5708.json` name files that were not imported. Files present are listed by `manifest_lf.sha256`.

Under `raw/`. `events_seed<N>.jsonl` and `population_seed<N>.jsonl` have 400 lines per seed (2 regimes × 200 generations); `summary_seed<N>.jsonl` has 40 (2 regimes × 20 snapshots).

**Parsing guidance:** the analysis reads `population_seed<N>.jsonl`. Each line has `regime`, `generation`, `host_joint_class_frequencies`, `host_joint_richness`, `dominant_host_class`, `antagonist_class_frequencies`, `antagonist_n`, `census` and the arm's own `model_realised_pressure`. The three slots are generations 90, 100, 110. `events_seed<N>.jsonl` carries the program's field list with explicit nulls: this arm exposes generation aggregates, not per-contact events, so the contact fields are null and `null_reason` states why.

| file | sha256 | bytes |
|---|---|---|
| `raw/population_seed5701.jsonl` | `81eda037ef4d90a82f8ec95ec7573e77a803e0be35b9c92f6e3d13e8373a42b2` | 652117 |
| `raw/population_seed5708.jsonl` | `94d0261ee1804f1d0f2942795469f136c3948ce6052c80538639a5833cbefd68` | 983304 |
| `raw/events_seed5701.jsonl` | `f796f352452f2a7667beba0956bfa2d8dcf1c0388bdbc5999b76350d7308fcde` | 282168 |
| `raw/seed_5701.json` | `c2335bc8eb397f5305e1e001c3b9deccbd59f79ae2c9d9fb9ce7deb9b2de603b` | 4417 |
| `raw/seed_5708.json` | `17760cec850758b9d4d44bf308389713a66c8acca4c9521a92d91e8f5a0ee4f0` | 4425 |

Checksums for all 32 raw files (8 seeds × 3 JSONL + 8 per-seed JSON) are printed by `analysis_confirmatory_rq1.py` and recorded in `run_manifest.json` and `analysis_confirmatory.json`.

## 7. Analysis, derived only from raw

Owner draft of an 8-seed analysis, including the “0 of 24” control count. It is not what `confirmatory/rebuild/` recomputed. The rebuild covers the five seeds that have `seed_<N>.json`.

`analysis_confirmatory_rq1.py` rebuilds each seed's 3×3 matrix from `raw/population_seed<N>.jsonl` at generations 90/100/110 and compares it with the matrix stored in `raw/seed_<N>.json` (tolerance 1e-12): `raw_recompute_matches_all_seeds = true`; `frozen_exactly_zero = true` (every frozen matrix is one repeated value and both frozen interaction scalars are 0.0); `all_seed_gates_ok = true`; shuffled time-label control **0 of 24** permutations receives a support label.

| seed | coevolve label | contemporary | lagged | frozen | raw recompute | wall s |
|---|---|---|---|---|---|---|
| 5701 | `other` | +0.0018655017 | +0.0009415523 | `flat`, 0.0 | match | 693.3 |
| 5702 | `contemporary_match` | +0.0117180970 | −0.0042388658 | `flat`, 0.0 | match | 856.4 |
| 5703 | `other` | +0.0057280175 | −0.0042985259 | `flat`, 0.0 | match | 806.8 |
| 5704 | `other` | −0.0021057947 | −0.0041118087 | `flat`, 0.0 | match | 1225.0 |
| 5705 | `other` | +0.0145240232 | −0.0063003503 | `flat`, 0.0 | match | 1355.3 |
| 5706 | `contemporary_match` | +0.0104490964 | −0.0053641081 | `flat`, 0.0 | match | 782.0 |
| 5707 | `other` | −0.0030418059 | −0.0031402793 | `flat`, 0.0 | match | 511.3 |
| 5708 | `contemporary_match` | +0.0125203250 | −0.0103798475 | `flat`, 0.0 | match | 1316.2 |

Support labels (`contemporary_match` or `lagged_match`): **3 of 8**.

### Effect table (95% paired t interval vs the frozen arm)

| arm | n | mean | 95% interval | excludes zero |
|---|---|---|---|---|
| contemporary | 8 | +0.006457182525 | [0.0007107158, 0.0122036492] | yes |
| lagged | 8 | −0.0046115291625 | [−0.0072590741, −0.0019639842] | yes |
| frozen | 8 | 0.0 (exactly flat) | [0.0, 0.0] | no |
| contemporary − lagged | 8 | +0.0110687116875 | [0.0034049586, 0.0187324648] | yes |

## 8. Verdict, interpretation and limits

`INCONCLUSIVE`

The locked rule requires the repository's `contemporary_match` or `lagged_match` label, a positive contemporary or lagged interaction, the largest interaction on a contemporary or lagged cell, and no uniform increase — none of it reproducible by the controls. Only part held: a small but consistent **positive contemporary** interaction is present (`+0.00646`, interval excludes zero), while the **lagged** interaction is consistently **negative** (`−0.00461`, interval excludes zero), the opposite of the lagged branch of the hypothesis; only **3 of 8** seeds carry a support label and five label `other`. The refusal branch was **not** triggered: the frozen control is exactly flat for every seed and the shuffled-label control is clean (0/24), so nothing shows the pattern under a negative control. Hence `INCONCLUSIVE`, not `FALSIFIED_IN_MODEL`.

For continuity, the earlier pilot (6 seeds × 3 arms × 40 generations) gave `contemporary = +0.005396` [0.003430, 0.007602], `lagged = −0.003454` [−0.005321, −0.001438], frozen exactly flat, rotation control 0/18, support labels 2/6 (`analysis_live.json`); the confirmatory pack reproduces the same qualitative picture with a longer horizon and more seeds.

* **No discovery claim.** Both flags are false; this is a digital system, so nothing here licenses a biological claim.
* **The locked pattern was not met.** A positive contemporary interaction whose interval excludes zero is **not** the pre-declared pattern, and an interval containing zero would not be a success either.
* **The frozen arm being exactly 0 is the negative control, not evidence for the hypothesis.** It shows the assay returns no interaction when the antagonist cannot adapt; it does not show adaptation produced the positive contemporary term.
* Associational, not causal: the matrix re-contacts archived genotypes outside evolution under equal exposure and does not replay the population's own contact history.
* Host census declines over the 200-generation horizon (21–55 hosts at the analysis slots), so drift and demography are not separated from selection.
* n = 8 (df = 7) gives a wide interval relative to the effect (mean ≈ 0.0065, half-width ≈ 0.0057).
* The antagonist is a stock of recognised windows, not individual organisms with birth and death; "genotype population" here means a heritable, mutating, selected class multiset.

## 9. Replay (in-repo paths)

From the repository root:

```
python docs/experiments/2026-09-29/rq1_time_shift/confirmatory/analysis_confirmatory_rq1.py \
  --raw docs/experiments/2026-09-29/rq1_time_shift/confirmatory/raw \
  --output docs/experiments/2026-09-29/rq1_time_shift/confirmatory/rebuild
```

The derived replay reads plain JSONL and `.jsonl.gz`. It checks the three meter files against the blobs shared by `6187ff4` and `a1d97e9` and stops on a mismatch. It does not overwrite `analysis_confirmatory.json`, `decision.md` or `run_manifest.json`.

A new simulation is not started from the live checkout. The runner requires the pinned tree explicitly and stops if that tree is missing or its `HEAD` is not `6187ff4`:

```
python docs/experiments/2026-09-29/rq1_time_shift/confirmatory/confirmatory_rq1.py \
  --reference-checkout /path/to/checkout-of-6187ff4 \
  --expect-commit 6187ff4 \
  --check-only
```

`--check-only` verifies the commit, the three meter blobs and the config digest, then exits before any seed. A new simulation also needs a fresh `--output`, which must not be the historical `confirmatory/` directory. There is no machine-local default path.

## 10. Files in this entry

`ARCHIVE_README.md` (this record) · `run_manifest.json` (commit, config digest, seeds, provenance, status) · `analysis_confirmatory.json` (derived summary, per-seed table, intervals, controls) · `effect_table_confirmatory.json` · `decision.md` (the single verdict label) · `exclusions.md` · `confirmatory_rq1.py` (locked runner) · `analysis_confirmatory_rq1.py` (derived-only analysis) · `raw/seed_<N>.json`, `raw/events_seed<N>.jsonl`, `raw/population_seed<N>.jsonl`, `raw/summary_seed<N>.jsonl`.
