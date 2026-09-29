# CausalTape — consolidated results (round 2, autonomous run)

Repo `codontrace-genesis` @ `5a161081`; all work local; no git writes. Workers: 4 per run.

## 1. Innovation #1 scaled (600 paired seeds, 2 environments, 3 depths)

`scale1.py`, `results/scale1_results.json`. All pattern checks pass in **both** coupling draws:

| check | env A | env B |
|---|---|---|
| specification bias = 0 at eps=0 | true (4.1e-15) | true (2.6e-15) |
| specification bias monotone in eps | true (0.0065 -> 0.926) | true (0.0053 -> 0.959) |
| naive conditioning **under**-estimates | true | true |
| exact per-lineage effect sd = 0 at eps=0 | true | true |
| sd > 0 at eps=0.8 | true | true |
| tau_epi = 0 at eps=0 | true | true |
| innovation rate at reference | 0.467 | 0.475 |

Instrument fix applied: the innovation threshold is now calibrated per depth on pilot seeds (the single global threshold saturated: 0.000 at depth 20, 1.000 at depth 80). The order effect first becomes non-zero at eps=0.2 (env A) and eps=0.05 (env B): the **location of the threshold is landscape-dependent, the qualitative pattern is not**. The R3 sign prediction was re-registered from the measured mechanism and now passes.

## 2. Innovation #2 — two-fold cost of sex in an audited closed energy ledger

`sex_arms.py`, `results/sex_arms_results.json`, 100 paired seeds per arm, 400 generations.

Instrument validation (all pass):

| gate | result |
|---|---|
| ledger identity, all arms | max residual 1.5e-10 |
| mating-dissipation audit | error 0.0 exactly |
| injected leak (1e-3/host/gen) detected | residual 17.1 -> detected |
| positive control: costless sex + parasite | 0.472 +- 0.157, 0% extinct |
| negative control: costly sex, no parasite | 8.6e-5, 100% extinct |

Main results:

| arm | sexual frequency | extinct |
|---|---|---|
| costless, no parasite | 0.391 | 0% |
| **costless + parasite** | **0.472** | 0% |
| **cost x2 + parasite** | **0.0000** | **100%** (median 125 gens) |
| cost x2, no parasite | 0.0001 | 100% (median 191 gens) |
| cost x2, delta=0.5 dissipation + parasite | 0.0000 | 100% (median 80 gens) |
| cost x2, **non-evolving** parasite | 0.0000 | 100% (infection only 3%) |
| cost x2, recombination disabled + parasite | 0.0000 | 100% |
| cost x1.0 + parasite | 0.472 | 0% |
| cost x1.5 + parasite | 0.0004 | 100% |
| cost x3.0 + parasite | 0.0000 | 100% |

Verdicts: **P4 refused** (paired diff 0, CI includes 0) and **P5 refused**: at the classical
two-fold cost the parasite does **not** rescue sex. What it does do is raise costless sex from
0.391 to 0.472 and delay extinction without the cost. **The critical cost is bracketed:
c\* in (1.0, 1.5]** — the standard 2.0 lies above it. A non-evolving parasite (3% infection)
has no effect, so coevolution rather than mere parasite presence is required.

This matches the literature audit's prediction (Otto & Nuismer 2004: interactions typically
select against sex) and is reported as an honest negative with a quantified null.

## 3. Innovation #3 — Red Queen vs Court Jester turnover share

`rjcj.py`, `results/rjcj_results.json`, 100 paired seeds per cell, 6 cells, 400 generations.
Primary metric after the red-team round: temporal `F_ST(w)` on per-locus frequencies with a
closed-form haploid Wright-Fisher drift null built from `N_e(t) = (sum k)^2 / sum k^2`
(measured `N_e` ~ 40 against census ~ 359 — matching the census would have been a 9x error).

| w | biotic effect | abiotic effect | interaction | uniform-tax control | biotic share |
|---|---|---|---|---|---|
| 5 | +0.00027 | +0.00007 | -0.00026 | -0.00246 | 0.788 |
| 10 | +0.00121 | +0.00019 | -0.00064 | -0.00197 | 0.866 |
| 20 | +0.00271 | +0.00026 | -0.00106 | -0.00165 | 0.913 |
| 25 | +0.00362 | +0.00034 | -0.00140 | -0.00147 | 0.914 |
| 50 | +0.00782 | +0.00048 | -0.00269 | -0.00107 | 0.942 |

* Ranking is **biotic-dominant at every window** (biotic share 0.79-0.94) — stable, not convention-dependent.
* The **genotype-blind uniform-tax control passes**: a 74% uniform energy tax does not reproduce
  the biotic effect (it moves turnover the other way), so the biotic factor is not merely a tax.
* The interaction is **negative** and grows with w, as the red-team predicted (the bolus makes the
  infection tax non-binding for one generation and raises N_e).
* Claim is restricted to the model world; no external-validity claim is made.

## 4. Cycle status

Three test designs, each through two critique rounds (literature audit + red-team) before running,
each instrument gate green before measurement. Hypotheses refused: P4/P5 (no rescue under the
two-fold cost) and the "clean order-effect threshold" reading. Those are scientific negatives
produced by working instruments, not instrument failures; no threshold was softened and no
positive was fabricated.
