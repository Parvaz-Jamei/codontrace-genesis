# SCALE_DESIGN — large-scale runs for CausalTape Tests 1–3

Workspace: `causal-tape-experiment/`. Host: 8 logical cores (4 physical + HT), Windows, Python 3.14, numpy 2.4.4, pandas available. Telemetry backend: `telemetry.py` (smoke-tested). Nothing here is code; no experiments were run for this design beyond the timing micro-benchmarks named below.

## 0. Cost model (basis for every estimate)

Measured baselines at 4 workers, from `elapsed_seconds` in `results/*.json` plus a local timing micro-benchmark (`_scale_design_bench.py`, raw numbers in `results/_scale_design_bench.json`):

| unit | measured |
|---|---|
| TEST 1 `scale1.py` current run (600 seeds x 2 env x 3 depths + order arms) | 1810 s (~25 min) |
| TEST 2 `sex_arms.py` current run (23 configs x 100 seeds, G=400, 400 hosts) | 1706 s (~20 min) |
| TEST 3 `rjcj.py` current run (6 cells x 100 seeds, G=400, 400 hosts) | 600 s (~10 min) |
| `run_arm` G=400, asex / sex+delta | 1.11 s / 1.92 s per replicate |
| `run_world` (rjcj) G=400 | 1.67 s per replicate |
| `confirm_task` G=40, K=6 mutants, 6 order perms | 0.198 s per seed |

Scaling laws used: TEST 1 cost per seed is sub-linear in depth (natural tape 5.5 ms at G=20 vs 13.7 ms at G=80; fixed per-invocation overhead dominates), while a confirmatory seed is ~0.20 s at G=40 and ~0.37 s at G=80. TEST 2 and TEST 3 scale ~linearly in seeds and generations. The 8-worker factor is **conservative 1.4x** vs 4 workers, not 2.0x (8 logical cores = 4 physical; measured pool speedup ~1.2x under load), so `wall(8w) ~= wall(4w)/1.4`.

## 1. Scale-up table (exact n, grid, estimated wall-clock)

### TEST 1 — exact-ground-truth estimator benchmark (`scale1.py`)

Grid: env_seed ∈ {20260927, 20260928, 20260929, 20260930} (4 independent coupling draws) x eps ∈ {0.0, 0.05, 0.1, 0.2, 0.4, 0.8} x depth ∈ {20, 40, 80}. Cells are **depth-stratified** because cost per seed grows with depth: G20 = 4 env x 6 eps = 24 cells, G40 = 4 env x 6 eps = 24 cells, G80 = 4 env x 2 eps (0.4, 0.8) = 8 cells. Total 56 cells.

| depth | seeds/cell | cells | total seeds | wall (4w) | wall (8w) |
|---|---|---|---|---|---|
| 20 | 6000 | 24 | 144 000 | 72 min | 52 min |
| 40 | 2000 | 24 | 48 000 | 96 min | 69 min |
| 80 | 600 | 8 | 4 800 | 38 min | 27 min |
| threshold calibration (pilot seeds, all depths) | — | 56 | — | 42 min | 30 min |
| **total** | | | **196 800** | **~4.1 h** | **~3.0 h** |

Order arms (6 global permutations + 12 adjacent swaps) run at **G40 only**: the first round showed no non-zero order effect below eps=0.05–0.2, so G20 buys nothing and the G80 arm cost is not defensible. G20 cells reach 6000 seeds/cell (well past the 1000 target); G40 carries 2000/cell; G80 is 600/cell and **honestly below 1000** — budget is spent on the two eps values where specification bias is largest.

### TEST 2 — two-fold cost of sex under an audited ledger (`sex_arms.py`)

Grid: cost_ratio ∈ {1.0, 1.25, 1.5, 2.0, 3.0} x mode/parasite/delta/recombine factorial = 20 main arms; G=400, 400 hosts, 16 parasites; all arms paired on the same seed (same host RNG fork).

| component | n | wall (4w) | wall (8w) |
|---|---|---|---|
| main factorial, 20 arms x 900 seeds, G=400 | 18 000 seeds | 82 min | 59 min |
| rescue sweep, 8 regimes x 2 cost arms x 900 seeds | 14 400 seeds | 52 min | 37 min |
| rjcj-in-sex 2x2, 4 cells x 900 seeds | 3 600 seeds | 14 min | 10 min |
| `delta` ladder {0, 0.25, 0.5, 1.0} x 400 seeds | 1 600 seeds | 12 min | 9 min |
| long-horizon extinction arms, 4 arms x 200 seeds, G=1200 | 800 seeds | 44 min | 31 min |
| leak / identity audit probes | 20 seeds | 3 min | 2 min |
| **total** | | **~3.5 h** | **~2.5 h** |

