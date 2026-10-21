"""Life-plugin registry: the population engine's only view of domain plugins.

The population engine (``genesis/population.py``) used to import the
host-parasite plugin directly, which inverted the dependency between the core
and a domain module (REPORT.md, "import direction is violated"). The engine now
names a plugin and asks this registry for it. It sees only the
:class:`LifePlugin` and :class:`LifePluginConfig` protocols below.

Plugins are found in three ways, in this order:

1. :func:`register_life_plugin`, at run time.
2. Entry points in the ``codontrace.life_plugins`` group (packaging entry-point
   specification, https://packaging.python.org/en/latest/specifications/entry-points/;
   ``importlib.metadata.entry_points(group=...)``, Python 3.10+). A third-party
   package can ship a plugin this way.
3. The built-in table :data:`BUILTIN_LIFE_PLUGINS`, a ``module:attribute``
   string, imported lazily. This keeps a source checkout working before the
   package metadata has been reinstalled.

Nothing is imported until a plugin is first asked for, so importing the core
does not import any plugin.
"""

from __future__ import annotations

import importlib
from collections.abc import Mapping, Sequence
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError

if TYPE_CHECKING:
    from codontrace.genesis.organism import GenesisOrganism
    from codontrace.rng import RNGManager

__all__ = [
    "BUILTIN_LIFE_PLUGINS",
    "ENTRY_POINT_GROUP",
    "LifePlugin",
    "LifePluginConfig",
    "get_life_plugin",
    "register_life_plugin",
]

ENTRY_POINT_GROUP = "codontrace.life_plugins"
BUILTIN_LIFE_PLUGINS: Mapping[str, str] = {
    "host_parasite": "codontrace.genesis.host_parasite_life_plugin:PLUGIN",
}

_REGISTRY: dict[str, LifePlugin] = {}


@runtime_checkable
class LifePluginConfig(Protocol):
    """The configuration fields the engine reads. Everything else is plugin-private."""

    @property
    def enabled(self) -> bool: ...
    @property
    def outcross_enabled(self) -> bool: ...
    @property
    def match_locus_enabled(self) -> bool: ...
    @property
    def outcross_same_role_only(self) -> bool: ...
    @property
    def mate_search_radius(self) -> int | None: ...
    @property
    def outcross_mates_per_generation_cap(self) -> int | None: ...
    def to_dict(self) -> dict[str, JsonValue]: ...


@runtime_checkable
class LifePlugin(Protocol):
    """Hooks the population engine calls. ``config`` is the plugin's own config."""

    name: str

    def default_config(self) -> LifePluginConfig: ...
    def config_from_dict(self, data: Mapping[str, Any]) -> LifePluginConfig: ...
    def apply_life(
        self, organisms: Sequence[GenesisOrganism], *, config: Any, stream: RNGManager,
        mutation_config: object, tick: int,
    ) -> list[GenesisOrganism]: ...
    def silence_locus(self, organism: GenesisOrganism, config: Any) -> None: ...
    def resolve_copy_self_mode(self, genome_bits: str, config: Any) -> str: ...
    def copy_self_chamber_refusal(self, genome_bits: str, config: Any, *, chamber_available: bool) -> str | None: ...
    def apply_mating_locus_lock(self, child: GenesisOrganism, *, parent: GenesisOrganism, config: Any) -> None: ...
    def apply_selfing_birth_endowment(self, child: GenesisOrganism, *, config: Any, tick: int) -> None: ...
    def mates_compatible(self, parent_a_id: str, parent_b_id: str, config: Any) -> bool: ...
    def mates_within_search_radius(
        self, position_a: tuple[int, int], position_b: tuple[int, int], *, radius: int | None
    ) -> bool: ...
    def outcross_entry_plan(
        self, organism: GenesisOrganism, config: Any, *, remaining_after_parent_cost: float,
        projected_offspring_atp: float,
    ) -> tuple[float, str | None]: ...
    def outcross_fee_debit(self, genome_bits: str, config: Any) -> tuple[float, str, str] | None: ...


def register_life_plugin(plugin: LifePlugin, *, replace: bool = False) -> None:
    if not isinstance(plugin, LifePlugin):
        raise ConfigurationError(f"{plugin!r} does not implement the LifePlugin hooks")
    if plugin.name in _REGISTRY and not replace and _REGISTRY[plugin.name] is not plugin:
        raise ConfigurationError(f"life plugin {plugin.name!r} is already registered")
    _REGISTRY[plugin.name] = plugin


def _load(target: str) -> object:
    module_name, _, attr = target.partition(":")
    return getattr(importlib.import_module(module_name), attr)


def get_life_plugin(name: str) -> LifePlugin:
    found = _REGISTRY.get(name)
    if found is not None:
        return found
    candidate: object | None = None
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        if ep.name == name:
            candidate = ep.load()
            break
    if candidate is None and name in BUILTIN_LIFE_PLUGINS:
        candidate = _load(BUILTIN_LIFE_PLUGINS[name])
    if candidate is None:
        raise ConfigurationError(f"no life plugin named {name!r}")
    if not isinstance(candidate, LifePlugin):
        raise ConfigurationError(f"life plugin {name!r} does not implement the LifePlugin hooks")
    _REGISTRY[name] = candidate
    return candidate
