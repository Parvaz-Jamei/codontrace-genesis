"""E1 size, bias and SD simulation for the JR5 prereg (numpy only, seeded).

This is the script behind the "Slope bias" figures and the TOST pass-rate
table in PREREG.md section 5 (E1). Model, per population:

- generation 0: the asexual count is fixed at round(0.2 * N), not drawn;
- each later generation: Wright-Fisher sampling, count ~ Binomial(N, q) with
  q = w p / (w p + 1 - p), p the previous asexual frequency and w the true
  per-generation odds ratio;
- a population that fixes before generation 3 is excluded and counted;
- both fits (plain and bias-reduced) use tests/_jr5_e1_fit.py on the same
  populations, generations 0 to T, census N every generation.

TOST: disjoint groups of 40 populations, no resampling, one-sample t interval
at 90% on the log scale, pass when it lies inside log(0.9 theory) and
log(1.1 theory). The t quantile for 39 degrees of freedom is a fixed constant.

Seed for setting j (j = 0, 1, 2 for true w = theory, 0.9 theory, 1.1 theory)
is 20261031 + j, one numpy default_rng stream per setting.

Usage: python docs/prereg/jr5/scripts/e1_power_sim.py M N [REPLICATES]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests._jr5_e1_fit import fit_logit  # noqa: E402

SEED_BASE = 20261031
FOUNDER_FREQUENCY = 0.2
EARLY_FIXATION_GENERATION = 3
GROUP = 40
# Upper 0.95 quantile of Student t with 39 degrees of freedom.
T_95_DF39 = 1.6848751217112248
REPLICATES = 40000


def horizon(m: float) -> int:
    return {0.5: 5, 0.25: 11}[m]


def simulate(n_host: int, w: float, t_max: int, replicates: int, seed: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Return plain slopes, bias-reduced slopes and the excluded count."""
    rng = np.random.default_rng(seed)
    x = np.arange(t_max + 1.0)
    n = np.full(t_max + 1, float(n_host))
    plain: list[float] = []
    reduced: list[float] = []
    excluded = 0
    for _ in range(replicates):
        k = [int(FOUNDER_FREQUENCY * n_host)]
        for _g in range(t_max):
            p = k[-1] / n_host
            q = w * p / (w * p + 1 - p) if 0 < p < 1 else p
            k.append(int(rng.binomial(n_host, q)))
        counts = np.array(k, dtype=float)
        if (counts[:EARLY_FIXATION_GENERATION] == n_host).any():
            excluded += 1
            continue
        plain.append(float(fit_logit(counts, n, x, bias_reduced=False)[1]))
        reduced.append(float(fit_logit(counts, n, x, bias_reduced=True)[1]))
    return np.array(plain), np.array(reduced), excluded


def tost_pass_rate(slopes: np.ndarray, theory: float, group: int = GROUP) -> tuple[float, float, int]:
    """Pass rate over disjoint groups, its Monte Carlo SE and the group count."""
    lo, hi = np.log(theory * 0.9), np.log(theory * 1.1)
    g = slopes[: len(slopes) // group * group].reshape(-1, group)
    mean = g.mean(axis=1)
    se = g.std(axis=1, ddof=1) / np.sqrt(group)
    ok = (mean - T_95_DF39 * se > lo) & (mean + T_95_DF39 * se < hi)
    rate = float(ok.mean())
    return rate, float(np.sqrt(rate * (1 - rate) / len(ok))), len(ok)


def main(argv: list[str]) -> None:
    m, n_host = float(argv[1]), int(argv[2])
    replicates = int(argv[3]) if len(argv) > 3 else REPLICATES
    theory = 1 / (1 - m)
    for j, w in enumerate((theory, theory * 0.9, theory * 1.1)):
        plain, reduced, excluded = simulate(n_host, w, horizon(m), replicates, SEED_BASE + j)
        parts = []
        for name, s in (("plain", plain), ("bias_reduced", reduced)):
            rate, se, groups = tost_pass_rate(s, theory)
            bias = s.mean() - np.log(w)
            parts.append(
                f"{name} bias {bias:+.4f} (se {s.std() / np.sqrt(len(s)):.4f}) sd {s.std():.3f} "
                f"pass {rate:.3f} (se {se:.3f}, groups {groups})"
            )
        print(m, n_host, round(w, 4), "excluded", excluded, " | ".join(parts), flush=True)


if __name__ == "__main__":
    main(sys.argv)
