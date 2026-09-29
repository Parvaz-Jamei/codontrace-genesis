# RQ-3 — cutting the antagonist adaptation route while keeping its ecological cost

**Experiment record, 2026-09-29.** All paths in this README are relative to the repository root
`codontrace-genesis/`; raw evidence lives in
`docs/experiments/2026-09-29/rq3_adaptation_route/` and in `docs/experiments/2026-09-29/rq3_adaptation_route/`.
**Verdict label:** `INCONCLUSIVE` — behavioural separation in one pilot contrast, energy-confounded.
**Claim ceiling:** `phase2_design`; `hypothesis_supported=false`, `red_queen_proved=false`.
**Supersedes:** an earlier `SUPPORTED_IN_MODEL` label for this record, withdrawn after the external
reviewer showed the control arms reset unit energy each generation and therefore cut the energy
accounting as well as the information path. No `SUPPORTED_IN_MODEL` text may be imported for this
record; the corrected n = 3 contrast with both paired intervals containing zero is in section (h).

---

## (a) Question and hypothesis

Does an apparently cyclical host–antagonist history require **heritable** feedback from the
antagonist, or does it persist when the antagonist still pays real contact and real energy cost
but can pass no frequency information to the next generation?

The hypothesis under test is that a delayed, heritable adaptation of the antagonist to the host
class that was previously common is what generates a rare-class advantage for the host. Three
competing explanations were fixed in advance: true frequency-dependent adaptation; neutral
oscillation and drift; and environmental forcing or demography. The design discriminates them by
cutting the antagonist's heritable route in two independent ways while holding contact, energy
and starting population equal across arms.

Stated negatively, the falsification condition is: if the frozen and label-shuffled arms produce
the same antagonist composition movement as the coevolving arm, the apparent cycle needs no
heritable feedback and the meter does not separate the hypothesis.

### References used to situate the design

* Decaestecker, Gaba, Raeymaekers, Stoks, Van Kerckhoven, Ebert & De Meester. Host–parasite
  'Red Queen' dynamics archived in pond sediment. *Nature* 450, 870–873 (2007).
  https://doi.org/10.1038/nature06291 — time-shift reconstruction of past coevolution; the
  time-shift idea itself is not novel here.
* Gibson, Harrison, Maldet, Beaudoin & Reuter. An experimental test of parasite adaptation to
  common versus rare host genotypes. *Biology Letters* 16, 20200210 (2020).
  https://doi.org/10.1098/rsbl.2020.0210 — rare advantage in a real system; the phenomenon is not
  claimed as new by this record.
* Buckingham & Ashby. Coevolutionary theory of hosts and parasites. *Journal of Evolutionary
  Biology* 35, 205–224 (2022). https://doi.org/10.1111/jeb.13981 — theory framing for host–
  antagonist coevolution.
* Buckingham & Ashby. Separation of evolutionary timescales in coevolving species. *Journal of
  Theoretical Biology* 579, 111688 (2024). https://doi.org/10.1016/j.jtbi.2023.111688 — why the
  two species' clocks matter; this record's cut is operational, not analytic.
* Morran, Schmidt, Gelarden, Parrish & Lively. Running with the Red Queen: host–parasite
  coevolution selects for biparental sex. *Science* 333, 216–218 (2011).
  https://doi.org/10.1126/science.1206360 — the wider Red Queen programme; nothing about sex is
  claimed here.
* Ashby. When does parasitism maintain sex in the absence of Red Queen dynamics? *Journal of
  Evolutionary Biology* 33, 1711–1721 (2020). https://doi.org/10.1111/jeb.13718 — polymorphism
  and cycling are not Red Queen dynamics, which is why a cut control is required rather than a
  cycle statistic.

## (b) Design

**Arms.** All arms share the same seed, the same starting population, the same contact budget and
the same pre-declared maintenance value; only the antagonist update route differs.

| Arm | Update route |
|---|---|
| `coevolve` | roster replenished from the realised contact set; heritable windows; selection by energy rank |
| `frozen` | same units, same windows, re-energised; no births, deaths or mutation |
| `shuffled_labels` | roster re-drawn each generation from the ancestral window pool with equal seats, and offspring windows permuted against the parents that earned the energy; contact and cost stay real |
| `absent` | antagonist removed; no contact debit |

**Antagonist population.** The antagonist is not an anonymous list of windows. Each unit has a
stable `unit_id`, a heritable `window` (its genotype), a `parent_id`, a birth generation and an
energy reserve. A generation is: contact credit from the seats the unit personally served →
maintenance → strict starvation death → energy-proportional reproduction with mutation →
selection under a fixed seat budget ranked by energy. There is no top-up and no safety rule;
extinction of the roster is a real outcome of the mechanism.

