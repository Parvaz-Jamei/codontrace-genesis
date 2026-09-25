"""Closed-loop HP life plugin hooked from step_population.

Domain-free. Mutates GenesisOrganism genomes via population.mutate_genome + the
live generation RNG stream (no parallel Mutation.point schedule, no parallel ATP bag).

P1 scope (hard): unify + engine-mutate scaffold.
P2 scope: opaque role_by_id map growth on birth (role inheritance).
P3 scope: kappa locus config (transfer lives in closed_loop_p3 via EnergyCoupling).
P4 scope: mutation_stream_lock_roles — skip mutate for locked roles here.
Birth energy partition itself lives in population.reproduce (engine-owned).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.organism import GenesisOrganism
from codontrace.rng import RNGManager

ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"
# Stable opaque tags (not parsed from organism id).
ROLE_TAG_PRIMARY = "clp1.role.primary"
ROLE_TAG_SECONDARY = "clp1.role.secondary"

P1_SCOPE = "unify_mutate_scaffold"
P2_SCOPE = "smith_fretwell_n1_birth_partition"
P3_SCOPE = "scalar_genetic_harm_help_kappa"
P4_SCOPE = "mutation_stream_lock_dual_arm_replay"

# Fixed bit-window for kappa decode (both roles). Post-f(κ) clamp is NOT a gene.
KAPPA_BIT_START = 9
KAPPA_BIT_WIDTH = 6
# Clamp applied after f(κ); never written into gene decode as a default.
KAPPA_TRANSFER_CLAMP = 0.8


@dataclass(frozen=True, slots=True)
class ClosedLoopHPLifeConfig:
    """Opt-in closed-loop HP life plugin (P1 unify+mutate; P2 role map growth)."""

    enabled: bool = False
    mutate_both_roles: bool = True
    # Opaque role map: organism_id -> ROLE_PRIMARY|ROLE_SECONDARY (not id-prefix).
    role_by_id: tuple[tuple[str, str], ...] = ()
    # P3: kappa coupling flags (transfer applied outside engine.py).
    kappa_enabled: bool = False
    kappa_ablate: bool = False
    kappa_bit_start: int = KAPPA_BIT_START
    kappa_bit_width: int = KAPPA_BIT_WIDTH
    # P4: roles whose genomes must not be mutated by this plugin.
    mutation_stream_lock_roles: tuple[str, ...] = ()
    # When locks are active, engine MutationConfig should be rate 0 at birth;
    # unlocked roles mutate here at this rate (None → use mutation_config as-is).
    plugin_bit_flip_rate: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "mutate_both_roles": self.mutate_both_roles,
            "role_by_id": {k: v for k, v in self.role_by_id},
            "kappa_enabled": self.kappa_enabled,
            "kappa_ablate": self.kappa_ablate,
            "kappa_bit_start": self.kappa_bit_start,
            "kappa_bit_width": self.kappa_bit_width,
            "mutation_stream_lock_roles": list(self.mutation_stream_lock_roles),
            "plugin_bit_flip_rate": self.plugin_bit_flip_rate,
            "p1_scope": P1_SCOPE,
            "p2_scope": P2_SCOPE,
            "p3_scope": P3_SCOPE,
            "p4_scope": P4_SCOPE,
        }

    def locked_roles(self) -> frozenset[str]:
        return frozenset(self.mutation_stream_lock_roles)

    @classmethod
    def from_dict(cls, data: object) -> ClosedLoopHPLifeConfig:
        if not isinstance(data, dict):
            return cls()
        raw_roles = data.get("role_by_id", {})
        roles: tuple[tuple[str, str], ...] = ()
        if isinstance(raw_roles, Mapping):
            roles = tuple((str(k), str(v)) for k, v in raw_roles.items())
        raw_locks = data.get("mutation_stream_lock_roles", ())
        locks: tuple[str, ...] = ()
        if isinstance(raw_locks, (list, tuple)):
            locks = tuple(str(item) for item in raw_locks)
        rate_raw = data.get("plugin_bit_flip_rate", None)
        rate: float | None
        if rate_raw is None:
            rate = None
        else:
            rate = float(rate_raw)
        return cls(
            enabled=bool(data.get("enabled", False)),
            mutate_both_roles=bool(data.get("mutate_both_roles", True)),
            role_by_id=roles,
            kappa_enabled=bool(data.get("kappa_enabled", False)),
            kappa_ablate=bool(data.get("kappa_ablate", False)),
            kappa_bit_start=int(data.get("kappa_bit_start", KAPPA_BIT_START)),
            kappa_bit_width=int(data.get("kappa_bit_width", KAPPA_BIT_WIDTH)),
            mutation_stream_lock_roles=locks,
            plugin_bit_flip_rate=rate,
        )

    def role_map(self) -> dict[str, str]:
        return dict(self.role_by_id)


def role_of(organism_id: str, role_by_id: Mapping[str, str] | None = None) -> str | None:
    """Resolve opaque role from explicit map only (never id-prefix parsing)."""

    if role_by_id is None:
        return None
    role = role_by_id.get(organism_id)
    if role in {ROLE_PRIMARY, ROLE_SECONDARY}:
        return role
    return None


def assert_single_atp_owner(organisms: Sequence[GenesisOrganism]) -> None:
    """Every organism must expose atp_state (no parallel HP accounts bag)."""

    for org in organisms:
        if not hasattr(org, "atp_state") or org.atp_state is None:
            raise ConfigurationError(
                f"organism {org.id} missing atp_state (two energy clocks)"
            )


def inherit_roles_for_births(
    role_by_id: Mapping[str, str],
    births: Sequence[tuple[str, str]],
) -> dict[str, str]:
    """Grow opaque role map: each child inherits its parent's role.

    ``births`` entries are ``(parent_id, child_id)``. Unmapped parents are skipped
    (child stays unmapped). Existing child entries are left unchanged.
    """

    roles = dict(role_by_id)
    for parent_id, child_id in births:
        if child_id in roles:
            continue
        parent_role = role_of(parent_id, roles)
        if parent_role is None:
            continue
        roles[child_id] = parent_role
    return roles


def with_inherited_birth_roles(
    config: ClosedLoopHPLifeConfig,
    births: Sequence[tuple[str, str]],
) -> ClosedLoopHPLifeConfig:
    """Return a new config whose role_by_id includes inherited child roles."""

    grown = inherit_roles_for_births(config.role_map(), births)
    return replace(config, role_by_id=tuple(sorted(grown.items())))



def decode_kappa(
    genome_bits: str,
    *,
    bit_start: int = KAPPA_BIT_START,
    bit_width: int = KAPPA_BIT_WIDTH,
    ablate: bool = False,
) -> float:
    """Decode κ ∈ [-1, +1] from a fixed bit window. Ablate forces 0.

    The transfer clamp (0.8) is intentionally NOT part of this decode.
    """

    if ablate:
        return 0.0
    if bit_width <= 0:
        raise ConfigurationError("kappa bit_width must be > 0")
    if bit_start < 0:
        raise ConfigurationError("kappa bit_start must be >= 0")
    bits = str(genome_bits)
    window = bits[bit_start : bit_start + bit_width]
    if len(window) < bit_width:
        window = window.ljust(bit_width, "0")
    if not window or any(ch not in "01" for ch in window):
        return 0.0
    unsigned = int(window, 2)
    max_u = (1 << bit_width) - 1
    if max_u <= 0:
        return 0.0
    return 2.0 * (unsigned / max_u) - 1.0


def kappa_transfer_amount(kappa: float, donor_available: float) -> float:
    """|transfer| = clamp(|f(κ)| × available, 0.8 × donor); f = identity."""

    available = float(donor_available)
    if available <= 0.0:
        return 0.0
    raw = abs(float(kappa)) * available
    ceiling = KAPPA_TRANSFER_CLAMP * available
    return min(raw, ceiling)


def apply_closed_loop_hp_life(
    organisms: Sequence[GenesisOrganism],
    *,
    config: ClosedLoopHPLifeConfig,
    stream: RNGManager,
    mutation_config: object,
    tick: int,
) -> list[GenesisOrganism]:
    """Engine-mutate every role-tagged organism via mutate_genome + live stream.

    Must be invoked post-ATP-settle / pre-birth. Forks the generation stream;
    does not construct a parallel RNGManager(seed=...). Unmapped ids are skipped.
    """

    if not config.enabled:
        return list(organisms)
    assert_single_atp_owner(organisms)
    if not config.mutate_both_roles:
        return list(organisms)

    # Local import avoids circular import with population.py
    from codontrace.genesis.population import MutationConfig, mutate_genome

    if not isinstance(mutation_config, MutationConfig):
        raise ConfigurationError("closed_loop_hp_life requires MutationConfig")

    effective = mutation_config
    if config.plugin_bit_flip_rate is not None:
        effective = replace(
            mutation_config, bit_flip_rate=float(config.plugin_bit_flip_rate)
        )

    roles = config.role_map()
    locked = config.locked_roles()
    out: list[GenesisOrganism] = []
    for org in organisms:
        role = role_of(org.id, roles)
        if role is None:
            out.append(org)
            continue
        if role in locked:
            out.append(org)
            continue
        org_stream = stream.fork(f"clp1/{role}/{org.id}/{tick}")
        result = mutate_genome(org.genome, effective, rng=org_stream)
        org.genome = result.mutated_genome
        out.append(org)
    return out


__all__ = [
    "ROLE_PRIMARY",
    "ROLE_SECONDARY",
    "ROLE_TAG_PRIMARY",
    "ROLE_TAG_SECONDARY",
    "P1_SCOPE",
    "P2_SCOPE",
    "P3_SCOPE",
    "P4_SCOPE",
    "KAPPA_BIT_START",
    "KAPPA_BIT_WIDTH",
    "KAPPA_TRANSFER_CLAMP",
    "ClosedLoopHPLifeConfig",
    "role_of",
    "assert_single_atp_owner",
    "inherit_roles_for_births",
    "with_inherited_birth_roles",
    "decode_kappa",
    "kappa_transfer_amount",
    "apply_closed_loop_hp_life",
]
