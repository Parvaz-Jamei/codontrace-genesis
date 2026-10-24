"""Section 8: separating selection, historical contingency and chance.

The design follows Travisano, Mongold, Bennett & Lenski (1995, Science
267:87-90, "Experimental tests of the roles of adaptation, chance, and
history in evolution") and the replay logic of Blount, Borland & Lenski
(2008, PNAS 105:7899-7906): the same intervention is replayed on several
historical backgrounds, each with several independent chance replicates.

For a balanced table ``Y[h][t][r]`` (history h, treatment t, replicate r)
the total sum of squares splits exactly (two-way ANOVA with replication)
into

* ``treatment``: the effect of the intervention averaged over histories
  (what selection acting on that variant can see everywhere),
* ``history``: differences between backgrounds that do not depend on the
  intervention,
* ``interaction``: how much the intervention's effect depends on history
  (potentiation, Blount et al. 2008),
* ``chance``: replicate-to-replicate variation within a cell.

``history + interaction`` is reported as historical contingency. Permutation
p-values (Manly 2007, *Randomization, Bootstrap and Monte Carlo Methods in
Biology*) use ``RNGManager``. Every term is tested by permuting residuals
of the reduced model that drops only that term (Freedman & Lane 1983,
J. Bus. Econ. Stat. 1:292-298), as Anderson & ter Braak (2003, J. Stat.
Comput. Simul. 73:85-113) recommend for crossed ANOVA designs:

* ``treatment``: residuals of history + interaction,
* ``history``: residuals of treatment + interaction,
* ``interaction``: residuals of the additive model (Anderson & Legendre 1999).

Shuffling raw observations across all cells would test the global null
(no effect of anything), not a main effect. The three p-values are one
family; :attr:`ContingencyDecomposition.verdict` uses Holm (1979,
Scand. J. Stat. 6:65-70) adjusted p-values, reported as ``p_holm``.

Scope limits. The permutation treats replicates within a cell as
exchangeable and the cells as independent. :func:`engine_contingency_table`
uses the same engine seeds in both treatment arms (common random numbers),
so its arms are paired; the test ignores that pairing, which wastes power
but does not use it to manufacture significance. The outcome is a
continuous or count response; no chi-square, G-test or small-cell
statistic for categorical outcomes is provided.

:func:`engine_contingency_table` fills the table from real engine reruns
using :class:`.engine_study.EngineBitStudy`: histories are founder
backgrounds, the treatment is ``do(focal bit)``, replicates are engine seeds.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager

__all__ = ["ContingencyDecomposition", "decompose", "engine_contingency_table"]

Table = Mapping[object, Mapping[object, Sequence[float]]]


@dataclass(frozen=True)
class ContingencyDecomposition:
    ss_treatment: float
    ss_history: float
    ss_interaction: float
    ss_chance: float
    p_treatment: float
    p_history: float
    p_interaction: float
    treatment_effect_by_history: dict[str, float]
    alpha: float = 0.05

    @property
    def p_holm(self) -> dict[str, float]:
        """Holm step-down adjusted p-values over the three tests."""
        raw = {"treatment": self.p_treatment, "history": self.p_history, "interaction": self.p_interaction}
        order = sorted(raw, key=lambda k: (raw[k], k))
        out: dict[str, float] = {}
        running = 0.0
        for rank, key in enumerate(order):
            running = max(running, min(1.0, (len(order) - rank) * raw[key]))
            out[key] = running
        return out

    @property
    def ss_total(self) -> float:
        return self.ss_treatment + self.ss_history + self.ss_interaction + self.ss_chance

    def share(self, part: str) -> float:
        tot = self.ss_total
        return 0.0 if tot == 0 else float(getattr(self, f"ss_{part}")) / tot

    @property
    def contingency_share(self) -> float:
        return self.share("history") + self.share("interaction")

    @property
    def verdict(self) -> str:
        """``historically_contingent`` when the effect depends on history,
        ``selection`` when a uniform effect is detected, else ``not_detected``."""
        adj = self.p_holm
        if adj["interaction"] < self.alpha:
            return "historically_contingent"
        if adj["treatment"] < self.alpha:
            return "selection"
        return "not_detected"

    def to_dict(self) -> dict[str, object]:
        return {
            "ss": {
                "treatment": self.ss_treatment,
                "history": self.ss_history,
                "interaction": self.ss_interaction,
                "chance": self.ss_chance,
            },
            "share": {p: self.share(p) for p in ("treatment", "history", "interaction", "chance")},
            "contingency_share": self.contingency_share,
            "p": {
                "treatment": self.p_treatment,
                "history": self.p_history,
                "interaction": self.p_interaction,
            },
            "p_holm": self.p_holm,
            "treatment_effect_by_history": self.treatment_effect_by_history,
            "verdict": self.verdict,
            "alpha": self.alpha,
        }


def _check(table: Table) -> tuple[list[object], list[object], int]:
    hs = sorted(table, key=str)
    if len(hs) < 2:
        raise ConfigurationError("need at least two histories")
    ts = sorted(table[hs[0]], key=str)
    if len(ts) < 2:
        raise ConfigurationError("need at least two treatments")
    r = len(table[hs[0]][ts[0]])
    for h in hs:
        if sorted(table[h], key=str) != ts:
            raise ConfigurationError("every history needs the same treatments")
        for t in ts:
            if len(table[h][t]) != r:
                raise ConfigurationError("design must be balanced")
    if r < 2:
        raise ConfigurationError("need at least two replicates per cell")
    return hs, ts, r


def _ss(cells: list[list[list[float]]]) -> tuple[float, float, float, float]:
    nh, nt, r = len(cells), len(cells[0]), len(cells[0][0])
    grand = sum(sum(sum(c) for c in row) for row in cells) / (nh * nt * r)
    cm = [[sum(c) / r for c in row] for row in cells]
    hm = [sum(row) / nt for row in cm]
    tm = [sum(cm[i][j] for i in range(nh)) / nh for j in range(nt)]
    ss_h = nt * r * sum((m - grand) ** 2 for m in hm)
    ss_t = nh * r * sum((m - grand) ** 2 for m in tm)
    ss_i = r * sum(
        (cm[i][j] - hm[i] - tm[j] + grand) ** 2 for i in range(nh) for j in range(nt)
    )
    ss_e = sum((y - cm[i][j]) ** 2 for i in range(nh) for j in range(nt) for y in cells[i][j])
    return ss_t, ss_h, ss_i, ss_e


def _f(ss_eff: float, df_eff: int, ss_e: float, df_e: int) -> float:
    if ss_e == 0.0:
        return float("inf") if ss_eff > 1e-12 else 0.0
    return (ss_eff / df_eff) / (ss_e / df_e)


def decompose(
    table: Table, *, n_permutations: int = 999, seed: int = 0, alpha: float = 0.05
) -> ContingencyDecomposition:
    hs, ts, r = _check(table)
    cells = [[[float(y) for y in table[h][t]] for t in ts] for h in hs]
    nh, nt = len(hs), len(ts)
    ss_t, ss_h, ss_i, ss_e = _ss(cells)
    df_t, df_h, df_i, df_e = nt - 1, nh - 1, (nh - 1) * (nt - 1), nh * nt * (r - 1)
    obs = (_f(ss_t, df_t, ss_e, df_e), _f(ss_h, df_h, ss_e, df_e), _f(ss_i, df_i, ss_e, df_e))

    rng = RNGManager(seed=seed, namespace="causal_inference/contingency")
    grand = sum(y for row in cells for c in row for y in c) / (nh * nt * r)
    cm = [[sum(c) / r for c in row] for row in cells]
    hm = [sum(row) / nt for row in cm]
    tm = [sum(cm[i][j] for i in range(nh)) / nh for j in range(nt)]
    # Fitted values of each reduced model (the full model minus one term).
    reduced = (
        [[cm[i][j] - (tm[j] - grand) for j in range(nt)] for i in range(nh)],  # no treatment
        [[cm[i][j] - (hm[i] - grand) for j in range(nt)] for i in range(nh)],  # no history
        [[hm[i] + tm[j] - grand for j in range(nt)] for i in range(nh)],  # additive
    )
    resid = [
        [cells[i][j][k] - fit[i][j] for i in range(nh) for j in range(nt) for k in range(r)]
        for fit in reduced
    ]
    dfs = (df_t, df_h, df_i)

    hits = [1, 1, 1]
    for _ in range(n_permutations):
        for term in range(3):
            fit, pr = reduced[term], list(resid[term])
            rng.shuffle(pr)
            pc = [
                [[fit[i][j] + pr[(i * nt + j) * r + k] for k in range(r)] for j in range(nt)]
                for i in range(nh)
            ]
            parts = _ss(pc)
            if _f(parts[term], dfs[term], parts[3], df_e) >= obs[term] - 1e-12:
                hits[term] += 1
    denom = n_permutations + 1
    effect = {
        str(h): (sum(cells[i][-1]) - sum(cells[i][0])) / r for i, h in enumerate(hs)
    }
    return ContingencyDecomposition(
        ss_t, ss_h, ss_i, ss_e,
        hits[0] / denom, hits[1] / denom, hits[2] / denom,
        effect, alpha,
    )


def engine_contingency_table(
    study: object, *, env: int = 0, seeds: Sequence[int] | None = None
) -> dict[str, dict[int, list[float]]]:
    """Histories = background bit values; treatment = do(focal bit); replicates = seeds."""
    from .engine_study import EngineBitStudy

    if not isinstance(study, EngineBitStudy):
        raise ConfigurationError("study must be an EngineBitStudy")
    reps = tuple(seeds) if seeds is not None else study.seeds
    return {
        f"{study.background_var}={bg}": {
            t: [float(study.run(s, env, bg, t)) for s in reps] for t in (0, 1)
        }
        for bg in (0, 1)
    }
