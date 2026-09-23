"""Phase 14 — transmission-mode contrast campaign (horizontal / vertical / mixed).

Produces pairwise-distinct mode digests and proves mixed mode blends a
successful horizontal inject with a vertical transmit in the same run.
Digital ClaimGate surface only; no infection physics in ``engine.py``.
Does not prove Red Queen, major transition, human virulence optimization,
phage therapy, vaccine effect, epidemic forecast, BSL, or CRISPR identity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_env import HostParasiteEnv

SCHEMA = "host_parasite_transmission_mode_contrast_v1"
MODES = ("horizontal", "vertical", "mixed")
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


@dataclass(frozen=True, slots=True)
class ModeArmOutcome:
    seed: int
    mode: str
    horizontal_injected: bool
    vertical_transmitted: bool
    blend_observed: bool
    occupied_hosts: int
    host_count: int
    mode_digest: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "mode": self.mode,
            "horizontal_injected": self.horizontal_injected,
            "vertical_transmitted": self.vertical_transmitted,
            "blend_observed": self.blend_observed,
            "occupied_hosts": self.occupied_hosts,
            "host_count": self.host_count,
            "mode_digest": self.mode_digest,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ModeContrastResult:
    schema: str
    seeds: tuple[int, ...]
    modes: tuple[str, ...]
    arm_outcomes: tuple[ModeArmOutcome, ...]
    claim_ceiling: str
    modes_are_distinct: bool
    mixed_blends_horizontal_and_vertical: bool
    red_queen_proved: bool
    virulence_optimized_for_humans: bool
    major_transition_proved: bool

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.arm_outcomes]
        mode_digests: dict[str, str] = {}
        for mode in self.modes:
            bodies = [o for o in outcomes if o["mode"] == mode]
            mode_digests[mode] = _digest_body({"mode": mode, "outcomes": bodies})
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "modes": list(self.modes),
            "arm_outcomes": outcomes,
            "mode_digests": mode_digests,
            "claim_ceiling": self.claim_ceiling,
            "modes_are_distinct": self.modes_are_distinct,
            "mixed_blends_horizontal_and_vertical": self.mixed_blends_horizontal_and_vertical,
            "red_queen_proved": False,
            "virulence_optimized_for_humans": False,
            "major_transition_proved": False,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "domain_profile": "host_parasite",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _run_mode(*, seed: int, mode: str) -> ModeArmOutcome:
    notes: list[str] = [f"mode_{mode}"]
    env = HostParasiteEnv(
        transmission_mode=mode,
        vertical_transmission_probability=1.0,
        steal_fraction=0.5,
        spatial_mode="well_mixed",
    )
    env.add_host("H0", ("and", "nand"))
    env.add_host("H1", ("and", "or"))

    horizontal_injected = False
    vertical_transmitted = False

    if mode == "vertical":
        env.seed_parasite_seat(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(seed % 97, 1, 2),
        )
        blocked = env.try_horizontal_inject(
            host_id="H1",
            parasite_id="P_block",
            parasite_tasks=("and",),
            payload=(3,),
        )
        if blocked.injected:
            raise ConfigurationError("vertical mode must block horizontal inject.")
        notes.append("horizontal_blocked_as_expected")
        child = env.replicate_host(parent_id="H0", child_id="H_child", draw=0.0)
        vertical_transmitted = child.parasite_id is not None
        notes.append("vertical_seed_then_replicate")
    else:
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=("and",),
            payload=(seed % 97, 1, 2),
        )
        horizontal_injected = bool(attempt.injected)
        if not horizontal_injected:
            raise ConfigurationError(f"{mode} mode expected successful horizontal inject.")
        notes.append("horizontal_inject_ok")
        child = env.replicate_host(parent_id="H0", child_id="H_child", draw=0.0)
        vertical_transmitted = child.parasite_id is not None
        if mode == "mixed":
            notes.append("mixed_expects_vertical_after_inject")
        else:
            notes.append("horizontal_skips_vertical")

    blend_observed = bool(horizontal_injected and vertical_transmitted)
    if mode == "mixed" and not blend_observed:
        raise ConfigurationError(
            "mixed mode must blend horizontal inject and vertical transmit "
            "(DEPTH Phase 5 / Wave-4 audit requirement)."
        )
    if mode == "horizontal" and vertical_transmitted:
        raise ConfigurationError("horizontal mode must not vertically transmit.")
    if mode == "vertical" and horizontal_injected:
        raise ConfigurationError("vertical mode must not horizontally inject.")

    occupied = sum(1 for host in env.hosts.values() if host.parasite_id is not None)
    body = {
        "seed": seed,
        "mode": mode,
        "horizontal_injected": horizontal_injected,
        "vertical_transmitted": vertical_transmitted,
        "blend_observed": blend_observed,
        "occupied_hosts": occupied,
        "host_count": len(env.hosts),
        "snapshot_vertical_component": env.snapshot().get("vertical_component"),
        "notes": notes,
    }
    return ModeArmOutcome(
        seed=seed,
        mode=mode,
        horizontal_injected=horizontal_injected,
        vertical_transmitted=vertical_transmitted,
        blend_observed=blend_observed,
        occupied_hosts=occupied,
        host_count=len(env.hosts),
        mode_digest=_digest_body(body),
        notes=tuple(notes),
    )


def run_transmission_mode_contrast(
    *,
    seeds: Sequence[int],
    request_claim_ceiling: str = "runtime_observation",
) -> ModeContrastResult:
    """Run horizontal / vertical / mixed contrast with canonical digests."""

    seed_tuple = _require_seeds(seeds)
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    outcomes = tuple(
        _run_mode(seed=seed, mode=mode) for seed in seed_tuple for mode in MODES
    )
    preview = ModeContrastResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        modes=MODES,
        arm_outcomes=outcomes,
        claim_ceiling=ceiling,
        modes_are_distinct=False,
        mixed_blends_horizontal_and_vertical=False,
        red_queen_proved=False,
        virulence_optimized_for_humans=False,
        major_transition_proved=False,
    ).to_dict()
    digests = preview["mode_digests"]
    assert isinstance(digests, dict)
    distinct = len(set(digests.values())) == len(MODES)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: transmission modes must produce distinct digests."
        )
    mixed_ok = all(item.blend_observed for item in outcomes if item.mode == "mixed")
    if not mixed_ok:
        raise ConfigurationError("mixed mode failed to blend horizontal and vertical.")

    return ModeContrastResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        modes=MODES,
        arm_outcomes=outcomes,
        claim_ceiling=ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        modes_are_distinct=distinct,
        mixed_blends_horizontal_and_vertical=mixed_ok,
        red_queen_proved=False,
        virulence_optimized_for_humans=False,
        major_transition_proved=False,
    )


BRAINSTORMED_KEEP_MODES: dict[str, str] = {
    "horizontal": "host_parasite_env + mode contrast",
    "vertical": "host_parasite_env + mode contrast",
    "mixed": "host_parasite_env + mode contrast (must blend H+V)",
    "well_mixed": "host_parasite_env + continuum factorial",
    "local_neighborhood": "host_parasite_env + continuum factorial",
    "interaction_value_continuum": "host_parasite_continuum",
    "freeze_parasites": "host_parasite_zaman + genome_zaman",
    "replay_parasite_schedule": "host_parasite_zaman + genome_zaman",
    "reciprocal_coevolution": "host_parasite_zaman + genome_zaman",
    "content_null": "campaign + genome_diversity dual-null",
    "structure_null": "campaign + genome_diversity dual-null",
    "abiotic_only": "campaign + genome_diversity",
    "hgt_analogue_segment_copy": "host_parasite_hgt",
    "hgt_analogue_noise_transfer": "host_parasite_hgt dual-null",
    "intracellular_seat_constraint": "host_parasite_hgt",
    "free_living_horizontal_inject": "host_parasite_hgt",
}


__all__ = [
    "BRAINSTORMED_KEEP_MODES",
    "MODES",
    "ModeArmOutcome",
    "ModeContrastResult",
    "SCHEMA",
    "run_transmission_mode_contrast",
]
