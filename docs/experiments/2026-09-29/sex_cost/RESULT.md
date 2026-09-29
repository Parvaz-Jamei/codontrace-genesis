# task-12 result — two-fold-cost critical ratio c* on the audited phase harness

## Result statement

Using the audited two-fold-cost harness at `origin/main` (harness files hash-verified at run time and unchanged since), we re-ran the critical-cost sweep that previously rested on one seed: **7 cost levels {0.9, 1.0, 1.1, 1.2, 1.25, 1.5, 1.75} × 3 antagonist turnovers {1, 6, 12} × 100 paired seeds (8000–8099) = 2,100 runs**, no level, seed or threshold dropped after seeing results, each run asserted against the ATP ledger identity (max residual **2.556e-10** over all 2,100 runs), with live per-seed JSONL and a manifest carrying the origin/main sha, config digest (57250550…) and harness hashes. Reading the bracket from intervals rather than point estimates — a level counts as maintained only if the paired-bootstrap lower bound on mean sexual frequency exceeds 0.05 **and** the Wilson upper bound on the extinction fraction stays below 0.5, at all three turnovers — **c = 1.1 passes at every turnover (LCL 0.0687 / 0.1089 / 0.1221; extinction UCL 0.3643 / 0.2098 / 0.1248) while c = 1.2 fails at every turnover (LCL 0.0163 / 0.0161 / 0.0203; extinction UCL 0.7182 / 0.5962 / 0.5476), so the interval-derived bracket is (1.1, 1.2] and the earlier single-seed narrowing to ~1.1–1.2 is CONFIRMED, not superseded.** Both criteria separate the edges with strictly disjoint intervals at all three turnovers (extinction 1.1: 0.06–0.27 vs 1.2: 0.45–0.63; the narrowest edge is frequency at turnover 12), and the endpoints behave as expected (c = 0.9 lifts mean frequency to 0.72–0.85 vs 0.31–0.47 at c = 1.0; c = 1.5 and 1.75 drive extinction to 0.99–1.00). The old single-seed probe's *qualitative* bracket survives, but its *magnitudes* do not: the probe's c = 1.1 values (0.203 / 0.079 / 0.285) sit outside the 100-seed intervals at turnover 1 (0.0687–0.1052) and turnover 12 (0.1221–0.1636), so the probe should be cited only as a superseded pilot, never as the evidence for the bracket.

## Decisive numbers (all from `raw.jsonl` only)

| turnover | c = 1.1 mean [95% CI] | c = 1.1 extinct [Wilson CI] | c = 1.2 mean [95% CI] | c = 1.2 extinct [Wilson CI] |
|---|---|---|---|---|
| 1 | 0.0862 [0.0687, 0.1052] | 0.27 [0.1927, 0.3643] | 0.0242 [0.0163, 0.0335] | 0.63 [0.5322, 0.7182] |
| 6 | 0.1283 [0.1089, 0.1479] | 0.13 [0.0776, 0.2098] | 0.0205 [0.0161, 0.0256] | 0.50 [0.4038, 0.5962] |
| 12 | 0.1426 [0.1221, 0.1636] | 0.06 [0.0278, 0.1248] | 0.0247 [0.0203, 0.0293] | 0.45 [0.3561, 0.5476] |

Paired against costless c = 1.0 by identical seed: ΔAUC at c = 1.1 is −0.180 / −0.214 / −0.231 (turnover 1/6/12) and at c = 1.2 is −0.266 / −0.329 / −0.351, all with bootstrap CIs excluding zero. Median time to sexual extinction at c = 1.2 is 307–336 generations; the run is 400 generations, so the c = 1.2 cells are measured mid-collapse, not at equilibrium.

## Pre-declared criterion

Fixed before the sweep finished and never changed: level is "maintained" iff **LCL95(mean sexual_final) > 0.05 AND UCL95(extinct fraction) < 0.5 across all three turnovers**; intervals are a paired bootstrap over the 100 shared seeds (10,000 draws, seed 12345) in `analysis.json`, cross-checked by a paired t-interval (df = 99, t = 1.984). Both the bootstrap and the paired-t intervals give the same pass/fail call at every level.

## Evidence paths

| artefact | path |
|---|---|
| raw per-seed records (2,100 rows, 828 KB) | `docs/experiments/2026-09-29/sex_cost/raw.jsonl` |
| raw bytes frozen for verification | `sha256(raw.jsonl) = 036451239d35dcab6a23b627bcfecd6b1db44ac81b39a5a4f90566a65ce9661c` |
| run manifest (sha, config digest, harness sha256, grid, environment) | `docs/experiments/2026-09-29/sex_cost/manifest.json` |
| analysis derived from raw only | `docs/experiments/2026-09-29/sex_cost/analysis.json`, `docs/experiments/2026-09-29/sex_cost/analysis.txt` |
| analysis stdout | `docs/experiments/2026-09-29/sex_cost/analysis.log` |
| sweeper (resumable) | `docs/experiments/2026-09-29/sex_cost/sweep_sex_cost.py` |
| analyser | `docs/experiments/2026-09-29/sex_cost/analyze_sex_cost.py` |
| sweep + resume wall time | `docs/experiments/2026-09-29/sex_cost/sweep.log`, `docs/experiments/2026-09-29/sex_cost/fill_gap.log` |

Wall time: 3,198.8 s main sweep (2,097 runs) + 14.9 s resumable gap-fill (3 runs) = **3,213.7 s ≈ 53.6 min at 4 workers**, run while a redundant pytest process was still consuming CPU. 8 workers would cut this to roughly 38 min at the measured ~1.4× factor.

## Honesty notes the manager must carry into the repair

1. **The claim survives, so do not re-word it as superseded.** What changes is the *citation*: the missing `phase_results.json` and the single-seed `phase_probe.txt` narrowing are replaced by `docs/experiments/2026-09-29/sex_cost/`. Cite the bracket as interval-derived from 100 paired seeds per level per turnover.
2. **`origin/main` was moving during this session** because other teammates were pushing (reflog: `01ee4a2 → 1355b6` at 16:17:25 "docs(campaign): repair a dangling citation and commit the novelty synthesis", then a further push to `74d98cb`). 2,097 of 2,100 runs executed at `1355b6` and the last 3 at `74d98cb`. The load-bearing guarantee is not the moving ref but the harness hashes: the four audited files (`sex_phase.py`, `sex_arms.py`, `telemetry.py`, `codontrace/rng.py`) were hash-identical at run time and are unchanged now (`harness_unchanged_since_run: true` in `analysis.json`). The manifest's sha field reflects the last fill invocation, and `manifest.json` states this explicitly.
3. **The 3-run gap is disclosed.** Killed in-flight work in an earlier attempt lost three replicates (turnover 6, c = 0.9, seeds 8021–8023). They were re-run with the identical script and configuration, not substituted; the raw file now contains exactly the pre-registered 2,100 keys with zero duplicates.
4. **Scope limits.** infection_cost is fixed at 0.4, parasite_mutation at 0.005, fail_death 0.9, generations 400, host cap 400, loci 6 — the parameter values of the original probe, held fixed so the new sweep tests the old claim rather than a new one. c* is therefore conditional on that regime; the wider phase diagram over infection_cost ∈ {0.4, 0.9, 1.6, 2.4} remains a separate run.
5. **What this is not.** A bracket is not a mechanism: the sweep shows where costly sex stops persisting, not that the antagonist is the cause. The existing genotype-blind tax control from `sex_arms.py` is the needed contrast before any causal wording.
