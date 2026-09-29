"""R2 red-team probe: actual coverage of the design's two-level percentile bootstrap.

Generative model calibrated to heavy1 G40 (per-env S(eps) trend, mutation-level
spread of |bias|, between-env spread of the eps-slope).
Target: the eps-slope of E_e[S(eps)] under the coupling-draw generator.
"""
from __future__ import annotations

import numpy as np

EPS = np.array([0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6, 0.8])
XC = EPS - EPS.mean()
XD = float(XC @ XC)
S_BAR = np.array([0.0, 0.00261, 0.00652, 0.01303, 0.03322, 0.22690, 0.34360, 0.74455, 1.02359])
T = {10: 2.262, 20: 2.093, 40: 2.023, 100: 1.984}


def slope(y):
    return (XC @ y) / XD


def gen(rng, E, M, tau, sm, sn):
    u = rng.normal(0, tau, size=(E, 1, 1))
    m = rng.normal(0, sm, size=(1, M, 1))
    n = rng.normal(0, sn, size=(E, M, len(EPS)))
    return np.abs(S_BAR.reshape(1, 1, -1) * np.exp(u + m + n))


def boot(v, rng, B=300):
    E, M, K = v.shape
    out = np.empty(B)
    for b in range(B):
        ei = rng.integers(0, E, E)
        mi = rng.integers(0, M, M)
        sub = v[np.ix_(ei, mi, np.arange(K))]
        out[b] = slope(np.median(sub, axis=1).mean(axis=0))
    return out


def main():
    rng = np.random.default_rng(7)
    big = gen(rng, 5000, 400, 0.35, 0.6, 0.15)
    target = float(slope(np.median(big, axis=(0, 1))))
    print(f"generator slope target = {target:.4f}", flush=True)
    for E in (10, 20, 40, 100):
        for M in (8, 24):
            reps, hp, ht, w = 300, 0, 0, []
            for _ in range(reps):
                v = gen(rng, E, M, 0.35, 0.6, 0.15)
                lo, hi = np.percentile(boot(v, rng), [2.5, 97.5])
                w.append(hi - lo)
                hp += lo <= target <= hi
                pe = np.array([slope(np.median(v[e], axis=0)) for e in range(E)])
                se = pe.std(ddof=1) / np.sqrt(E)
                ht += abs(pe.mean() - target) <= T[E] * se
            print(f"E={E:>3} M={M:>2}  pct-boot cov={hp/reps:.3f}  t-interval cov={ht/reps:.3f}  median CI width={np.median(w):.4f}", flush=True)


if __name__ == "__main__":
    main()
