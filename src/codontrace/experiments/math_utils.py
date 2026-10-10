"""Mathematical, statistical, and PRNG foundations for scientific experiments."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass


def sha_prng_float(seed: int, step: int, salt: str) -> float:
    """Cryptographic deterministic float in [0.0, 1.0) with salt separation."""
    data = f"{int(seed)}:{int(step)}:{salt}".encode()
    digest = hashlib.sha256(data).digest()
    return int.from_bytes(digest[:4], "big") / 4294967296.0


def sha_prng_int(seed: int, step: int, salt: str, min_val: int, max_val: int) -> int:
    """Cryptographic deterministic integer in [min_val, max_val] inclusive."""
    if max_val < min_val:
        raise ValueError(f"max_val ({max_val}) must be >= min_val ({min_val})")
    span = max_val - min_val + 1
    val_float = sha_prng_float(seed, step, salt)
    return min_val + int(val_float * span) % span


@dataclass(frozen=True, slots=True)
class PriceEquationAccounting:
    """Exact discrete generation Price equation decomposition."""
    mean_w: float
    mean_z_parent: float
    mean_z_offspring: float
    delta_z_observed: float
    covariance_selection: float
    transmission_bias: float
    price_predicted_delta_z: float
    identity_residual: float
    between_group_term: float
    within_group_term: float

    @property
    def is_identity_exact(self) -> bool:
        return abs(self.identity_residual) < 1e-7


def compute_exact_price_equation(
    parents_z: Sequence[float],
    offspring_counts: Sequence[int],
    offspring_mean_z: Sequence[float],
    deme_ids: Sequence[int] | None = None,
) -> PriceEquationAccounting:
    """Computes exact Price equation terms and verifies mathematical identity.
    
    Formula:
      Delta bar(z) = Cov(w, z) / bar(w) + E[w * (z' - z)] / bar(w)
      where:
        w_i = realized offspring count of parent i
        z_i = trait value of parent i
        z'_i = mean trait value of offspring of parent i (or z_i if w_i == 0)
    """
    n = len(parents_z)
    if n == 0 or len(offspring_counts) != n or len(offspring_mean_z) != n:
        raise ValueError("Inputs must be non-empty and of identical length.")

    total_offspring = sum(offspring_counts)
    if total_offspring == 0:
        return PriceEquationAccounting(
            mean_w=0.0,
            mean_z_parent=sum(parents_z) / n,
            mean_z_offspring=0.0,
            delta_z_observed=0.0,
            covariance_selection=0.0,
            transmission_bias=0.0,
            price_predicted_delta_z=0.0,
            identity_residual=0.0,
            between_group_term=0.0,
            within_group_term=0.0,
        )

    mean_w = total_offspring / n
    mean_z = sum(parents_z) / n

    # Offspring population mean trait
    weighted_offspring_z_sum = sum(
        w * z_prime for w, z_prime in zip(offspring_counts, offspring_mean_z, strict=True)
    )
    mean_z_prime = weighted_offspring_z_sum / total_offspring
    delta_z_observed = mean_z_prime - mean_z

    # Covariance(w, z) = E[w*z] - E[w]*E[z]
    e_wz = sum(w * z for w, z in zip(offspring_counts, parents_z, strict=True)) / n
    cov_w_z = e_wz - (mean_w * mean_z)
    selection_term = cov_w_z / mean_w

    # Transmission bias: E[w * (z' - z)] / bar(w)
    bias_sum = sum(
        w * (z_prime - z)
        for w, z, z_prime in zip(offspring_counts, parents_z, offspring_mean_z, strict=True)
    )
    transmission_term = bias_sum / total_offspring

    price_predicted = selection_term + transmission_term
    residual = delta_z_observed - price_predicted

    # Multilevel decomposition if demes provided
    between_group = 0.0
    within_group = 0.0
    if deme_ids is not None and len(deme_ids) == n:
        demes = sorted(set(deme_ids))
        deme_sizes: dict[int, int] = {d: 0 for d in demes}
        deme_w_sum: dict[int, int] = {d: 0 for d in demes}
        deme_z_sum: dict[int, float] = {d: 0.0 for d in demes}

        for d, w, z in zip(deme_ids, offspring_counts, parents_z, strict=True):
            deme_sizes[d] += 1
            deme_w_sum[d] += w
            deme_z_sum[d] += z

        deme_w_mean = {d: deme_w_sum[d] / max(1, deme_sizes[d]) for d in demes}
        deme_z_mean = {d: deme_z_sum[d] / max(1, deme_sizes[d]) for d in demes}

        # Between-deme covariance: Cov(W_k, Z_k) / bar(W)
        num_demes = len(demes)
        mean_W = sum(deme_w_mean.values()) / num_demes
        mean_Z = sum(deme_z_mean.values()) / num_demes
        e_WZ = sum(deme_w_mean[d] * deme_z_mean[d] for d in demes) / num_demes
        cov_W_Z = e_WZ - (mean_W * mean_Z)
        between_group = cov_W_Z / max(1e-12, mean_W)
        within_group = selection_term - between_group

    return PriceEquationAccounting(
        mean_w=mean_w,
        mean_z_parent=mean_z,
        mean_z_offspring=mean_z_prime,
        delta_z_observed=delta_z_observed,
        covariance_selection=selection_term,
        transmission_bias=transmission_term,
        price_predicted_delta_z=price_predicted,
        identity_residual=residual,
        between_group_term=between_group,
        within_group_term=within_group,
    )


def compute_functional_information(
    num_successes: int,
    total_samples: int,
    confidence_level: float = 0.95,
) -> tuple[float, float, float]:
    """Computes Hazen functional information bits: I(E) = -log2(F(E)).
    
    Returns:
      (point_estimate_bits, lower_bound_bits, upper_bound_bits)
    """
    if total_samples <= 0:
        raise ValueError("total_samples must be positive.")
    if num_successes < 0 or num_successes > total_samples:
        raise ValueError("num_successes must be between 0 and total_samples.")

    if num_successes == 0:
        # Rule of Three / Exact Binomial upper bound on fraction F
        alpha = 1.0 - confidence_level
        p_upper = 1.0 - (alpha ** (1.0 / total_samples))
        point_bits = math.inf
        lower_bound_bits = -math.log2(max(1e-15, p_upper))
        upper_bound_bits = math.inf
        return (point_bits, lower_bound_bits, upper_bound_bits)

    fraction = num_successes / total_samples
    point_bits = -math.log2(fraction)

    # Standard normal approximation for binomial proportion CI
    z = 1.96 if confidence_level == 0.95 else 2.576
    se = math.sqrt((fraction * (1.0 - fraction)) / total_samples)
    p_low = max(1e-12, fraction - z * se)
    p_high = min(1.0, fraction + z * se)

    # Note that -log2 is monotonically decreasing: higher p => lower bits
    lower_bound_bits = -math.log2(p_high)
    upper_bound_bits = -math.log2(p_low)

    return (point_bits, lower_bound_bits, upper_bound_bits)


def compute_lag_contrast_matrix(
    timeshift_matrix: Sequence[Sequence[float]],
    lags: Sequence[int],
) -> dict[int, float]:
    """Computes mean performance contrast at positive vs negative time-shift lags."""
    n = len(timeshift_matrix)
    lag_values: dict[int, list[float]] = {lag: [] for lag in lags}

    for i in range(n):
        for j in range(n):
            lag = j - i
            if lag in lag_values:
                lag_values[lag].append(timeshift_matrix[i][j])

    contrasts: dict[int, float] = {}
    for lag, vals in lag_values.items():
        contrasts[lag] = sum(vals) / len(vals) if vals else 0.0

    return contrasts
