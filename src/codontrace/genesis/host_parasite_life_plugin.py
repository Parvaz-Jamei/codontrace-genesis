"""Closed-loop P1: optional HP life plugin hooked from step_population.

Domain-free. Mutates GenesisOrganism genomes via population.mutate_genome + the
live generation RNG stream (no parallel Mutation.point schedule, no parallel ATP bag).

P1 scope (hard): unify + engine-mutate scaffold. Birth/energy-coupling = P2+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class ClosedLoopHPLifeConfig:
    """Opt-in closed-loop HP life plugin (P1 unify+mutate scaffold)."""

    enabled: bool = False
    mutate_both_roles: bool = True
    # Opaque role map: organism_id -> ROLE_PRIMARY|ROLE_SECONDARY (not id-prefix).
    role_by_id: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "mutate_both_roles": self.mutate_both_roles,
            "role_by_id": {k: v for k, v in self.role_by_id},
            "p1_scope": P1_SCOPE,
        }

    @classmethod
    def from_dict(cls, data: object) -> ClosedLoopHPLifeConfig:
        if not isinstance(data, dict):
            return cls()
        raw_roles = data.get("role_by_id", {})
        roles: tuple[tuple[str, str], ...] = ()
        if isinstance(raw_roles, Mapping):
            roles = tuple((str(k), str(v)) for k, v in raw_roles.items())
        return cls(
            enabled=bool(data.get("enabled", False)),
            mutate_both_roles=bool(data.get("mutate_both_roles", True)),
            role_by_id=roles,
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
    does not construct a parallel RNGManager(seed=...).
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

    roles = config.role_map()
    out: list[GenesisOrganism] = []
    for org in organisms:
        role = role_of(org.id, roles)
        if role is None:
            out.append(org)
            continue
        org_stream = stream.fork(f"clp1/{role}/{org.id}/{tick}")
        result = mutate_genome(org.genome, mutation_config, rng=org_stream)
        org.genome = result.mutated_genome
        out.append(org)
    return out


__all__ = [
    "ROLE_PRIMARY",
    "ROLE_SECONDARY",
    "ROLE_TAG_PRIMARY",
    "ROLE_TAG_SECONDARY",
    "P1_SCOPE",
    "ClosedLoopHPLifeConfig",
    "role_of",
    "assert_single_atp_owner",
    "apply_closed_loop_hp_life",
]