900 seeds/arm is below 1000, for an honest reason: the sex arm costs 1.7–2.2x the asex arm (per-parent Python recombination loop) and 400 hosts x 400 generations is already the cheapest regime that produces extinction. The deficiency is repaid with a **host-capacity tier** C ∈ {200, 400, 800} — n=900 at C=200/400, n=300 at C=800 (C=800 costs ~4x/seed) — which is what makes c* a density curve rather than a single point.

### TEST 3 — Red Queen vs Court Jester (`rjcj.py` + `rjcj_diag.py`)

| component | grid | n | wall (4w) | wall (8w) |
|---|---|---|---|---|
| main factorial | 4 cells x W ∈ {5,10,20,25,50}, G=400, LOCI=6 | 1600/cell = 6400 | 179 min | 128 min |
| tax controls (genotype-blind uniform tax) | 2 cells | 1600/cell = 3200 | 89 min | 64 min |
| `rjcj_diag` diagnostics | 4 cells | 400/cell = 1600 | 62 min | 44 min |
| LOCI=7 generality tier | 4 core cells, 128-genotype space | 400/cell = 1600 | 62 min | 44 min |
| **total** | | **12 800** | **~6.5 h** | **~4.7 h** |

`rjcj_diag` costs ~1.6x `run_world` per replicate (20-shuffle label-permutation null per generation), hence the smaller diagnostic n; that tier is a mechanism check, not an effect-size estimate. The 1600 seeds/cell in the main factorial is the strongest claim of the three tests.

**Feasibility verdict:** all three fit on 8 cores as three sequential runs — 4.1 / 3.5 / 6.5 h at 4 workers, or 3.0 / 2.5 / 4.7 h at 8 workers, ~10 h total at 8 workers. Do **not** run them concurrently.

## 2. Telemetry tiering, retrieval, disk estimate

**Full per-generation telemetry** (one JSONL line per generation + state snapshot every 5 generations): every natural-tape replicate in TEST 1 at G20 and G40 (the cheap ones, 5–7 ms), and every replicate of the TEST 3 main factorial and tax cells — there the primary estimand is a trajectory, so `F_ST(w)` needs the allele-frequency path. **Summary-only** (event at start/finish/failure + a single final snapshot + arm aggregates in the manifest): all TEST 1 confirmatory arms (19 runs per seed; per-generation logging would multiply event volume by ~19 for zero inferential benefit), all TEST 2 arms (only `sexual_final`, `sexual_auc`, extinction time and ledger residual are read out), the TEST 1 G80 cells, and `rjcj_diag` (4 scalars per run).

Snapshot columns — TEST 1/2 per generation: `generation, seed, cell, alive, mean_fitness, sd_fitness, accepted_rate, mean_energy, sexual_freq, infected_frac` (11 columns). TEST 3 adds the trajectory: `generation, cell, census, N_e, infected_frac, allele_freq[0..LOCI-1], eff_genotypes` (LOCI=6 or 7 → 12–13 columns). **numpy `.npz` is the right container**, not CSV or Parquet: rows are appended per run by a single writer, sizes are small, pandas adds a pyarrow dependency for marginal gain, and `.npz` round-trips `np.load` directly. CSV is only for the derived per-run summary tables.

Retrieval commands a human runs afterwards:

```powershell
# live event stream of a cell (one JSON object per line)
Get-Content telemetry/test3/logs/b1_s0_L6_s70123.jsonl -Tail 20 -Wait
# all events for a test, as a dataframe
python -c "import glob,pandas as pd; df=pd.concat(pd.read_json(f,lines=True) for f in glob.glob('telemetry/test3/logs/*.jsonl')); print(df.groupby('cell').size())"
# one run's per-generation state rows
python -c "import numpy as np; d=np.load('telemetry/test3/snapshots/b1_s0_L6_s70123.npz'); print(d['generation'][:5], d['allele_freq'].shape)"
# which replicates still need running
python -c "from telemetry import completed_keys, iter_missing; import json; keys=[l.split()[0] for l in open('keys_test3.txt')]; print(len(iter_missing(keys, completed_keys('telemetry','test3'))))"
```