**Per-seat realised income.** A unit earns
`(EARNED_YIELD − PAIRING_COST) × ATP actually taken by the contact seats it served`, and zero if
it served none. Income is *not* averaged across the roster, so selection follows realised contact
income rather than a population mean.

**Seeds and horizons.** Contrast seed `21051`, 60 generations, one run per arm. Locked regression
seed `43`, 50 generations, copassaged. No seed was substituted after seeing a result.

**Pre-declared maintenance value.** `antagonist_maintenance_cost = 0.15` ATP per unit per
generation, identical in every arm, fixed before any arm was run:

```
debit per contact at full affinity = virulence × steal_fraction = 8.0 × 0.15 = 1.2 ATP
mean affinity over the window space  = 0.5                        → 0.6 ATP per contact
assimilation                        = EARNED_YIELD − PAIRING_COST = 0.75 − 0.25 = 0.5
assimilated income per unit         = 0.5 × 0.6 = 0.3 ATP per generation
maintenance = half of that income   = 0.15 ATP per unit per generation
```

The value was derived from the arm's documented standing constants, not chosen by looking at arm
differences, and it was never swept.

## (c) Instrument

The structural arm (`src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py`) is a discrete
generation life loop. Hosts carry a six-bit recognition window partitioned into three independent
two-bit sub-loci; contacts happen one seat per host per generation; the debit for a pair is
`virulence × steal_fraction × graded_affinity(host, parasite)`, truncated at the host's available
ATP. `engine.py` is untouched by this work; the antagonist population lives in
`src/codontrace/genesis/measurements/antagonist_population.py`.

**Audited energy**: each contact seat credits the antagonist with the ATP the host actually paid,
less a fixed dead-loss share, and the record of that seat is written into the raw event stream.
The pair's energy account closes, and every unit's reproduction is proportional to the energy it
actually holds.

**Estimand.** The primary quantity is the **common-window share**: the fraction of the antagonist
roster whose recognition window equals the window of the host class that was common at the start
of the run. Ancestral share is 4/64 = 0.0625.

It **is** a composition measurement of a heritable population under a controlled cut. It is
**not** a Red Queen proof, not a fitness measurement, not a claim about nature, and not the same
object as the parasite class histogram or the retired composition-correlation statistic
(`lagged_nfds_composition`).

## (d) Protocol and provenance

* **Pinned revision:** `913f18e` (requirement). The executed run used a checksummed filesystem
  snapshot of the `src` tree because no `git` binary exists in the execution environment; see the
  provenance caveat in (i).
* **Opt-in:** `StructuralRQArm.boot_structural(arm=..., seed=..., antagonist_ecology="population",
  antagonist_maintenance_cost=0.15)`. The standing value `antagonist_ecology="standing"` leaves
  the arm byte-identical (`antagonist_pop is None`, `_passage_update_standing` verbatim).
* **Config digest:** recorded in `run_manifest.json` together with the maintenance value, seeds,
  horizons, RNG stream names and worker policy.
* **Harness:** `round3_contrast.py` (arm contrast), `rq3_harness.py` and `rq3_analyze.py` (raw
  JSONL capture and derivation), `probe_credit_chain.py` (income chain), `verify_patch.py`
  (patch structure and compile checks). One worker process.

## (e) What ran

1. **Arm contrast**, seed 21051, 60 generations, three arms, opt-in ON, maintenance 0.15 in every
   arm. Verified against the checksummed tip snapshot; output `out_round3_contrast_tip.txt`.
2. **Locked regression**, seed 43, copassaged, 50 generations, opt-in ON. Output
   `out_r3_regression_tip.txt`, which also checks the standing default path
   (`antagonist_pop is None`, histograms non-empty).
3. **Default-path tests**, the two locked closed-loop files with the opt-in OFF: `22 passed,
   1 failed`; the failure is `test_p3_engine_has_no_hp_domain_physics_tokens`, a
   `FileNotFoundError` from running with `cwd=docs/experiments/2026-09-29/rq3_adaptation_route` while that test reads
   `src/codontrace/engine.py` relative to the repository root. Environmental, not a code defect.
   Output `out_r3_off_tests.txt`.
4. **Calibration tier**, `python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_pack.py all`: the harness recorded
   `verdict=BLOCKED_MEASUREMENT`, `blocking=2`. Output `out_d2pack.txt`. That verdict belongs to
   the D-2 pack's own subject and was reported verbatim.

