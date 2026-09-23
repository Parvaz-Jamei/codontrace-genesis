"""Phase 19 — ARD→FSD transition + cost-of-generalism digests.

Time-sliced range trajectories produce pairwise-distinct slice digests and a
transition protocol (not a Phase-5 enum alone). Cost-of-generalism proxies pair
infectivity/resistance breadth with a specialization score (Koskella &
Brockhurst 2014 / Hall 2011 digital honesty map). Dual-null arms can falsify
“dynamics always ARD under parasitism.” ``red_queen_proved`` is always False.
No wet ARD/FSD identity, phage therapy, or clinical claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_diagnostics import (
    diagnose_coevolution_ranges,
)

SCHEMA = "host_parasite_ard_fsd_transition_v1"
ARMS = (
    "parasite_coevolution",
    "structure_null_shuffled",
    "abiotic_only",
)
HYPOTHESIS = "dynamics_always_ard_under_parasitism"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    out: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be a non-negative int.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        out.append(seed)
    return tuple(out)


def _cost_of_generalism(infectivity_range: float, resistance_range: float) -> float:
    """Digital proxy: broader joint range ⇒ higher generalism cost pressure.

    Specialization score is inverse breadth; never a wet infectivity identity.
    """

    breadth = float(infectivity_range) + float(resistance_range)
    specialization = 1.0 / (1.0 + breadth)
    # Cost rises as breadth grows while specialization falls.
    return round(breadth * (1.0 - specialization), 10)


def _slice_trajectory(
    *,
    arm: str,
    seed: int,
    n_slices: int,
) -> list[dict[str, object]]:
    """Deterministic synthetic range trajectories per arm (digital assay)."""

    rows: list[dict[str, object]] = []
    for t in range(n_slices):
        if arm == "parasite_coevolution":
            # Early ARD-like climb, later FSD-like wobble (Hall-style transition).
            if t < n_slices // 2:
                inf = 0.10 + 0.12 * t + 0.01 * (seed % 7)
                res = 0.08 + 0.11 * t + 0.01 * ((seed // 3) % 5)
            else:
                base_t = n_slices // 2 - 1
                base_inf = 0.10 + 0.12 * base_t + 0.01 * (seed % 7)
                base_res = 0.08 + 0.11 * base_t + 0.01 * ((seed // 3) % 5)
                wobble = 0.08 * ((-1) ** t) * (1 + (seed % 3) * 0.1)
                inf = max(0.0, base_inf + wobble)
                res = max(0.0, base_res - wobble * 0.7)
        elif arm == "structure_null_shuffled":
            # Flat / undeclared — partner structure destroyed.
            inf = 0.05 + 0.001 * (seed % 5)
            res = 0.05 + 0.001 * ((seed // 2) % 5)
        else:  # abiotic_only
            # Mild monotonic abiotic climb without biotic partner — not ARD same.
            inf = 0.02 + 0.03 * t + 0.002 * (seed % 4)
            res = 0.02 + 0.01 * t
        rows.append(
            {
                "time_index": t,
                "infectivity_range": round(inf, 10),
                "resistance_range": round(res, 10),
                "cost_of_generalism": _cost_of_generalism(inf, res),
            }
        )
    return rows


@dataclass(frozen=True, slots=True)
class TransitionSlice:
    slice_id: str
    arm: str
    seed: int
    label: str
    mean_cost_of_generalism: float
    slice_digest: str
    observations: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "slice_id": self.slice_id,
            "arm": self.arm,
            "seed": self.seed,
            "label": self.label,
            "mean_cost_of_generalism": self.mean_cost_of_generalism,
            "slice_digest": self.slice_digest,
            "observations": list(self.observations),
            "red_queen_proved": False,
        }


@dataclass(frozen=True, slots=True)
class ArdFsdTransitionResult:
    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    slices: tuple[TransitionSlice, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    transition_observed: bool
    slices_are_distinct: bool
    claim_ceiling: str
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        slice_rows = [item.to_dict() for item in self.slices]
        arm_digests = {
            arm: _digest_body(
                {"arm": arm, "slices": [s for s in slice_rows if s["arm"] == arm]}
            )
            for arm in self.arms
        }
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "slices": slice_rows,
            "arm_digests": arm_digests,
            "slice_digests": {s["slice_id"]: s["slice_digest"] for s in slice_rows},
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "transition_observed": self.transition_observed,
            "slices_are_distinct": self.slices_are_distinct,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "wet_ard_fsd_identity": False,
            "domain_profile": "host_parasite",
            "note": (
                "Digital ARD→FSD transition protocol + cost-of-generalism proxies; "
                "Red Queen dynamics are not proved."
            ),
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def run_ard_fsd_transition_campaign(
    *,
    seeds: Sequence[int],
    n_slices: int = 6,
    request_claim_ceiling: str = "runtime_observation",
) -> ArdFsdTransitionResult:
    """Run time-sliced ARD→FSD transition with dual-null and cost proxies."""

    seed_tuple = _require_seeds(seeds)
    if isinstance(n_slices, bool) or not isinstance(n_slices, int) or n_slices < 4:
        raise ConfigurationError("n_slices must be an int >= 4.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    slices: list[TransitionSlice] = []
    parasite_labels: list[str] = []
    for seed in seed_tuple:
        for arm in ARMS:
            rows = _slice_trajectory(arm=arm, seed=seed, n_slices=n_slices)
            # Split into early / late windows for transition protocol.
            mid = n_slices // 2
            windows = (
                ("early", rows[:mid]),
                ("late", rows[mid:]),
            )
            for window_name, window_rows in windows:
                diag = diagnose_coevolution_ranges(window_rows)
                mean_cost = round(
                    sum(float(r["cost_of_generalism"]) for r in window_rows)
                    / len(window_rows),
                    10,
                )
                slice_id = f"{arm}:{window_name}:seed{seed}"
                slice_digest = _digest_body(
                    {
                        "slice_id": slice_id,
                        "arm": arm,
                        "seed": seed,
                        "label": diag.label,
                        "mean_cost_of_generalism": mean_cost,
                        "observations": window_rows,
                    }
                )
                slices.append(
                    TransitionSlice(
                        slice_id=slice_id,
                        arm=arm,
                        seed=seed,
                        label=diag.label,
                        mean_cost_of_generalism=mean_cost,
                        slice_digest=slice_digest,
                        observations=tuple(window_rows),
                    )
                )
                if arm == "parasite_coevolution":
                    parasite_labels.append(f"{window_name}:{diag.label}")

    # Transition: early vs late parasite labels differ for at least one seed.
    transition_observed = False
    for seed in seed_tuple:
        early = next(
            s for s in slices if s.arm == "parasite_coevolution" and s.seed == seed and "early" in s.slice_id
        )
        late = next(
            s for s in slices if s.arm == "parasite_coevolution" and s.seed == seed and "late" in s.slice_id
        )
        if early.label != late.label:
            transition_observed = True
            break

    # Dual-null falsifies universal ARD: structure/abiotic must not all be ard_like
    # while parasite arm claims always-ARD.
    parasite_all_ard = all(
        s.label == "ard_like" for s in slices if s.arm == "parasite_coevolution"
    )
    null_not_always_ard = any(
        s.label != "ard_like"
        for s in slices
        if s.arm in {"structure_null_shuffled", "abiotic_only"}
    )
    hypothesis_supported = parasite_all_ard and not transition_observed
    if transition_observed or null_not_always_ard:
        hypothesis_supported = False
        failure_reason = (
            "transition_or_dual_null_falsifies_dynamics_always_ard_under_parasitism"
        )
    else:
        failure_reason = ""

    digests = {s.slice_id: s.slice_digest for s in slices}
    distinct = len(set(digests.values())) == len(digests)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: transition slices must produce distinct digests."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        raise ConfigurationError(
            "candidate_evidence refused while dynamics_always_ard_under_parasitism still holds."
        )

    return ArdFsdTransitionResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=ARMS,
        slices=tuple(slices),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        transition_observed=transition_observed,
        slices_are_distinct=distinct,
        claim_ceiling=ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        red_queen_proved=False,
    )


__all__ = [
    "ARMS",
    "HYPOTHESIS",
    "SCHEMA",
    "ArdFsdTransitionResult",
    "TransitionSlice",
    "run_ard_fsd_transition_campaign",
]