Disk estimate (uncompressed JSONL ~60 B/event; compressed `.npz` rows ~0.4–1.5 KB):

| run group | event lines | event MB | snapshot rows | snap MB |
|---|---|---|---|---|
| T1 G20 natural, full | 2.9 M | 175 | 576 k | 320 |
| T1 G40 natural, full | 1.9 M | 115 | 192 k | 150 |
| T1 G40 confirm arms + G80, summary | 120 k | 7.5 | 9.6 k | 8 |
| T2 main + sweep + long-horizon, summary | 13.9 M | 833 | 45 k | 42 |
| T3 main + tax, full | 10.2 M | 615 | 1.28 M | 640 |
| T3 diag + LOCI=7, summary | 3.2 M | 190 | 90 k | 70 |
| manifests + `done.jsonl` | — | 12 | — | — |
| **total** | **~32 M** | **~1.95 GB** | | **~1.23 GB** |

**~3.2 GB total** for all three tests, ~3.3x the existing `results/` footprint — acceptable on a desktop disk. The `snapshot_every=5` decimation is what keeps it there: full per-generation rows for all runs would be ~6.2 GB of snapshots alone. If disk is tight, cut TEST 2's summary event lines first (833 MB, the largest block, and fully reconstructible from per-seed manifest summaries); never cut the TEST 3 trajectories.

**Mandatory telemetry fix before scaling:** `Telemetry.flush_snapshots` rewrites and re-compresses the *entire* `.npz` every 50 buffered rows — 8 full rewrites per G=400 run of up to 5 MB, 24 for the G=1200 arms, i.e. quadratic I/O over ~1.3 M snapshot rows. Fix by appending fixed-width raw records to a `.bin` and compressing once at `close()`, or by buffering the whole run and writing once at `close()`. Keep `snapshot_every=5` either way.

## 3. Checkpoint / resume key scheme

`run_key` is deterministic and human-readable; the same key must reproduce the same work:

```
test1/e{env_seed}/eps{eps:.3f}/G{depth}/s{seed}                  # natural tape (full telemetry)
test1/e{env_seed}/eps{eps:.3f}/G{depth}/s{seed}/cf{mutation_id}  # suppression arm
test1/e{env_seed}/eps{eps:.3f}/G{depth}/s{seed}/ord{k}           # permutation arm
test1/e{env_seed}/eps{eps:.3f}/G{depth}/s{seed}/loc{i}           # adjacent-swap arm
test2/{arm}/d{delta:.2f}/c{cost_ratio:.2f}/C{host_cap}/s{seed}
test2/rescue/{tag}/{cost|costless}/s{seed}
test2/long/{arm}/s{seed}
test3/{cell}/L{loci}/s{seed}
test3diag/{cell}/L{loci}/s{seed}
```

Rules: sanitise mutation ids for the filesystem (`:`→`-`, `>`→`_`); floats get fixed-width formatting (1.000, 2.00) so no two processes can spell a key differently; the exact config is stored in the manifest and a key reused with a different `config_digest` must fail loudly. Resume protocol: the batch starts by calling `completed_keys(root, test)` once, then `iter_missing(all_keys, done)`, and works only the missing keys. Only `done.jsonl` entries with `status == "done"` count, so a kill loses at most the in-flight replicate — one seed, not a cell. Two residual hazards to handle: partial `runs/<key>.json` with `status="running"` is simply overwritten on retry, but a partial `snapshots/<key>.npz` must be truncated on retry (the append path in `flush_snapshots` would merge stale and fresh rows) — add a truncate/`force` flag to the constructor and call `close(status="failed")` from an `except` block so crashes are visible. The unit of work handed to the pool is always one `run_key`, never a batch of seeds, so resume is an exact set difference and no writer process holds state across the boundary.

## 4. Implementer checklist

