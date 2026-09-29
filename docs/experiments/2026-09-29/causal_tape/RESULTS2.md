# CausalTape-2/3 — order arm, environment replication, pipeline fix

**Run date:** 2026-09-27 · **Repo:** `codontrace-genesis` @ `5a161081` (local edits only; nothing pushed, nothing fetched)
**Scripts:** `order_arm.py`, `replicate.py` · **Raw output:** `results/order_results.json`, `results/replication_results.json`, `order_stdout.txt`, `replicate_stdout.txt`

## A. Port fix — the engine-native substrate now responds

The first port used remaining ATP as the outcome. ATP is monotonically
decreasing in activity, so no mutation ever improved it, no mutation was ever
accepted, and all 100 seeds returned the identical value 19.20. The outcome is
now read out of the trace: visited-cell count plus the closed-ledger
`resource_credit` from `world_delta` (remaining ATP only as a tie-breaker).

| genome | outcome |
|---|---|
| all-wait | 1.0 |
| single move codon | 6.0 |
| mixed move/collect | 17.0 |

Over 30 seeds at depth 10/20/40 the tapes now accept **81 / 116 / 128** events and
fitness spreads to sd 1.23 / 0.91 / 1.65. The engine-native substrate is usable;
the failure was the outcome variable, not the engine.

## B. Order arm — matched schedules on every arm

Intervention: hold the multiset of drawn proposals fixed, change only their
arrival order. Both arms are scheduled tapes and each carries a
`schedule_digest`. Gates first:

| gate | check | result |
|---|---|---|
| E | replaying a recorded schedule in recorded order reproduces the draw-driven tape | PASS — events, bits, fitness identical |
| F | `ε = 0`: the order effect must be **exactly** zero | PASS — max abs τ_order = **0.0** over 40 seeds × 4 permutations, with all 160 permuted schedules verified different |
| G | `ε = 0.8`: the order effect must be non-zero | PASS — median abs 3.55, mean 2.98, sd 3.31 |

Measured with 120 seeds, depth 40, 4 permutations per seed:

| ε | τ_order mean | median abs | 95% CI | seeds non-zero | `|τ|/FMAX` | above `0.01` | above `0.1` |
|---|---|---|---|---|---|---|---|
| 0.0 | 0.0000 | 0.0000 | [0, 0] | 0.00 | 0.0000 | 0.0 % | 0.0 % |
| 0.05 | 0.0000 | 0.0000 | [0, 0] | 0.00 | 0.0000 | 0.0 % | 0.0 % |
| 0.1 | 0.0000 | 0.0000 | [0, 0] | 0.00 | 0.0000 | 0.0 % | 0.0 % |
| 0.2 | 0.0699 | 0.1033 | [0.027, 0.108] | 0.84 | 0.0065 | 14.2 % | 0.0 % |
| 0.4 | 1.0483 | 1.1717 | [0.832, 1.248] | 1.00 | 0.0630 | 91.7 % | 36.7 % |
| 0.8 | 3.3053 | 3.7713 | [2.727, 3.839] | 1.00 | 0.1464 | 100 % | 85.8 % |

`FMAX` normalisation and the `0.01` / `0.1` floors follow the closest published
precedent for this quantity (Bajić, Vila, Blount & Sánchez, PNAS 2018,
doi:10.1073/pnas.1808485115, "noncommutative epistasis", δ = ε_AB − ε_BA); they
are that paper's convention, not a ratified community standard. The same
estimand is standard and named; what this run adds is the *intervention* (a
matched multiset permuted in arrival order, with a per-arm schedule digest),
which the evolutionary literature characteristically observes across replicates
rather than imposes.

**Reading.** Order dependence is exactly absent while the landscape commutes,
switches on as epistasis grows, and by ε = 0.8 moves fitness by ~15 % of the
largest endpoint value in 86 % of seeds. It is *not* a mechanism beyond static
epistasis here: the fitness map is time-invariant and frequency-independent, and
order matters only because the acceptance rule is conditioned on the realised
background. The honest claim is that order dependence is **enabled by epistasis
and quantified by this instrument**, not that it is an independent force.

