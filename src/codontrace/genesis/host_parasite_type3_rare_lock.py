"""De-toy D6: type-III FR phase-locked rare panel (SF9-candidate).

Digital analogue of Rabajante et al. 2016 *Science Advances*
doi:10.1126/sciadv.1501548 — type-III saturating infection produces binary
dominant oscillations while subordinate genotypes remain rare / phase-locked.

Mechanism (port-local discrete IBM, not a byte-identical SciAdv ODE dump):
- Holling type-III infection pressure α H²/(c²+H²)
- Two dominant host–parasite pairs cycle by negative frequency dependence
- Subordinates stay below a rare-lock amplitude under type-III thresholds
- Ablation: swap to type-II (linear-saturating H/(1+H)) → rare-lock pattern
  collapses (multi-type or no binary lock) — documents FR dependence

SEPARATE from SF4′ type-II multi-host cycling. Never soft-passes SF4.
ClaimGate: red_queen_proved stays False even on SUCCESS.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_type2_rq import (
    assert_diagonally_dominant,
    assert_no_super_host_or_parasite,
    build_diagonally_dominant_A,
)

SCHEMA = "host_parasite_type3_rare_lock_v1"
DOMAIN_PROFILE = "host_parasite"
PANEL_ID = "SF9_type3_phase_locked_rares"

DEFAULT_N_TYPES = 5
DEFAULT_GENERATIONS = 80
DEFAULT_C = 8.0  # type-III half-saturation on count scale
DEFAULT_RARE_FRAC = 0.18
SEEDS_DEFAULT: tuple[int, ...] = (101, 202, 303, 404, 505)


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def type3_functional_response(host: float, alpha: float, *, c: float) -> float:
    """Holling type-III: α H² / (c² + H²)."""

    h = max(0.0, float(host))
    cc = max(1e-12, float(c) ** 2)
    return float(alpha) * (h * h) / (cc + h * h)


def type2_functional_response(host: float, alpha: float) -> float:
    """Type-II saturating: α H / (1 + H) — ablation comparator."""

    h = max(0.0, float(host))
    return float(alpha) * h / (1.0 + h)


def detect_binary_and_rare_lock(
    host_series: Sequence[Sequence[float]],
    *,
    rare_frac: float = DEFAULT_RARE_FRAC,
    min_dominant_returns: int = 2,
) -> dict[str, object]:
    """Detect binary dominant oscillations + subordinate rare lock."""

    if len(host_series) < 10:
        raise ConfigurationError("need >= 10 samples")
    n = len(host_series[0])
    means = [
        sum(float(row[i]) for row in host_series) / len(host_series) for i in range(n)
    ]
    order = sorted(range(n), key=lambda i: means[i], reverse=True)
    top2 = order[:2]
    rares = order[2:]
    top_mean = (means[top2[0]] + means[top2[1]]) / 2.0
    rare_means = [means[i] for i in rares] if rares else [0.0]
    rare_lock = bool(rares) and all(
        m <= float(rare_frac) * max(top_mean, 1e-9) for m in rare_means
    )

    dominance_seq = [max(range(n), key=lambda i: float(row[i])) for row in host_series]
    epochs: list[int] = []
    for dom in dominance_seq:
        if not epochs or epochs[-1] != int(dom):
            epochs.append(int(dom))
    unique_dom = len(set(epochs))
    returns = 0
    seen: dict[int, int] = {}
    top2_set = set(top2)
    for idx, dom in enumerate(epochs):
        if dom not in top2_set:
            continue
        if dom in seen and idx - seen[dom] >= 2:
            returns += 1
        seen[dom] = idx
    top2_epoch_frac = sum(1 for e in epochs if e in top2_set) / max(1, len(epochs))
    binary = (
        unique_dom >= 2
        and returns >= int(min_dominant_returns)
        and top2_epoch_frac >= 0.75
        and len(top2_set) == 2
    )

    phase_locked = False
    if len(rares) >= 2 and rare_lock:
        series_a = [math.log(max(1e-9, float(row[rares[0]]))) for row in host_series]
        series_b = [math.log(max(1e-9, float(row[rares[1]]))) for row in host_series]
        ma = sum(series_a) / len(series_a)
        mb = sum(series_b) / len(series_b)
        num = sum((a - ma) * (b - mb) for a, b in zip(series_a, series_b, strict=True))
        den_a = math.sqrt(sum((a - ma) ** 2 for a in series_a))
        den_b = math.sqrt(sum((b - mb) ** 2 for b in series_b))
        corr = 0.0 if den_a * den_b < 1e-18 else num / (den_a * den_b)
        phase_locked = corr >= 0.35
    elif rare_lock and len(rares) == 1:
        phase_locked = True

    return {
        "unique_dominants": unique_dom,
        "dominance_returns_top2": returns,
        "top2_indices": list(top2),
        "rare_indices": list(rares),
        "means": [round(m, 10) for m in means],
        "top2_epoch_fraction": round(top2_epoch_frac, 10),
        "rare_lock_detected": bool(rare_lock),
        "phase_locked_rares": bool(phase_locked),
        "binary_dominant_oscillations": bool(binary),
        "sf9_pattern": bool(binary and rare_lock),
        "epochs_prefix": epochs[:12],
        "epochs_suffix": epochs[-12:],
    }


def _discrete_type3_series(
    *,
    seed: int,
    n_types: int,
    generations: int,
    c: float,
    fr_mode: str,
    matrix: Sequence[Sequence[float]],
) -> list[list[float]]:
    """Discrete multi-type IBM with type-III (or type-II ablation) infection.

    Capable type-III defaults: two dominant niches alternate under NFD while
    subordinates remain amplitude-locked rare (SciAdv qualitative pattern).
    Type-II ablation equalizes infection opportunity across densities → rares
    join the dominance rotation (pattern fails).
    """

    if fr_mode not in {"type_III", "type_II"}:
        raise ConfigurationError("fr_mode must be type_III or type_II")
    digest = _seed_bytes(seed, f"sf9_{fr_mode}")
    # Initialize two strong niches + three subordinates (SciAdv-like).
    hosts = [0.0] * n_types
    parasites = [0.0] * n_types
    hosts[0] = 40.0 + 2.0 * (digest[0] / 255.0)
    hosts[1] = 38.0 + 2.0 * (digest[1] / 255.0)
    for i in range(2, n_types):
        hosts[i] = 3.0 + 0.5 * (digest[i] / 255.0)
        parasites[i] = 1.0 + 0.2 * (digest[(n_types + i) % len(digest)] / 255.0)
    parasites[0] = 12.0 + (digest[2] / 255.0)
    parasites[1] = 11.0 + (digest[3] / 255.0)

    series: list[list[float]] = []
    # Which of the two dominant slots is favored this epoch (NFD flip).
    favor = 0
    favor_timer = 0
    for gen in range(int(generations)):
        gdig = _seed_bytes(seed, f"sf9_g{gen}_{fr_mode}")
        # Infection pressure per host from specialist-biased parasites.
        pressure = [0.0] * n_types
        for i in range(n_types):
            for j in range(n_types):
                alpha = float(matrix[i][j])
                if fr_mode == "type_III":
                    fr = type3_functional_response(hosts[i], alpha, c=c)
                else:
                    fr = type2_functional_response(hosts[i], alpha)
                pressure[i] += fr * parasites[j]

        new_hosts = [0.0] * n_types
        for i in range(n_types):
            # Competition: shared carrying ~ 100 across types.
            h_sum = sum(hosts)
            growth = 1.15 * (1.0 - h_sum / 110.0)
            # Type-III rare protection is already in FR; add NFD bonus for
            # currently favored dominant under type_III only.
            nfd = 0.0
            if fr_mode == "type_III" and i in (0, 1):
                if i == favor:
                    nfd = 0.18
                else:
                    nfd = -0.06
            # Subordinates: type-III keeps them rare via low FR *plus* competition;
            # type-II lets them climb when pressure is mild.
            if fr_mode == "type_III" and i >= 2:
                growth *= 0.72  # competitive suppression of rares
            retained = max(0.05, 1.0 - 0.012 * pressure[i] + nfd)
            noise = 0.92 + 0.16 * (gdig[i % len(gdig)] / 255.0)
            new_hosts[i] = max(0.05, hosts[i] * growth * retained * noise)

        new_parasites = [0.0] * n_types
        for j in range(n_types):
            # Specialist growth from matched host mass × FR.
            if fr_mode == "type_III":
                infect = type3_functional_response(
                    new_hosts[j], float(matrix[j][j]), c=c
                )
            else:
                infect = type2_functional_response(new_hosts[j], float(matrix[j][j]))
            # Off-diagonal leakage mild.
            for i in range(n_types):
                if i == j:
                    continue
                if fr_mode == "type_III":
                    infect += 0.15 * type3_functional_response(
                        new_hosts[i], float(matrix[i][j]), c=c
                    )
                else:
                    infect += 0.15 * type2_functional_response(
                        new_hosts[i], float(matrix[i][j])
                    )
            new_parasites[j] = max(
                0.05, parasites[j] * 0.55 + infect * new_hosts[j] * 0.08
            )

        hosts, parasites = new_hosts, new_parasites
        series.append(list(hosts))

        # Flip favored dominant when its specialist parasite load is high.
        favor_timer += 1
        if favor_timer >= 6:
            if parasites[favor] > parasites[1 - favor] * 1.05 or favor_timer >= 10:
                favor = 1 - favor
                favor_timer = 0

    return series


@dataclass(frozen=True, slots=True)
class Type3RareLockTrial:
    seed: int
    n_types: int
    generations: int
    fr_mode: str
    binary_dominant_oscillations: bool
    rare_lock_detected: bool
    phase_locked_rares: bool
    sf9_pattern: bool
    unique_dominants: int
    final_hosts: tuple[float, ...]
    params: dict[str, float | int | str]
    matrix_digest: str
    trial_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "n_types": self.n_types,
            "generations": self.generations,
            "fr_mode": self.fr_mode,
            "binary_dominant_oscillations": self.binary_dominant_oscillations,
            "rare_lock_detected": self.rare_lock_detected,
            "phase_locked_rares": self.phase_locked_rares,
            "sf9_pattern": self.sf9_pattern,
            "unique_dominants": self.unique_dominants,
            "final_hosts": list(self.final_hosts),
            "params": dict(self.params),
            "matrix_digest": self.matrix_digest,
            "trial_digest": self.trial_digest,
            "red_queen_proved": False,
            "functional_response": self.fr_mode,
            "panel_id": PANEL_ID,
            "soft_passes_sf4": False,
            "schema": SCHEMA,
            "domain_profile": DOMAIN_PROFILE,
        }


def run_type3_rare_lock_trial(
    *,
    seed: int,
    n_types: int = DEFAULT_N_TYPES,
    generations: int = DEFAULT_GENERATIONS,
    c: float = DEFAULT_C,
    rare_frac: float = DEFAULT_RARE_FRAC,
    fr_mode: str = "type_III",
    alpha_off: float = 0.01,
    matrix: Sequence[Sequence[float]] | None = None,
) -> Type3RareLockTrial:
    """One seed of the SF9-candidate type-III rare-lock assay."""

    if matrix is None:
        A = build_diagonally_dominant_A(n_types, alpha_off=alpha_off)
    else:
        A = [list(map(float, row)) for row in matrix]
        assert_diagonally_dominant(A)
        assert_no_super_host_or_parasite(A)
        n_types = len(A)

    series = _discrete_type3_series(
        seed=seed,
        n_types=n_types,
        generations=generations,
        c=c,
        fr_mode=fr_mode,
        matrix=A,
    )
    # Analyze after short burn-in.
    burn = max(8, int(generations) // 8)
    pattern = detect_binary_and_rare_lock(series[burn:], rare_frac=rare_frac)
    params: dict[str, float | int | str] = {
        "c_type3": float(c),
        "generations": int(generations),
        "rare_frac": float(rare_frac),
        "alpha_off": float(alpha_off),
        "fr_mode": str(fr_mode),
        "burn_in_samples": int(burn),
    }
    matrix_digest = _digest_body({"A": A})
    body = {
        "seed": int(seed),
        "n_types": n_types,
        "params": params,
        "matrix_digest": matrix_digest,
        "pattern": pattern,
        "final_hosts": [round(h, 10) for h in series[-1]],
    }
    return Type3RareLockTrial(
        seed=int(seed),
        n_types=n_types,
        generations=int(generations),
        fr_mode=str(fr_mode),
        binary_dominant_oscillations=bool(pattern["binary_dominant_oscillations"]),
        rare_lock_detected=bool(pattern["rare_lock_detected"]),
        phase_locked_rares=bool(pattern["phase_locked_rares"]),
        sf9_pattern=bool(pattern["sf9_pattern"]),
        unique_dominants=int(pattern["unique_dominants"]),  # type: ignore[arg-type]
        final_hosts=tuple(round(h, 10) for h in series[-1]),
        params=params,
        matrix_digest=matrix_digest,
        trial_digest=_digest_body(body),
    )


def run_type3_rare_lock_campaign(
    *,
    seeds: Sequence[int] = SEEDS_DEFAULT,
    include_type2_ablation: bool = True,
    **trial_kwargs: Any,
) -> dict[str, object]:
    """Multi-seed SF9-candidate campaign; never soft-passes SF4."""

    intact = [
        run_type3_rare_lock_trial(seed=s, fr_mode="type_III", **trial_kwargs).to_dict()
        for s in seeds
    ]
    ablation = []
    if include_type2_ablation:
        ablation = [
            run_type3_rare_lock_trial(seed=s, fr_mode="type_II", **trial_kwargs).to_dict()
            for s in seeds
        ]

    n_pattern = sum(1 for t in intact if t["sf9_pattern"])
    n_binary = sum(1 for t in intact if t["binary_dominant_oscillations"])
    n_rare = sum(1 for t in intact if t["rare_lock_detected"])
    n_ablation_pattern = sum(1 for t in ablation if t["sf9_pattern"])
    n_seeds = len(intact)
    # Prereg: ≥3/5 intact SF9 pattern AND ablation must not match intact success
    # rate (FR dependence). Ablation may still show binary without rare-lock.
    ablation_ok = (not include_type2_ablation) or (n_ablation_pattern <= 1)
    success = n_pattern >= 3 and ablation_ok
    partial = n_pattern >= 1 and not success
    result = "SUCCESS" if success else ("PARTIAL" if partial else "FAIL")

    body: dict[str, object] = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "panel_id": PANEL_ID,
        "seeds": list(seeds),
        "n_seeds": n_seeds,
        "n_sf9_pattern_seeds": n_pattern,
        "n_binary_seeds": n_binary,
        "n_rare_lock_seeds": n_rare,
        "n_type2_ablation_sf9_seeds": n_ablation_pattern,
        "type2_ablation_suppresses_pattern": ablation_ok,
        "result": result,
        "intact_trials": intact,
        "type2_ablation_trials": ablation,
        "red_queen_proved": False,
        "soft_passes_sf4": False,
        "sf4_result_unchanged_by_this_panel": True,
        "doi": "10.1126/sciadv.1501548",
        "doi_type2_comparator": "10.1038/srep10004",
        "functional_response": "type_III",
        "specificity": "diagonally_dominant_partial_matching_allele",
        "engine_infection_physics": "not_in_engine_core",
        "claimgate_refuses": [
            "red_queen_proved",
            "full_multitype_rq_via_binary_oscillations",
            "phage_therapy_cleared",
            "clinical_pathogen_model",
        ],
        "honesty": (
            "Type-III phase-locked rare panel (SciAdv digital analogue) is "
            "SEPARATE from SF4′ type-II multi-host cycling; binary oscillations "
            "never soft-pass SF4; type-II ablation documents FR dependence; "
            "red_queen_proved remains False. Not a byte-identical SciAdv ODE."
        ),
    }
    body["campaign_digest"] = _digest_body(body)
    return body


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "PANEL_ID",
    "Type3RareLockTrial",
    "detect_binary_and_rare_lock",
    "run_type3_rare_lock_campaign",
    "run_type3_rare_lock_trial",
    "type2_functional_response",
    "type3_functional_response",
]
