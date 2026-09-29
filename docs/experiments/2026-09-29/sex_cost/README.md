# Sex Cost — experiment record, 2026-09-29

This directory is the complete archived record for the two-fold-cost critical-ratio (`c*`) sweep: design, protocol,
instrument, raw data, analysis and result together. All paths below are relative to
`docs/experiments/2026-09-29/sex_cost/`. Skeleton text has been replaced by this full record.

**Files in this record:** 12. **Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path`
line per file, covering every artefact including the compressed raw data).

---

## 1. Question and hypothesis

The two-fold cost of sex asks why sexual reproduction persists when an asexual lineage can leave twice as many
offspring per unit resource. The Red Queen hypothesis answers that coevolving antagonists make sexual recombination
advantageous. This record tests where the advantage stops: **at what relative cost of sexual reproduction does
costly sex cease to be maintained in a closed, energy-audited digital population, and how precisely can that
critical cost `c*` be located?**

The hypothesis under test is directional and falsifiable: if a coevolving antagonist is sufficient to maintain
costly sex, then sexual frequency should remain bounded away from zero across cost levels up to and beyond the
classical factor of 2. The record's own instrument (`sex_arms.py`) had already reported the opposite for the
classical cost, so this sweep measures the threshold location rather than re-testing the headline.

**Status of the prior evidence.** The `c*` narrowing then in the campaign document rested on a single-seed probe
(`phase_probe.txt`, seed 9000, five costs, three turnovers) and cited a `phase_results.json` that does not exist
anywhere in the workspace. A one-seed probe cannot support a bracketed claim, so this record replaces both with a
2,100-run sweep whose bracket is read from confidence intervals.

**Dated references**
1. **Maynard Smith, J. 1978.** *The Evolution of Sex.* Cambridge University Press. — the two-fold cost as a quantitative problem.
2. **Williams, G. C. 1975.** *Sex and Evolution.* Princeton University Press. — the cost of meiosis.
3. **Hamilton, W. D. 1980.** *Oikos* 35(2):282–290. [doi:10.2307/3544435](https://doi.org/10.2307/3544435) — the parasite-driven (Red Queen) maintenance hypothesis.
4. **Otto, S. P. & Nuismer, S. L. 2004.** *Science* 304(5673):1018–1020. [doi:10.1126/science.1094072](https://doi.org/10.1126/science.1094072) — species interactions "typically select against sex"; the prediction this sweep's outcome matches.
5. **Misevic, D., Ofria, C. & Lenski, R. E. 2006.** *Proc. R. Soc. B* 273(1585):457–464. [doi:10.1098/rspb.2005.3338](https://doi.org/10.1098/rspb.2005.3338) — the direct digital-organism precedent; Avida's cost is charged demographically with energy scaled by genome length, which is why this record charges it inside an audited ledger instead.
6. **Salathé, M., Kouyos, R. D., Regoes, R. R. & Bonhoeffer, S. 2008.** *Evolution* 62(2):295–300. [doi:10.1111/j.1558-5646.2007.00265.x](https://doi.org/10.1111/j.1558-5646.2007.00265.x) — the main pro-sex simulation result: a severe cost to non-infecting parasites is what drives selection for recombination. This harness exposes exactly that knob (antagonist turnover and infection cost).
7. **Yasui, Y. 2026.** *J. Evol. Biol.* 39(9):1154–1168. [doi:10.1093/jeb/voag069](https://doi.org/10.1093/jeb/voag069) — resource limitation removes the *realised* two-fold cost; the reason the estimand here is sexual frequency and extinction, not equilibrium per-capita fitness.

---

## 2. Design

**Grid (pre-registered; no level, seed or threshold dropped after seeing results):**

| axis | values |
|---|---|
| cost ratio `c` (sexual:BIRTH_COST multiplier) | 0.9, 1.0, 1.1, 1.2, 1.25, 1.5, 1.75 (7 levels) |
| antagonist turnover (antagonist generations per host generation) | 1, 6, 12 (3 values) |
| seeds | 8000–8099 (100 paired seeds) |
| **total runs** | **7 × 3 × 100 = 2,100** |

Seeds are paired: the same seed drives the same RNG forks in every cell, so cells are comparable per-seed rather
than only in aggregate.

**Held-fixed parameters** (those of the original probe, so the sweep tests the old claim rather than a new one):
`infection_cost = 0.4`, `parasite_mutation = 0.005`, `fail_death = 0.9`, `generations = 400`, `host_cap = 400`,
`parasite_cap = 16`, `parasite_pool = 2`, `loci = 6`, `mating_tolerance = 1`, `host_mutation = 0.02`, `mortality = 0.10`.

**Costless reference.** `c = 1.0` is the costless control: it charges sexual parents the same `BIRTH_COST` as
asexual parents and therefore isolates the effect of the cost from the effect of recombination itself. Every cost
level is contrasted against it by paired seed difference.

**Maintenance criterion, fixed BEFORE the sweep completed and never changed.** A cost level counts as *maintained*
only if, **at all three turnovers**:

* `LCL95(mean sexual_final) > 0.05` — the lower 95 % bound of the mean sexual frequency over the last quarter of the run exceeds 0.05, and
* `UCL95(extinct fraction) < 0.5` — the upper 95 % bound of the fraction of seeds in which sex went extinct stays below 0.5.

The bracket is then read off the intervals — the highest level that passes and the lowest that fails — never from
point estimates.

---

## 3. Instrument

**What `sex_phase.run_phase` simulates.** A population of up to 400 host slots with 6-bit haploid genomes and a
per-host energy account. Each host generation: hosts take up `INTAKE` and pay `METABOLISM`; `turnover` antagonist
generations run *nested inside* that host generation, in which an antagonist genotype pool (16 slots, 2 alive)
infects every host within Hamming distance 1, survives in proportion to the hosts it infected (mutating at 0.005
per locus), and dies with probability `fail_death = 0.9` if it infects nobody; infected hosts pay `infection_cost = 0.4`. Reproduction then occurs by energy rank: eligible sexual parents pay `BIRTH_COST × c` and recombine with a
randomly chosen sexual mate, eligible asexual parents pay `BIRTH_COST` and copy themselves; all offspring mutate at
0.02 per locus; bankrupt hosts and a 10 % random mortality are removed. The reported estimand `sexual_final` is the
mean sexual frequency over the last 25 % of the 400 generations.

**The audited ATP ledger identity.** `sex_arms.Ledger` accumulates every energy flow in the run — initial stock,
intake, metabolism, infection, births paid, offspring endowment, deaths — and after every generation asserts the
closure identity

```
initial + intake − metabolism − infection − births + offspring − deaths  ==  energy now held by living hosts
```

The residual (left side minus right side) is tracked as a running maximum per run. This is the instrument check
that separates "the population changed because of selection" from "the population changed because energy was
created or destroyed". **Measured maximum residual across all 2,100 runs: 2.556e-10** (2.5556801119819283e-10,
double-precision round-off, i.e. the ledger closes exactly for practical purposes). `analysis.json` records
`ledger_identity_all_below_1e_9: true`. The wider `sex_arms.py` design also carries an injected-leak negative
control that verifies the audit detects deliberate energy destruction; that control belongs to `sex_arms.py`'s own
record and was not re-run here.

---

## 4. Protocol and provenance

* **Runner:** `sweep_sex_cost.py` (resumable, 4 worker processes, `ProcessPoolExecutor`).
* **Analyser:** `analyze_sex_cost.py` (reads `raw.jsonl` only).
* **Config digest:** `572505500794cc3eeaae15c1a0e5e210b72aa67e415c655a40c1fe954a734c38`, computed over the full grid, fixed parameters, seed range, worker count and expected ref.
* **Raw-data hash:** `sha256(raw.jsonl) = 036451239d35dcab6a23b627bcfecd6b1db44ac81b39a5a4f90566a65ce9661c`.
* **Harness hashes (sha256, recorded at run time and re-verified after the run):** `sex_phase.py 5491d49830e937df86084f9a622e2709cafd977afb96fd4d59795e32ebb0c253`, `sex_arms.py 58053c539ccfea3e592abd219b0aaf8bb0848f2d09e2d637f442cabbf134766a`, `telemetry.py 2dedde57dfe2bf658bd2f8a465c9b801ac709184c540e2c3d8c74ad8884cc10c`, `codontrace/rng.py f47fb9c1f9609a931fe9553e157eaac57d928dfb86b6c78ef1c46f4e813ded15` (full values in `manifest.json`).

**Commit at run time — and why the harness hash, not the ref, is the load-bearing guarantee.** `origin/main` was
moving during this session because other team members were pushing; it was not changed by this task. 2,097 of the
2,100 runs executed while `origin/main` was `1355b60099f62a8352ba867575e5bab7565c4518`, and the final 3 (the
gap-fill, §5) while it was `74d98cb9575fc16f7137a3704a8cd896685df1c7`. The ref recorded in `manifest.json`
therefore reflects only the last invocation, and `manifest.json` states this explicitly. A moving branch head is
not a provenance guarantee for a computational run; the guarantee is that **the four audited source files that
define the instrument were hash-identical at run time and verify unchanged now** (`harness_unchanged_since_run: true`).
Every one of the 2,100 runs therefore executed byte-identical simulation code, and a reviewer can confirm
that from the hashes alone without trusting any commit pointer. `git.exe` was not on `PATH` in the executing
environment, so refs and the reflog were read directly from `.git/`; this is recorded in the manifest.

---

## 5. What was executed

* **2,100 runs**, one JSON object per run appended live to `raw.jsonl` and flushed immediately, so a kill loses at most the in-flight replicate.
* **Wall time: 3,198.8 s (main sweep, 2,097 runs) + 14.9 s (gap-fill, 3 runs) = 3,213.7 s ≈ 53.6 min at 4 workers**, measured while a redundant test process was still consuming CPU. `sweep.log` and `fill_gap.log` contain the streamed progress lines and final `SWEEP_COMPLETE` records.
* **Disclosed deviation.** An earlier attempt was deliberately killed after 50 logged runs in order to correct the manifest's ref-selection logic. Killing a process pool discards in-flight work, and three replicates that had been dispatched but not yet written were lost: **turnover 6, `c = 0.9`, seeds 8021–8023**. The restart re-ran them with the identical script and configuration (the sweeper skips any `run_key` already present in `raw.jsonl`); they were re-run, not substituted, and the final raw file contains exactly the 2,100 pre-registered keys with **zero duplicates**. This is disclosed because post-hoc completion of a dataset must be visible, not silent.
* No result was inspected before the full grid finished; the criterion in §2 was fixed in advance.

---

## 6. Raw data and parsing

| file | contents |
|---|---|
| `raw.jsonl` (archived as `raw.jsonl.gz`, 107,477 bytes compressed) | 2,100 lines; one object per run |
| `raw.jsonl` sha256 | `036451239d35dcab6a23b627bcfecd6b1db44ac81b39a5a4f90566a65ce9661c` (uncompressed) |
| `manifest.json` | grid, config digest, harness hashes, refs observed, environment, run counts, wall time |
| `evidence_files.sha256` | one `sha256  size  path` line per archived artefact |

Each `raw.jsonl` line carries: `run_key`, `seed`, `turnover`, `infection_cost`, `cost_ratio`, `parasite_mutation`,
`fail_death`, `generations`, `sexual_final`, `sexual_auc`, `extinct`, `extinction_generation`, `infected_mean`,
`ledger_residual`, `worker_seconds`. Parsing guidance: split on lines and `json.loads` each line independently;
ignore a torn final line (the sweeper does the same, and the affected run simply re-runs). Filter by `cost_ratio`
and `turnover`, then group by `seed` for paired contrasts. `run_key` has the form
`t{turnover}_ic{infection_cost}_c{cost_ratio}_s{seed}`, e.g. `t6_ic0.4_c1.10_s8000`.

---

## 7. Analysis

`analyze_sex_cost.py` derives every reported number from `raw.jsonl` alone — it does not read `RESULT.md` or any
hand-written summary, and `analysis.json` embeds the raw file's sha256 so the derivation is pinned to the exact
bytes analysed.

* **Estimator:** the per-cell estimand is the mean of `sexual_final` over the 100 paired seeds; the reported interval is a **paired bootstrap over the 100 shared seeds** (10,000 resamples, seed 12345, 2.5th/97.5th percentiles).
* **Cross-check:** a **paired t-interval** (two-sided 95 %, df = 99, t = 1.984). Both interval types give the same pass/fail call at every cost level.
* **Extinction bounds:** the extinct fraction uses a **Wilson score interval**, which is well behaved at the 0 and 1 boundaries that occur at `c = 0.9` (0/100 extinct) and `c = 1.75` (100/100 extinct).
* **Cost contrasts:** every cost level is differenced against `c = 1.0` **by identical seed**, on both `sexual_final` and `sexual_auc`, with bootstrap intervals on the difference.
* Outputs: `analysis.json` (full structured results, including the pre-declared criterion, per-cell intervals and the separation evidence), `analysis.txt` (human-readable tables), `analysis.log` (stdout).

---

## 8. Results

**Bracket read from the intervals: `c* = (1.1, 1.2]`.** With the criterion of §2, `c = 1.1` is maintained at all
three turnovers and `c = 1.2` fails at all three.

| turnover | `c = 1.1` mean [95 % CI] | `c = 1.1` extinct [Wilson CI] | `c = 1.2` mean [95 % CI] | `c = 1.2` extinct [Wilson CI] |
|---|---|---|---|---|
| 1 | 0.0862 [0.0687, 0.1052] | 0.27 [0.1927, 0.3643] | 0.0242 [0.0163, 0.0335] | 0.63 [0.5322, 0.7182] |
| 6 | 0.1283 [0.1089, 0.1479] | 0.13 [0.0776, 0.2098] | 0.0205 [0.0161, 0.0256] | 0.50 [0.4038, 0.5962] |
| 12 | 0.1426 [0.1221, 0.1636] | 0.06 [0.0278, 0.1248] | 0.0247 [0.0203, 0.0293] | 0.45 [0.3561, 0.5476] |

The edges are separated by **strictly disjoint intervals at all three turnovers**: mean sexual frequency at
`c = 1.1` lies above the `c = 1.2` interval everywhere (narrowest at turnover 12, where the `c = 1.1` lower bound 0.1221
exceeds the `c = 1.2` upper bound 0.0293), and extinction at `c = 1.1` (0.06–0.27) lies entirely below extinction
at `c = 1.2` (0.45–0.63). The extinction criterion is the stronger signal; the frequency criterion is the tighter
one at turnover 12.

**Per-level verdict.** Pass: `c = 0.9` and `c = 1.0` (both intervals far from the criterion edges) and `c = 1.1`.
Fail: `c = 1.2`, `1.25`, `1.5`, `1.75`.

**Endpoint behaviour confirms the instrument responds to the intended knob.** The costless reference `c = 1.0`
yields mean sexual frequency 0.31 / 0.44 / 0.47 (turnover 1 / 6 / 12); lowering the cost to `c = 0.9` raises it to
0.72 / 0.80 / 0.85; raising the cost to `c = 1.5` and `1.75` drives extinction to 0.99–1.00 with mean frequencies
of 0.0000–0.0006. Monotone in cost, as required.

**Paired cost contrasts.** Against `c = 1.0` by identical seed, the change in mean sexual frequency (ΔAUC) at
`c = 1.1` is −0.180 / −0.214 / −0.231 and at `c = 1.2` is −0.266 / −0.329 / −0.351 for turnover 1 / 6 / 12, every
bootstrap interval excluding zero. At `c = 1.2` the median time to sexual extinction is 307 / 336 / 330 generations
(turnover 1 / 6 / 12) within a 400-generation run, so those cells are sampled mid-collapse rather than at
equilibrium — which is why the extinction fraction, not the final frequency, is the sharper discriminator at the
bracket edge.

---

## 9. Interpretation and limits

**Meaning.** Within this model the maintenance of costly sex is lost between a 10 % and a 20 % surcharge on the
cost of a sexual birth: `c = 1.1` persists at all three antagonist turnovers, `c = 1.2` does not. The classical
two-fold cost (`c = 2.0`) sits far above the bracket, consistent with the earlier `sex_arms.py` finding that
coevolution does not rescue sex at the classical cost. Faster antagonist turnover does not move the bracket; it
changes the *level* at which sex persists inside the passing region (higher turnover, higher surviving frequency).

**Relationship to the superseded pilot, stated precisely.** The original single-seed probe's *qualitative*
narrowing to ~1.1–1.2 is **CONFIRMED**, not superseded — the interval-derived bracket agrees with it, and the
campaign document's headline does not need re-wording. What does not survive is the probe's *evidence status and
magnitudes*: it is a one-seed pilot (seed 9000), and its `c = 1.1` values (0.203 / 0.079 / 0.285) fall outside the
100-seed intervals at turnover 1 (0.0687–0.1052) and turnover 12 (0.1221–0.1636). A single seed samples a very wide
distribution here — the 100-seed spread at `c = 1.0` is roughly 0.26–0.50 — so the probe should be cited only as a
superseded pilot, never as evidence for the bracket. The `phase_results.json` cited by the campaign document never
existed; this record replaces that citation.

**Limits.**

* **Conditional on one regime.** `infection_cost = 0.4` throughout. The bracket is a conditional statement about that antagonist regime, not a claim about coevolution in general; the wider phase diagram over infection costs {0.4, 0.9, 1.6, 2.4} remains a separate, un-run experiment.
* **No mechanism claim for the threshold.** The sweep locates *where* costly sex stops persisting; it does not show *that the antagonist causes* the loss. A genotype-blind uniform-tax control (present in `sex_arms.py`) is the required contrast before any causal wording, and it was not re-run here.
* **Finite population and finite horizon.** 400 hosts, 400 generations, 6 loci. At `c = 1.2` the measured extinction fractions (0.45–0.63) are mid-collapse estimates, and the 0.5 upper-bound criterion is deliberately conservative, which is why `c = 1.2` is called failing rather than ambiguous.
* **Judgment encoded in the criterion.** The 0.05/0.5 thresholds are a pre-declared operationalisation of "maintained", not a natural constant; both edges are reported with intervals so a reader can apply a different criterion and read the bracket off the same table.
* **This is a negative result for the two-fold cost of sex in this model.** Costly sex at the classical factor of 2 is not maintained by the coevolving antagonist modelled here.

---

## 10. Replay

All commands are run from the repository root and use only in-repo paths. The archive stores the raw data
compressed as `raw.jsonl.gz`; decompress it first (`gunzip -k raw.jsonl.gz`) or point the analyser at the
decompressed file.

```bash
cd codontrace-genesis  # commands below are relative to the repository root
sha256sum -c docs/experiments/2026-09-29/sex_cost/evidence_files.sha256   # 1. verify artefacts
gunzip -k docs/experiments/2026-09-29/sex_cost/raw.jsonl.gz              # 2. expand raw data
python docs/experiments/2026-09-29/sex_cost/analyze_sex_cost.py          # 3. re-derive section 8
```

To re-run the sweep from scratch (≈54 min at 4 workers; it skips any `run_key` already present in `raw.jsonl`, so
it also serves as the resume path):

`python docs/experiments/2026-09-29/sex_cost/sweep_sex_cost.py`

`analysis.json` is the machine-readable form of §8; `RESULT.md` in this directory is the pack's own short-form
summary and agrees with it number for number.
