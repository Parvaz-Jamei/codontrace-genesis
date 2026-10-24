"""Life-plugin registry: the population engine's only view of domain plugins.

The population engine (``genesis/population.py``) used to import the
host-parasite plugin directly, which inverted the dependency between the core
and a domain module (the core must not import domain modules; see the
import-linter contracts in ``pyproject.toml``). The engine now names a plugin
and asks this registry for it. It sees only the :class:`LifePlugin` and
:class:`LifePluginConfig` protocols below.

Plugins are found in two ways, in this order:

1. :func:`register_life_plugin`. A plugin module registers its own plugin
   object when it is imported (the host-parasite module does).
2. Entry points in the ``codontrace.life_plugins`` group (packaging entry-point
   specification, https://packaging.python.org/en/latest/specifications/entry-points/;
   ``importlib.metadata.entry_points(group=...)``, Python 3.10+). A third-party
   package can ship a new plugin this way.

There is no string table of built-in ``module:attribute`` targets: that was a
lazy import by name, invisible to the import-graph contracts.

The packaging specification leaves duplicate entry-point names to the
consumer. This consumer refuses them: two entry points with the same name,
or an entry point for a name that codontrace itself ships
(:data:`RESERVED_PLUGIN_NAMES`) from any other distribution, raise
:class:`~codontrace.errors.ConfigurationError`, so a replay-critical hook can
not be swapped by installing a package, and :func:`register_life_plugin` will
not replace a reserved name even with ``replace=True``. A declared plugin whose
module fails to import re-raises that ``ImportError`` (a broken install is not a
missing plugin); any other load failure raises ``ConfigurationError``.

When no host-parasite plugin is available the engine still runs with the
plugin disabled: :data:`DISABLED_LIFE_PLUGIN` implements every hook with the
disabled path of the host-parasite plugin, and :class:`DisabledLifeConfig`
serialises exactly like that plugin's default configuration, so the run and
its digests are the same. Any non-default life configuration then needs the
real plugin and is refused with ``ConfigurationError``.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import codontrace
from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError

_PACKAGE_ROOT = Path(codontrace.__file__).resolve().parent

if TYPE_CHECKING:
    from codontrace.genesis.organism import GenesisOrganism
    from codontrace.rng import RNGManager

__all__ = [
    "DISABLED_LIFE_PLUGIN",
    "ENTRY_POINT_GROUP",
    "RESERVED_PLUGIN_NAMES",
    "DisabledLifeConfig",
    "LifePlugin",
    "LifePluginConfig",
    "LifePluginNotFound",
    "get_life_plugin",
    "life_plugin_provenance",
    "resolve_life_plugin",
    "register_life_plugin",
]

ENTRY_POINT_GROUP = "codontrace.life_plugins"
# Names codontrace itself provides; only the codontrace distribution may
# provide them through an entry point.
RESERVED_PLUGIN_NAMES: frozenset[str] = frozenset({"host_parasite"})
CODONTRACE_DISTRIBUTION = "codontrace"

_REGISTRY: dict[str, LifePlugin] = {}


class LifePluginNotFound(ConfigurationError):
    """No plugin of that name is registered or declared by an entry point."""


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


def _defined_in_codontrace(cls: type) -> bool:
    """True only if ``cls`` really lives in a loaded codontrace module.

    ``__module__`` is a plain string any class can set, so the name alone
    proves nothing. The module must already be imported, its file must sit
    inside this package, and the class must be the object found at its own
    qualified name there. A look-alike class (same module string, or a name
    the real module does not have) fails, whether or not the registry is
    still empty.
    """

    module = sys.modules.get(cls.__module__)
    if module is None or not cls.__module__.startswith(f"{CODONTRACE_DISTRIBUTION}."):
        return False
    origin = getattr(module, "__file__", None)
    if origin is None or _PACKAGE_ROOT not in Path(origin).resolve().parents:
        return False
    found: object = module
    for part in cls.__qualname__.split("."):
        found = getattr(found, part, None)
    return found is cls


def register_life_plugin(plugin: LifePlugin, *, replace: bool = False) -> None:
    if not isinstance(plugin, LifePlugin):
        raise ConfigurationError(f"{plugin!r} does not implement the LifePlugin hooks")
    current = _REGISTRY.get(plugin.name)
    if plugin.name in RESERVED_PLUGIN_NAMES:
        # Reserved names are replay-critical: only codontrace's own module may
        # provide them, and once registered they cannot be swapped, not even
        # with replace=True.
        if not _defined_in_codontrace(type(plugin)):
            raise ConfigurationError(
                f"life plugin {plugin.name!r} is reserved for the {CODONTRACE_DISTRIBUTION} distribution"
            )
        if current is not None and current is not plugin:
            raise ConfigurationError(f"life plugin {plugin.name!r} is reserved and cannot be replaced")
    elif current is not None and not replace and current is not plugin:
        raise ConfigurationError(f"life plugin {plugin.name!r} is already registered")
    _REGISTRY[plugin.name] = plugin


def _entry_point_candidate(name: str) -> object | None:
    matches = [ep for ep in entry_points(group=ENTRY_POINT_GROUP) if ep.name == name]
    if not matches:
        return None
    providers = sorted({getattr(getattr(ep, "dist", None), "name", None) or "<unknown>" for ep in matches})
    if len(matches) > 1:
        targets = sorted(ep.value for ep in matches)
        if len(set(targets)) > 1 or len(providers) > 1:
            raise ConfigurationError(
                f"life plugin {name!r} is provided by more than one entry point "
                f"({', '.join(targets)}; distributions {', '.join(providers)})"
            )
    ep = matches[0]
    if name in RESERVED_PLUGIN_NAMES and providers != [CODONTRACE_DISTRIBUTION]:
        raise ConfigurationError(
            f"life plugin {name!r} is reserved for the {CODONTRACE_DISTRIBUTION} distribution; "
            f"refusing the entry point {ep.value} from {', '.join(providers)}"
        )
    try:
        loaded: object = ep.load()
        return loaded
    except ImportError:
        # A declared plugin that cannot be imported is a broken install, not a
        # missing plugin: re-raise so resolve_life_plugin() does not fall back.
        raise
    except Exception as exc:  # noqa: BLE001 - any load failure becomes a clear configuration error
        raise ConfigurationError(f"life plugin {name!r} could not be loaded from {ep.value}: {exc!r}") from exc


def get_life_plugin(name: str) -> LifePlugin:
    found = _REGISTRY.get(name)
    if found is not None:
        return found
    candidate = _entry_point_candidate(name)
    if candidate is None:
        raise LifePluginNotFound(f"no life plugin named {name!r}")
    if not isinstance(candidate, LifePlugin):
        raise ConfigurationError(f"life plugin {name!r} does not implement the LifePlugin hooks")
    if getattr(candidate, "name", None) != name:
        raise ConfigurationError(f"entry point {name!r} resolved to a plugin named {getattr(candidate, 'name', None)!r}")
    _REGISTRY[name] = candidate
    return candidate


# The host-parasite plugin's default configuration, as it serialises. Kept in
# step with ClosedLoopHPLifeConfig().to_dict() by
# tests/architecture/test_life_plugin_registry.py.
_DISABLED_PAYLOAD: dict[str, JsonValue] = {
    "enabled": False,
    "mutate_both_roles": True,
    "role_by_id": {},
    "kappa_enabled": False,
    "kappa_ablate": False,
    "kappa_bit_start": 9,
    "kappa_bit_width": 6,
    "mutation_stream_lock_roles": [],
    "plugin_bit_flip_rate": None,
    "p1_scope": "unify_mutate_scaffold",
    "p2_scope": "smith_fretwell_n1_birth_partition",
    "p3_scope": "scalar_genetic_harm_help_kappa",
    "p4_scope": "mutation_stream_lock_dual_arm_replay",
}


@dataclass(frozen=True, slots=True)
class DisabledLifeConfig:
    """The life plugin switched off, without the plugin installed."""

    enabled: bool = False
    outcross_enabled: bool = False
    match_locus_enabled: bool = False
    outcross_same_role_only: bool = True
    mate_search_radius: int | None = None
    outcross_mates_per_generation_cap: int | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        out: dict[str, JsonValue] = {}
        for key, value in _DISABLED_PAYLOAD.items():
            out[key] = dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value
        return out


class _DisabledLifePlugin:
    """Every hook on the disabled path of the host-parasite plugin."""

    name = "disabled"

    def default_config(self) -> DisabledLifeConfig:
        return DisabledLifeConfig()

    def config_from_dict(self, data: Mapping[str, Any]) -> DisabledLifeConfig:
        if dict(data) != _DISABLED_PAYLOAD:
            raise ConfigurationError(
                "this life configuration needs the host_parasite life plugin, which is not "
                "available; reinstall codontrace (pip install -e .) so its entry point is registered"
            )
        return DisabledLifeConfig()

    def apply_life(
        self, organisms: Sequence[GenesisOrganism], *, config: Any, stream: RNGManager,
        mutation_config: object, tick: int,
    ) -> list[GenesisOrganism]:
        return list(organisms)

    def silence_locus(self, organism: GenesisOrganism, config: Any) -> None:
        return None

    def resolve_copy_self_mode(self, genome_bits: str, config: Any) -> str:
        return "default"

    def copy_self_chamber_refusal(self, genome_bits: str, config: Any, *, chamber_available: bool) -> str | None:
        return None

    def apply_mating_locus_lock(self, child: GenesisOrganism, *, parent: GenesisOrganism, config: Any) -> None:
        return None

    def apply_selfing_birth_endowment(self, child: GenesisOrganism, *, config: Any, tick: int) -> None:
        return None

    def mates_compatible(self, parent_a_id: str, parent_b_id: str, config: Any) -> bool:
        # outcross_same_role_only with an empty role map: no role, not compatible.
        return False

    def mates_within_search_radius(
        self, position_a: tuple[int, int], position_b: tuple[int, int], *, radius: int | None
    ) -> bool:
        if radius is None:
            return True
        dist = abs(int(position_a[0]) - int(position_b[0])) + abs(int(position_a[1]) - int(position_b[1]))
        return dist <= int(radius)

    def outcross_entry_plan(
        self, organism: GenesisOrganism, config: Any, *, remaining_after_parent_cost: float,
        projected_offspring_atp: float,
    ) -> tuple[float, str | None]:
        return 0.0, None

    def outcross_fee_debit(self, genome_bits: str, config: Any) -> tuple[float, str, str] | None:
        return None


DISABLED_LIFE_PLUGIN: LifePlugin = _DisabledLifePlugin()


def resolve_life_plugin(name: str) -> LifePlugin:
    """The named plugin, or :data:`DISABLED_LIFE_PLUGIN` when none is installed.

    Only absence (no registered plugin and no declared entry point) falls
    back. A refused duplicate, a reserved-name entry point from another
    distribution, or a declared plugin that fails to import still raises.
    """
    try:
        return get_life_plugin(name)
    except LifePluginNotFound:
        return DISABLED_LIFE_PLUGIN


def life_plugin_provenance(plugin: LifePlugin) -> dict[str, str | None]:
    """Where the active life plugin came from, for the run manifest.

    ``target`` is ``module:qualname`` of the plugin object's class and
    ``distribution``/``version`` name the installed distribution that ships
    that module (``None`` when it is not part of any installed distribution,
    for example a plugin defined in a test).  This is recorded next to the
    manifest, outside every digest; see ``RunManifest.life_plugin_provenance``.
    """
    from importlib.metadata import PackageNotFoundError, packages_distributions, version

    cls = type(plugin)
    module = cls.__module__
    dists = packages_distributions().get(module.split(".", 1)[0], [])
    dist = sorted(dists)[0] if dists else None
    dist_version: str | None = None
    if dist is not None:
        try:
            dist_version = version(dist)
        except PackageNotFoundError:
            dist_version = None
    return {
        "name": str(getattr(plugin, "name", "")),
        "target": f"{module}:{cls.__qualname__}",
        "distribution": dist,
        "version": dist_version,
    }
