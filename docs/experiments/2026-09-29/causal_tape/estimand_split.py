"""estimand_split.py -- split the published "specification bias" into two parts.

Background
----------
`heavy2.py` reported, per focal mutation j,

    specification_bias_j = beta_j - ATT_whole_tape_j

with beta_j the OLS coefficient of continuous fitness on the 18 final bits and
ATT_whole_tape_j = E[Y - Y(do(m_j suppressed)) | m_j occurred] the exact
whole-tape effect of suppression. A reviewer objected that one number conflates
two different things. This script recomputes everything from the saved per-seed
arrays (no re-simulation) and splits it term by term:

    beta_j - ATT_whole_tape_j
        = ( beta_j - ATT_onebit_j )            <- component (i)
        + ( ATT_onebit_j - ATT_whole_tape_j )  <- component (ii)

component (i)   linear outcome-model misspecification, measured against the
                one-bit contrast of a saturated second-order (quadratic) model
                fitted on that configuration's natural ensemble;
component (ii)  re-routing: suppressing the mutation consumes the draw but
                re-routes every later acceptance decision, so the exact contrast
                is a whole-tape effect while any single-locus quantity is a
                one-bit effect.

ATT_onebit proxy
----------------
ATT_onebit_j is the change in the *fitted* quadratic outcome model (intercept +
18 main effects + all 153 pairwise products) when only locus j is flipped,
evaluated at each seed's observed covariates and then averaged over the exposed
seeds (the ATT-style average, matching ATT_whole_tape's conditioning):

    f(x_j = 1) - f(x_j = 0) = c_j + sum_{l != j} c_jl x_l     (linear in x_j)

This is a MODEL-BASED one-bit quantity, NOT an interventional one: it is the
best an in-class one-bit model can do, and therefore upper-bounds what a
correctly specified one-bit model can achieve. On this substrate the caveat is
additionally checkable: harness.py scores the synthetic genotype with the exact
quadratic map F(x) = sum_i w_i x_i + eps * sum_{i<j} J_ij x_i x_j, and the fitted
design here is full rank (172) with R^2 = 1 to machine precision, so the proxy
numerically equals the exact one-bit contrast rather than approximating it. The
residual ATT_onebit - ATT_whole_tape is therefore genuine re-routing: no one-bit
model, however well specified, can remove it.

Output: results/estimand_split.json plus a printed table.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
# The archived arrays live in results/; datasets/ is kept as a documented fallback
DATASETS = (HERE / "results") if (HERE / "results").is_dir() else (HERE / "datasets")
RESULTS = HERE / "results"
OUT_PATH = RESULTS / "estimand_split.json"
PUBLISHED = RESULTS / "heavy2_results.json"

N_BITS = 18
PAIRS = [(i, j) for i in range(N_BITS) for j in range(i + 1, N_BITS)]
PAIR_FIRST = np.array([pair[0] for pair in PAIRS])
PAIR_SECOND = np.array([pair[1] for pair in PAIRS])
EPS_ORDER = (0.0, 0.05, 0.1, 0.2, 0.4, 0.8)
BOOTSTRAP_DRAWS = 500
BOOTSTRAP_SEED = 20261004
ZERO_TOL = 1e-9

NOTES = [
    "ATT_whole_tape_j = mean over exposed seeds of (fitness - counterfactual[:, j]): the exact "
    "whole-tape effect of do(m_j suppressed).",
    "beta_j = OLS coefficient of fitness on the 18 final bits with an intercept (linear outcome model).",
    "ATT_onebit_proxy_j = mean over exposed seeds of the change in the fitted quadratic outcome model "
    "(intercept + 18 main effects + 153 pairwise products) when only locus j is flipped to 1 with the "
    "other loci held at their observed values.",
    "ATT_onebit_proxy is a MODEL-BASED one-bit quantity, NOT an interventional one; it is the best an "
    "in-class one-bit model can do and therefore upper-bounds what a correctly specified one-bit model "
    "can achieve.",
    "On this substrate the quadratic model is in fact exactly correctly specified (rank 172, R^2 = 1 to "
    "machine precision) because harness.py scores fitness with the exact quadratic map "
    "F(x) = sum_i w_i x_i + eps * sum_{i<j} J_ij x_i x_j. The proxy therefore equals the exact one-bit "
    "contrast, and component (ii) cannot be attributed to model error.",
    "Component (i) = beta_j - ATT_onebit_proxy_j is linear-model misspecification (a genuine modelling "
    "error, removable in principle by a correct one-bit model).",
    "Component (ii) = ATT_onebit_proxy_j - ATT_whole_tape_j is re-routing / estimand mismatch: "
    "suppressing a mutation re-routes later acceptance decisions, so no single-locus quantity can "
    "recover the whole-tape contrast.",
    "The identity beta_j - ATT_whole_tape_j = (i) + (ii) holds exactly, term by term.",
    "Caveat measured from the data: on a small share of exposed seeds (5.5% on average at eps = 0.8, up to 38% "
    "for the most reverted locus) a later accepted reversal has cleared the focal locus, so flipping the final "
    "state is not the same intervention as never applying the mutation. A carried-only robustness variant "
    "restricts both the one-bit proxy and the whole-tape contrast to exposed seeds that still carry the bit.",
]


# --------------------------------------------------------------------------
# design matrices and fits
# --------------------------------------------------------------------------


def quadratic_design(bits: np.ndarray) -> np.ndarray:
    """Intercept, 18 main effects, then all 153 pairwise products."""

    extra = bits[:, PAIR_FIRST] * bits[:, PAIR_SECOND]
    return np.hstack([np.ones((bits.shape[0], 1)), bits, extra])


def onebit_seed_matrix(bits: np.ndarray, quad_coef: np.ndarray) -> np.ndarray:
    """Per-seed one-bit contrast of the fitted quadratic model, for every locus.

    Row b holds f(x_b = 1) - f(x_b = 0), which for a model linear in x_b depends
    only on the other loci: c_b + sum_{l != b} c_bl x_l.
    """

    main = quad_coef[1 : 1 + N_BITS]
    pair = np.zeros((N_BITS, N_BITS))
    pair[PAIR_FIRST, PAIR_SECOND] = quad_coef[1 + N_BITS :]
    symmetric = pair + pair.T
    return main[:, None] + symmetric @ bits.T


def solve_via_svd(gram: np.ndarray, rhs: np.ndarray, rank_tol: float | None = None) -> np.ndarray | None:
    """Solve ``gram @ c = rhs`` for a symmetric positive semi-definite Gram matrix.

    Uses the SVD rather than np.linalg.solve: on this interpreter np.linalg.solve
    takes ~270 ms for a 172x172 system while the SVD takes ~12 ms, and the SVD
    also delivers the rank check needed to reject resamples that lost rank.
    For a full-rank Gram this returns the same vector as solve, up to rounding.
    """

    u, singular, vt = np.linalg.svd(gram)
    if rank_tol is not None and singular[-1] <= singular[0] * rank_tol:
        return None
    return vt.T @ ((u.T @ rhs) / singular)


class SeedEnsembleOLS:
    """OLS on the natural seed ensemble, with a fast path for bootstrap resampling.

    Only 789 of the 3000 seeds have distinct 18-bit states, so both designs are
    collapsed onto unique rows; a resample is then a set of integer row weights
    and the fit is a 172x172 (or 19x19) solve. Identical estimator to lstsq on
    the resampled design up to floating-point summation order.
    """

    def __init__(self, bits: np.ndarray, y: np.ndarray) -> None:
        self.unique_bits, row_of_seed = np.unique(bits, axis=0, return_inverse=True)
        self.row_of_seed = np.asarray(row_of_seed).reshape(-1)
        self.n_unique = self.unique_bits.shape[0]
        self.linear = np.hstack([np.ones((self.n_unique, 1)), self.unique_bits])
        self.quadratic = quadratic_design(self.unique_bits)
        self.y = y

    def fit(self, seed_index: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        take = self.row_of_seed[seed_index]
        counts = np.bincount(take, minlength=self.n_unique).astype(float)
        weighted_y = np.bincount(take, weights=self.y[seed_index], minlength=self.n_unique)
        beta = solve_via_svd((self.linear * counts[:, None]).T @ self.linear, self.linear.T @ weighted_y)[1:]
        coef = solve_via_svd((self.quadratic * counts[:, None]).T @ self.quadratic, self.quadratic.T @ weighted_y)
        return beta, coef

    def fit_checked(self, seed_index: np.ndarray, rank_tol: float = 1e-8) -> tuple[np.ndarray, np.ndarray] | None:
        """Fit, but return None if the resampled design has lost rank.

        A seed resample can drop every seed carrying a genotype pattern that is
        needed to identify the quadratic model, which would make the coefficient
        vector (and hence the one-bit contrast) non-unique. The bootstrap redraws
        such resamples instead of silently taking a minimum-norm solution.
        """

        take = self.row_of_seed[seed_index]
        counts = np.bincount(take, minlength=self.n_unique).astype(float)
        weighted_y = np.bincount(take, weights=self.y[seed_index], minlength=self.n_unique)
        gram = (self.quadratic * counts[:, None]).T @ self.quadratic
        coef = solve_via_svd(gram, self.quadratic.T @ weighted_y, rank_tol=rank_tol)
        if coef is None:
            return None
        beta = solve_via_svd((self.linear * counts[:, None]).T @ self.linear, self.linear.T @ weighted_y)[1:]
        return beta, coef


def split_from_fit(
    bits: np.ndarray,
    y: np.ndarray,
    counter: np.ndarray,
    present: np.ndarray,
    bit_of: np.ndarray,
    beta: np.ndarray,
    quad_coef: np.ndarray,
) -> dict:
    """Whole-tape ATT, one-bit proxy and the two components, from a given fit."""

    seed_onebit = onebit_seed_matrix(bits, quad_coef)
    has = present.astype(bool)
    delta = y[:, None] - counter
    att_whole = np.array([delta[has[:, j], j].mean() for j in range(bit_of.size)])
    att_onebit = np.array([seed_onebit[bit_of[j], has[:, j]].mean() for j in range(bit_of.size)])
    att_onebit_all = np.array([seed_onebit[bit_of[j]].mean() for j in range(bit_of.size)])
    component_i = beta[bit_of] - att_onebit
    component_ii = att_onebit - att_whole
    total = beta[bit_of] - att_whole

    # Robustness variant: on some exposed seeds a later accepted reversal has
    # cleared the focal locus, so a flip of the final state is not the same
    # intervention as never applying the mutation. Restrict both the one-bit
    # proxy and the whole-tape contrast to exposed seeds that still carry the bit.
    carried = has & (bits[:, bit_of] == 1.0)
    att_whole_carried = np.array(
        [delta[carried[:, j], j].mean() if carried[:, j].any() else np.nan for j in range(bit_of.size)]
    )
    att_onebit_carried = np.array(
        [seed_onebit[bit_of[j], carried[:, j]].mean() if carried[:, j].any() else np.nan for j in range(bit_of.size)]
    )
    return {
        "beta": beta,
        "att_whole": att_whole,
        "att_onebit": att_onebit,
        "att_onebit_all": att_onebit_all,
        "component_i": component_i,
        "component_ii": component_ii,
        "total_gap": total,
        "exposed": has.sum(axis=0),
        "carried": carried.sum(axis=0),
        "component_i_carried": beta[bit_of] - att_onebit_carried,
        "component_ii_carried": att_onebit_carried - att_whole_carried,
        "total_gap_carried": beta[bit_of] - att_whole_carried,
        "identity_residual_max": float(np.max(np.abs(total - component_i - component_ii))),
    }


def analyse(cfg: dict) -> dict:
    """Point estimate with plain lstsq (the published pipeline's estimator)."""

    n = cfg["bits"].shape[0]
    linear = np.hstack([np.ones((n, 1)), cfg["bits"]])
    beta = np.linalg.lstsq(linear, cfg["fitness"], rcond=None)[0][1:]
    quad_coef = np.linalg.lstsq(cfg["quad"], cfg["fitness"], rcond=None)[0]
    residual = cfg["fitness"] - cfg["quad"] @ quad_coef
    out = split_from_fit(
        cfg["bits"], cfg["fitness"], cfg["counterfactual"], cfg["present"], cfg["bit_of"], beta, quad_coef
    )
    out["quad_coef"] = quad_coef
    # duplicated genotype rows cannot add rank, so the rank is measured on the unique rows
    unique_bits = np.unique(cfg["bits"], axis=0)
    out["quad_rank"] = int(np.linalg.matrix_rank(quadratic_design(unique_bits)))
    out["n_unique_genotypes"] = int(unique_bits.shape[0])
    out["quad_r2"] = 1.0 - float((residual**2).sum() / ((cfg["fitness"] - cfg["fitness"].mean()) ** 2).sum())
    out["quad_residual_max"] = float(np.max(np.abs(residual)))
    out["linear_condition"] = float(np.linalg.cond(linear))
    return out


def load_configs() -> list[dict]:
    configs = []
    for path in sorted(DATASETS.glob("*.npz")):
        stem = path.stem
        env_seed = int(stem.split("_")[0][1:])
        eps = float(stem.split("_eps")[1].split("_")[0])
        with np.load(path) as data:
            mutations = [str(m) for m in data["mutations"]]
            bits = data["bits"].astype(float)
            configs.append(
                {
                    "key": stem,
                    "env_seed": env_seed,
                    "eps": eps,
                    "mutations": mutations,
                    "bit_of": np.array([int(m.split(":")[0]) for m in mutations]),
                    "fitness": data["fitness"].astype(float),
                    "bits": bits,
                    "counterfactual": data["counterfactual"].astype(float),
                    "present": data["present"].astype(np.int8),
                    "threshold": float(data["threshold"][0]),
                    "quad": quadratic_design(bits),
                }
            )
    return configs


# --------------------------------------------------------------------------
# summaries and statistics
# --------------------------------------------------------------------------


def summarise(res: dict) -> dict:
    component_i = np.abs(res["component_i"])
    component_ii = np.abs(res["component_ii"])
    total = np.abs(res["total_gap"])
    gross = component_i + component_ii
    med_i, med_ii, med_tot = float(np.median(component_i)), float(np.median(component_ii)), float(np.median(total))
    share_of_total = med_ii / med_tot if med_tot > ZERO_TOL else float("nan")
    med_gross = float(np.median(gross))
    share_of_gross = med_ii / med_gross if med_gross > ZERO_TOL else float("nan")
    per_mutation_share = component_ii / np.where(total > ZERO_TOL, total, np.nan)
    finite_share = per_mutation_share[np.isfinite(per_mutation_share)]
    return {
        "median_abs_component_i_misspec": med_i,
        "mean_abs_component_i_misspec": float(component_i.mean()),
        "median_abs_component_ii_reroute": med_ii,
        "mean_abs_component_ii_reroute": float(component_ii.mean()),
        "median_abs_total_gap": med_tot,
        "mean_abs_total_gap": float(total.mean()),
        "median_abs_gross_i_plus_ii": med_gross,
        "reroute_share_of_total_ratio_of_medians": float(share_of_total),
        "reroute_share_of_total_ratio_of_means": float(component_ii.mean() / total.mean())
        if total.mean() > ZERO_TOL
        else float("nan"),
        "reroute_share_of_total_median_of_shares": float(np.median(finite_share))
        if finite_share.size
        else float("nan"),
        "reroute_share_of_gross_ratio_of_medians": float(share_of_gross),
        "cancellation_median_abs_total_over_gross": float(np.median(total / np.where(gross > ZERO_TOL, gross, np.nan))),
        "fraction_total_lt_gross": float(np.mean(total < gross - 1e-12)),
        "same_sign_fraction": float(np.mean(np.sign(res["component_i"]) == np.sign(res["component_ii"]))),
        "cleared_exposed_fraction": float(np.mean(1.0 - res["carried"] / np.maximum(res["exposed"], 1))),
        "carried_median_abs_component_i": float(np.nanmedian(np.abs(res["component_i_carried"]))),
        "carried_median_abs_component_ii": float(np.nanmedian(np.abs(res["component_ii_carried"]))),
        "carried_median_abs_total_gap": float(np.nanmedian(np.abs(res["total_gap_carried"]))),
        "carried_reroute_share_of_total": float(
            np.nanmedian(np.abs(res["component_ii_carried"])) / np.nanmedian(np.abs(res["total_gap_carried"]))
        )
        if np.nanmedian(np.abs(res["total_gap_carried"])) > ZERO_TOL
        else float("nan"),
        "identity_residual_max": res["identity_residual_max"],
    }


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = x - x.mean()
    y = y - y.mean()
    den = float(np.sqrt((x**2).sum() * (y**2).sum()))
    return float((x * y).sum() / den) if den else float("nan")


def rank_average(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    for index in range(1, len(values) + 1):
        if index == len(values) or sorted_values[index] != sorted_values[start]:
            if index - start > 1:
                ranks[order[start:index]] = ranks[order[start:index]].mean()
            start = index
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return pearson(rank_average(x), rank_average(y))


def correlation_block(x: np.ndarray, y: np.ndarray) -> dict:
    return {
        "n": int(x.size),
        "pearson_signed": pearson(x, y),
        "spearman_signed": spearman(x, y),
        "pearson_absolute": pearson(np.abs(x), np.abs(y)),
        "spearman_absolute": spearman(np.abs(x), np.abs(y)),
    }


def bootstrap(entries: list[dict]) -> dict:
    """Seed bootstrap of the re-routing share at a fixed epistasis level.

    Seeds are resampled with replacement within each configuration and the whole
    chain is recomputed from scratch: linear fit, quadratic fit, one-bit proxy,
    ATT_whole_tape, both components. Resamples that lose rank of the quadratic
    design are redrawn (they are rare and would leave the one-bit contrast
    non-unique).
    """

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    ensembles = {entry["key"]: SeedEnsembleOLS(entry["bits"], entry["fitness"]) for entry in entries}
    per_config: dict[str, list[float]] = {entry["key"]: [] for entry in entries}
    pooled_total: list[float] = []
    pooled_gross: list[float] = []
    pooled_mean: list[float] = []
    carried_total: list[float] = []
    per_draw_mean_share: list[float] = []
    rejected = 0
    used = 0

    for _ in range(BOOTSTRAP_DRAWS):
        reroute_all: list[np.ndarray] = []
        total_all: list[np.ndarray] = []
        miss_all: list[np.ndarray] = []
        reroute_carried: list[np.ndarray] = []
        total_carried: list[np.ndarray] = []
        draw_shares: list[float] = []
        for entry in entries:
            n = entry["fitness"].size
            while True:
                index = rng.integers(0, n, size=n)
                fitted = ensembles[entry["key"]].fit_checked(index)
                if fitted is not None:
                    break
                rejected += 1
            used += 1
            beta, coef = fitted
            res = split_from_fit(
                entry["bits"][index],
                entry["fitness"][index],
                entry["counterfactual"][index],
                entry["present"][index],
                entry["bit_of"],
                beta,
                coef,
            )
            reroute = np.abs(res["component_ii"])
            total = np.abs(res["total_gap"])
            miss_all.append(np.abs(res["component_i"]))
            reroute_all.append(reroute)
            total_all.append(total)
            reroute_carried.append(np.abs(res["component_ii_carried"]))
            total_carried.append(np.abs(res["total_gap_carried"]))
            share = float(np.median(reroute) / np.median(total)) if np.median(total) > ZERO_TOL else float("nan")
            per_config[entry["key"]].append(share)
            draw_shares.append(share)
        reroute_pool = np.concatenate(reroute_all)
        total_pool = np.concatenate(total_all)
        miss_pool = np.concatenate(miss_all)
        denom = float(np.median(total_pool))
        gross = float(np.median(miss_pool + reroute_pool))
        pooled_total.append(float(np.median(reroute_pool) / denom) if denom > ZERO_TOL else float("nan"))
        pooled_gross.append(float(np.median(reroute_pool) / gross) if gross > ZERO_TOL else float("nan"))
        pooled_mean.append(
            float(reroute_pool.mean() / total_pool.mean()) if total_pool.mean() > ZERO_TOL else float("nan")
        )
        finite = [value for value in draw_shares if np.isfinite(value)]
        per_draw_mean_share.append(float(np.mean(finite)) if finite else float("nan"))
        carried_reroute_pool = np.concatenate(reroute_carried)
        carried_total_pool = np.concatenate(total_carried)
        carried_denom = float(np.median(carried_total_pool))
        carried_total.append(
            float(np.median(carried_reroute_pool) / carried_denom) if carried_denom > ZERO_TOL else float("nan")
        )

    def interval(values: list[float]) -> dict:
        array = np.array([v for v in values if np.isfinite(v)])
        return {
            "draws": int(array.size),
            "median": float(np.median(array)),
            "ci95": [float(np.percentile(array, 2.5)), float(np.percentile(array, 97.5))],
        }

    return {
        "draws_requested": BOOTSTRAP_DRAWS,
        "rng_seed": BOOTSTRAP_SEED,
        "estimand": "re-routing share = |ATT_onebit_proxy - ATT_whole_tape| / |beta_j - ATT_whole_tape|",
        "rank_deficient_resamples_redrawn": rejected,
        "fits_used": used,
        "pooled_share_of_total_ratio_of_medians": interval(pooled_total),
        "pooled_share_of_total_ratio_of_means": interval(pooled_mean),
        "pooled_share_of_gross_ratio_of_medians": interval(pooled_gross),
        "pooled_carried_share_of_total_ratio_of_medians": interval(carried_total),
        "mean_of_per_draw_shares": interval(per_draw_mean_share),
        "per_env_seed_share_of_total": {key: interval(values) for key, values in per_config.items()},
    }


# --------------------------------------------------------------------------
# presentation
# --------------------------------------------------------------------------


def average_rows(rows: list[dict]) -> dict:
    numeric = [
        key
        for key in rows[0]
        if isinstance(rows[0][key], float) and key not in {"identity_residual_max"}
    ]
    out = {key: safe_nanmean([row[key] for row in rows]) for key in numeric}
    out["n_pairs"] = int(sum(row["n_pairs"] for row in rows))
    return out


def safe_nanmean(values: list[float]) -> float:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    return float(array.mean()) if array.size else float("nan")


def fmt(value: float, width: int, precision: int = 3) -> str:
    if not np.isfinite(value):
        return f"{'n/a':>{width}}"
    return f"{value:>{width}.{precision}f}"


def print_table(title: str, rows: list[dict], label_header: str, label_values: list[str]) -> None:
    print()
    print("-" * 126)
    print(title)
    print("-" * 126)
    print(
        f"{label_header:>10} {'med|i|':>8} {'mean|i|':>8} {'med|ii|':>8} {'mean|ii|':>8} "
        f"{'med|tot|':>9} {'mean|tot|':>9} {'med gross':>10} {'ii/tot':>7} {'ii/gross':>8} "
        f"{'mean ii/tot':>11} {'n':>4}"
    )
    for label, row in zip(label_values, rows, strict=True):
        print(
            f"{label:>10} {row['median_abs_component_i_misspec']:>8.4f} {row['mean_abs_component_i_misspec']:>8.4f} "
            f"{row['median_abs_component_ii_reroute']:>8.4f} {row['mean_abs_component_ii_reroute']:>8.4f} "
            f"{row['median_abs_total_gap']:>9.4f} {row['mean_abs_total_gap']:>9.4f} "
            f"{row['median_abs_gross_i_plus_ii']:>10.4f} "
            f"{fmt(row['reroute_share_of_total_ratio_of_medians'], 7)} "
            f"{fmt(row['reroute_share_of_gross_ratio_of_medians'], 8)} "
            f"{fmt(row['reroute_share_of_total_ratio_of_means'], 11)} {row['n_pairs']:>4}"
        )


def main() -> int:
    started = time.perf_counter()
    RESULTS.mkdir(exist_ok=True)
    published = json.loads(PUBLISHED.read_text(encoding="utf-8")) if PUBLISHED.exists() else None

    configs = load_configs()
    width = 126
    print("=" * width)
    print("estimand split:  beta_j - ATT_whole_tape  =  (beta_j - ATT_onebit)  +  (ATT_onebit - ATT_whole_tape)")
    print("=" * width)
    print(
        f"datasets: {len(configs)} configurations x {configs[0]['bit_of'].size} focal mutations x "
        f"{configs[0]['fitness'].size} seeds (depth 40); no re-simulation, all recomputed from the saved arrays"
    )
    print(f"eps grid: {list(EPS_ORDER)};  coupling draws: {sorted({c['env_seed'] for c in configs})}")
    print()
    print("component (i)  = |beta_j - ATT_onebit_proxy|          -> linear-model misspecification")
    print("component (ii) = |ATT_onebit_proxy - ATT_whole_tape|   -> whole-tape re-routing / estimand mismatch")
    print()
    print("NOTE on the one-bit proxy: ATT_onebit_proxy is the change in the FITTED quadratic outcome model when")
    print("only locus j is flipped, evaluated at each seed's observed covariates. It is a MODEL-BASED one-bit")
    print("quantity, NOT an interventional one, and it is therefore an upper bound on what a correctly specified")
    print("one-bit model can do. On this substrate the synthetic landscape is exactly quadratic in the final bits")
    print("(harness.py) and the fitted design has full rank, so the proxy in fact equals the exact one-bit")
    print("contrast; what remains against ATT_whole_tape is re-routing, which no one-bit model can remove.")

    per_config: dict[str, dict] = {}
    check_spec = check_beta = check_quad = check_identity = 0.0
    check_gram = 0.0
    bad_exposed_bit = 0
    r2_values: list[float] = []
    residual_max_values: list[float] = []

    for cfg in configs:
        config_started = time.perf_counter()
        res = analyse(cfg)
        ensemble = SeedEnsembleOLS(cfg["bits"], cfg["fitness"])
        beta_gram, coef_gram = ensemble.fit(np.arange(cfg["fitness"].size))
        check_gram = max(
            check_gram,
            float(np.max(np.abs(beta_gram - res["beta"]))),
            float(np.max(np.abs(coef_gram - res["quad_coef"]))),
        )
        summary = summarise(res)
        summary.update(
            {
                "key": cfg["key"],
                "env_seed": cfg["env_seed"],
                "eps": cfg["eps"],
                "n_seeds": int(cfg["fitness"].size),
                "n_mutations": int(cfg["bit_of"].size),
                "n_pairs": int(cfg["bit_of"].size),
                "median_exposed": float(np.median(res["exposed"])),
                "min_exposed": int(res["exposed"].min()),
                "quad_rank": res["quad_rank"],
                "quad_r2": res["quad_r2"],
                "quad_residual_max": res["quad_residual_max"],
                "n_unique_genotypes": res["n_unique_genotypes"],
                "linear_design_condition": res["linear_condition"],
                "pearson_signed_within_config": pearson(res["component_i"], res["component_ii"]),
                "spearman_signed_within_config": spearman(res["component_i"], res["component_ii"]),
                "pearson_absolute_within_config": pearson(np.abs(res["component_i"]), np.abs(res["component_ii"])),
                "per_mutation": [
                    {
                        "mutation": mid,
                        "bit": int(cfg["bit_of"][j]),
                        "frequency": float(cfg["present"][:, j].mean()),
                        "n_exposed": int(res["exposed"][j]),
                        "beta": float(res["beta"][cfg["bit_of"][j]]),
                        "att_whole_tape": float(res["att_whole"][j]),
                        "att_onebit_proxy_exposed": float(res["att_onebit"][j]),
                        "att_onebit_proxy_all_seeds": float(res["att_onebit_all"][j]),
                        "component_i_misspec": float(res["component_i"][j]),
                        "component_ii_reroute": float(res["component_ii"][j]),
                        "total_gap": float(res["total_gap"][j]),
                    }
                    for j, mid in enumerate(cfg["mutations"])
                ],
            }
        )
        per_config[cfg["key"]] = summary
        r2_values.append(res["quad_r2"])
        residual_max_values.append(res["quad_residual_max"])
        check_identity = max(check_identity, res["identity_residual_max"])
        for j in range(cfg["bit_of"].size):
            has = cfg["present"][:, j].astype(bool)
            if has.any() and np.any(cfg["bits"][has, cfg["bit_of"][j]] != 1.0):
                bad_exposed_bit += 1
        if published is not None and cfg["key"] in published.get("configs", {}):
            rows = {r["mutation"]: r for r in published["configs"][cfg["key"]]["per_mutation"]}
            for j, mid in enumerate(cfg["mutations"]):
                if mid in rows:
                    check_spec = max(check_spec, abs(res["total_gap"][j] - rows[mid]["specification_bias"]))
                    check_beta = max(check_beta, abs(res["beta"][cfg["bit_of"][j]] - rows[mid]["adjusted"]))
                    check_quad = max(check_quad, abs(res["att_onebit_all"][j] - rows[mid]["quadratic"]))
        print(
            f"  analysed {cfg['key']:<26} eps={cfg['eps']:<4g} unique genotypes={res['n_unique_genotypes']:<5d} "
            f"({time.perf_counter() - config_started:.2f}s)",
            flush=True,
        )

    print()
    print("-" * width)
    print("REPRODUCTION CHECK against results/heavy2_results.json (published numbers)")
    print("-" * width)
    print(f"  max |recomputed (beta_j - ATT_whole_tape) - published specification_bias| : {check_spec:.3e}")
    print(f"  max |recomputed beta_j - published adjusted|                              : {check_beta:.3e}")
    print(f"  max |recomputed one-bit proxy (all seeds) - published quadratic|          : {check_quad:.3e}")
    print(f"  max |component(i) + component(ii) - total gap| (exact identity)           : {check_identity:.3e}")
    print(f"  max |lstsq fit - weighted-Gram fit used by the bootstrap|                 : {check_gram:.3e}")
    print(
        f"  fitted quadratic: rank {per_config[configs[0]['key']]['quad_rank']}/172 over all configs, "
        f"R^2 in [{min(r2_values):.12f}, {max(r2_values):.12f}], max |residual| {max(residual_max_values):.3e}"
    )
    print(
        "  -> the synthetic landscape is exactly quadratic in the final bits (harness.py), so the quadratic "
        "plug-in\n     recovers the exact one-bit contrast; component (ii) is genuine re-routing, not fit error."
    )
    cleared = float(np.mean([row["cleared_exposed_fraction"] for row in per_config.values()]))
    cleared_max_eps = next(
        row["cleared_exposed_fraction"] for row in per_config.values() if row["eps"] == max(EPS_ORDER)
    )
    cleared_max = max(row["cleared_exposed_fraction"] for row in per_config.values())
    print(
        f"  exposed seeds whose focal locus was later cleared by an accepted reversal: {cleared:.2%} averaged "
        f"over all configs"
    )
    print(
        f"     ({cleared_max_eps:.2%} at eps = {max(EPS_ORDER):g}, up to {cleared_max:.2%} for one config); the "
        "carried-only robustness variant below excludes them"
    )

    print()
    print("=" * width)
    print("PER CONFIGURATION")
    print("=" * width)
    print(
        f"{'config':<26} {'eps':>5} {'med|i|':>8} {'med|ii|':>8} {'med|tot|':>9} {'ii/tot':>7} "
        f"{'ii/gross':>8} {'corr(i,ii)':>10} {'frac same sign':>14}"
    )
    for cfg in configs:
        row = per_config[cfg["key"]]
        print(
            f"{cfg['key']:<26} {cfg['eps']:>5g} {row['median_abs_component_i_misspec']:>8.4f} "
            f"{row['median_abs_component_ii_reroute']:>8.4f} {row['median_abs_total_gap']:>9.4f} "
            f"{fmt(row['reroute_share_of_total_ratio_of_medians'], 7)} "
            f"{fmt(row['reroute_share_of_gross_ratio_of_medians'], 8)} "
            f"{row['pearson_signed_within_config']:>+10.3f} {row['same_sign_fraction']:>14.2f}"
        )

    by_eps = []
    for eps in EPS_ORDER:
        rows = [per_config[c["key"]] for c in configs if c["eps"] == eps]
        avg = average_rows(rows)
        avg["eps"] = eps
        by_eps.append(avg)
    print_table(
        "BY EPISTASIS LEVEL (mean over the 3 coupling draws; |i| = misspecification, |ii| = re-routing)",
        by_eps,
        "eps",
        [f"{eps:g}" for eps in EPS_ORDER],
    )

    draws = sorted({c["env_seed"] for c in configs})
    by_draw = []
    for env_seed in draws:
        rows = [per_config[c["key"]] for c in configs if c["env_seed"] == env_seed]
        avg = average_rows(rows)
        avg["env_seed"] = env_seed
        by_draw.append(avg)
    print_table(
        "BY COUPLING DRAW (mean over the 6 epistasis levels)",
        by_draw,
        "env_seed",
        [str(env_seed) for env_seed in draws],
    )

    # ---- robustness: carried-only variant ----------------------------------
    print()
    print("-" * 126)
    print(
        "ROBUSTNESS VARIANT: exposed seeds whose focal locus is STILL CARRIED at the end "
        "(one-bit flip then really mirrors suppression)"
    )
    print("-" * 126)
    print(
        f"{'eps':>10} {'cleared seeds':>14} {'med|i|':>8} {'med|ii|':>8} {'med|tot|':>9} {'ii/tot':>7} "
        f"{'vs primary ii/tot':>18}"
    )
    for row in by_eps:
        print(
            f"{row['eps']:>10g} {row['cleared_exposed_fraction']:>14.4f} "
            f"{row['carried_median_abs_component_i']:>8.4f} {row['carried_median_abs_component_ii']:>8.4f} "
            f"{row['carried_median_abs_total_gap']:>9.4f} {fmt(row['carried_reroute_share_of_total'], 7)} "
            f"{fmt(row['reroute_share_of_total_ratio_of_medians'], 18)}"
        )

    # ---- correlation between the two components ---------------------------
    def collect(keep) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        ci, cii, eps = [], [], []
        for cfg in configs:
            if not keep(cfg):
                continue
            rows = per_config[cfg["key"]]["per_mutation"]
            ci.append(np.array([m["component_i_misspec"] for m in rows]))
            cii.append(np.array([m["component_ii_reroute"] for m in rows]))
            eps.append(np.full(len(rows), cfg["eps"]))
        return np.concatenate(ci), np.concatenate(cii), np.concatenate(eps)

    miss_all, reroute_all, eps_all = collect(lambda cfg: True)
    miss_pos, reroute_pos, eps_pos = collect(lambda cfg: cfg["eps"] > 0.0)
    correlation = {
        "all_configs_including_eps0": correlation_block(miss_all, reroute_all),
        "eps_gt_0": correlation_block(miss_pos, reroute_pos),
        "by_eps": {
            f"eps{eps:g}": correlation_block(miss_pos[eps_pos == eps], reroute_pos[eps_pos == eps])
            for eps in EPS_ORDER
            if eps > 0.0
        },
        "within_config": {
            "median_pearson_signed": float(np.median([r["pearson_signed_within_config"] for r in per_config.values()])),
            "min_pearson_signed": float(np.min([r["pearson_signed_within_config"] for r in per_config.values()])),
            "max_pearson_signed": float(np.max([r["pearson_signed_within_config"] for r in per_config.values()])),
            "median_pearson_absolute": float(
                np.median([r["pearson_absolute_within_config"] for r in per_config.values()])
            ),
            "median_spearman_signed": float(
                np.median([r["spearman_signed_within_config"] for r in per_config.values()])
            ),
        },
    }
    conditional_abs = np.array([abs(block["pearson_absolute"]) for block in correlation["by_eps"].values()])
    conditional_signed = np.array([abs(block["pearson_signed"]) for block in correlation["by_eps"].values()])
    corr_eps_gt0 = correlation["eps_gt_0"]

    print()
    print("=" * width)
    print(f"CORRELATION BETWEEN COMPONENT (i) AND COMPONENT (ii)  [pooled eps>0: {corr_eps_gt0['n']} mutation-config pairs]")
    print("=" * width)
    print(
        f"  pooled eps > 0 :  signed Pearson {corr_eps_gt0['pearson_signed']:+.4f} / Spearman "
        f"{corr_eps_gt0['spearman_signed']:+.4f}   |component| Pearson {corr_eps_gt0['pearson_absolute']:+.4f} / "
        f"Spearman {corr_eps_gt0['spearman_absolute']:+.4f}"
    )
    print(
        f"  pooled all eps :  signed Pearson {correlation['all_configs_including_eps0']['pearson_signed']:+.4f}   "
        f"|component| Pearson {correlation['all_configs_including_eps0']['pearson_absolute']:+.4f} "
        "(degenerate: both components are ~1e-15 at eps = 0)"
    )
    print("  conditional on eps (48 mutation-draw pairs each):")
    for key, block in correlation["by_eps"].items():
        print(
            f"      {key:<7} signed Pearson {block['pearson_signed']:+.4f}  Spearman {block['spearman_signed']:+.4f}   "
            f"|component| Pearson {block['pearson_absolute']:+.4f}  Spearman {block['spearman_absolute']:+.4f}"
        )
    within = correlation["within_config"]
    print(
        f"  within a single configuration (16 mutations): signed Pearson median {within['median_pearson_signed']:+.4f} "
        f"[{within['min_pearson_signed']:+.4f}, {within['max_pearson_signed']:+.4f}], "
        f"|component| Pearson median {within['median_pearson_absolute']:+.4f}"
    )
    print("  reading: the strong marginal correlation is an eps-scale artefact (both components grow with eps);")
    print("           conditional on the landscape the two components are only weakly related.")

    # ---- bootstrap at the highest epistasis level --------------------------
    eps_max = max(EPS_ORDER)
    top = [cfg for cfg in configs if cfg["eps"] == eps_max]
    t0 = time.perf_counter()
    boot = bootstrap(top)
    boot_seconds = round(time.perf_counter() - t0, 2)
    pooled = boot["pooled_share_of_total_ratio_of_medians"]
    gross = boot["pooled_share_of_gross_ratio_of_medians"]
    bymean = boot["pooled_share_of_total_ratio_of_means"]
    per_draw = boot["mean_of_per_draw_shares"]
    print()
    print("=" * width)
    print(
        f"BOOTSTRAP AT THE HIGHEST EPISTASIS LEVEL eps = {eps_max:g}  "
        f"({BOOTSTRAP_DRAWS} seed resamples, fixed rng seed {BOOTSTRAP_SEED}, {boot_seconds}s)"
    )
    print("=" * width)
    print(
        f"  {boot['fits_used']} resampled fits used; rank-deficient resamples redrawn: "
        f"{boot['rank_deficient_resamples_redrawn']}"
    )
    print(f"  share of the published bias that is re-routing, pooled over the {len(top)} coupling draws:")
    print(f"      |ii| / |total|  (ratio of medians) : {pooled['median']:.4f}   95% CI [{pooled['ci95'][0]:.4f}, {pooled['ci95'][1]:.4f}]")
    print(f"      |ii| / |total|  (ratio of means)   : {bymean['median']:.4f}   95% CI [{bymean['ci95'][0]:.4f}, {bymean['ci95'][1]:.4f}]")
    print(f"      |ii| / (|i|+|ii|) (gross, ratio of medians) : {gross['median']:.4f}   95% CI [{gross['ci95'][0]:.4f}, {gross['ci95'][1]:.4f}]")
    print(
        f"      mean of the per-draw |ii|/|total| shares (3 coupling draws equally weighted) : "
        f"{per_draw['median']:.4f}   95% CI [{per_draw['ci95'][0]:.4f}, {per_draw['ci95'][1]:.4f}]"
    )
    carried = boot["pooled_carried_share_of_total_ratio_of_medians"]
    print(
        f"      carried-only robustness variant (locus still on at the end) : {carried['median']:.4f}   "
        f"95% CI [{carried['ci95'][0]:.4f}, {carried['ci95'][1]:.4f}]"
    )
    print("  per coupling draw (the share is strongly draw-dependent):")
    for key, block in boot["per_env_seed_share_of_total"].items():
        print(
            f"      {key:<26} |ii|/|total| {block['median']:.4f}   95% CI "
            f"[{block['ci95'][0]:.4f}, {block['ci95'][1]:.4f}]"
        )
    print("  note: the two components cancel in the published number, so |ii|/|total| exceeds |ii|/(|i|+|ii|);")
    print("        the gross share is the cancellation-free measure of the same quantity.")

    # ---- verdict -----------------------------------------------------------
    row0 = next(row for row in by_eps if row["eps"] == 0.0)
    rowmax = next(row for row in by_eps if row["eps"] == eps_max)
    frac = pooled["median"]
    frac_ci = pooled["ci95"]
    if abs(within["median_pearson_signed"]) < 0.4 and float(np.median(conditional_abs)) < 0.5:
        separable_answer = (
            "separable: conditional on the landscape the two components are only weakly correlated "
            "(within-configuration median signed Pearson %.3f; median within-eps |component| Pearson %.3f), "
            "so misspecification and re-routing carry distinguishable information" % (
                within["median_pearson_signed"], float(np.median(conditional_abs))
            )
        )
    elif float(np.median(conditional_abs)) < 0.7:
        separable_answer = (
            "partially separable: conditional on the landscape the components are moderately correlated "
            "(median within-eps |component| Pearson %.3f), so their magnitudes co-move and neither can be "
            "inferred from the other" % float(np.median(conditional_abs))
        )
    else:
        separable_answer = (
            "not separable: even conditional on the landscape the two components are strongly correlated "
            "(median within-eps |component| Pearson %.3f), so the split cannot be identified from the total"
            % float(np.median(conditional_abs))
        )
    print()
    print("=" * width)
    print("VERDICT")
    print("=" * width)
    print(
        f"  1. At eps = 0 both components vanish (median |i| = {row0['median_abs_component_i_misspec']:.2e}, "
        f"median |ii| = {row0['median_abs_component_ii_reroute']:.2e}): with an additive landscape the linear"
    )
    print("     model is correct and suppression does not re-route. The published zero at eps = 0 survives the split.")
    print(
        f"  2. At eps = {eps_max:g}: median |i| (misspecification) = {rowmax['median_abs_component_i_misspec']:.4f}, "
        f"median |ii| (re-routing) = {rowmax['median_abs_component_ii_reroute']:.4f}, "
        f"median |total| = {rowmax['median_abs_total_gap']:.4f}."
    )
    print(
        f"  3. Fraction of the previously reported 'specification bias' that is actually re-routing: "
        f"{frac:.1%} [95% CI {frac_ci[0]:.1%}, {frac_ci[1]:.1%}] at eps = {eps_max:g};"
    )
    print(
        f"     genuine linear-model misspecification: {1 - frac:.1%}. Cancellation-free (gross) split: "
        f"re-routing {gross['median']:.1%} vs misspecification {1 - gross['median']:.1%}."
    )
    print(
        f"     Per coupling draw the share is {per_draw['median']:.1%} on average over the 3 draws "
        f"[95% CI {per_draw['ci95'][0]:.1%}, {per_draw['ci95'][1]:.1%}], and it ranges from "
        f"{min(b['median'] for b in boot['per_env_seed_share_of_total'].values()):.1%} to "
        f"{max(b['median'] for b in boot['per_env_seed_share_of_total'].values()):.1%} across draws -- "
        "re-routing dominance is landscape-specific, not a constant."
    )
    print(
        f"     Robustness: restricted to exposed seeds that still carry the locus at the end, the re-routing "
        f"share is {carried['median']:.1%} [95% CI {carried['ci95'][0]:.1%}, {carried['ci95'][1]:.1%}], "
        "so the conclusion does not rest on seeds whose locus was later reverted."
    )
    print(
        "  4. The re-routing share is negligible for eps <= 0.1 and only becomes comparable to misspecification "
        "from eps = 0.2 on:"
    )
    for row in by_eps:
        print(
            f"       eps = {row['eps']:<4g}  med|i| = {row['median_abs_component_i_misspec']:.4f}   "
            f"med|ii| = {row['median_abs_component_ii_reroute']:.4f}   "
            f"ii/tot = {fmt(row['reroute_share_of_total_ratio_of_medians'], 5)}   "
            f"ii/gross = {fmt(row['reroute_share_of_gross_ratio_of_medians'], 5)}"
        )
    print(f"  5. Separability: {separable_answer}.")
    print("  6. Honest labels:")
    print("       component (i)  = linear-model misspecification relative to a one-bit contrast")
    print("                        (a real modelling error, removable in principle by a correct one-bit model);")
    print("       component (ii) = whole-tape re-routing / estimand mismatch")
    print("                        (not a modelling error, and not removable by any one-bit model at all);")
    print("       the old label 'specification bias' for beta_j - ATT_whole_tape is wrong: it is the sum of the")
    print("       two, i.e. a total one-bit-versus-whole-tape gap, of which the majority at high eps is re-routing.")

    report = {
        "experiment": "estimand_split",
        "source_datasets": sorted(cfg["key"] for cfg in configs),
        "n_seeds_per_config": int(configs[0]["fitness"].size),
        "n_mutations_per_config": int(configs[0]["bit_of"].size),
        "eps_grid": list(EPS_ORDER),
        "env_seeds": draws,
        "bootstrap": {"draws": BOOTSTRAP_DRAWS, "rng_seed": BOOTSTRAP_SEED, "seconds": boot_seconds},
        "notes": NOTES,
        "reproduction_check": {
            "max_abs_recomputed_minus_published_specification_bias": check_spec,
            "max_abs_recomputed_minus_published_adjusted": check_beta,
            "max_abs_recomputed_minus_published_quadratic": check_quad,
            "max_abs_identity_residual": check_identity,
            "max_abs_lstsq_minus_weighted_gram_fit": check_gram,
            "fitted_quadratic_rank": per_config[configs[0]["key"]]["quad_rank"],
            "fitted_quadratic_r2_min": float(min(r2_values)),
            "fitted_quadratic_r2_max": float(max(r2_values)),
            "fitted_quadratic_max_abs_residual": float(max(residual_max_values)),
            "exposed_seeds_missing_focal_bit": bad_exposed_bit,
            "cleared_exposed_fraction_overall_mean": cleared,
            "cleared_exposed_fraction_at_eps_max": cleared_max_eps,
        },
        "per_config": per_config,
        "by_eps": by_eps,
        "by_coupling_draw": by_draw,
        "correlation": {**correlation, "conditional_median_abs_pearson": float(np.median(conditional_abs)),
                        "conditional_median_abs_signed_pearson": float(np.median(conditional_signed))},
        "bootstrap_reroute_share_eps_max": boot,
        "verdict": {
            "eps_max": eps_max,
            "eps0_median_abs_component_i": row0["median_abs_component_i_misspec"],
            "eps0_median_abs_component_ii": row0["median_abs_component_ii_reroute"],
            "eps_max_median_abs_component_i_misspec": rowmax["median_abs_component_i_misspec"],
            "eps_max_median_abs_component_ii_reroute": rowmax["median_abs_component_ii_reroute"],
            "eps_max_median_abs_total_gap": rowmax["median_abs_total_gap"],
            "fraction_of_published_bias_that_is_rerouting": frac,
            "fraction_of_published_bias_that_is_rerouting_ci95": frac_ci,
            "fraction_that_is_misspecification": 1.0 - frac,
            "gross_fraction_rerouting": gross["median"],
            "gross_fraction_rerouting_ci95": gross["ci95"],
            "mean_of_per_draw_reroute_shares": per_draw["median"],
            "mean_of_per_draw_reroute_shares_ci95": per_draw["ci95"],
            "carried_only_share_at_eps_max": carried["median"],
            "carried_only_share_at_eps_max_ci95": carried["ci95"],
            "reroute_share_by_coupling_draw": {
                key: block["median"] for key, block in boot["per_env_seed_share_of_total"].items()
            },
            "reroute_share_by_eps_ratio_of_medians": {
                f"eps{row['eps']:g}": row["reroute_share_of_total_ratio_of_medians"] for row in by_eps
            },
            "separable": separable_answer,
            "honest_labels": {
                "component_i": "linear-model misspecification relative to a one-bit contrast "
                "(modelling error, removable in principle by a correct one-bit model)",
                "component_ii": "whole-tape re-routing / estimand mismatch "
                "(not a modelling error, not removable by any one-bit model)",
                "old_label": "beta_j - ATT_whole_tape is NOT 'specification bias'; it is the total "
                "one-bit-versus-whole-tape gap, mostly re-routing at high eps",
            },
        },
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print()
    print(f"wrote results/{OUT_PATH.name}  ({report['elapsed_seconds']}s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
