"""Per-organism mating types (sexes) for birth-chamber pairing.

Active only when ``SexualRecombinationConfig.mating_types_enabled`` is True.
An organism's mating type is drawn once, from its own named RNG stream
``genesis/mating_type/<organism_id>`` under the run seed. Because the stream
name depends only on the organism id, the draw never consumes from, or shifts,
any other stream, and the type is the same whichever code path asks first. The
map below records types as organisms are born or first seen; it can be rebuilt
from the seed and ids alone. The population engine keeps the run seed in
``PopulationState.mating_seed`` (captured on the first sexes-on step) and
stores each organism's type once set, so a sex is fixed for life even when a
caller passes a different seed on every step.

Whether an organism enters the chamber at all (outcross vs selfing) is still
decided by the existing heritable outcross locus in the life plugin. This
module only adds the sex check on top of that policy. With sexes on, only a
designated asexual founder lineage (``GenesisOrganism.asexual_lineage``) may
reproduce uniparentally; the population engine refuses every other
uniparental copy, including the chamber timeout fallback.

This differs from item 3 of docs/prereg/jr5/MATING_TYPES_DESIGN_NOTE.md,
which says hermaphrodites with the outcross locus off may self. That note is
covered by the sealed prereg record, so the difference is recorded here
instead. By default no mating type selfs, hermaphrodites included.

``SexualRecombinationConfig.hermaphrodite_selfing`` is the opt-in selfing
mode. With it on, a hermaphrodite whose outcross locus reads selfing makes a
uniparental selfed child; males and females still never self. A selfed child
is a hermaphrodite by construction (its type is pinned, not drawn), so
selfing makes no sons and pays no cost of males, while outcrossing with a
male still draws sons at ``sex_ratio``. Self and outcross arms therefore run
under the same sexes-on engine mode and ledger.
"""

from __future__ import annotations

from collections.abc import Mapping

from codontrace.genesis.birth import (
    MATING_TYPE_FEMALE,
    MATING_TYPE_HERMAPHRODITE,
    MATING_TYPE_MALE,
    SexualRecombinationConfig,
)
from codontrace.rng import RNGManager

MATING_TYPE_STREAM_NAMESPACE = "genesis/mating_type"
# Census label for the designated asexual founder lineage; not a mating type.
ASEXUAL_LINEAGE_TYPE = "asexual"


def mating_type_stream(seed: int | None, organism_id: str) -> RNGManager:
    """Return the dedicated RNG stream for one organism's mating type."""

    if not organism_id:
        raise ValueError("organism_id is required.")
    return RNGManager(seed=seed, namespace=f"{MATING_TYPE_STREAM_NAMESPACE}/{organism_id}")


def draw_mating_type(seed: int | None, organism_id: str, config: SexualRecombinationConfig) -> str:
    """Draw the mating type of ``organism_id`` under ``config``.

    With a set containing ``male``, a newborn is male with probability
    ``sex_ratio`` and otherwise takes the other type in the set. A
    hermaphrodite-only set needs no draw.
    """

    if not config.mating_types_enabled:
        raise ValueError("draw_mating_type requires mating_types_enabled=True.")
    types = frozenset(config.mating_type_set)
    if MATING_TYPE_MALE not in types:
        return MATING_TYPE_HERMAPHRODITE
    other = MATING_TYPE_FEMALE if MATING_TYPE_FEMALE in types else MATING_TYPE_HERMAPHRODITE
    draw = mating_type_stream(seed, organism_id).random()
    return MATING_TYPE_MALE if draw < config.sex_ratio else other


def can_self(mating_type: str, config: SexualRecombinationConfig) -> bool:
    """Only hermaphrodites self, and only in the opt-in selfing mode."""

    return config.hermaphrodite_selfing and mating_type == MATING_TYPE_HERMAPHRODITE


def mating_types_compatible(type_a: str, type_b: str) -> bool:
    """Male x female, or a hermaphrodite with any type."""

    if MATING_TYPE_HERMAPHRODITE in (type_a, type_b):
        return True
    return {type_a, type_b} == {MATING_TYPE_MALE, MATING_TYPE_FEMALE}


class MatingTypeMap:
    """Mating type by organism id, filled at birth or on first lookup."""

    __slots__ = ("_config", "_seed", "_types")

    def __init__(self, seed: int | None, config: SexualRecombinationConfig) -> None:
        if not config.mating_types_enabled:
            raise ValueError("MatingTypeMap requires mating_types_enabled=True.")
        self._seed = seed
        self._config = config
        self._types: dict[str, str] = {}

    def pin(self, organism_id: str, mating_type: str) -> None:
        """Record a type that is fixed by birth mode rather than drawn."""

        self._types[organism_id] = mating_type

    def assign(self, organism_id: str) -> str:
        """Return the type of ``organism_id``, drawing it on first use."""

        found = self._types.get(organism_id)
        if found is None:
            found = draw_mating_type(self._seed, organism_id, self._config)
            self._types[organism_id] = found
        return found

    def compatible(self, organism_a: str, organism_b: str) -> bool:
        return mating_types_compatible(self.assign(organism_a), self.assign(organism_b))

    def as_mapping(self) -> Mapping[str, str]:
        return dict(sorted(self._types.items()))


__all__ = [
    "ASEXUAL_LINEAGE_TYPE",
    "MATING_TYPE_STREAM_NAMESPACE",
    "MatingTypeMap",
    "can_self",
    "draw_mating_type",
    "mating_type_stream",
    "mating_types_compatible",
]
