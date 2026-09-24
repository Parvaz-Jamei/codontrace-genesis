"""Phase 9 — Continuum / intervention analytics on HostParasiteWorld (no new physics).

Refuse-safe factorial continuum cells, ScheduleLock/Ablation intervention
contrasts, and reciprocal observational contrasts. Continuum emerges from
World profile axes + HookMeter / MatchRule channels — never a free
interaction_value continuum engine, never Env.step, never ClaimGate allows.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.host_parasite_world import (
    ABLATION_PRESETS,
    SCHEDULE_ARMS,
    SPATIAL_MODES,
    HostParasiteProfile,
    HostParasiteWorld,
)

SCHEMA_CONTINUUM = "host_parasite_continuum_analytics_v1"
SCHEMA_INTERVENTION = "host_parasite_intervention_analytics_v1"
SCHEMA_RECIPROCAL = "host_parasite_reciprocal_observational_v1"

ClaimRole = Literal["primary", "exploratory", "smoke"]
Ceiling = Literal["runtime_observation", "candidate_evidence"]

_CORE_REFUSES: frozenset[str] = frozenset(
    {
        "red_queen_proved",
        "modes_passed_proved",
        "tokyo_type1_passed",
        "price_as_causality",
        "crispr_identity_proved",
        "phage_therapy_cleared",
        "vaccine_efficacy_proved",
        "epidemic_forecast_certified",
        "biosafety_level_certified",
        "major_transition_proved",
        "intervention_supported",
        "intelligence",
    }
)

CONTINUUM_PHYSICS_SOURCE = "world_meters"


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a bool.")
    return value


def _as_nonneg(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0:
        raise ConfigurationError(f"{name} must be >= 0.")
    return number


def _as_unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _merge_refuses(extra: Sequence[str] | None = None) -> tuple[str, ...]:
    merged = set(_CORE_REFUSES)
    if extra:
        for item in extra:
            merged.add(_as_str(item, "refuse_item"))
    return tuple(sorted(merged))


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _emergent_interaction_proxy(
    *,
    coupling_total: float,
    match_score_sum: float,
    contact_success: int,
    contact_fail: int,
    density_primary: int,
    density_secondary: int,
) -> float:
    """Derive a [0,1] proxy from meter channels (not a free slider)."""

    contacts = contact_success + contact_fail
    contact_rate = (contact_success / contacts) if contacts else 0.0
    density_sum = density_primary + density_secondary
    coexistence = (
        (2.0 * min(density_primary, density_secondary) / density_sum)
        if density_sum
        else 0.0
    )
    match_term = _clamp01(match_score_sum / max(1.0, float(contact_success or 1)))
    coupling_term = _clamp01(coupling_total / max(1.0, coupling_total + 1.0))
    proxy = 0.35 * contact_rate + 0.25 * coexistence + 0.20 * match_term + 0.20 * coupling_term
    return round(_clamp01(proxy), 10)


def _run_world_cell(
    *,
    profile_id: str,
    seed: int,
    ticks: int,
    coupling_amount: float,
    spatial_mode: str,
    inherit_probability: float,
    match_score_scale: float,
    schedule_arm: str = "none",
    ablation_preset: str = "none",
    match_rule_id: str = "always",
    phenotype_tags: Mapping[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
    """Construct HostParasiteWorld and tick; return meter/census snapshot body."""

    profile = HostParasiteProfile(
        profile_id=profile_id,
        seed=seed,
        coupling_amount=coupling_amount,
        spatial_mode=spatial_mode,
        inherit_probability=inherit_probability,
        inherit_mode="copy" if inherit_probability > 0.0 else "none",
        match_score_scale=match_score_scale,
        schedule_arm=schedule_arm,
        ablation_preset=ablation_preset,
        match_rule_id=match_rule_id,
        phenotype_tags=dict(phenotype_tags or {}),
        contact_probability=1.0,
    )
    world = HostParasiteWorld(profile)
    world.run(ticks)
    snap = world.meter.snapshot()
    census = world.census()
    related = dict(snap.related_counts)
    totals = dict(snap.related_totals)
    coupling_total = float(totals.get("coupling_total", 0.0))
    match_score_sum = float(totals.get("match_score_sum", 0.0))
    contact_success = int(related.get("contact_success", 0))
    contact_fail = int(related.get("contact_fail", 0))
    proxy = _emergent_interaction_proxy(
        coupling_total=coupling_total,
        match_score_sum=match_score_sum,
        contact_success=contact_success,
        contact_fail=contact_fail,
        density_primary=int(census["primary"]),
        density_secondary=int(census["secondary"]),
    )
    return {
        "profile_digest": profile.digest,
        "world_digest": str(world.summary()["world_digest"]),
        "meter_digest": snap.digest,
        "hook_counts": dict(snap.hook_counts),
        "related_counts": related,
        "related_totals": totals,
        "census": dict(census),
        "emergent_interaction_proxy": proxy,
        "coexistence_min_density": float(min(census["primary"], census["secondary"])),
        "coupling_amount": coupling_amount,
        "spatial_mode": spatial_mode,
        "inherit_probability": inherit_probability,
        "match_score_scale": match_score_scale,
        "schedule_arm": schedule_arm,
        "ablation_preset": ablation_preset,
    }


@dataclass(frozen=True, slots=True)
class ContinuumCellResult:
    """One continuum factorial cell observed on HostParasiteWorld meters."""

    cell_id: str
    seed: int
    ticks: int
    coupling_amount: float
    spatial_mode: str
    inherit_probability: float
    match_score_scale: float
    emergent_interaction_proxy: float
    coexistence_min_density: float
    meter_digest: str
    world_digest: str
    census: Mapping[str, int]
    related_totals: Mapping[str, float]
    cell_digest: str = ""
    continuum_physics_source: str = CONTINUUM_PHYSICS_SOURCE
    interaction_value_compat: float | None = None
    mutualism_equals_success: bool = False

    def __post_init__(self) -> None:
        cid = _refuse_banned_fragment(_as_str(self.cell_id, "cell_id"), "cell_id")
        object.__setattr__(self, "cell_id", cid)
        object.__setattr__(self, "seed", _as_int(self.seed, "seed", minimum=0))
        object.__setattr__(self, "ticks", _as_int(self.ticks, "ticks", minimum=0))
        object.__setattr__(
            self, "coupling_amount", _as_nonneg(self.coupling_amount, "coupling_amount")
        )
        spatial = _as_str(self.spatial_mode, "spatial_mode").casefold()
        if spatial not in SPATIAL_MODES:
            raise ConfigurationError(f"unknown spatial_mode {self.spatial_mode!r}.")
        object.__setattr__(self, "spatial_mode", spatial)
        object.__setattr__(
            self,
            "inherit_probability",
            _as_unit_interval(self.inherit_probability, "inherit_probability"),
        )
        scale = float(require_finite_float("match_score_scale", self.match_score_scale))
        if scale <= 0.0 or scale > 1.0:
            raise ConfigurationError("match_score_scale must be in (0, 1].")
        object.__setattr__(self, "match_score_scale", scale)
        proxy = float(
            require_finite_float(
                "emergent_interaction_proxy", self.emergent_interaction_proxy
            )
        )
        object.__setattr__(self, "emergent_interaction_proxy", _clamp01(proxy))
        object.__setattr__(
            self,
            "coexistence_min_density",
            _as_nonneg(self.coexistence_min_density, "coexistence_min_density"),
        )
        object.__setattr__(self, "meter_digest", _as_str(self.meter_digest, "meter_digest"))
        object.__setattr__(self, "world_digest", _as_str(self.world_digest, "world_digest"))
        if not isinstance(self.census, Mapping):
            raise ConfigurationError("census must be a mapping.")
        census = {
            _as_str(k, "census.key"): _as_int(v, "census.value", minimum=0)
            for k, v in self.census.items()
        }
        object.__setattr__(self, "census", dict(sorted(census.items())))
        if not isinstance(self.related_totals, Mapping):
            raise ConfigurationError("related_totals must be a mapping.")
        totals = {
            _refuse_banned_fragment(_as_str(k, "total.key"), "total.key"): _as_nonneg(
                v, "total.value"
            )
            for k, v in self.related_totals.items()
        }
        object.__setattr__(self, "related_totals", dict(sorted(totals.items())))
        if self.continuum_physics_source != CONTINUUM_PHYSICS_SOURCE:
            raise ConfigurationError(
                "continuum_physics_source must be 'world_meters' "
                "(interaction_value is not continuum physics)."
            )
        if self.mutualism_equals_success:
            raise ConfigurationError("refuses mutualism_equals_success=True.")
        object.__setattr__(self, "mutualism_equals_success", False)
        if self.interaction_value_compat is not None:
            object.__setattr__(
                self,
                "interaction_value_compat",
                float(
                    require_finite_float(
                        "interaction_value_compat", self.interaction_value_compat
                    )
                ),
            )
        computed = canonical_digest(self._body(), prefix="hp_cont_cell")
        object.__setattr__(
            self, "cell_digest", _check_digest(self.cell_digest, computed, "ContinuumCellResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "cell_id": self.cell_id,
            "seed": self.seed,
            "ticks": self.ticks,
            "coupling_amount": self.coupling_amount,
            "spatial_mode": self.spatial_mode,
            "inherit_probability": self.inherit_probability,
            "match_score_scale": self.match_score_scale,
            "emergent_interaction_proxy": self.emergent_interaction_proxy,
            "coexistence_min_density": self.coexistence_min_density,
            "meter_digest": self.meter_digest,
            "world_digest": self.world_digest,
            "census": dict(self.census),
            "related_totals": dict(self.related_totals),
            "continuum_physics_source": CONTINUUM_PHYSICS_SOURCE,
            "mutualism_equals_success": False,
        }
        if self.interaction_value_compat is not None:
            body["interaction_value_compat"] = self.interaction_value_compat
        return body

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "cell_digest": self.cell_digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ContinuumCellResult:
        return cls(
            cell_id=_as_str(data.get("cell_id"), "cell_id"),
            seed=_as_int(data.get("seed"), "seed", minimum=0),
            ticks=_as_int(data.get("ticks"), "ticks", minimum=0),
            coupling_amount=float(
                require_finite_float("coupling_amount", data.get("coupling_amount"))
            ),
            spatial_mode=_as_str(data.get("spatial_mode"), "spatial_mode"),
            inherit_probability=float(
                require_finite_float(
                    "inherit_probability", data.get("inherit_probability")
                )
            ),
            match_score_scale=float(
                require_finite_float(
                    "match_score_scale", data.get("match_score_scale", 1.0)
                )
            ),
            emergent_interaction_proxy=float(
                require_finite_float(
                    "emergent_interaction_proxy",
                    data.get("emergent_interaction_proxy"),
                )
            ),
            coexistence_min_density=float(
                require_finite_float(
                    "coexistence_min_density", data.get("coexistence_min_density", 0.0)
                )
            ),
            meter_digest=_as_str(data.get("meter_digest"), "meter_digest"),
            world_digest=_as_str(data.get("world_digest"), "world_digest"),
            census=dict(data.get("census") or {}),  # type: ignore[arg-type]
            related_totals=dict(data.get("related_totals") or {}),  # type: ignore[arg-type]
            cell_digest=_as_str(data.get("cell_digest", ""), "cell_digest", allow_empty=True),
            continuum_physics_source=_as_str(
                data.get("continuum_physics_source", CONTINUUM_PHYSICS_SOURCE),
                "continuum_physics_source",
            ),
            interaction_value_compat=(
                None
                if data.get("interaction_value_compat") is None
                else float(
                    require_finite_float(
                        "interaction_value_compat", data.get("interaction_value_compat")
                    )
                )
            ),
            mutualism_equals_success=_as_bool(
                data.get("mutualism_equals_success", False), "mutualism_equals_success"
            ),
        )


@dataclass(frozen=True, slots=True)
class ContinuumFactorialResult:
    """Digest-stable continuum factorial over World profile axes."""

    factorial_id: str
    seeds: tuple[int, ...]
    ticks: int
    cells: tuple[ContinuumCellResult, ...]
    claim_ceiling: str = "runtime_observation"
    smoke_only: bool = False
    refuse_list: tuple[str, ...] = ()
    digest: str = ""
    red_queen_proved: bool = False
    intervention_supported: bool = False
    raises_claim_ladder: bool = False
    mutualism_equals_success: bool = False
    continuum_physics_source: str = CONTINUUM_PHYSICS_SOURCE

    def __post_init__(self) -> None:
        fid = _refuse_banned_fragment(
            _as_str(self.factorial_id, "factorial_id"), "factorial_id"
        )
        object.__setattr__(self, "factorial_id", fid)
        seeds = tuple(_as_int(s, "seed", minimum=0) for s in self.seeds)
        if not seeds:
            raise ConfigurationError("ContinuumFactorialResult requires at least one seed.")
        if len(seeds) != len(set(seeds)):
            raise ConfigurationError("seeds must be unique.")
        object.__setattr__(self, "seeds", seeds)
        object.__setattr__(self, "ticks", _as_int(self.ticks, "ticks", minimum=0))
        if not self.cells:
            raise ConfigurationError("cells must be non-empty.")
        object.__setattr__(self, "cells", tuple(self.cells))
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        object.__setattr__(self, "smoke_only", _as_bool(self.smoke_only, "smoke_only"))
        object.__setattr__(self, "refuse_list", _merge_refuses(self.refuse_list))
        if self.red_queen_proved:
            raise ConfigurationError("refuses red_queen_proved=True.")
        if self.intervention_supported:
            raise ConfigurationError("refuses intervention_supported=True.")
        if self.raises_claim_ladder:
            raise ConfigurationError("refuses raises_claim_ladder=True.")
        if self.mutualism_equals_success:
            raise ConfigurationError("refuses mutualism_equals_success=True.")
        if self.continuum_physics_source != CONTINUUM_PHYSICS_SOURCE:
            raise ConfigurationError("continuum_physics_source must be world_meters.")
        object.__setattr__(self, "red_queen_proved", False)
        object.__setattr__(self, "intervention_supported", False)
        object.__setattr__(self, "raises_claim_ladder", False)
        object.__setattr__(self, "mutualism_equals_success", False)
        computed = canonical_digest(self._body(), prefix="hp_cont_fact")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "ContinuumFactorialResult"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema": SCHEMA_CONTINUUM,
            "factorial_id": self.factorial_id,
            "seeds": list(self.seeds),
            "ticks": self.ticks,
            "cells": [c.to_dict() for c in self.cells],
            "claim_ceiling": self.claim_ceiling,
            "smoke_only": self.smoke_only,
            "refuse_list": list(self.refuse_list),
            "red_queen_proved": False,
            "intervention_supported": False,
            "raises_claim_ladder": False,
            "mutualism_equals_success": False,
            "continuum_physics_source": CONTINUUM_PHYSICS_SOURCE,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ContinuumFactorialResult:
        cells_raw = data.get("cells")
        if not isinstance(cells_raw, Sequence):
            raise ConfigurationError("cells must be a sequence.")
        cells = tuple(
            ContinuumCellResult.from_dict(c)  # type: ignore[arg-type]
            for c in cells_raw
        )
        return cls(
            factorial_id=_as_str(data.get("factorial_id"), "factorial_id"),
            seeds=tuple(int(s) for s in (data.get("seeds") or ())),  # type: ignore[arg-type]
            ticks=_as_int(data.get("ticks"), "ticks", minimum=0),
            cells=cells,
            claim_ceiling=_as_str(
                data.get("claim_ceiling", "runtime_observation"), "claim_ceiling"
            ),
            smoke_only=_as_bool(data.get("smoke_only", False), "smoke_only"),
            refuse_list=tuple(str(x) for x in (data.get("refuse_list") or ())),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
            red_queen_proved=_as_bool(
                data.get("red_queen_proved", False), "red_queen_proved"
            ),
            intervention_supported=_as_bool(
                data.get("intervention_supported", False), "intervention_supported"
            ),
            raises_claim_ladder=_as_bool(
                data.get("raises_claim_ladder", False), "raises_claim_ladder"
            ),
            mutualism_equals_success=_as_bool(
                data.get("mutualism_equals_success", False), "mutualism_equals_success"
            ),
            continuum_physics_source=_as_str(
                data.get("continuum_physics_source", CONTINUUM_PHYSICS_SOURCE),
                "continuum_physics_source",
            ),
        )


def run_continuum_factorial(
    *,
    factorial_id: str,
    seeds: Sequence[int],
    ticks: int = 2,
    coupling_levels: Sequence[float] = (0.1, 0.5),
    spatial_modes: Sequence[str] = ("well_mixed", "local_neighborhood"),
    inherit_levels: Sequence[float] = (0.0, 0.5),
    match_score_scales: Sequence[float] = (1.0,),
    smoke_only: bool = True,
    claim_ceiling: str = "runtime_observation",
    interaction_value_compat: float | None = None,
) -> ContinuumFactorialResult:
    """Run World-backed continuum factorial; digests differ when axes change."""

    seed_t = tuple(_as_int(s, "seed", minimum=0) for s in seeds)
    if not seed_t:
        raise ConfigurationError("seeds required.")
    tick_n = _as_int(ticks, "ticks", minimum=0)
    cells: list[ContinuumCellResult] = []
    for seed in seed_t:
        for coupling in coupling_levels:
            for spatial in spatial_modes:
                for inherit in inherit_levels:
                    for scale in match_score_scales:
                        spatial_s = _as_str(spatial, "spatial_mode").casefold()
                        cell_id = (
                            f"c_s{seed}_k{coupling}_sp{spatial_s}"
                            f"_vt{inherit}_ms{scale}"
                        )
                        # Sanitize dots in id.
                        cell_id = cell_id.replace(".", "p")
                        raw = _run_world_cell(
                            profile_id=f"p_{cell_id}"[:48],
                            seed=seed,
                            ticks=tick_n,
                            coupling_amount=float(coupling),
                            spatial_mode=spatial_s,
                            inherit_probability=float(inherit),
                            match_score_scale=float(scale),
                        )
                        cells.append(
                            ContinuumCellResult(
                                cell_id=cell_id,
                                seed=seed,
                                ticks=tick_n,
                                coupling_amount=float(coupling),
                                spatial_mode=spatial_s,
                                inherit_probability=float(inherit),
                                match_score_scale=float(scale),
                                emergent_interaction_proxy=float(
                                    raw["emergent_interaction_proxy"]
                                ),
                                coexistence_min_density=float(
                                    raw["coexistence_min_density"]
                                ),
                                meter_digest=str(raw["meter_digest"]),
                                world_digest=str(raw["world_digest"]),
                                census=dict(raw["census"]),
                                related_totals={
                                    k: float(v)
                                    for k, v in dict(raw["related_totals"]).items()
                                },
                                interaction_value_compat=interaction_value_compat,
                            )
                        )
    return ContinuumFactorialResult(
        factorial_id=factorial_id,
        seeds=seed_t,
        ticks=tick_n,
        cells=tuple(cells),
        claim_ceiling=claim_ceiling,
        smoke_only=_as_bool(smoke_only, "smoke_only"),
    )


@dataclass(frozen=True, slots=True)
class InterventionArmResult:
    """One intervention / ablation arm observed on World meters."""

    arm_id: str
    schedule_arm: str
    ablation_preset: str
    seed: int
    ticks: int
    primary_channel: str
    channel_value: float
    meter_digest: str
    world_digest: str
    arm_digest: str = ""

    def __post_init__(self) -> None:
        aid = _refuse_banned_fragment(_as_str(self.arm_id, "arm_id"), "arm_id")
        object.__setattr__(self, "arm_id", aid)
        sched = _as_str(self.schedule_arm, "schedule_arm").casefold()
        if sched not in SCHEDULE_ARMS:
            raise ConfigurationError(f"unknown schedule_arm {self.schedule_arm!r}.")
        object.__setattr__(self, "schedule_arm", sched)
        abl = _as_str(self.ablation_preset, "ablation_preset").casefold()
        if abl not in ABLATION_PRESETS:
            raise ConfigurationError(f"unknown ablation_preset {self.ablation_preset!r}.")
        object.__setattr__(self, "ablation_preset", abl)
        object.__setattr__(self, "seed", _as_int(self.seed, "seed", minimum=0))
        object.__setattr__(self, "ticks", _as_int(self.ticks, "ticks", minimum=0))
        ch = _refuse_banned_fragment(
            _as_str(self.primary_channel, "primary_channel"), "primary_channel"
        )
        object.__setattr__(self, "primary_channel", ch)
        object.__setattr__(
            self,
            "channel_value",
            float(require_finite_float("channel_value", self.channel_value)),
        )
        object.__setattr__(self, "meter_digest", _as_str(self.meter_digest, "meter_digest"))
        object.__setattr__(self, "world_digest", _as_str(self.world_digest, "world_digest"))
        computed = canonical_digest(self._body(), prefix="hp_int_arm")
        object.__setattr__(
            self, "arm_digest", _check_digest(self.arm_digest, computed, "InterventionArmResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "arm_id": self.arm_id,
            "schedule_arm": self.schedule_arm,
            "ablation_preset": self.ablation_preset,
            "seed": self.seed,
            "ticks": self.ticks,
            "primary_channel": self.primary_channel,
            "channel_value": self.channel_value,
            "meter_digest": self.meter_digest,
            "world_digest": self.world_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "arm_digest": self.arm_digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> InterventionArmResult:
        return cls(
            arm_id=_as_str(data.get("arm_id"), "arm_id"),
            schedule_arm=_as_str(data.get("schedule_arm"), "schedule_arm"),
            ablation_preset=_as_str(data.get("ablation_preset"), "ablation_preset"),
            seed=_as_int(data.get("seed"), "seed", minimum=0),
            ticks=_as_int(data.get("ticks"), "ticks", minimum=0),
            primary_channel=_as_str(data.get("primary_channel"), "primary_channel"),
            channel_value=float(
                require_finite_float("channel_value", data.get("channel_value"))
            ),
            meter_digest=_as_str(data.get("meter_digest"), "meter_digest"),
            world_digest=_as_str(data.get("world_digest"), "world_digest"),
            arm_digest=_as_str(data.get("arm_digest", ""), "arm_digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class InterventionContrastResult:
    """Refuse-safe intervention contrast with identifiable-bounds language."""

    contrast_id: str
    control_arm_id: str
    arms: tuple[InterventionArmResult, ...]
    effect_delta: float
    effect_lower: float
    effect_upper: float
    identifiability: str = "observational_bounds"
    claim_role: str = "exploratory"
    claim_ceiling: str = "runtime_observation"
    smoke_only: bool = False
    science_grade: bool = False
    refuse_list: tuple[str, ...] = ()
    digest: str = ""
    intervention_supported: bool = False
    red_queen_proved: bool = False
    raises_claim_ladder: bool = False

    def __post_init__(self) -> None:
        cid = _refuse_banned_fragment(
            _as_str(self.contrast_id, "contrast_id"), "contrast_id"
        )
        object.__setattr__(self, "contrast_id", cid)
        object.__setattr__(
            self,
            "control_arm_id",
            _refuse_banned_fragment(
                _as_str(self.control_arm_id, "control_arm_id"), "control_arm_id"
            ),
        )
        if not self.arms:
            raise ConfigurationError("arms must be non-empty.")
        object.__setattr__(self, "arms", tuple(self.arms))
        arm_ids = {a.arm_id for a in self.arms}
        if self.control_arm_id not in arm_ids:
            raise ConfigurationError("control_arm_id must be present in arms.")
        role = _as_str(self.claim_role, "claim_role").casefold()
        if role not in {"primary", "exploratory", "smoke"}:
            raise ConfigurationError("claim_role must be primary, exploratory, or smoke.")
        smoke = _as_bool(self.smoke_only, "smoke_only")
        science = _as_bool(self.science_grade, "science_grade")
        if role == "smoke" or smoke:
            if role == "primary":
                raise ConfigurationError("smoke_only cannot use claim_role=primary.")
            science = False
        if role == "primary":
            has_dual = any(a.ablation_preset == "dual_null" for a in self.arms)
            if not has_dual:
                raise ConfigurationError(
                    "primary intervention contrast requires a dual_null arm."
                )
        object.__setattr__(self, "claim_role", role)
        object.__setattr__(self, "smoke_only", smoke)
        object.__setattr__(self, "science_grade", science)
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        ident = _as_str(self.identifiability, "identifiability")
        if ident != "observational_bounds":
            raise ConfigurationError(
                "identifiability must be observational_bounds (no causal_proved)."
            )
        object.__setattr__(self, "identifiability", ident)
        object.__setattr__(
            self, "effect_delta", float(require_finite_float("effect_delta", self.effect_delta))
        )
        object.__setattr__(
            self, "effect_lower", float(require_finite_float("effect_lower", self.effect_lower))
        )
        object.__setattr__(
            self, "effect_upper", float(require_finite_float("effect_upper", self.effect_upper))
        )
        if self.effect_lower > self.effect_upper:
            raise ConfigurationError("effect_lower must be <= effect_upper.")
        object.__setattr__(self, "refuse_list", _merge_refuses(self.refuse_list))
        if self.intervention_supported:
            raise ConfigurationError("refuses intervention_supported=True.")
        if self.red_queen_proved:
            raise ConfigurationError("refuses red_queen_proved=True.")
        if self.raises_claim_ladder:
            raise ConfigurationError("refuses raises_claim_ladder=True.")
        object.__setattr__(self, "intervention_supported", False)
        object.__setattr__(self, "red_queen_proved", False)
        object.__setattr__(self, "raises_claim_ladder", False)
        computed = canonical_digest(self._body(), prefix="hp_int_ctr")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "InterventionContrastResult"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema": SCHEMA_INTERVENTION,
            "contrast_id": self.contrast_id,
            "control_arm_id": self.control_arm_id,
            "arms": [a.to_dict() for a in self.arms],
            "effect_delta": self.effect_delta,
            "effect_lower": self.effect_lower,
            "effect_upper": self.effect_upper,
            "identifiability": self.identifiability,
            "claim_role": self.claim_role,
            "claim_ceiling": self.claim_ceiling,
            "smoke_only": self.smoke_only,
            "science_grade": self.science_grade,
            "refuse_list": list(self.refuse_list),
            "intervention_supported": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "claim_status": "observational_bounds_only",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> InterventionContrastResult:
        arms_raw = data.get("arms")
        if not isinstance(arms_raw, Sequence):
            raise ConfigurationError("arms must be a sequence.")
        arms = tuple(
            InterventionArmResult.from_dict(a)  # type: ignore[arg-type]
            for a in arms_raw
        )
        return cls(
            contrast_id=_as_str(data.get("contrast_id"), "contrast_id"),
            control_arm_id=_as_str(data.get("control_arm_id"), "control_arm_id"),
            arms=arms,
            effect_delta=float(
                require_finite_float("effect_delta", data.get("effect_delta"))
            ),
            effect_lower=float(
                require_finite_float("effect_lower", data.get("effect_lower"))
            ),
            effect_upper=float(
                require_finite_float("effect_upper", data.get("effect_upper"))
            ),
            identifiability=_as_str(
                data.get("identifiability", "observational_bounds"), "identifiability"
            ),
            claim_role=_as_str(data.get("claim_role", "exploratory"), "claim_role"),
            claim_ceiling=_as_str(
                data.get("claim_ceiling", "runtime_observation"), "claim_ceiling"
            ),
            smoke_only=_as_bool(data.get("smoke_only", False), "smoke_only"),
            science_grade=_as_bool(data.get("science_grade", False), "science_grade"),
            refuse_list=tuple(str(x) for x in (data.get("refuse_list") or ())),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
            intervention_supported=_as_bool(
                data.get("intervention_supported", False), "intervention_supported"
            ),
            red_queen_proved=_as_bool(
                data.get("red_queen_proved", False), "red_queen_proved"
            ),
            raises_claim_ladder=_as_bool(
                data.get("raises_claim_ladder", False), "raises_claim_ladder"
            ),
        )


def _channel_value(raw: Mapping[str, Any], channel: str) -> float:
    totals = dict(raw.get("related_totals") or {})
    related = dict(raw.get("related_counts") or {})
    if channel in totals:
        return float(totals[channel])
    if channel in related:
        return float(related[channel])
    if channel == "emergent_interaction_proxy":
        return float(raw["emergent_interaction_proxy"])
    if channel == "coexistence_min_density":
        return float(raw["coexistence_min_density"])
    raise ConfigurationError(f"unknown primary_channel {channel!r}.")


def run_intervention_contrast(
    *,
    contrast_id: str,
    seed: int = 0,
    ticks: int = 2,
    control_schedule_arm: str = "none",
    control_ablation_preset: str = "none",
    contrast_schedule_arm: str = "freeze",
    contrast_ablation_preset: str = "none",
    include_dual_null_arm: bool = False,
    primary_channel: str = "coupling_total",
    claim_role: str = "exploratory",
    smoke_only: bool = True,
    claim_ceiling: str = "runtime_observation",
) -> InterventionContrastResult:
    """Compare control vs intervention World arms; never sets intervention_supported."""

    channel = _refuse_banned_fragment(
        _as_str(primary_channel, "primary_channel"), "primary_channel"
    )
    arms_spec: list[tuple[str, str, str]] = [
        ("arm_control", control_schedule_arm, control_ablation_preset),
        ("arm_contrast", contrast_schedule_arm, contrast_ablation_preset),
    ]
    if include_dual_null_arm:
        arms_spec.append(("arm_dual_null", "none", "dual_null"))

    arm_results: list[InterventionArmResult] = []
    values: dict[str, float] = {}
    for arm_id, sched, abl in arms_spec:
        raw = _run_world_cell(
            profile_id=f"p_{contrast_id}_{arm_id}"[:48],
            seed=seed,
            ticks=ticks,
            coupling_amount=0.25,
            spatial_mode="well_mixed",
            inherit_probability=0.0,
            match_score_scale=1.0,
            schedule_arm=sched,
            ablation_preset=abl,
        )
        value = _channel_value(raw, channel)
        values[arm_id] = value
        arm_results.append(
            InterventionArmResult(
                arm_id=arm_id,
                schedule_arm=sched,
                ablation_preset=abl,
                seed=seed,
                ticks=ticks,
                primary_channel=channel,
                channel_value=value,
                meter_digest=str(raw["meter_digest"]),
                world_digest=str(raw["world_digest"]),
            )
        )
    control_v = values["arm_control"]
    contrast_v = values["arm_contrast"]
    delta = contrast_v - control_v
    # Identifiable observational bounds: point delta ± |delta| (wide, honest).
    half = abs(delta)
    return InterventionContrastResult(
        contrast_id=contrast_id,
        control_arm_id="arm_control",
        arms=tuple(arm_results),
        effect_delta=delta,
        effect_lower=delta - half,
        effect_upper=delta + half,
        claim_role=claim_role,
        claim_ceiling=claim_ceiling,
        smoke_only=smoke_only,
        science_grade=False if smoke_only or claim_role != "primary" else False,
    )


@dataclass(frozen=True, slots=True)
class ReciprocalObservationalContrast:
    """Refuse-safe freeze vs unlock (optional replay) observational contrast.

    Lands the Phase 7/8 deferred reciprocal RQ analytics as observation only —
    never soft-passes red_queen_proved.
    """

    contrast_id: str
    seed: int
    ticks: int
    freeze_arm: InterventionArmResult
    unlock_arm: InterventionArmResult
    replay_arm: InterventionArmResult | None
    channel_delta_unlock_minus_freeze: float
    claim_ceiling: str = "runtime_observation"
    smoke_only: bool = True
    refuse_list: tuple[str, ...] = ()
    digest: str = ""
    red_queen_proved: bool = False
    intervention_supported: bool = False
    raises_claim_ladder: bool = False

    def __post_init__(self) -> None:
        cid = _refuse_banned_fragment(
            _as_str(self.contrast_id, "contrast_id"), "contrast_id"
        )
        object.__setattr__(self, "contrast_id", cid)
        object.__setattr__(self, "seed", _as_int(self.seed, "seed", minimum=0))
        object.__setattr__(self, "ticks", _as_int(self.ticks, "ticks", minimum=0))
        if self.freeze_arm.schedule_arm != "freeze":
            raise ConfigurationError("freeze_arm.schedule_arm must be 'freeze'.")
        if self.unlock_arm.schedule_arm != "unlock":
            raise ConfigurationError("unlock_arm.schedule_arm must be 'unlock'.")
        if self.replay_arm is not None and self.replay_arm.schedule_arm != "replay_schedule":
            raise ConfigurationError(
                "replay_arm.schedule_arm must be 'replay_schedule'."
            )
        object.__setattr__(
            self,
            "channel_delta_unlock_minus_freeze",
            float(
                require_finite_float(
                    "channel_delta_unlock_minus_freeze",
                    self.channel_delta_unlock_minus_freeze,
                )
            ),
        )
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        object.__setattr__(self, "smoke_only", _as_bool(self.smoke_only, "smoke_only"))
        object.__setattr__(self, "refuse_list", _merge_refuses(self.refuse_list))
        if self.red_queen_proved:
            raise ConfigurationError("refuses red_queen_proved=True.")
        if self.intervention_supported:
            raise ConfigurationError("refuses intervention_supported=True.")
        if self.raises_claim_ladder:
            raise ConfigurationError("refuses raises_claim_ladder=True.")
        object.__setattr__(self, "red_queen_proved", False)
        object.__setattr__(self, "intervention_supported", False)
        object.__setattr__(self, "raises_claim_ladder", False)
        computed = canonical_digest(self._body(), prefix="hp_recip_obs")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "ReciprocalObservationalContrast"),
        )

    def _body(self) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "schema": SCHEMA_RECIPROCAL,
            "contrast_id": self.contrast_id,
            "seed": self.seed,
            "ticks": self.ticks,
            "freeze_arm": self.freeze_arm.to_dict(),
            "unlock_arm": self.unlock_arm.to_dict(),
            "channel_delta_unlock_minus_freeze": self.channel_delta_unlock_minus_freeze,
            "claim_ceiling": self.claim_ceiling,
            "smoke_only": self.smoke_only,
            "refuse_list": list(self.refuse_list),
            "red_queen_proved": False,
            "intervention_supported": False,
            "raises_claim_ladder": False,
            "claim_status": "observational_only",
            "note": (
                "Refuse-safe reciprocal observational contrast on ScheduleLock "
                "arms; does not prove Red Queen dynamics."
            ),
        }
        if self.replay_arm is not None:
            body["replay_arm"] = self.replay_arm.to_dict()
        return body

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ReciprocalObservationalContrast:
        replay_raw = data.get("replay_arm")
        replay = (
            InterventionArmResult.from_dict(replay_raw)  # type: ignore[arg-type]
            if isinstance(replay_raw, Mapping)
            else None
        )
        return cls(
            contrast_id=_as_str(data.get("contrast_id"), "contrast_id"),
            seed=_as_int(data.get("seed"), "seed", minimum=0),
            ticks=_as_int(data.get("ticks"), "ticks", minimum=0),
            freeze_arm=InterventionArmResult.from_dict(
                data.get("freeze_arm")  # type: ignore[arg-type]
            ),
            unlock_arm=InterventionArmResult.from_dict(
                data.get("unlock_arm")  # type: ignore[arg-type]
            ),
            replay_arm=replay,
            channel_delta_unlock_minus_freeze=float(
                require_finite_float(
                    "channel_delta_unlock_minus_freeze",
                    data.get("channel_delta_unlock_minus_freeze"),
                )
            ),
            claim_ceiling=_as_str(
                data.get("claim_ceiling", "runtime_observation"), "claim_ceiling"
            ),
            smoke_only=_as_bool(data.get("smoke_only", True), "smoke_only"),
            refuse_list=tuple(str(x) for x in (data.get("refuse_list") or ())),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
            red_queen_proved=_as_bool(
                data.get("red_queen_proved", False), "red_queen_proved"
            ),
            intervention_supported=_as_bool(
                data.get("intervention_supported", False), "intervention_supported"
            ),
            raises_claim_ladder=_as_bool(
                data.get("raises_claim_ladder", False), "raises_claim_ladder"
            ),
        )


def run_reciprocal_observational_contrast(
    *,
    contrast_id: str,
    seed: int = 0,
    ticks: int = 2,
    primary_channel: str = "coupling_total",
    include_replay: bool = True,
    smoke_only: bool = True,
    claim_ceiling: str = "runtime_observation",
) -> ReciprocalObservationalContrast:
    """Freeze vs unlock (+ optional replay) observational contrast; RQ stays refuse."""

    channel = _refuse_banned_fragment(
        _as_str(primary_channel, "primary_channel"), "primary_channel"
    )

    def _arm(arm_id: str, sched: str) -> InterventionArmResult:
        raw = _run_world_cell(
            profile_id=f"p_{contrast_id}_{arm_id}"[:48],
            seed=seed,
            ticks=ticks,
            coupling_amount=0.25,
            spatial_mode="well_mixed",
            inherit_probability=0.0,
            match_score_scale=1.0,
            schedule_arm=sched,
            ablation_preset="none",
        )
        return InterventionArmResult(
            arm_id=arm_id,
            schedule_arm=sched,
            ablation_preset="none",
            seed=seed,
            ticks=ticks,
            primary_channel=channel,
            channel_value=_channel_value(raw, channel),
            meter_digest=str(raw["meter_digest"]),
            world_digest=str(raw["world_digest"]),
        )

    freeze = _arm("arm_freeze", "freeze")
    unlock = _arm("arm_unlock", "unlock")
    replay = _arm("arm_replay", "replay_schedule") if include_replay else None
    delta = unlock.channel_value - freeze.channel_value
    return ReciprocalObservationalContrast(
        contrast_id=contrast_id,
        seed=seed,
        ticks=ticks,
        freeze_arm=freeze,
        unlock_arm=unlock,
        replay_arm=replay,
        channel_delta_unlock_minus_freeze=delta,
        claim_ceiling=claim_ceiling,
        smoke_only=smoke_only,
    )


SCHEMA_DID = "host_parasite_did_intervention_v1"


@dataclass(frozen=True, slots=True)
class DidCellResult:
    """One pre/post × treat/control cell on World meters."""

    cell_id: str
    period: str  # "pre" | "post"
    treated: bool
    schedule_arm: str
    ablation_preset: str
    channel_value: float
    meter_digest: str
    world_digest: str
    cell_digest: str = ""

    def __post_init__(self) -> None:
        cid = _refuse_banned_fragment(_as_str(self.cell_id, "cell_id"), "cell_id")
        object.__setattr__(self, "cell_id", cid)
        period = _as_str(self.period, "period").casefold()
        if period not in {"pre", "post"}:
            raise ConfigurationError("period must be 'pre' or 'post'.")
        object.__setattr__(self, "period", period)
        object.__setattr__(self, "treated", _as_bool(self.treated, "treated"))
        sched = _as_str(self.schedule_arm, "schedule_arm").casefold()
        if sched not in SCHEDULE_ARMS:
            raise ConfigurationError(f"unknown schedule_arm {self.schedule_arm!r}.")
        object.__setattr__(self, "schedule_arm", sched)
        abl = _as_str(self.ablation_preset, "ablation_preset").casefold()
        if abl not in ABLATION_PRESETS:
            raise ConfigurationError(f"unknown ablation_preset {self.ablation_preset!r}.")
        object.__setattr__(self, "ablation_preset", abl)
        object.__setattr__(
            self,
            "channel_value",
            float(require_finite_float("channel_value", self.channel_value)),
        )
        object.__setattr__(self, "meter_digest", _as_str(self.meter_digest, "meter_digest"))
        object.__setattr__(self, "world_digest", _as_str(self.world_digest, "world_digest"))
        computed = canonical_digest(self._body(), prefix="hp_did_cell")
        object.__setattr__(
            self, "cell_digest", _check_digest(self.cell_digest, computed, "DidCellResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "cell_id": self.cell_id,
            "period": self.period,
            "treated": self.treated,
            "schedule_arm": self.schedule_arm,
            "ablation_preset": self.ablation_preset,
            "channel_value": self.channel_value,
            "meter_digest": self.meter_digest,
            "world_digest": self.world_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "cell_digest": self.cell_digest}


@dataclass(frozen=True, slots=True)
class DidInterventionContrast:
    """Difference-in-differences contrast; observational_bounds only."""

    contrast_id: str
    cells: tuple[DidCellResult, ...]
    did_estimate: float
    effect_lower: float
    effect_upper: float
    dual_null_delta: float
    identifiability: str = "observational_bounds"
    claim_role: str = "exploratory"
    claim_ceiling: str = "runtime_observation"
    smoke_only: bool = True
    refuse_list: tuple[str, ...] = ()
    digest: str = ""
    intervention_supported: bool = False
    red_queen_proved: bool = False
    price_as_causality: bool = False
    raises_claim_ladder: bool = False

    def __post_init__(self) -> None:
        cid = _refuse_banned_fragment(
            _as_str(self.contrast_id, "contrast_id"), "contrast_id"
        )
        object.__setattr__(self, "contrast_id", cid)
        if len(self.cells) < 4:
            raise ConfigurationError("DiD requires at least 4 cells (2x2 design).")
        object.__setattr__(self, "cells", tuple(self.cells))
        object.__setattr__(
            self,
            "did_estimate",
            float(require_finite_float("did_estimate", self.did_estimate)),
        )
        object.__setattr__(
            self,
            "effect_lower",
            float(require_finite_float("effect_lower", self.effect_lower)),
        )
        object.__setattr__(
            self,
            "effect_upper",
            float(require_finite_float("effect_upper", self.effect_upper)),
        )
        if self.effect_lower > self.effect_upper:
            raise ConfigurationError("effect_lower must be <= effect_upper.")
        object.__setattr__(
            self,
            "dual_null_delta",
            float(require_finite_float("dual_null_delta", self.dual_null_delta)),
        )
        ident = _as_str(self.identifiability, "identifiability")
        if ident != "observational_bounds":
            raise ConfigurationError(
                "identifiability must be observational_bounds (no causal_proved)."
            )
        object.__setattr__(self, "identifiability", ident)
        role = _as_str(self.claim_role, "claim_role").casefold()
        if role not in {"primary", "exploratory", "smoke"}:
            raise ConfigurationError("claim_role must be primary, exploratory, or smoke.")
        object.__setattr__(self, "claim_role", role)
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        object.__setattr__(self, "smoke_only", _as_bool(self.smoke_only, "smoke_only"))
        object.__setattr__(self, "refuse_list", _merge_refuses(self.refuse_list))
        if self.intervention_supported:
            raise ConfigurationError("refuses intervention_supported=True.")
        if self.red_queen_proved:
            raise ConfigurationError("refuses red_queen_proved=True.")
        if self.price_as_causality:
            raise ConfigurationError("refuses price_as_causality=True.")
        if self.raises_claim_ladder:
            raise ConfigurationError("refuses raises_claim_ladder=True.")
        object.__setattr__(self, "intervention_supported", False)
        object.__setattr__(self, "red_queen_proved", False)
        object.__setattr__(self, "price_as_causality", False)
        object.__setattr__(self, "raises_claim_ladder", False)
        computed = canonical_digest(self._body(), prefix="hp_did_ctr")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "DidInterventionContrast"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema": SCHEMA_DID,
            "contrast_id": self.contrast_id,
            "cells": [c.to_dict() for c in self.cells],
            "did_estimate": self.did_estimate,
            "effect_lower": self.effect_lower,
            "effect_upper": self.effect_upper,
            "dual_null_delta": self.dual_null_delta,
            "identifiability": self.identifiability,
            "claim_role": self.claim_role,
            "claim_ceiling": self.claim_ceiling,
            "smoke_only": self.smoke_only,
            "refuse_list": list(self.refuse_list),
            "intervention_supported": False,
            "red_queen_proved": False,
            "price_as_causality": False,
            "raises_claim_ladder": False,
            "claim_status": "observational_bounds_only",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def run_did_intervention_contrast(
    *,
    contrast_id: str,
    seed: int = 0,
    pre_ticks: int = 1,
    post_ticks: int = 2,
    control_schedule_arm: str = "none",
    treat_schedule_arm: str = "freeze",
    primary_channel: str = "coupling_total",
    claim_role: str = "exploratory",
    smoke_only: bool = True,
    claim_ceiling: str = "runtime_observation",
) -> DidInterventionContrast:
    """2×2 DiD on ScheduleLock arms + dual_null post cell; never causal_proved.

    Design:
      pre-control, pre-treat (both schedule=none, short ticks),
      post-control (control_schedule_arm), post-treat (treat_schedule_arm),
      plus a dual_null post cell for honesty contrast.
    did = (post_treat - pre_treat) - (post_control - pre_control)
    """

    channel = _refuse_banned_fragment(
        _as_str(primary_channel, "primary_channel"), "primary_channel"
    )
    specs: list[tuple[str, str, bool, str, str, int]] = [
        ("pre_control", "pre", False, "none", "none", pre_ticks),
        ("pre_treat", "pre", True, "none", "none", pre_ticks),
        ("post_control", "post", False, control_schedule_arm, "none", post_ticks),
        ("post_treat", "post", True, treat_schedule_arm, "none", post_ticks),
        ("post_dual_null", "post", False, "none", "dual_null", post_ticks),
    ]
    cells: list[DidCellResult] = []
    values: dict[str, float] = {}
    for cell_id, period, treated, sched, abl, ticks in specs:
        raw = _run_world_cell(
            profile_id=f"did_{contrast_id}_{cell_id}"[:48],
            seed=seed,
            ticks=ticks,
            coupling_amount=0.25,
            spatial_mode="well_mixed",
            inherit_probability=0.0,
            match_score_scale=1.0,
            schedule_arm=sched,
            ablation_preset=abl,
        )
        value = _channel_value(raw, channel)
        values[cell_id] = value
        cells.append(
            DidCellResult(
                cell_id=cell_id,
                period=period,
                treated=treated,
                schedule_arm=sched,
                ablation_preset=abl,
                channel_value=value,
                meter_digest=str(raw["meter_digest"]),
                world_digest=str(raw["world_digest"]),
            )
        )
    did = (values["post_treat"] - values["pre_treat"]) - (
        values["post_control"] - values["pre_control"]
    )
    dual_delta = values["post_dual_null"] - values["post_control"]
    half = abs(did)
    return DidInterventionContrast(
        contrast_id=contrast_id,
        cells=tuple(cells),
        did_estimate=did,
        effect_lower=did - half,
        effect_upper=did + half,
        dual_null_delta=dual_delta,
        claim_role=claim_role,
        claim_ceiling=claim_ceiling,
        smoke_only=smoke_only,
    )
