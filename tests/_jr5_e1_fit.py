"""Reference E1 slope fit for the JR5 prereg (numpy only).

The bias-reduced fit maximises the binomial log likelihood plus half the log
determinant of the Fisher information. It is solved by Newton steps on the
modified score U + X^T (h * (1/2 - p)), with h the hat values, using the
Fisher information as the step matrix.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

TOL = 1e-10
MAX_ITER = 100

Array = NDArray[np.float64]


def fit_logit(k: Array, n: Array, x: Array, *, bias_reduced: bool, tol: float = TOL, max_iter: int = MAX_ITER) -> Array:
    """Return (intercept, slope) for counts k out of n against x."""
    design = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(max_iter):
        p = 1.0 / (1.0 + np.exp(-(design @ beta)))
        w = n * p * (1.0 - p)
        info = design.T @ (design * w[:, None])
        score = design.T @ (k - n * p)
        if bias_reduced:
            hat = w * np.einsum("ij,jk,ik->i", design, np.linalg.inv(info), design)
            score = score + design.T @ (hat * (0.5 - p))
        step = np.linalg.solve(info, score)
        beta = beta + step
        if float(np.max(np.abs(step))) < tol:
            return beta
    raise RuntimeError("fit did not converge")