1. `scale1.py`: replace `CONFIRM_SEEDS`/`ENV_SEEDS`/`EPS_GRID`/`DEPTHS` with the §1 depth-stratified table; keep `REFERENCE=(0.2, 40)`; make the eps list per-depth (6 eps at G20/G40, `(0.4, 0.8)` at G80).
2. `scale1.py`: build the task list as `run_key`-indexed tuples and wrap each unit in `Telemetry(root, "test1", key, cfg)`; full per-generation events only for natural tapes, `close(status="failed")` from `except`.
3. `scale1.py`: split `confirm_task` into `(natural, cf, ord, loc)` sub-keys so resume granularity is one arm; emit per-generation events for `natural` and never for `cf`/`ord`/`loc`.
4. `workers.py`: read `WORKERS` from `DSH_SCALE_WORKERS` (default 8); keep `ProcessPoolExecutor` (spawn on Windows); use `chunksize=1` — measured chunking 4/8/16 gains no wall-clock and delays first writes.
5. `sex_arms.py`: hoist `ARMS`, the rescue `settings`, the rjcj cells, the `delta` ladder and the long-horizon arms into one flat list of specs tagged `main|rescue|rjcj|delta|long`; extend `cost_ratio` to the 5-point grid; add the C ∈ {200,400,800} tier; one `run_key` per `(spec, seed)`.
6. `sex_arms.py`: summary-only telemetry — one completion event per replicate carrying the 13 scalars `run_arm` already returns plus `config_digest`, `ledger_residual` and `dissipation_error`, so the identity is re-verifiable from the log alone; keep the exact `ledger.check()` assertion.
7. `rjcj.py`: keep 4 factorial + 2 tax cells, raise seeds to 1600/cell, make `LOCI` a parameter (6 main, 7 generality) with `GENOTYPES = 1 << LOCI` and `POWERS` computed per call; move the per-generation `allele_freq`/`census`/`breeding`/`infected_series` values into the snapshot call *inside* the generation loop.
8. `rjcj.py`: write whole-run `windows` and the eta² decomposition into `close(summary)`; keep per-seed window series in the manifest rather than in separate files.
9. `rjcj_diag.py`: reduce to the 4-cell n=400 diagnostic tier under the `test3diag` namespace and `L{loci}` keys; vectorise the `compatible` genotype test over `POWERS` instead of the `for g in range(GENOTYPES)` loop; keep 20 shuffles in the permutation null.
10. All three: add `--resume` and `--dry-run` flags that print the key count, the missing key count and the disk estimate before launching; document the §2 retrieval commands in a `telemetry/README.md`.

## 5. What each test needs to be answer-bearing, not merely bigger

**TEST 1 (estimator benchmark).** Size adds precision, not novelty. Required: a *third estimator family* that is not a linear adjustment — g-computation/ICE plus a doubly-robust AIPW combination — so the paper reports a bias–variance frontier against the exact ground truth instead of one adjusted coefficient. Plus pre-register the sign hypothesis per (env_seed, eps) and report the **order-effect threshold as a calibration curve** (≈30 pilot seeds per cell) showing the threshold moves with the coupling draw; turning the failed "clean threshold" reading into a landscape-dependent calibration *is* the novel claim. The eps≈0 cells must stay in as the falsification arm where specification bias is provably zero.

**TEST 2 (two-fold cost).** Bigger n at one `C=400` would be an artefact study. Required: (a) the **host-capacity tier** C ∈ {200, 400, 800} with c* re-estimated per tier, so the claim is "c* is a function of density and c* < 2 at every tier"; (b) the **`delta` ladder with the audit identity as the estimand** — the mating-dissipation flow must be recoverable from the ledger at every delta and the injected-leak probe re-run at each tier; (c) an explicit **analytic no-parasite baseline** for the costless arm (closed-form expected sexual-frequency decay overlaid on the simulated curve), so the simulation is anchored to theory rather than to itself. Without (a) and (c), the reviewer discounts c* as a finite-size artefact of a 400-slot pool.

**TEST 3 (Red Queen vs Court Jester).** The uniform-tax control already exists and passes, so size alone upgrades nothing. Required: (a) the **LOCI=7 tier** (128-genotype space vs the current ~25 effective of 64) proving the biotic share is not saturation of a 64-point space; (b) a **second turnover metric that is not F_ST-based** (genotype turnover / Bray–Curtis, or a mutation–selection balance proxy) with the share recomputed independently in that metric, so the ranking is not an artefact of the drift null's form; (c) a **drift-only negative control cell** (no mutation, no selection) whose `F_ST(w)` must bracket the closed-form Wright–Fisher prediction — currently the null is asserted analytically and never validated against a drift-only simulation, which leaves the share's denominator unverified.
