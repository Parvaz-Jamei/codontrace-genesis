"""Closed-loop P1: optional HP life plugin hooked from step_population.

Domain-free: mutates GenesisOrganism genomes via core Mutation + RNG.
No infection vocabulary. Never writes a parallel ATP bag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.organism import GenesisOrganism
from codontrace.mutation import Mutation
from codontrace.rng import RNGManager

ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"
ID_PREFIX_PRIMARY = "clp1_primary_"
ID_PREFIX_SECONDARY = "clp1_secondary_"


@dataclass(frozen=True, slots=True)
class ClosedLoopHPLifeConfig:
    """Opt-in closed-loop HP life plugin (P1)."""

    enabled: bool = False
    mutate_both_roles: bool = True
    point_mutation_per_tick: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "mutate_both_roles": self.mutate_both_roles,
            "point_mutation_per_tick": self.point_mutation_per_tick,
        }

    @classmethod
    def from_dict(cls, data: object) -> ClosedLoopHPLifeConfig:
        if not isinstance(data, dict):
            return cls()
        return cls(
            enabled=bool(data.get("enabled", False)),
            mutate_both_roles=bool(data.get("mutate_both_roles", True)),
            point_mutation_per_tick=bool(data.get("point_mutation_per_tick", True)),
        )


def role_of(organism_id: str) -> str | None:
    if organism_id.startswith(ID_PREFIX_PRIMARY):
        return ROLE_PRIMARY
    if organism_id.startswith(ID_PREFIX_SECONDARY):
        return ROLE_SECONDARY
    return None


def apply_closed_loop_hp_life(
    organisms: Sequence[GenesisOrganism],
    *,
    config: ClosedLoopHPLifeConfig,
    seed: int,
    tick: int,
) -> list[GenesisOrganism]:
    """Point-mutate every role-tagged organism via core Mutation (both roles)."""

    if not config.enabled:
        return list(organisms)
    if not config.mutate_both_roles or not config.point_mutation_per_tick:
        return list(organisms)

    out: list[GenesisOrganism] = []
    for org in organisms:
        role = role_of(org.id)
        if role is None:
            out.append(org)
            continue
        # Deterministic per (seed, role, id, tick); core Mutation owns validity.
        stream = RNGManager(seed=seed).fork(f"clp1/{role}/{org.id}/{tick}")
        point_seed = int(stream.randrange(0, 2**31))
        new_genome = Mutation.point(seed=point_seed).apply(org.genome)
        org.genome = new_genome
        out.append(org)
    return out


def assert_single_atp_owner(organisms: Sequence[GenesisOrganism]) -> None:
    """Every organism must expose atp_state (no parallel HP accounts bag)."""

    for org in organisms:
        if not hasattr(org, "atp_state") or org.atp_state is None:
            raise ConfigurationError(f"organism {org.id} missing atp_state (two energy clocks)")
