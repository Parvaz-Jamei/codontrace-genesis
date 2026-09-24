"""Port-local type-II / diagonally-dominant multi-host RQ stepper (De-toy D1).

Implements a discrete Euler analogue of Rabajante et al. 2015 *Sci Rep*
doi:10.1038/srep10004 (PMC4405699) structural conditions:

- type-II functional response α_ij H_i / (1 + H_i)
- diagonally dominant specificity matrix A (partial matching-allele)
- no super-host / super-parasite
- intermediate parasite mortality d and adequate host carrying capacity K
- inter-host competition

Infection physics stay on the host_parasite DomainProfile port — never in
engine.py. Graded α_ij may be derived from digital task-overlap + specialist
bias (extends boolean infection_eligible at the campaign layer).

ClaimGate: even when cycling_detected is True, red_queen_proved stays False.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

SCHEMA = "host_parasite_type2_rq_stepper_v1"
DOMAIN_PROFILE = "host_parasite"

# Capable defaults (digital analogue of Sci Rep mid-d / adequate-K region).
DEFAULT_N_TYPES = 5
DEFAULT_STEPS = 8000
DEFAULT_DT = 0.05
DEFAULT_R = 0.5
DEFAULT_D = 0.12
DEFAULT_K = 2.0
DEFAULT_A_OFF = 0.01
DEFAULT_SAMPLE_EVERY = 20
DEFAULT_BURN_IN = 1000
FLOOR = 1e-9


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def build_diagonally_dominant_A(
    n: int,
    *,
    alpha_off: float = DEFAULT_A_OFF,
) -> list[list[float]]:
    """Build row-stochastic diagonally dominant specificity matrix.

    α_ii = 1 - (n-1)*α_off, α_ij = α_off (i≠j). Matches Rabajante Methods
    (row/column sums ≈ 1; diagonal dominance; no super-* when α_off small).
    """

    if n < 3:
        raise ConfigurationError("type-II RQ stepper requires n >= 3 types")
    if not (0.0 < alpha_off < 1.0 / max(n, 1)):
        raise ConfigurationError(
            f"alpha_off={alpha_off} must be in (0, 1/n) for diagonal dominance"
        )
    alpha_diag = 1.0 - (n - 1) * float(alpha_off)
    if alpha_diag <= (n - 1) * float(alpha_off):
        raise ConfigurationError("matrix would not be diagonally dominant")
    matrix = [[float(alpha_off)] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = float(alpha_diag)
    assert_diagonally_dominant(matrix)
    assert_no_super_host_or_parasite(matrix)
    return matrix


def assert_diagonally_dominant(matrix: Sequence[Sequence[float]]) -> None:
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ConfigurationError("A must be square and non-empty")
    for i, row in enumerate(matrix):
        diag = float(row[i])
        off = sum(float(row[j]) for j in range(n) if j != i)
        if diag <= off:
            raise ConfigurationError(
                f"row {i} not diagonally dominant: diag={diag} off={off}"
            )


def assert_no_super_host_or_parasite(
    matrix: Sequence[Sequence[float]],
    *,
    infect_threshold: float = 0.85,
    resist_threshold: float = 0.15,
) -> None:
    """Refuse universal infectors / universal resisters (super-*)."""

    n = len(matrix)
    for j in range(n):
        if all(float(matrix[i][j]) >= infect_threshold for i in range(n)):
            raise ConfigurationError(
                f"super-parasite column j={j} (all α_ij >= {infect_threshold})"
            )
    for i in range(n):
        if all(float(matrix[i][j]) <= resist_threshold for j in range(n)):
            raise ConfigurationError(
                f"super-host row i={i} (all α_ij <= {resist_threshold})"
            )


def graded_alpha_from_overlap(
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    *,
    specialist_bias: float = 0.8,
    floor: float = 0.01,
    ceiling: float = 0.99,
) -> float:
    """Map digital task-set overlap to a graded α in [floor, ceiling].

    Extends boolean infection_eligible: empty overlap → floor; full specialist
    match (overlap / |parasite|) → near ceiling weighted by specialist_bias.
    """

    if not (0.0 <= specialist_bias <= 1.0):
        raise ConfigurationError("specialist_bias must be in [0, 1]")
    hset = {str(t) for t in host_tasks}
    pset = {str(t) for t in parasite_tasks}
    if not pset:
        return float(floor)
    overlap = len(hset & pset) / float(len(pset))
    # specialist_bias pulls toward high α only when overlap is strong
    raw = floor + (ceiling - floor) * (
        specialist_bias * overlap + (1.0 - specialist_bias) * (overlap**2)
    )
    return float(min(ceiling, max(floor, raw)))


def build_graded_A_from_repertoires(
    host_repertoires: Sequence[Sequence[str]],
    parasite_repertoires: Sequence[Sequence[str]],
    *,
    specialist_bias: float = 0.85,
    enforce_diagonal_boost: float = 0.35,
) -> list[list[float]]:
    """Build graded A from digital overlaps, then enforce diagonal dominance.

    Diagonal boost mirrors specialist matching-allele bias without claiming
    wet immunology identity.
    """

    n_h = len(host_repertoires)
    n_p = len(parasite_repertoires)
    if n_h != n_p or n_h < 3:
        raise ConfigurationError("host/parasite repertoire counts must match and be >= 3")
    raw = [
        [
            graded_alpha_from_overlap(
                host_repertoires[i],
                parasite_repertoires[j],
                specialist_bias=specialist_bias,
            )
            for j in range(n_p)
        ]
        for i in range(n_h)
    ]
    # Enforce specialist diagonal: boost diag, renormalize rows softly.
    for i in range(n_h):
        raw[i][i] = min(0.99, raw[i][i] + enforce_diagonal_boost)
        row_sum = sum(raw[i]) or 1.0
        raw[i] = [v / row_sum for v in raw[i]]
    # If still not diag-dominant, fall back to canonical generator.
    try:
        assert_diagonally_dominant(raw)
        assert_no_super_host_or_parasite(raw)
        return raw
    except ConfigurationError:
        return build_diagonally_dominant_A(n_h)


def _euler_step(
    hosts: list[float],
    parasites: list[float],
    matrix: Sequence[Sequence[float]],
    *,
    r: float,
    d: float,
    k: float,
    dt: float,
) -> tuple[list[float], list[float]]:
    n = len(hosts)
    h_sum = sum(hosts)
    new_h: list[float] = []
    for i in range(n):
        fr = sum(
            float(matrix[i][j]) * hosts[i] / (1.0 + hosts[i]) * parasites[j]
            for j in range(n)
        )
        growth = float(r) * hosts[i] * (1.0 - h_sum / float(k)) - fr
        new_h.append(max(FLOOR, hosts[i] + float(dt) * growth))
    new_p: list[float] = []
    for j in range(n):
        infect = sum(
            float(matrix[i][j]) * hosts[i] / (1.0 + hosts[i]) * parasites[j]
            for i in range(n)
        )
        new_p.append(max(FLOOR, parasites[j] + float(dt) * (infect - float(d) * parasites[j])))
    return new_h, new_p


def detect_dominance_cycling(
    dominance_seq: Sequence[int],
    *,
    min_unique: int = 3,
    min_returns: int = 2,
) -> dict[str, object]:
    """Qualitative cycling: ≥3 unique dominants with ≥2 returns (epoch view)."""

    epochs: list[int] = []
    for dom in dominance_seq:
        if not epochs or epochs[-1] != int(dom):
            epochs.append(int(dom))
    unique = len(set(epochs))
    returns = 0
    seen: dict[int, int] = {}
    for idx, dom in enumerate(epochs):
        if dom in seen and idx - seen[dom] >= 2:
            returns += 1
        seen[dom] = idx
    cycling = unique >= min_unique and returns >= min_returns
    return {
        "unique_dominants": unique,
        "dominance_returns": returns,
        "n_epochs": len(epochs),
        "cycling_detected": cycling,
        "epochs_prefix": epochs[:12],
        "epochs_suffix": epochs[-12:],
    }


@dataclass(frozen=True, slots=True)
class Type2RQTrial:
    seed: int
    n_types: int
    steps: int
    cycling_detected: bool
    unique_dominants: int
    dominance_returns: int
    final_hosts: tuple[float, ...]
    final_parasites: tuple[float, ...]
    params: dict[str, float | int]
    matrix_digest: str
    trial_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "n_types": self.n_types,
            "steps": self.steps,
            "cycling_detected": self.cycling_detected,
            "unique_dominants": self.unique_dominants,
            "dominance_returns": self.dominance_returns,
            "final_hosts": list(self.final_hosts),
            "final_parasites": list(self.final_parasites),
            "params": dict(self.params),
            "matrix_digest": self.matrix_digest,
            "trial_digest": self.trial_digest,
            "red_queen_proved": False,
            "schema": SCHEMA,
            "domain_profile": DOMAIN_PROFILE,
        }


def run_type2_cycling_trial(
    *,
    seed: int,
    n_types: int = DEFAULT_N_TYPES,
    steps: int = DEFAULT_STEPS,
    dt: float = DEFAULT_DT,
    r: float = DEFAULT_R,
    d: float = DEFAULT_D,
    k: float = DEFAULT_K,
    alpha_off: float = DEFAULT_A_OFF,
    sample_every: int = DEFAULT_SAMPLE_EVERY,
    burn_in: int = DEFAULT_BURN_IN,
    matrix: Sequence[Sequence[float]] | None = None,
) -> Type2RQTrial:
    """Run one seed of the port-local type-II multi-host stepper."""

    if matrix is None:
        A = build_diagonally_dominant_A(n_types, alpha_off=alpha_off)
    else:
        A = [list(map(float, row)) for row in matrix]
        assert_diagonally_dominant(A)
        assert_no_super_host_or_parasite(A)
        n_types = len(A)

    digest = _seed_bytes(seed, "type2_rq_init")
    hosts = [
        0.01 + 0.001 * i + 0.0001 * (digest[i % len(digest)] / 255.0)
        for i in range(n_types)
    ]
    parasites = [
        0.01
        + 0.001 * i
        + 0.0001 * (digest[(n_types + i) % len(digest)] / 255.0)
        for i in range(n_types)
    ]
    dominance_seq: list[int] = []
    for step in range(int(steps)):
        hosts, parasites = _euler_step(hosts, parasites, A, r=r, d=d, k=k, dt=dt)
        if step >= int(burn_in) and step % int(sample_every) == 0:
            dominance_seq.append(max(range(n_types), key=lambda i: hosts[i]))

    cycle = detect_dominance_cycling(dominance_seq)
    params: dict[str, float | int] = {
        "dt": float(dt),
        "r": float(r),
        "d": float(d),
        "K": float(k),
        "alpha_off": float(alpha_off),
        "sample_every": int(sample_every),
        "burn_in": int(burn_in),
        "steps": int(steps),
    }
    matrix_digest = _digest_body({"A": A})
    body = {
        "seed": int(seed),
        "n_types": n_types,
        "params": params,
        "matrix_digest": matrix_digest,
        "cycle": cycle,
        "final_hosts": [round(h, 10) for h in hosts],
        "final_parasites": [round(p, 10) for p in parasites],
    }
    return Type2RQTrial(
        seed=int(seed),
        n_types=n_types,
        steps=int(steps),
        cycling_detected=bool(cycle["cycling_detected"]),
        unique_dominants=int(cycle["unique_dominants"]),  # type: ignore[arg-type]
        dominance_returns=int(cycle["dominance_returns"]),  # type: ignore[arg-type]
        final_hosts=tuple(round(h, 10) for h in hosts),
        final_parasites=tuple(round(p, 10) for p in parasites),
        params=params,
        matrix_digest=matrix_digest,
        trial_digest=_digest_body(body),
    )


def run_type2_campaign(
    *,
    seeds: Sequence[int],
    **trial_kwargs: Any,
) -> dict[str, object]:
    """Multi-seed campaign; SUCCESS if ≥3/5 seeds cycling (prereg)."""

    trials = [run_type2_cycling_trial(seed=s, **trial_kwargs).to_dict() for s in seeds]
    n_cycle = sum(1 for t in trials if t["cycling_detected"])
    n_seeds = len(trials)
    success = n_cycle >= 3
    partial = n_cycle >= 1 and not success
    result = "SUCCESS" if success else ("PARTIAL" if partial else "FAIL")
    body = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "seeds": list(seeds),
        "n_seeds": n_seeds,
        "n_cycling_seeds": n_cycle,
        "result": result,
        "trials": trials,
        "red_queen_proved": False,
        "doi": "10.1038/srep10004",
        "pmc": "PMC4405699",
        "functional_response": "type_II",
        "specificity": "diagonally_dominant_partial_matching_allele",
        "engine_infection_physics": "not_in_engine_core",
    }
    body["campaign_digest"] = _digest_body(body)
    return body


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "Type2RQTrial",
    "assert_diagonally_dominant",
    "assert_no_super_host_or_parasite",
    "build_diagonally_dominant_A",
    "build_graded_A_from_repertoires",
    "detect_dominance_cycling",
    "graded_alpha_from_overlap",
    "run_type2_campaign",
    "run_type2_cycling_trial",
]
