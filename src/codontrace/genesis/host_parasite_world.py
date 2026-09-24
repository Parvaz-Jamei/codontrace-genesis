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

from codontrace._types import JsonValue
from codontrace.contracts import world_digest
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.host_parasite_he_hp_refresh import (
    validate_he_hp_locked_pack,
)
from codontrace.life_loop import (
    AblationTemplate,
    AttachmentBook,
    AttachmentSlot,
    ContactTransferPolicy,
    EnergyCoupling,
    InheritAttachedPolicy,
    PopulationRegistry,
    ScheduleLock,
    ScheduleLockState,
    apply_ablation,
    apply_contact,
    apply_schedule_lock,
    resolve_member_state,
)

SCHEMA_VERSION = "host_parasite_world_profile_v1"
ADAPTER_SCHEMA = "host_parasite_locked_digest_adapter_v1"

SpatialMode = Literal["well_mixed", "local_neighborhood"]
AblationPreset = Literal["none", "content_null", "structure_null", "dual_null"]
ScheduleArm = Literal["none", "freeze", "replay_schedule", "unlock"]
MatchRuleId = Literal["always", "never"]
InheritModeName = Literal["none", "copy", "share"]

SPATIAL_MODES: frozenset[str] = frozenset({"well_mixed", "local_neighborhood"})
ABLATION_PRESETS: frozenset[str] = frozenset(
    {"none", "content_null", "structure_null", "dual_null"}
)
SCHEDULE_ARMS: frozenset[str] = frozenset(
    {"none", "freeze", "replay_schedule", "unlock"}
)
MATCH_RULE_IDS: frozenset[str] = frozenset({"always", "never"})
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


def _deterministic_unit(seed: int, tick: int, salt: str) -> float:
    raw = canonical_digest(
        {"seed": seed, "tick": tick, "salt": salt}, prefix="hp_draw"
    )
    hexpart = raw.split(":", 1)[-1]
    return (int(hexpart[:8], 16) % 10_000_000) / 10_000_000.0


def _match_rule_for(rule_id: str) -> Callable[[str, str], bool]:
    if rule_id == "always":
        return lambda _a, _b: True
    if rule_id == "never":
        return lambda _a, _b: False
    raise ConfigurationError(f"unknown match_rule_id {rule_id!r}.")


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
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def population_id(self, role: str) -> str:
        try:
            return self.role_population_ids[role]
        except KeyError as exc:
            raise ConfigurationError(f"unknown role {role!r}.") from exc


@dataclass
class HostParasiteWorld:
    """Facade: wires life_loop primitives from a profile; no private physics loop."""

    profile: HostParasiteProfile
    registry: PopulationRegistry = field(init=False)
    book: AttachmentBook = field(init=False)
    balances: dict[str, float] = field(init=False)
    payloads: dict[str, dict[str, JsonValue]] = field(init=False)
    state_bags: dict[str, dict[str, JsonValue]] = field(init=False)
    tick_index: int = field(init=False, default=0)
    _lock_state: ScheduleLockState | None = field(init=False, default=None)
    _ablation_applied: bool = field(init=False, default=False)
    _contact_policy: ContactTransferPolicy = field(init=False)
    _inherit_policy: InheritAttachedPolicy = field(init=False)
    _match_rule: Callable[[str, str], bool] = field(init=False)

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
        self.balances = {m: float(self.profile.initial_energy) for m in members}
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
        self._match_rule = _match_rule_for(self.profile.match_rule_id)

    def census(self) -> dict[str, int]:
        """Return census keyed by role (always both roles)."""

        return {
            "primary": self.registry.census(self.profile.population_id("primary")),
            "secondary": self.registry.census(self.profile.population_id("secondary")),
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

    def tick(self) -> None:
        """Advance one tick by calling life_loop primitives only."""

        self._apply_ablation_once()
        self._ensure_schedule_lock()

        # Resolve schedule-locked member bags (opaque snapshots).
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
        all_ids = tuple(sorted(set(primary_ids) | set(secondary_ids)))

        # Attachment + energy coupling for first primary/secondary pair when linked.
        if primary_ids and secondary_ids:
            holder = primary_ids[0]
            occupant = secondary_ids[0]
            slot_id = f"slot_{holder}"
            if slot_id in self.book.list_slot_ids():
                slot = self.book.get(slot_id)
                if not slot.has_occupant(occupant) and not slot.is_full:
                    self.book, _ = self.book.attach(slot_id, occupant)
                attached = self.book.any_link(holder, occupant)
                if attached:
                    coupling = EnergyCoupling(
                        coupling_id=f"ec_{holder}_{occupant}",
                        source_id=holder,
                        target_id=occupant,
                        amount=self.profile.coupling_amount,
                        loss_fraction=self.profile.coupling_loss_fraction,
                    )
                    try:
                        new_balances, _, _, _ = coupling.apply(
                            self.balances,
                            tick=self.tick_index,
                            require_attached=True,
                            attached=True,
                            allow_partial=True,
                        )
                        self.balances = new_balances
                    except ConfigurationError:
                        pass

            # Contact transfer (deterministic gate).
            draw = _deterministic_unit(self.profile.seed, self.tick_index, "contact")
            if draw <= self.profile.contact_probability:
                neighbors = None
                if self.profile.spatial_mode == "local_neighborhood":
                    neighbors = {
                        holder: list(secondary_ids),
                        occupant: list(primary_ids),
                    }
                new_payloads, new_book, _, _, _ = apply_contact(
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

        self.registry = self.registry.advance_tick(self.tick_index + 1)
        self.book = self.book.advance_tick(self.tick_index + 1)
        self.tick_index += 1

    def run(self, ticks: int) -> dict[str, JsonValue]:
        """Run ``ticks`` facade ticks; return honesty-forced summary."""

        n = _as_int(ticks, "ticks", minimum=0)
        for _ in range(n):
            self.tick()
        return self.summary()

    def summary(self) -> dict[str, JsonValue]:
        census = self.census()
        extras = {
            "profile_digest": self.profile.digest,
            "registry_digest": self.registry.digest,
            "book_digest": self.book.digest,
            "tick": self.tick_index,
            "census": dict(census),
        }
        digest = world_digest(
            self.profile.seed, self.profile.digest, extras=extras, prefix="hp_world"
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "profile_id": self.profile.profile_id,
            "profile_digest": self.profile.digest,
            "tick": self.tick_index,
            "census": dict(census),
            "world_digest": digest,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "ablation_preset": self.profile.ablation_preset,
            "schedule_arm": self.profile.schedule_arm,
            "domain_profile": "host_parasite",
            "physics_home": "codontrace.life_loop",
        }


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