**The 52× inflation did not reproduce.** Comparing a fully unmatched design
(natural tapes of one half of the seeds vs permuted outcomes of the other half —
no shared seed, no shared schedule) against the matched estimate gives a ratio
of only **1.06–1.57×** (ε = 0.2: 1.57, ε = 0.4: 1.09, ε = 0.8: 1.06). The
failure mode is real in general (Buffalo, Pearson & Klein 2026,
arXiv:2603.11084, "causally incoherent paired counterfactual comparisons"), but
in this substrate it is mild, and the large inflation the red team measured came
from a control arm with no declared schedule at all rather than from
permutation. Reported as a measured null, not as support for the stronger claim.

## C. Environment replication

The whole depth-40 grid was rerun against a second, independent coupling draw
(`ENV_SEED` 20260928; the first is 20260927).

| ε | `|spec bias|` env A | `|spec bias|` env B | `sd(ATT)` A | `sd(ATT)` B |
|---|---|---|---|---|---|
| 0.0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 0.05 | 0.0117 | 0.0040 | 0.0640 | 0.0623 |
| 0.1 | 0.0234 | 0.0193 | 0.1279 | 0.1349 |
| 0.2 | 0.0709 | 0.0481 | 0.3241 | 0.3517 |
| 0.4 | 0.3703 | 0.1632 | 0.7831 | 0.8080 |
| 0.8 | 0.7925 | 1.0021 | 1.8096 | 1.6597 |

Replication of the env-A numbers is exact against the first run (a whole-pipeline
reproducibility check). Verdict:

* specification bias is machine-zero at ε = 0 in **both** draws — **replicated**;
* it rises monotonically with ε in **both** draws — **replicated**;
* the exact per-lineage effect has zero spread at ε = 0 and a large spread at
  ε = 0.8 in **both** draws — **replicated**;
* selection bias is non-zero at ε = 0 in **both** draws — **replicated**;
* the **order-effect threshold did not replicate**: first non-zero at ε = 0.2 in
  draw A but ε = 0.05 in draw B. Draw B also has the larger specification bias
  at ε = 0.8, so the threshold tracks the strength of the *realised* coupling,
  not the ε parameter alone. The qualitative pattern (exactly zero at ε = 0,
  positive at high ε) replicates; the location of the switch does not, and the
  pre-registered "clean threshold" reading is therefore refused.

## D. Claim-pipeline fix (local, repo source)

The two defects verified in the previous review are fixed and guarded:

* `src/codontrace/genesis/causal_validation.py` — `build_causal_evidence_report`
  no longer fabricates a zero-width interval at the mean. It now returns a 95 %
  t interval over the paired deltas for n ≥ 2, and `(0.0, 0.0)` for n < 2 or for
  zero variance, i.e. an interval that cannot be read as excluding zero.
* `src/codontrace/claimgate/auditor.py` — `_ci_excludes_zero` refuses a
  zero-width interval; `_comparison_has_difference` now **fails closed** when a
  comparison has a non-zero effect and neither an interval nor a p-value.

New adversarial tests: `tests/science_gates/test_causal_interval_guard.py`
(8 tests, all pass), covering the single-pair case, the real two-pair interval,
the zero-variance case, and the four fail-closed shapes.

Test sweep over the claimgate and science-gate suites:
**240 passed, 1 failed** (`tests/science_gates/test_replay_digest_policy_sweep.py`).
That failure is **pre-existing and unrelated**: it is an unregistered-digest
assertion whose missing class paths are all `closed_loop_hp_arm01_*` modules
introduced by the upstream `5a161081` fast-forward; neither changed file defines
a digest dataclass.

## E. Standing limitations

* One substrate pair, one fitness generator family; the order arm was measured
  against one `ENV_SEED` (the replication of the order arm covers A and B only
  at the threshold level).
* The order perturbation is a uniform random permutation; local (adjacent-pair)
  order effects, which would be more biologically legible, are not measured.
* No Walsh–Hadamard estimate is reported: the fitness map is exactly quadratic,
  so the epistasis spectrum is known in closed form (order-1 `w_i`, order-2
  `ε·J_ij`, order ≥ 3 zero) and a transform would only re-derive the generator.
* Nothing here is a biological claim, and no ClaimGate refusal was relaxed.
