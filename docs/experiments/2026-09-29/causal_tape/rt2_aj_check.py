"""R2 red-team probe: does A_j(eps)=eps*E|c_j(x)| predict |specification_bias|?

Recomputes, for env 20260927 at G40, the natural tape and the 8 suppressed
counterfactual tapes for the focal set stored in heavy1_results.json, then
compares three quantities per focal mutation:
  bias_tape_j   = OLS beta_j - E[F(natural) - F(suppressed_j) | present]   (the stored estimand)
  bias_onebit_j = w_j + eps*E[c_j(x)|x_j=1]  computed on the natural final bits,
                  i.e. the immediate one-bit contrast against the SAME ensemble
  A_j(eps)      = eps*E[|c_j(x)|]  over the natural final bits (the design's predictor)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from harness import build_env, run_tape
from workers import Cfg

HERE = Path(__file__).resolve().parent
CFGS = json.loads((HERE / "results" / "heavy1_results.json").read_text(encoding="utf-8"))["configs"]
ENV_SEED = 20260927
DEPTH = 40
SEEDS = tuple(range(1000, 1300))


def run(eps: float) -> None:
    key = f"e{ENV_SEED}_eps{eps}_G{depth_label(eps)}"
    stored = {m["mutation"]: m for m in CFGS[key]["per_mutation"]}
    mids = list(stored)
    env = build_env(eps, env_seed=ENV_SEED)
    natural = {s: run_tape(seed=s, generations=DEPTH, env=env) for s in SEEDS}
    fit = np.array([natural[s].fitness for s in SEEDS])
    bits = np.array([natural[s].final_bits for s in SEEDS], dtype=float)
    design = np.hstack([np.ones((bits.shape[0], 1)), bits])
    beta = np.linalg.pinv(design) @ fit
    beta = beta[1:]
    J = np.asarray(env.couplings)
    w = np.asarray(env.weights)

    print(f"\n=== eps={eps} ({key}) n_seeds={len(SEEDS)} ===")
    rows = []
    for mid in mids:
        j = int(mid.split(":")[0])
        has = np.array([mid in natural[s].mutation_ids() for s in SEEDS], dtype=bool)
        counter = np.array(
            [
                run_tape(seed=s, generations=DEPTH, env=env, suppress=frozenset({mid})).fitness
                for s in SEEDS
            ]
        )
        att_tape = float(np.mean((fit - counter)[has]))
        bias_tape = float(beta[j] - att_tape)
        # ---- immediate one-bit contrast on the same natural ensemble -------------
        c = 0.5 * (bits @ J[j])  # c_j(x) = 0.5*sum_k J_jk x_k
        c_exposed = c[has]
        att_onebit = float(w[j] + eps * np.mean(2.0 * c_exposed))
        bias_onebit = float(beta[j] - att_onebit)
        A = float(eps * np.mean(np.abs(c)))
        # stored value, for a consistency check
        print(
            f"{mid:>8} freq={has.mean():.3f} "
            f"stored_bias={stored[mid]['specification_bias']:+.4f} "
            f"tape_bias={bias_tape:+.4f} onebit_bias={bias_onebit:+.4f} "
            f"A_j={A:.4f} eps*cbar={eps*np.mean(2*c):+.4f} "
            f"eps*E|c|(exposed)={eps*np.mean(np.abs(2*c_exposed)):.4f}"
        )
        rows.append((abs(bias_tape), abs(bias_onebit), A))

    y = np.array([r[0] for r in rows])
    y1 = np.array([r[1] for r in rows])
    A = np.array([r[2] for r in rows])
    for name, target in (("|bias_tape|", y), ("|bias_onebit|", y1)):
        slope, intercept = np.polyfit(A, target, 1)
        r = np.corrcoef(A, target)[0, 1] if A.std() > 0 and target.std() > 0 else float("nan")
        print(f"  regress {name} on A_j: slope={slope:.3f} intercept={intercept:+.4f} pearson_r={r:.3f} n={len(A)}")
    # exact closed form check on the one-bit estimand (residual should be ~0)
    exact = np.array([abs(beta[int(m.split(":")[0])] - (w[int(m.split(":")[0])] + eps * np.mean(2 * (0.5 * (bits @ J[int(m.split(":")[0])]))[np.array([m in natural[s].mutation_ids() for s in SEEDS], dtype=bool)]))) for m in mids])
    print(f"  corr(|bias_onebit|, A_j)={np.corrcoef(exact, A)[0,1]:.3f}")


def depth_label(eps: float) -> int:
    return DEPTH


if __name__ == "__main__":
    for e in (0.05, 0.2, 0.4, 0.8):
        run(e)
