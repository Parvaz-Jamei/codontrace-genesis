"""Phase 6 — HostParasiteWorld thin configuration profile + locked-digest adapter.

CodonTrace module: configures life_loop primitives; does not reimplement tick
physics, ATP economy, or replay. Domain role labels stay on the profile map;
life_loop ids remain opaque. ClaimGate compatibility is read-only and must not
invent allows. Positioning: CodonTrace is an independent engine — design and
novelty baseline is our life_loop/contracts, not a peer platform.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from dataclasses import replace

from codontrace._types import JsonValue
from codontrace.contracts import world_digest
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.energy import ATPAccount
from codontrace.errors import ConfigurationError
from codontrace.genome import SemanticGenome
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.host_parasite_he_hp_refresh import (
    validate_he_hp_locked_pack,
)
from codontrace.genesis.host_parasite_metrics import (
    HostParasiteMetricSummary,
    HostParasitePreregSpec,
    build_metric_summary,
)
from codontrace.mutation import Mutation
from codontrace.rng import RNGManager
from codontrace.life_loop import (
    AblationTemplate,
    AttachmentBook,
    AttachmentSlot,
    ContactTransferPolicy,
    EnergyCoupling,
    InheritAttachedPolicy,
    InheritAttemptCensus,
    PopulationRegistry,
    ScheduleLock,
    ScheduleLockState,
    apply_ablation,
    apply_birth_inherit,
    apply_contact,
    apply_schedule_lock,
    resolve_member_state,
    HookMeter,
    MatchRuleSpec,
    PhenotypeMap,
    bind_match_rule,
    evaluate_match,
    spec_for_mode,
)

SCHEMA_VERSION = "host_parasite_world_profile_v1"
ADAPTER_SCHEMA = "host_parasite_locked_digest_adapter_v1"

SpatialMode = Literal["well_mixed", "local_neighborhood"]
AblationPreset = Literal["none", "content_null", "structure_null", "dual_null"]
ScheduleArm = Literal["none", "freeze", "replay_schedule", "unlock"]
MatchRuleId = Literal["always", "never", "feature_overlap", "allele_match"]
InheritModeName = Literal["none", "copy", "share"]

SPATIAL_MODES: frozenset[str] = frozenset({"well_mixed", "local_neighborhood"})
ABLATION_PRESETS: frozenset[str] = frozenset(
    {"none", "content_null", "structure_null", "dual_null"}
)
SCHEDULE_ARMS: frozenset[str] = frozenset(
    {"none", "freeze", "replay_schedule", "unlock"}
)
MATCH_RULE_IDS: frozenset[str] = frozenset({"always", "never", "feature_overlap", "allele_match"})
INHERIT_MODES: frozenset[str] = frozenset({"none", "copy", "share"})

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HE_HP_PATH = _REPO_ROOT / "docs" / "hard_experiment_hp" / "locked_campaign_digests.json"
_BAIC_PINS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)

_DEFAULT_ROLE_MAP: dict[str, str] = {"primary": "pop_a", "secondary": "pop_b"}


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


def _as_unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _as_nonneg(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0:
        raise ConfigurationError(f"{name} must be >= 0.")
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


def _build_match_rule(
    profile: "HostParasiteProfile",
    phenotype_map: PhenotypeMap,
) -> Callable[[str, str], bool | float]:
    """Bind a contact MatchRule from profile match_rule_id + phenotype map."""

    rule_id = profile.match_rule_id
    if rule_id == "always":
        return bind_match_rule(spec_for_mode("always", spec_id=f"spec_{profile.profile_id}"))
    if rule_id == "never":
        return bind_match_rule(spec_for_mode("never", spec_id=f"spec_{profile.profile_id}"))
    if rule_id == "feature_overlap":
        spec = MatchRuleSpec(
            spec_id=f"spec_{profile.profile_id}_overlap",
            mode="feature_overlap",
            threshold=profile.match_threshold,
            score_scale=profile.match_score_scale,
            allele_mode_enabled=False,
        )
        return bind_match_rule(spec, phenotype_map)
    if rule_id == "allele_match":
        spec = MatchRuleSpec(
            spec_id=f"spec_{profile.profile_id}_allele",
            mode="allele_match",
            threshold=profile.match_threshold,
            score_scale=profile.match_score_scale,
            allele_mode_enabled=True,
        )
        return bind_match_rule(spec, phenotype_map)
    raise ConfigurationError(f"unknown match_rule_id {rule_id!r}.")


def _phenotype_map_for(profile: "HostParasiteProfile") -> PhenotypeMap:
    """Build opaque PhenotypeMap from profile.phenotype_tags (labels stay out of kernel)."""

    tags = dict(profile.phenotype_tags)
    members = list(profile.primary_members) + list(profile.secondary_members)
    for mid in members:
        tags.setdefault(mid, ())
    return PhenotypeMap.from_tag_mapping(
        map_id=f"pheno_{profile.profile_id}",
        tags_by_member=tags,
    )


def assert_baic_pins_untouched() -> None:
    """Fail closed if Phase 0 BAIC pin bytes drifted."""

    for rel, expected in _BAIC_PINS:
        path = _REPO_ROOT / rel
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != expected:
            raise ConfigurationError(f"BAIC pin drift for {rel}: got {got}")


@dataclass(frozen=True, slots=True)
class HostParasiteProfile:
    """Immutable configuration profile wiring life_loop primitives."""

    profile_id: str
    seed: int
    role_population_ids: Mapping[str, str] = field(
        default_factory=lambda: dict(_DEFAULT_ROLE_MAP)
    )
    slot_capacity: int = 1
    coupling_amount: float = 0.1
    coupling_loss_fraction: float = 0.0
    match_rule_id: str = "always"
    contact_probability: float = 1.0
    inherit_probability: float = 0.0
    inherit_mode: str = "none"
    spatial_mode: str = "well_mixed"
    ablation_preset: str = "none"
    schedule_arm: str = "none"
    schedule_target_role: str = "secondary"
    primary_members: tuple[str, ...] = ("a0", "a1")
    secondary_members: tuple[str, ...] = ("b0",)
    initial_energy: float = 10.0
    match_threshold: float = 0.0
    match_score_scale: float = 1.0
    phenotype_tags: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    birth_probability_primary: float = 0.0
    birth_probability_secondary: float = 0.0
    death_probability_primary: float = 0.0
    death_probability_secondary: float = 0.0
    mutation_probability_primary: float = 0.0
    mutation_probability_secondary: float = 0.0
    max_population_primary: int = 64
    max_population_secondary: int = 64
    birth_energy_cost: float = 1.0
    basal_energy_cost: float = 0.0
    founder_genome_compact: str = "000000"
    digest: str = ""

    def __post_init__(self) -> None:
        pid = _refuse_banned_fragment(
            _as_str(self.profile_id, "profile_id"), "profile_id"
        )
        object.__setattr__(self, "profile_id", pid)
        object.__setattr__(self, "seed", _as_int(self.seed, "seed", minimum=0))
        if not isinstance(self.role_population_ids, Mapping) or not self.role_population_ids:
            raise ConfigurationError("role_population_ids must be a non-empty mapping.")
        cleaned_roles: dict[str, str] = {}
        for role, pop in self.role_population_ids.items():
            r = _as_str(role, "role")
            # Role labels may use domain words; wired population ids may not.
            p = _refuse_banned_fragment(_as_str(pop, "population_id"), "population_id")
            cleaned_roles[r] = p
        if "primary" not in cleaned_roles or "secondary" not in cleaned_roles:
            raise ConfigurationError(
                "role_population_ids must include 'primary' and 'secondary'."
            )
        object.__setattr__(self, "role_population_ids", cleaned_roles)
        object.__setattr__(
            self, "slot_capacity", _as_int(self.slot_capacity, "slot_capacity", minimum=1)
        )
        object.__setattr__(
            self, "coupling_amount", _as_nonneg(self.coupling_amount, "coupling_amount")
        )
        object.__setattr__(
            self,
            "coupling_loss_fraction",
            _as_unit_interval(self.coupling_loss_fraction, "coupling_loss_fraction"),
        )
        mid = _as_str(self.match_rule_id, "match_rule_id").casefold()
        if mid not in MATCH_RULE_IDS:
            raise ConfigurationError(f"unknown match_rule_id {self.match_rule_id!r}.")
        object.__setattr__(self, "match_rule_id", mid)
        object.__setattr__(
            self,
            "contact_probability",
            _as_unit_interval(self.contact_probability, "contact_probability"),
        )
        object.__setattr__(
            self,
            "inherit_probability",
            _as_unit_interval(self.inherit_probability, "inherit_probability"),
        )
        imode = _as_str(self.inherit_mode, "inherit_mode").casefold()
        if imode not in INHERIT_MODES:
            raise ConfigurationError(f"unknown inherit_mode {self.inherit_mode!r}.")
        object.__setattr__(self, "inherit_mode", imode)
        spatial = _as_str(self.spatial_mode, "spatial_mode").casefold()
        if spatial not in SPATIAL_MODES:
            raise ConfigurationError(f"unknown spatial_mode {self.spatial_mode!r}.")
        object.__setattr__(self, "spatial_mode", spatial)
        ab = _as_str(self.ablation_preset, "ablation_preset").casefold()
        if ab not in ABLATION_PRESETS:
            raise ConfigurationError(f"unknown ablation_preset {self.ablation_preset!r}.")
        object.__setattr__(self, "ablation_preset", ab)
        arm = _as_str(self.schedule_arm, "schedule_arm").casefold()
        if arm not in SCHEDULE_ARMS:
            raise ConfigurationError(f"unknown schedule_arm {self.schedule_arm!r}.")
        object.__setattr__(self, "schedule_arm", arm)
        target_role = _as_str(self.schedule_target_role, "schedule_target_role")
        if target_role not in cleaned_roles:
            raise ConfigurationError(
                "schedule_target_role must be a key in role_population_ids."
            )
        object.__setattr__(self, "schedule_target_role", target_role)
        primary = tuple(
            _refuse_banned_fragment(_as_str(m, "member_id"), "member_id")
            for m in self.primary_members
        )
        secondary = tuple(
            _refuse_banned_fragment(_as_str(m, "member_id"), "member_id")
            for m in self.secondary_members
        )
        if not primary or not secondary:
            raise ConfigurationError("primary_members and secondary_members required.")
        object.__setattr__(self, "primary_members", primary)
        object.__setattr__(self, "secondary_members", secondary)
        object.__setattr__(
            self, "initial_energy", _as_nonneg(self.initial_energy, "initial_energy")
        )
        object.__setattr__(
            self,
            "match_threshold",
            _as_unit_interval(self.match_threshold, "match_threshold"),
        )
        scale = float(require_finite_float("match_score_scale", self.match_score_scale))
        if scale <= 0.0 or scale > 1.0:
            raise ConfigurationError("match_score_scale must be in (0, 1].")
        object.__setattr__(self, "match_score_scale", scale)
        if not isinstance(self.phenotype_tags, Mapping):
            raise ConfigurationError("phenotype_tags must be a mapping.")
        cleaned_tags: dict[str, tuple[str, ...]] = {}
        for member, tags in self.phenotype_tags.items():
            mid = _refuse_banned_fragment(_as_str(member, "phenotype_tags.member"), "phenotype_tags.member")
            if not isinstance(tags, (list, tuple)):
                raise ConfigurationError("phenotype_tags values must be lists or tuples.")
            cleaned: list[str] = []
            seen: set[str] = set()
            for tag in tags:
                t = _refuse_banned_fragment(_as_str(tag, "phenotype_tag"), "phenotype_tag")
                if t not in seen:
                    seen.add(t)
                    cleaned.append(t)
            cleaned_tags[mid] = tuple(sorted(cleaned))
        object.__setattr__(self, "phenotype_tags", cleaned_tags)
        object.__setattr__(
            self,
            "birth_probability_primary",
            _as_unit_interval(self.birth_probability_primary, "birth_probability_primary"),
        )
        object.__setattr__(
            self,
            "birth_probability_secondary",
            _as_unit_interval(self.birth_probability_secondary, "birth_probability_secondary"),
        )
        object.__setattr__(
            self,
            "death_probability_primary",
            _as_unit_interval(self.death_probability_primary, "death_probability_primary"),
        )
        object.__setattr__(
            self,
            "death_probability_secondary",
            _as_unit_interval(self.death_probability_secondary, "death_probability_secondary"),
        )
        object.__setattr__(
            self,
            "mutation_probability_primary",
            _as_unit_interval(self.mutation_probability_primary, "mutation_probability_primary"),
        )
        object.__setattr__(
            self,
            "mutation_probability_secondary",
            _as_unit_interval(self.mutation_probability_secondary, "mutation_probability_secondary"),
        )
        object.__setattr__(
            self,
            "max_population_primary",
            _as_int(self.max_population_primary, "max_population_primary", minimum=1),
        )
        object.__setattr__(
            self,
            "max_population_secondary",
            _as_int(self.max_population_secondary, "max_population_secondary", minimum=1),
        )
        object.__setattr__(
            self, "birth_energy_cost", _as_nonneg(self.birth_energy_cost, "birth_energy_cost")
        )
        object.__setattr__(
            self, "basal_energy_cost", _as_nonneg(self.basal_energy_cost, "basal_energy_cost")
        )
        genome_compact = _as_str(self.founder_genome_compact, "founder_genome_compact")
        # Validate genome early so profile construction fails closed.
        SemanticGenome.from_compact(genome_compact)
        object.__setattr__(self, "founder_genome_compact", genome_compact)
        computed = canonical_digest(self._body(), prefix="hp_profile")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "HostParasiteProfile")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "seed": self.seed,
            "role_population_ids": dict(sorted(self.role_population_ids.items())),
            "slot_capacity": self.slot_capacity,
            "coupling_amount": self.coupling_amount,
            "coupling_loss_fraction": self.coupling_loss_fraction,
            "match_rule_id": self.match_rule_id,
            "contact_probability": self.contact_probability,
            "inherit_probability": self.inherit_probability,
            "inherit_mode": self.inherit_mode,
            "spatial_mode": self.spatial_mode,
            "ablation_preset": self.ablation_preset,
            "schedule_arm": self.schedule_arm,
            "schedule_target_role": self.schedule_target_role,
            "primary_members": list(self.primary_members),
            "secondary_members": list(self.secondary_members),
            "initial_energy": self.initial_energy,
            "match_threshold": self.match_threshold,
            "match_score_scale": self.match_score_scale,
            "phenotype_tags": {
                key: list(vals)
                for key, vals in sorted(self.phenotype_tags.items())
            },
            "birth_probability_primary": self.birth_probability_primary,
            "birth_probability_secondary": self.birth_probability_secondary,
            "death_probability_primary": self.death_probability_primary,
            "death_probability_secondary": self.death_probability_secondary,
            "mutation_probability_primary": self.mutation_probability_primary,
            "mutation_probability_secondary": self.mutation_probability_secondary,
            "max_population_primary": self.max_population_primary,
            "max_population_secondary": self.max_population_secondary,
            "birth_energy_cost": self.birth_energy_cost,
            "basal_energy_cost": self.basal_energy_cost,
            "founder_genome_compact": self.founder_genome_compact,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HostParasiteProfile:
        roles_raw = data.get("role_population_ids", _DEFAULT_ROLE_MAP)
        if not isinstance(roles_raw, Mapping):
            raise ConfigurationError("role_population_ids must be a mapping.")
        primary_raw = data.get("primary_members", ("a0", "a1"))
        secondary_raw = data.get("secondary_members", ("b0",))
        if not isinstance(primary_raw, (list, tuple)):
            raise ConfigurationError("primary_members must be a list or tuple.")
        if not isinstance(secondary_raw, (list, tuple)):
            raise ConfigurationError("secondary_members must be a list or tuple.")
        return cls(
            profile_id=_as_str(data.get("profile_id"), "profile_id"),
            seed=_as_int(data.get("seed"), "seed", minimum=0),
            role_population_ids={str(k): str(v) for k, v in roles_raw.items()},
            slot_capacity=_as_int(data.get("slot_capacity", 1), "slot_capacity", minimum=1),
            coupling_amount=float(
                require_finite_float("coupling_amount", data.get("coupling_amount", 0.1))
            ),
            coupling_loss_fraction=float(
                require_finite_float(
                    "coupling_loss_fraction", data.get("coupling_loss_fraction", 0.0)
                )
            ),
            match_rule_id=_as_str(data.get("match_rule_id", "always"), "match_rule_id"),
            contact_probability=float(
                require_finite_float(
                    "contact_probability", data.get("contact_probability", 1.0)
                )
            ),
            inherit_probability=float(
                require_finite_float(
                    "inherit_probability", data.get("inherit_probability", 0.0)
                )
            ),
            inherit_mode=_as_str(data.get("inherit_mode", "none"), "inherit_mode"),
            spatial_mode=_as_str(data.get("spatial_mode", "well_mixed"), "spatial_mode"),
            ablation_preset=_as_str(
                data.get("ablation_preset", "none"), "ablation_preset"
            ),
            schedule_arm=_as_str(data.get("schedule_arm", "none"), "schedule_arm"),
            schedule_target_role=_as_str(
                data.get("schedule_target_role", "secondary"), "schedule_target_role"
            ),
            primary_members=tuple(str(x) for x in primary_raw),
            secondary_members=tuple(str(x) for x in secondary_raw),
            initial_energy=float(
                require_finite_float("initial_energy", data.get("initial_energy", 10.0))
            ),
            match_threshold=float(
                require_finite_float("match_threshold", data.get("match_threshold", 0.0))
            ),
            match_score_scale=float(
                require_finite_float(
                    "match_score_scale", data.get("match_score_scale", 1.0)
                )
            ),
            phenotype_tags={
                str(k): tuple(str(t) for t in (v if isinstance(v, (list, tuple)) else ()))
                for k, v in dict(data.get("phenotype_tags") or {}).items()
            },
            birth_probability_primary=float(
                require_finite_float(
                    "birth_probability_primary",
                    data.get("birth_probability_primary", 0.0),
                )
            ),
            birth_probability_secondary=float(
                require_finite_float(
                    "birth_probability_secondary",
                    data.get("birth_probability_secondary", 0.0),
                )
            ),
            death_probability_primary=float(
                require_finite_float(
                    "death_probability_primary",
                    data.get("death_probability_primary", 0.0),
                )
            ),
            death_probability_secondary=float(
                require_finite_float(
                    "death_probability_secondary",
                    data.get("death_probability_secondary", 0.0),
                )
            ),
            mutation_probability_primary=float(
                require_finite_float(
                    "mutation_probability_primary",
                    data.get("mutation_probability_primary", 0.0),
                )
            ),
            mutation_probability_secondary=float(
                require_finite_float(
                    "mutation_probability_secondary",
                    data.get("mutation_probability_secondary", 0.0),
                )
            ),
            max_population_primary=_as_int(
                data.get("max_population_primary", 64), "max_population_primary", minimum=1
            ),
            max_population_secondary=_as_int(
                data.get("max_population_secondary", 64),
                "max_population_secondary",
                minimum=1,
            ),
            birth_energy_cost=float(
                require_finite_float("birth_energy_cost", data.get("birth_energy_cost", 1.0))
            ),
            basal_energy_cost=float(
                require_finite_float("basal_energy_cost", data.get("basal_energy_cost", 0.0))
            ),
            founder_genome_compact=_as_str(
                data.get("founder_genome_compact", "000000"), "founder_genome_compact"
            ),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def population_id(self, role: str) -> str:
        try:
            return self.role_population_ids[role]
        except KeyError as exc:
            raise ConfigurationError(f"unknown role {role!r}.") from exc


@dataclass
class HostParasiteWorld:
    """Facade: wires life_loop primitives from a profile; no private physics loop.

    Demographics (birth/death), attachment, energy coupling, mutation, and
    inherit-attached all run inside ``tick`` via life_loop + core RNG/mutation/
    ATP ledger. ``PopulationRegistry`` is the membership book advanced here —
    not a second engine (see ``life_loop.genesis_path``).
    """

    profile: HostParasiteProfile
    registry: PopulationRegistry = field(init=False)
    book: AttachmentBook = field(init=False)
    balances: dict[str, float] = field(init=False)
    accounts: dict[str, ATPAccount] = field(init=False)
    genomes: dict[str, SemanticGenome] = field(init=False)
    payloads: dict[str, dict[str, JsonValue]] = field(init=False)
    state_bags: dict[str, dict[str, JsonValue]] = field(init=False)
    tick_index: int = field(init=False, default=0)
    _lock_state: ScheduleLockState | None = field(init=False, default=None)
    _ablation_applied: bool = field(init=False, default=False)
    _contact_policy: ContactTransferPolicy = field(init=False)
    _inherit_policy: InheritAttachedPolicy = field(init=False)
    _match_rule: Callable[[str, str], bool | float] = field(init=False)
    phenotype_map: PhenotypeMap = field(init=False)
    _match_spec: MatchRuleSpec = field(init=False)
    meter: HookMeter = field(init=False)
    prereg: HostParasitePreregSpec | None = field(init=False, default=None)
    rng: RNGManager = field(init=False)
    attach_fail_census: dict[str, int] = field(init=False)
    coupling_fail_census: dict[str, int] = field(init=False)
    inherit_fail_census: dict[str, int] = field(init=False)
    birth_counts: dict[str, int] = field(init=False)
    death_counts: dict[str, int] = field(init=False)
    mutation_counts: dict[str, int] = field(init=False)
    outcome_log: list[dict[str, JsonValue]] = field(init=False)
    _birth_seq: int = field(init=False, default=0)
    _inherit_census: InheritAttemptCensus = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.profile, HostParasiteProfile):
            raise ConfigurationError("profile must be a HostParasiteProfile.")
        pop_a = self.profile.population_id("primary")
        pop_b = self.profile.population_id("secondary")
        registry = PopulationRegistry(tick=0)
        registry = registry.create_population(
            pop_a, schedule_partition="part_primary"
        )
        registry = registry.create_population(
            pop_b, schedule_partition="part_secondary"
        )
        for mid in self.profile.primary_members:
            registry, _ = registry.add_member(pop_a, mid)
        for mid in self.profile.secondary_members:
            registry, _ = registry.add_member(pop_b, mid)
        self.registry = registry

        book = AttachmentBook()
        for mid in self.profile.primary_members:
            slot = AttachmentSlot(
                slot_id=f"slot_{mid}",
                owner_id=mid,
                capacity=self.profile.slot_capacity,
                tick=0,
            )
            book = book.add_slot(slot)
        self.book = book

        members = list(self.profile.primary_members) + list(self.profile.secondary_members)
        founder = SemanticGenome.from_compact(self.profile.founder_genome_compact)
        self.accounts = {
            m: ATPAccount(float(self.profile.initial_energy)) for m in members
        }
        self.balances = {m: float(self.accounts[m].current_atp) for m in members}
        self.genomes = {m: founder for m in members}
        self.payloads = {
            m: {"tag": m, "payload": f"p_{m}"} for m in members
        }
        self.state_bags = {
            m: {
                "payload": f"p_{m}",
                "signal": 1,
                "link_tag": "grid",
                "overlap": True,
            }
            for m in members
        }
        self.tick_index = 0
        self._ablation_applied = False
        self._lock_state = None
        self._contact_policy = ContactTransferPolicy(
            rule_id=f"ct_{self.profile.profile_id}",
            transfer_mode="payload_copy",
            candidate_mode=(
                "well_mixed"
                if self.profile.spatial_mode == "well_mixed"
                else "local"
            ),
            payload_keys=("payload",),
        )
        self._inherit_policy = InheritAttachedPolicy(
            policy_id=f"inh_{self.profile.profile_id}",
            mode=self.profile.inherit_mode,  # type: ignore[arg-type]
            probability=self.profile.inherit_probability,
        )
        self.phenotype_map = _phenotype_map_for(self.profile)
        self._match_spec = MatchRuleSpec(
            spec_id=f"spec_{self.profile.profile_id}",
            mode=(
                "feature_overlap"
                if self.profile.match_rule_id == "feature_overlap"
                else (
                    "allele_match"
                    if self.profile.match_rule_id == "allele_match"
                    else self.profile.match_rule_id
                )
            ),
            threshold=self.profile.match_threshold,
            score_scale=self.profile.match_score_scale,
            allele_mode_enabled=(self.profile.match_rule_id == "allele_match"),
        )
        self._match_rule = _build_match_rule(self.profile, self.phenotype_map)
        self.meter = HookMeter(meter_id=f"meter_{self.profile.profile_id}")
        self.prereg = None
        self.rng = RNGManager(seed=self.profile.seed, namespace="hp_world")
        self.attach_fail_census = {}
        self.coupling_fail_census = {}
        self.inherit_fail_census = {}
        self.birth_counts = {"primary": 0, "secondary": 0}
        self.death_counts = {"primary": 0, "secondary": 0}
        self.mutation_counts = {"primary": 0, "secondary": 0}
        self.outcome_log = []
        self._birth_seq = 0
        self._inherit_census = InheritAttemptCensus()
        self._refresh_meter_densities()
        self._record_outcome()

    def _sync_balances_from_accounts(self) -> None:
        self.balances = {
            mid: float(acct.current_atp) for mid, acct in self.accounts.items()
        }

    def _bump_census(self, bag: dict[str, int], reason: str) -> None:
        bag[reason] = int(bag.get(reason, 0)) + 1

    def _record_outcome(self) -> None:
        pop_a = self.profile.population_id("primary")
        pop_b = self.profile.population_id("secondary")
        census = self.census()
        self.outcome_log.append(
            {
                "tick": self.tick_index,
                "census_primary": census["primary"],
                "census_secondary": census["secondary"],
                "extinct_primary": census["primary"] == 0,
                "extinct_secondary": census["secondary"] == 0,
                "coexistence": bool(self.registry.coexistence(pop_a, pop_b)),
            }
        )

    def _refresh_meter_densities(self) -> None:
        """Push opaque population densities + attachment stats into the meter."""

        self.meter.set_tick(self.tick_index)
        densities = {
            self.profile.population_id("primary"): self.registry.census(
                self.profile.population_id("primary")
            ),
            self.profile.population_id("secondary"): self.registry.census(
                self.profile.population_id("secondary")
            ),
        }
        self.meter.set_densities(densities)
        occupancy = 0
        capacity = 0
        for sid in self.book.list_slot_ids():
            slot = self.book.get(sid)
            occupancy += len(slot.occupant_ids)
            capacity += slot.capacity
        self.meter.set_attachment_stats(occupancy=occupancy, capacity=capacity)

    def attach_prereg(self, prereg: HostParasitePreregSpec) -> None:
        """Attach a frozen prereg/spec; refuse overwrite."""

        if not isinstance(prereg, HostParasitePreregSpec):
            raise ConfigurationError("prereg must be a HostParasitePreregSpec.")
        if self.prereg is not None:
            raise ConfigurationError("prereg already attached; refuse overwrite.")
        self.prereg = prereg

    def metric_summary(
        self, *, claim_role: str = "exploratory", summary_id: str | None = None
    ) -> HostParasiteMetricSummary:
        """Build a refuse-safe metric summary from the current meter snapshot."""

        self._refresh_meter_densities()
        snap = self.meter.snapshot()
        unique_payloads = len({str(p.get("payload")) for p in self.payloads.values()})
        sid = summary_id or f"sum_{self.profile.profile_id}_{self.tick_index}"
        return build_metric_summary(
            summary_id=sid,
            meter=snap,
            census=self.census(),
            ablation_preset=self.profile.ablation_preset,
            prereg=self.prereg,
            claim_role=claim_role,
            unique_payloads=unique_payloads,
            labels={
                "domain_profile": "host_parasite",
                "physics_home": "codontrace.life_loop",
            },
        )

    def census(self) -> dict[str, int]:
        """Return census keyed by role (always both roles)."""

        return {
            "primary": self.registry.census(self.profile.population_id("primary")),
            "secondary": self.registry.census(self.profile.population_id("secondary")),
        }

    def extinction_flags(self) -> dict[str, bool]:
        census = self.census()
        return {
            "primary": census["primary"] == 0,
            "secondary": census["secondary"] == 0,
        }

    def coexistence(self) -> bool:
        return bool(
            self.registry.coexistence(
                self.profile.population_id("primary"),
                self.profile.population_id("secondary"),
            )
        )

    def life_loop_snapshot(self) -> dict[str, JsonValue]:
        """Opaque digests for GenesisEngine evidence mirroring (no infection)."""

        self._sync_balances_from_accounts()
        return {
            "tick": self.tick_index,
            "registry_digest": self.registry.digest,
            "book_digest": self.book.digest,
            "census": dict(self.census()),
            "extinct_primary": self.extinction_flags()["primary"],
            "extinct_secondary": self.extinction_flags()["secondary"],
            "coexistence": self.coexistence(),
            "attach_fail_census": dict(sorted(self.attach_fail_census.items())),
            "coupling_fail_census": dict(sorted(self.coupling_fail_census.items())),
            "inherit_fail_census": dict(sorted(self.inherit_fail_census.items())),
            "birth_counts": dict(self.birth_counts),
            "death_counts": dict(self.death_counts),
            "mutation_counts": dict(self.mutation_counts),
            "rng_draw_count": self.rng.draw_count,
            "rng_state_digest": self.rng.state_digest(),
            "energy_ledger_digest": canonical_digest(
                {
                    mid: acct.ledger_digest()
                    for mid, acct in sorted(self.accounts.items())
                },
                prefix="hp_energy",
            ),
            "genome_digest": canonical_digest(
                {
                    mid: g.to_compact()
                    for mid, g in sorted(self.genomes.items())
                },
                prefix="hp_genomes",
            ),
        }

    def _apply_ablation_once(self) -> None:
        if self._ablation_applied:
            return
        template = AblationTemplate(
            arm_id=f"arm_{self.profile.profile_id}",
            mode=self.profile.ablation_preset,  # type: ignore[arg-type]
            content_keys=("payload", "signal"),
            structure_keys=("link_tag", "overlap"),
        )
        for mid, bag in list(self.state_bags.items()):
            record, _ = apply_ablation(template, bag, tick=self.tick_index)
            self.state_bags[mid] = dict(record.bag)  # type: ignore[arg-type]
        self._ablation_applied = True

    def _ensure_schedule_lock(self) -> None:
        arm = self.profile.schedule_arm
        if arm == "none":
            return
        if self._lock_state is not None:
            return
        target_pop = self.profile.population_id(self.profile.schedule_target_role)
        lock_mode = "freeze" if arm == "freeze" else arm
        lock = ScheduleLock(
            schedule_id=f"sched_{self.profile.profile_id}",
            lock_mode=lock_mode,  # type: ignore[arg-type]
            population_id=target_pop,
        )
        live_bags = {
            mid: dict(self.state_bags[mid])
            for mid in self.registry.get(target_pop).member_ids
            if mid in self.state_bags
        }
        state, _record, _census = apply_schedule_lock(
            lock,
            self.registry,
            live_bags,
            tick=self.tick_index,
        )
        self._lock_state = state

    def _apply_basal_energy(self, member_ids: tuple[str, ...]) -> None:
        cost = float(self.profile.basal_energy_cost)
        if cost <= 0.0:
            return
        for mid in member_ids:
            acct = self.accounts.get(mid)
            if acct is None:
                continue
            if acct.can_pay(cost):
                acct.debit(
                    cost,
                    tick=self.tick_index,
                    agent_id=mid,
                    codon="BAS",
                    action="basal",
                    reason="basal_energy_cost",
                )
            else:
                # Drain remaining; starvation handled in death pass.
                rem = float(acct.current_atp)
                if rem > 0.0:
                    acct.debit(
                        rem,
                        tick=self.tick_index,
                        agent_id=mid,
                        codon="BAS",
                        action="basal",
                        reason="basal_partial",
                    )
        self._sync_balances_from_accounts()

    def _attach_whole_population(
        self, primary_ids: tuple[str, ...], secondary_ids: tuple[str, ...]
    ) -> None:
        """Quantitative attachment for every primary/secondary pair with fail census."""

        for holder in primary_ids:
            slot_id = f"slot_{holder}"
            if slot_id not in self.book.list_slot_ids():
                for occupant in secondary_ids:
                    self._bump_census(self.attach_fail_census, "slot_missing")
                continue
            for occupant in secondary_ids:
                slot = self.book.get(slot_id)
                if slot.has_occupant(occupant):
                    self._bump_census(self.attach_fail_census, "already_occupant")
                    continue
                if slot.is_full:
                    self._bump_census(self.attach_fail_census, "seat_full")
                    continue
                try:
                    self.book, _ = self.book.attach(slot_id, occupant)
                    self._bump_census(self.attach_fail_census, "success")
                except ConfigurationError as exc:
                    reason = str(exc)
                    if reason not in {"seat_full", "already_occupant", "self_attach"}:
                        reason = "attach_refused"
                    self._bump_census(self.attach_fail_census, reason)

    def _couple_attached_pairs(
        self, primary_ids: tuple[str, ...], secondary_ids: tuple[str, ...]
    ) -> None:
        """Energy trade for every attached pair via core ATP ledger + EnergyCoupling."""

        self._sync_balances_from_accounts()
        for holder in primary_ids:
            for occupant in secondary_ids:
                attached = self.book.any_link(holder, occupant)
                if not attached:
                    continue
                if holder not in self.balances or occupant not in self.balances:
                    self._bump_census(self.coupling_fail_census, "missing_balance")
                    continue
                coupling = EnergyCoupling(
                    coupling_id=f"ec_{holder}_{occupant}",
                    source_id=holder,
                    target_id=occupant,
                    amount=self.profile.coupling_amount,
                    loss_fraction=self.profile.coupling_loss_fraction,
                )
                try:
                    before = dict(self.balances)
                    new_balances, _event, _entries, _cons = coupling.apply(
                        self.balances,
                        tick=self.tick_index,
                        require_attached=True,
                        attached=True,
                        allow_partial=True,
                    )
                except ConfigurationError as exc:
                    reason = str(exc)
                    if reason not in {
                        "not_attached",
                        "insufficient_energy",
                        "identical_endpoints",
                    }:
                        reason = "coupling_refused"
                    self._bump_census(self.coupling_fail_census, reason)
                    # Gate: never silent-swallow — census always updated.
                    continue
                # Mirror into core ATP ledger end-to-end.
                src_paid = float(before[holder]) - float(new_balances[holder])
                tgt_gain = float(new_balances[occupant]) - float(before[occupant])
                if src_paid > 0.0:
                    paid = self.accounts[holder].debit(
                        src_paid,
                        tick=self.tick_index,
                        agent_id=holder,
                        codon="CPL",
                        action="energy_coupling",
                        reason=f"couple_to_{occupant}",
                    )
                    if paid is None and src_paid > 0.0:
                        self._bump_census(self.coupling_fail_census, "ledger_debit_failed")
                        continue
                if tgt_gain > 0.0:
                    self.accounts[occupant].credit(
                        tgt_gain,
                        tick=self.tick_index,
                        agent_id=occupant,
                        codon="CPL",
                        action="energy_coupling",
                        reason=f"couple_from_{holder}",
                    )
                self._sync_balances_from_accounts()
                self._bump_census(self.coupling_fail_census, "success")
                transferred = float(self.profile.coupling_amount)
                self.meter.record_hook("on_resource")
                self.meter.record_related_total("coupling_total", transferred)
                loss = transferred * float(self.profile.coupling_loss_fraction)
                if loss > 0.0:
                    self.meter.record_related_total("coupling_loss_total", loss)

    def _contact_whole_population(
        self, primary_ids: tuple[str, ...], secondary_ids: tuple[str, ...]
    ) -> None:
        all_ids = tuple(sorted(set(primary_ids) | set(secondary_ids)))
        contact_rng = self.rng.fork(f"contact/{self.tick_index}")
        for holder in primary_ids:
            for occupant in secondary_ids:
                draw = contact_rng.random()
                if draw > self.profile.contact_probability:
                    continue
                neighbors = None
                if self.profile.spatial_mode == "local_neighborhood":
                    neighbors = {
                        holder: list(secondary_ids),
                        occupant: list(primary_ids),
                    }
                new_payloads, new_book, _event, reason, _census = apply_contact(
                    self._contact_policy,
                    actor_id=holder,
                    other_id=occupant,
                    tick=self.tick_index,
                    member_ids=all_ids,
                    payloads=self.payloads,
                    book=self.book,
                    neighbors=neighbors,
                    match_rule=self._match_rule,
                )
                self.payloads = new_payloads
                if new_book is not None:
                    self.book = new_book
                self.meter.record_contact_outcome(
                    reason, success=(reason == "success")
                )
                match_outcome = evaluate_match(
                    self._match_spec,
                    self.phenotype_map,
                    holder,
                    occupant,
                )
                self.meter.record_match_outcome(
                    passed=match_outcome.passed,
                    score=match_outcome.score if match_outcome.passed else 0.0,
                )

    def _mutate_population(self, role: str, member_ids: tuple[str, ...], prob: float) -> None:
        if prob <= 0.0 or not member_ids:
            return
        for mid in member_ids:
            stream = self.rng.fork(f"mutate/{role}/{mid}/{self.tick_index}")
            if stream.random() >= prob:
                continue
            mut = Mutation(operation="point", rng=stream)
            parent = self.genomes[mid]
            child = mut.apply(
                parent,
                parent_id=mid,
                generation=self.tick_index,
            )
            self.genomes[mid] = child
            self.mutation_counts[role] = int(self.mutation_counts.get(role, 0)) + 1

    def _birth_role(
        self,
        role: str,
        member_ids: tuple[str, ...],
        *,
        birth_prob: float,
        max_pop: int,
        owns_slots: bool,
    ) -> None:
        if birth_prob <= 0.0 or not member_ids:
            return
        pop_id = self.profile.population_id(role)
        cost = float(self.profile.birth_energy_cost)
        birth_rng = self.rng.fork(f"birth/{role}/{self.tick_index}")
        # Snapshot parents; births append within this pass.
        parents = list(member_ids)
        for parent_id in parents:
            if self.registry.census(pop_id) >= max_pop:
                break
            if parent_id not in self.accounts:
                continue
            if birth_rng.random() >= birth_prob:
                continue
            acct = self.accounts[parent_id]
            if cost > 0.0 and not acct.can_pay(cost):
                continue
            if cost > 0.0:
                acct.debit(
                    cost,
                    tick=self.tick_index,
                    agent_id=parent_id,
                    codon="BIR",
                    action="birth",
                    reason="birth_energy_cost",
                )
            self._birth_seq += 1
            child_id = f"{parent_id}_c{self.tick_index}_{self._birth_seq}"
            self.registry, _ = self.registry.add_member(pop_id, child_id)
            # Inherit genome then maybe mutate child.
            self.genomes[child_id] = self.genomes[parent_id]
            child_stream = self.rng.fork(f"birth_mut/{role}/{child_id}")
            mut_prob = (
                self.profile.mutation_probability_primary
                if role == "primary"
                else self.profile.mutation_probability_secondary
            )
            if mut_prob > 0.0 and child_stream.random() < mut_prob:
                mut = Mutation(operation="point", rng=child_stream)
                self.genomes[child_id] = mut.apply(
                    self.genomes[child_id],
                    parent_id=parent_id,
                    generation=self.tick_index,
                )
                self.mutation_counts[role] = int(self.mutation_counts.get(role, 0)) + 1
            # Energy endowment for child from remaining parent split is not used;
            # child starts at initial_energy (parameterized trade via coupling).
            self.accounts[child_id] = ATPAccount(float(self.profile.initial_energy))
            self.payloads[child_id] = {"tag": child_id, "payload": f"p_{child_id}"}
            self.state_bags[child_id] = {
                "payload": f"p_{child_id}",
                "signal": 1,
                "link_tag": "grid",
                "overlap": True,
            }
            if owns_slots:
                slot_id = f"slot_{child_id}"
                if slot_id not in self.book.list_slot_ids():
                    self.book = self.book.add_slot(
                        AttachmentSlot(
                            slot_id=slot_id,
                            owner_id=child_id,
                            capacity=self.profile.slot_capacity,
                            tick=self.book.tick,
                        )
                    )
            # Gate 5: InheritAttachedPolicy MUST be invoked on birth.
            parent_slot = f"slot_{parent_id}" if owns_slots else None
            offspring_slot = f"slot_{child_id}" if owns_slots else None
            policy = replace(
                self._inherit_policy,
                parent_slot_id=parent_slot,
                offspring_slot_id=offspring_slot,
                digest="",
            )
            draws = None
            if self.profile.inherit_probability < 1.0:
                n_occ = 0
                if parent_slot and parent_slot in self.book.list_slot_ids():
                    n_occ = len(self.book.get(parent_slot).occupant_ids) or 1
                draws = tuple(
                    self.rng.fork(f"inherit/{child_id}/{i}").random()
                    for i in range(max(1, n_occ))
                )
            self.book, _events, reasons, self._inherit_census = apply_birth_inherit(
                policy,
                self.book,
                parent_id=parent_id,
                offspring_id=child_id,
                tick=self.tick_index,
                draws=draws,
                census=self._inherit_census,
            )
            for reason in reasons:
                self._bump_census(self.inherit_fail_census, reason)
            self.birth_counts[role] = int(self.birth_counts.get(role, 0)) + 1
        self._sync_balances_from_accounts()

    def _death_role(
        self,
        role: str,
        member_ids: tuple[str, ...],
        *,
        death_prob: float,
        owns_slots: bool,
    ) -> None:
        if not member_ids:
            return
        pop_id = self.profile.population_id(role)
        death_rng = self.rng.fork(f"death/{role}/{self.tick_index}")
        for mid in list(member_ids):
            if mid not in self.accounts:
                continue
            energy = float(self.accounts[mid].current_atp)
            # Starvation death only when basal metabolism is enabled (basal>0).
            # Coupling drain alone must not wipe default static-census profiles.
            starved = energy <= 0.0 and float(self.profile.basal_energy_cost) > 0.0
            rolled = death_prob > 0.0 and death_rng.random() < death_prob
            if not starved and not rolled:
                continue
            # Detach from any slots before remove.
            for sid in list(self.book.list_slot_ids()):
                slot = self.book.get(sid)
                if slot.has_occupant(mid):
                    try:
                        self.book, _ = self.book.detach(sid, mid)
                    except ConfigurationError:
                        pass
                if owns_slots and sid == f"slot_{mid}":
                    # Clear occupants then leave slot bookkeeping; remove_slot N/A —
                    # empty owned slots remain harmless; occupants already detached.
                    for occ in list(slot.occupant_ids):
                        try:
                            self.book, _ = self.book.detach(sid, occ)
                        except ConfigurationError:
                            pass
            self.registry, _ = self.registry.remove_member(pop_id, mid)
            self.accounts.pop(mid, None)
            self.genomes.pop(mid, None)
            self.payloads.pop(mid, None)
            self.state_bags.pop(mid, None)
            self.balances.pop(mid, None)
            self.death_counts[role] = int(self.death_counts.get(role, 0)) + 1
        self._sync_balances_from_accounts()

    def tick(self) -> None:
        """Advance one tick: attach, couple, contact, mutate, birth, death."""

        self._apply_ablation_once()
        self._ensure_schedule_lock()

        if self._lock_state is not None and self._lock_state.lock_mode == "freeze":
            for mid in list(self.state_bags):
                resolved, _reason = resolve_member_state(
                    self._lock_state, mid, self.state_bags[mid]
                )
                self.state_bags[mid] = dict(resolved)

        primary_ids = self.registry.get(self.profile.population_id("primary")).member_ids
        secondary_ids = self.registry.get(
            self.profile.population_id("secondary")
        ).member_ids
        living = tuple(sorted(set(primary_ids) | set(secondary_ids)))
        self._apply_basal_energy(living)

        # Re-read after basal (no membership change yet).
        primary_ids = self.registry.get(self.profile.population_id("primary")).member_ids
        secondary_ids = self.registry.get(
            self.profile.population_id("secondary")
        ).member_ids

        self._attach_whole_population(primary_ids, secondary_ids)
        self._couple_attached_pairs(primary_ids, secondary_ids)
        self._contact_whole_population(primary_ids, secondary_ids)

        self._mutate_population(
            "primary", primary_ids, self.profile.mutation_probability_primary
        )
        self._mutate_population(
            "secondary", secondary_ids, self.profile.mutation_probability_secondary
        )

        # Birth then death so both populations can change in one tick.
        self._birth_role(
            "primary",
            primary_ids,
            birth_prob=self.profile.birth_probability_primary,
            max_pop=self.profile.max_population_primary,
            owns_slots=True,
        )
        self._birth_role(
            "secondary",
            secondary_ids,
            birth_prob=self.profile.birth_probability_secondary,
            max_pop=self.profile.max_population_secondary,
            owns_slots=False,
        )

        primary_ids = self.registry.get(self.profile.population_id("primary")).member_ids
        secondary_ids = self.registry.get(
            self.profile.population_id("secondary")
        ).member_ids
        self._death_role(
            "primary",
            primary_ids,
            death_prob=self.profile.death_probability_primary,
            owns_slots=True,
        )
        self._death_role(
            "secondary",
            secondary_ids,
            death_prob=self.profile.death_probability_secondary,
            owns_slots=False,
        )

        self.registry = self.registry.advance_tick(self.tick_index + 1)
        self.book = self.book.advance_tick(self.tick_index + 1)
        self.tick_index += 1
        self._sync_balances_from_accounts()
        self._refresh_meter_densities()
        self._record_outcome()


    def run(self, ticks: int) -> dict[str, JsonValue]:
        """Run ``ticks`` facade ticks; return honesty-forced summary."""

        n = _as_int(ticks, "ticks", minimum=0)
        for _ in range(n):
            self.tick()
        return self.summary()

    def summary(self) -> dict[str, JsonValue]:
        census = self.census()
        self._refresh_meter_densities()
        meter_snap = self.meter.snapshot()
        extras = {
            "profile_digest": self.profile.digest,
            "registry_digest": self.registry.digest,
            "book_digest": self.book.digest,
            "meter_digest": meter_snap.digest,
            "tick": self.tick_index,
            "census": dict(census),
        }
        if self.prereg is not None:
            extras["prereg_digest"] = self.prereg.digest
        digest = world_digest(
            self.profile.seed, self.profile.digest, extras=extras, prefix="hp_world"
        )
        snap = self.life_loop_snapshot()
        out: dict[str, JsonValue] = {
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile.profile_id,
            "profile_digest": self.profile.digest,
            "tick": self.tick_index,
            "census": dict(census),
            "world_digest": digest,
            "meter_digest": meter_snap.digest,
            "hook_counts": dict(meter_snap.hook_counts),
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "ablation_preset": self.profile.ablation_preset,
            "schedule_arm": self.profile.schedule_arm,
            "domain_profile": "host_parasite",
            "physics_home": "codontrace.life_loop",
            "extinct_primary": snap["extinct_primary"],
            "extinct_secondary": snap["extinct_secondary"],
            "coexistence": snap["coexistence"],
            "birth_counts": dict(self.birth_counts),
            "death_counts": dict(self.death_counts),
            "mutation_counts": dict(self.mutation_counts),
            "attach_fail_census": dict(sorted(self.attach_fail_census.items())),
            "coupling_fail_census": dict(sorted(self.coupling_fail_census.items())),
            "inherit_fail_census": dict(sorted(self.inherit_fail_census.items())),
            "life_loop_snapshot": snap,
        }
        if self.prereg is not None:
            out["prereg_digest"] = self.prereg.digest
        return out


@dataclass(frozen=True, slots=True)
class LockedDigestAdapterRecord:
    """Read-only compatibility record for HE_HP / BAIC locked digests."""

    schema: str
    locked_digest: str
    campaign_names: tuple[str, ...]
    baic_pins_untouched: bool
    pack_valid: bool
    raises_claim_ladder: bool
    red_queen_proved: bool
    adapter_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "schema": self.schema,
            "locked_digest": self.locked_digest,
            "campaign_names": list(self.campaign_names),
            "baic_pins_untouched": True,
            "pack_valid": self.pack_valid,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "note": (
                "Read-only map of HE_HP locked digests for the HostParasiteWorld "
                "profile. Does not fork physics or invent ClaimGate allows."
            ),
        }
        body["adapter_digest"] = self.adapter_digest or canonical_digest(
            {k: body[k] for k in body if k != "adapter_digest"},
            prefix="hp_lock_adapter",
        )
        return body


def adapt_locked_digests(
    *,
    pack_path: Path | None = None,
    pack: Mapping[str, object] | None = None,
) -> LockedDigestAdapterRecord:
    """Validate HE_HP pack + BAIC pins; return read-only compatibility record."""

    assert_baic_pins_untouched()
    if pack is None:
        path = pack_path if pack_path is not None else _HE_HP_PATH
        if not path.is_file():
            raise ConfigurationError(f"missing HE_HP locked pack: {path}")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, Mapping):
            raise ConfigurationError("HE_HP locked pack must be a mapping.")
        pack = loaded
    validate_he_hp_locked_pack(pack)
    campaigns = pack.get("campaigns")
    if not isinstance(campaigns, Mapping):
        raise ConfigurationError("HE_HP pack campaigns must be a mapping.")
    names = tuple(sorted(str(k) for k in campaigns.keys()))
    locked_digest = _as_str(pack.get("locked_digest"), "locked_digest")
    record = LockedDigestAdapterRecord(
        schema=ADAPTER_SCHEMA,
        locked_digest=locked_digest,
        campaign_names=names,
        baic_pins_untouched=True,
        pack_valid=True,
        raises_claim_ladder=False,
        red_queen_proved=False,
        adapter_digest="",
    )
    # Recompute with digest filled.
    payload = record.to_dict()
    return LockedDigestAdapterRecord(
        schema=ADAPTER_SCHEMA,
        locked_digest=locked_digest,
        campaign_names=names,
        baic_pins_untouched=True,
        pack_valid=True,
        raises_claim_ladder=False,
        red_queen_proved=False,
        adapter_digest=str(payload["adapter_digest"]),
    )


__all__ = [
    "ADAPTER_SCHEMA",
    "SCHEMA_VERSION",
    "HostParasiteProfile",
    "HostParasiteWorld",
    "LockedDigestAdapterRecord",
    "adapt_locked_digests",
    "assert_baic_pins_untouched",
]