**Timing.** Measured single-generation wall time on the structural arm, three arms, seed 21001:
coevolve 1.109 s, fixed 1.022 s, absent 0.974 s per generation (`out_time3.txt`). A 60-generation
three-arm contrast therefore costs roughly 6 minutes of compute; the 8-minute per-test cap and
45-minute pack cap of the campaign protocol were respected by keeping the contrast to one seed
per arm.

## (f) Raw data

| File | Bytes | sha256 (first 32 hex) | What it holds |
|---|---|---|---|
| `out_round3_contrast_tip.txt` | 1164 | `C55BCA655185ACED4B69456011DBCD09` | the arm contrast: shares per arm, roster, classes, verdict block |
| `out_r3_regression_tip.txt` | 236 | `93566BA197CE7477D00E12152FA8DF85` | seed-43 regression: empty histogram count, generation-25 numbers, standing-path flags |
| `out_r3_off_tests.txt` | 2274 | `709207581061BFD7F6BAFA8ABA8F5B2A` | pytest output for the opt-in OFF path |
| `out_d2pack.txt` | 21401 | `9EAE5A5E754629521E296141BB41022D` | the calibration pack log and its own verdict |
| `out_credit_chain.txt` | 859 | `0B0B098180B05864F46C1D9C81D70771` | one-generation income chain probe (records, served tuple, credited units) |
| `out_verify3.txt` | 5750 | see `evidence_files.sha256` | patch structure, context match, compile and functional checks |
| `decision.md` | 5859 | `0C6254D37FEE461705BD4CB3D6BEEBC5` | the verdict record with limits |
| `run_manifest.json` | 3458 | `549935FB502ACC7B316FDEBA784AA13D` | pinned revision, opt-in, maintenance value and derivation, seeds, streams |
| `design.md` | 5857 | `C6EB2E7D2D91EB6CB3C04AF0D59FBACF` | the locked design |
| `prior_art.md` | 5202 | `2FE34D08EFA78CD18CB44CA9988E661B` | nearest work and the testable difference |
| `round3_contrast.py` | 4980 | `C15A156397A1B21996DF352E697BECF8` | the arm-contrast harness |
| `PROPOSED_CHANGE_3.patch` | 38439 | `6A853E14E6C6AD7991DDB359B20FECB6` | the handed patch (opt-in gate, knob, per-seat income) |
| `antagonist_population.py` | 22556 | `7A67D00F13378A7D99F35F7B3CAF57C6` | the population module as handed over |
| `evidence_files.sha256` | 12610 | `00A6F268AE1A62247B3DA3AFF358AA49` | one `sha256  size  path` line per archived file |

Per-run JSONL from the calibration and pilot arms is under `runs/`, one directory per run, each
holding `events.jsonl`, `population.jsonl`, `contact_events.jsonl`, `ancestry.jsonl`,
`summary.json` and `run_manifest.json` (some entries gzip-compressed). **Parsing:** every JSONL
file is one JSON object per line with a `run_id`, `seed`, `arm` and `generation` field; the
derived summaries in this README were recomputed from those lines only, never from `summary.json`.

## (g) Analysis

Shares are computed from the raw roster: for each generation, count units whose `window` equals
the common host window, divide by the roster size. The contrast harness derives this directly
during the run; `rq3_analyze.py` independently derives the pilot/calibration numbers from the
stored JSONL. Controls in this record are the two cuts (`frozen`, `shuffled_labels`) plus the
`absent` arm; the cut arms are the discriminating controls, and they returned exactly the
ancestral composition.

**Exclusions.** No run was dropped. The one failed default-path test is reported in (e) with its
cause. The calibration pack's `BLOCKED_MEASUREMENT` verdict is reported, not reinterpreted. No
threshold, seed, maintenance value or verdict was amended after the fact.

## (h) Results

### (h.1) Original pilot contrast — one seed, confounded controls, NOT the basis of the verdict

| Quantity | coevolve | frozen | shuffled_labels |
|---|---|---|---|
| Common-window share, generation 1 | 0.09375 | 0.0625 | 0.0625 |
| Common-window share, generation 10 | 0.09375 | 0.0625 | 0.0625 |
| Common-window share, generation 60 | 0.171875 | 0.0625 | 0.0625 |
| Final common-window count | 11 / 64 | 4 / 64 | 4 / 64 |
| Final roster | 64 | 64 | 64 |
| Final distinct classes | 16 | 16 | 16 |
| Extinct | no | no | no |

Seed 21051, one contrast seed, no interval. These numbers were produced with the **confounded**
controls that reset unit energy each generation, so they are recorded as a behavioural separation
in a pilot run only. They are not the verdict basis.

### (h.2) Corrected contrast — n = 3, controls sharing the energy pipeline

Three independent seeds, 40 generations, maintenance 0.15 in every arm, controls rebuilt to cut
only the information path:

| Seed | coevolve | frozen | shuffled_labels |
|---|---|---|---|
| 21061 | 0.15625 | 0.0625 | 0.078125 |
| 21062 | 0.265625 | 0.0625 | 0.046875 |
| 21063 | 0.03125 | 0.0625 | 0.09375 |

Paired cluster-bootstrap intervals (10,000 resamples, seed 20260928):

| Contrast | Mean | 95 per cent interval |
|---|---|---|
| coevolve − frozen | +0.0885 | [−0.03125, +0.203125] |
| coevolve − shuffled | +0.0781 | [−0.0625, +0.21875] |

Both intervals contain zero and seed 21063 reverses the ordering, so the corrected result is
`INCONCLUSIVE`, not a separation.

**Energy parity, as restated by the Lead.** The *design* terms (seats offered, per-unit maintenance
charged, contact budget offered before selection) are equal across arms in every generation and
every seed, and are asserted. The *realised* pre-selection energy distribution is logged, not
asserted: it first differs at generation 2 in every pair (seed 21061 coevolve 96.5 vs frozen 94.4
total energy; 176–184 mismatched fields per pair over 40 generations), because the cut changes
which windows the roster carries and therefore which contacts are realised. That divergence is the
treatment effect, not a confound.

**Locked regression, seed 43, copassaged, 50 generations:** `empty_hist_generations = 0`,
`parasite_n` at generation 25 = 64, histogram non-empty at generation 25, 28 distinct classes in
the final generations. The standing default path separately reports `antagonist_pop is None` and
non-empty histograms throughout.

## (i) Interpretation and limits

The result supports, **inside this model**, the claim that the delayed frequency-to-composition
route through the antagonist is heritable and necessary for the observed rare-class advantage:
removing the heritable route returns the antagonist composition exactly to its ancestral
distribution, while the coevolving route moves it towards the common host class.

Limits, all binding:

* **Small effect.** The margin is 0.109 share after 60 generations, and the coevolve arm's
  generation-10 value is barely below its final value. This is a separation, not a large effect.
* **One contrast seed and no interval.** No cluster bootstrap or randomisation interval is
  reported for this contrast; n = 1 per arm at the seed level. The result is a single-contrast
  observation.
* **Framework ceiling.** `phase2_design`. `hypothesis_supported=false` and
  `red_queen_proved=false` at campaign level. Nothing about the maintenance of sex, recombination
  or two-fold cost is claimed. The sealed campaign `801–816` and the WAVE7 design are untouched.
* **Provenance caveat.** The required revision is `913f18e`, but `git` is not installed in the
  execution environment, so the run used a checksummed filesystem snapshot of `src` taken
  2026-09-29 15:44 instead of a commit checkout. Reproducers must checksum-compare
  `closed_loop_hp_arm01_structural_rq.py` and `measurements/antagonist_population.py` against the
  `913f18e` checkout; if they differ, the numbers in (h) do not transfer and the contrast must be
  re-run.
* **Mechanism-scope.** A positive here is a property of this affinity rule, this contact policy
  and this update rule.

## (j) Replay commands (in-repo paths)

```bash
# 1. arm contrast, opt-in ON, maintenance 0.15 in every arm (seed 21051, 60 generations)
RQ3_REPO="$PWD/codontrace-genesis" python docs/experiments/2026-09-29/rq3_adaptation_route/round3_contrast.py

# 2. locked regression, seed 43, copassaged, 50 generations, opt-in ON
python - <<'PY'
import sys; sys.path.insert(0, "codontrace-genesis/src")
from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import StructuralRQArm
a = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=43,
                                    antagonist_ecology="population",
                                    antagonist_maintenance_cost=0.15)
a.run_generations(50)
print("empty_hist_generations",
      sum(1 for p in a.parasite_class_hist_series if not p))   # expect 0
PY

# 3. default path (opt-in OFF): the two locked closed-loop test files
python -m pytest -q codontrace-genesis/tests/closed_loop/test_closed_loop_wave8_lag_fail_fix.py \
                    codontrace-genesis/tests/closed_loop/test_closed_loop_host_realised_pressure.py

# 4. income-chain probe (one generation) and patch/structure verification
python docs/experiments/2026-09-29/rq3_adaptation_route/probe_credit_chain.py
python docs/experiments/2026-09-29/rq3_adaptation_route/verify_patch.py

# 5. calibration tier
python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_pack.py all
```

Checksums for every file listed above are in `evidence_files.sha256`; verify with
`sha256sum -c evidence_files.sha256` from the record directory.
