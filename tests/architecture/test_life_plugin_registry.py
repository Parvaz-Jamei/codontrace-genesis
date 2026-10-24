"""The population engine reaches the host-parasite plugin only through the registry."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import life_plugins
from codontrace.genesis.life_plugins import (
    DISABLED_LIFE_PLUGIN,
    DisabledLifeConfig,
    LifePlugin,
    LifePluginConfig,
    get_life_plugin,
    register_life_plugin,
)

SRC = Path(__file__).resolve().parents[2] / "src"
POPULATION = SRC / "codontrace" / "genesis" / "population.py"


def test_population_does_not_import_the_plugin_module() -> None:
    tree = ast.parse(POPULATION.read_text(encoding="utf-8"))
    names = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("host_parasite" in n for n in names), sorted(n for n in names if "host_parasite" in n)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "codontrace/__init__ -> genesis/__init__ -> replay_integrity resolves its class "
        "registry eagerly (replay_integrity.py:1926) and imports campaign modules that use "
        "the plugin. That is removed when the campaign modules move out of the core."
    ),
)
def test_importing_population_does_not_load_the_plugin() -> None:
    code = (
        "import sys; import codontrace.genesis.population as p; "
        "print('codontrace.genesis.host_parasite_life_plugin' in sys.modules)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                         env={"PYTHONPATH": str(SRC)})
    assert out.stdout.strip() == "False"


def test_builtin_plugin_resolves_and_implements_the_hooks() -> None:
    plugin = get_life_plugin("host_parasite")
    assert isinstance(plugin, LifePlugin)
    cfg = plugin.default_config()
    assert isinstance(cfg, LifePluginConfig) and cfg.enabled is False
    assert plugin.config_from_dict(cfg.to_dict()) == cfg
    assert not hasattr(life_plugins, "BUILTIN_LIFE_PLUGINS")
    assert "importlib" not in life_plugins.__dict__


def test_default_population_config_is_the_plugin_default() -> None:
    from codontrace.genesis.host_parasite_life_plugin import ClosedLoopHPLifeConfig
    from codontrace.genesis.population import PopulationConfigs

    assert PopulationConfigs().closed_loop_hp_life == ClosedLoopHPLifeConfig()


def test_unknown_and_malformed_plugins_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigurationError, match="no life plugin"):
        get_life_plugin("no-such-plugin")
    with pytest.raises(ConfigurationError, match="does not implement"):
        register_life_plugin(object())  # type: ignore[arg-type]
    plugin = get_life_plugin("host_parasite")
    monkeypatch.setitem(life_plugins._REGISTRY, "host_parasite", plugin)
    register_life_plugin(plugin)  # same object: idempotent



def test_a_different_plugin_with_the_same_name_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    import copy

    plugin = get_life_plugin("host_parasite")
    monkeypatch.setitem(life_plugins._REGISTRY, "host_parasite", plugin)
    impostor = copy.copy(plugin)
    assert impostor is not plugin
    with pytest.raises(ConfigurationError, match="already registered"):
        register_life_plugin(impostor)
    assert get_life_plugin("host_parasite") is plugin


class _EP:
    def __init__(self, name: str, value: str, dist: str, obj: object) -> None:
        self.name, self.value, self._obj = name, value, obj
        self.dist = type("D", (), {"name": dist})()

    def load(self) -> object:
        return self._obj


def _with_entry_points(monkeypatch: pytest.MonkeyPatch, eps: list[_EP]) -> None:
    monkeypatch.setattr(life_plugins, "entry_points", lambda group: [e for e in eps if group == life_plugins.ENTRY_POINT_GROUP])
    monkeypatch.setattr(life_plugins, "_REGISTRY", {})


def test_entry_point_shadowing_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    real = get_life_plugin("host_parasite")
    # A reserved name from another distribution (the review's evilplug repro).
    _with_entry_points(monkeypatch, [_EP("host_parasite", "evilplug:PLUGIN", "evil", real)])
    with pytest.raises(ConfigurationError, match="reserved"):
        get_life_plugin("host_parasite")
    # Two providers for one name.
    _with_entry_points(monkeypatch, [
        _EP("host_parasite", "codontrace.genesis.host_parasite_life_plugin:PLUGIN", "codontrace", real),
        _EP("host_parasite", "evilplug:PLUGIN", "evil", real),
    ])
    with pytest.raises(ConfigurationError, match="more than one entry point"):
        get_life_plugin("host_parasite")
    # The same target listed twice by codontrace (stale metadata) is accepted.
    _with_entry_points(monkeypatch, [
        _EP("host_parasite", "codontrace.genesis.host_parasite_life_plugin:PLUGIN", "codontrace", real),
        _EP("host_parasite", "codontrace.genesis.host_parasite_life_plugin:PLUGIN", "codontrace", real),
    ])
    assert get_life_plugin("host_parasite") is real


def test_load_failures_are_configuration_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class Boom(_EP):
        def load(self) -> object:
            raise RuntimeError("boom")

    _with_entry_points(monkeypatch, [Boom("thirdparty", "x:P", "x", None)])
    with pytest.raises(ConfigurationError, match="could not be loaded"):
        get_life_plugin("thirdparty")


def test_disabled_config_serialises_like_the_plugin_default() -> None:
    from codontrace.genesis.host_parasite_life_plugin import ClosedLoopHPLifeConfig

    hp = ClosedLoopHPLifeConfig()
    off = DisabledLifeConfig()
    assert off.to_dict() == hp.to_dict()
    for field in ("enabled", "outcross_enabled", "match_locus_enabled", "outcross_same_role_only",
                  "mate_search_radius", "outcross_mates_per_generation_cap"):
        assert getattr(off, field) == getattr(hp, field), field
    assert DISABLED_LIFE_PLUGIN.config_from_dict(hp.to_dict()) == off
    with pytest.raises(ConfigurationError, match="needs the host_parasite life plugin"):
        DISABLED_LIFE_PLUGIN.config_from_dict({**hp.to_dict(), "enabled": True})


_BLOCKED_RUN = """
import importlib.abc, json, os, sys, tempfile
os.environ["CODONTRACE_SOURCE_ROOT"] = tempfile.mkdtemp()
if sys.argv[1] == "block":
    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if "host_parasite" in name.rsplit(".", 1)[-1]:
                raise ImportError("blocked " + name)
            return None
    sys.meta_path.insert(0, Block())
from codontrace.engine import GenesisEngine
from codontrace.genesis.population import PopulationConfigs
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
cfg = PopulationConfigs().closed_loop_hp_life
spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=6, population=4)
r = GenesisEngine.from_spec(spec).run_ticks()
print(json.dumps({"config": type(cfg).__name__, "spec": spec.digest(), "run": r.digest(),
                  "loaded": any("host_parasite_life_plugin" in m for m in sys.modules)}))
"""


def test_engine_runs_without_the_plugin_with_identical_digests() -> None:
    import json

    def run(mode: str) -> dict[str, object]:
        out = subprocess.run([sys.executable, "-c", _BLOCKED_RUN, mode], capture_output=True, text=True,
                             check=True, env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"})
        return dict(json.loads(out.stdout.strip().splitlines()[-1]))

    normal, blocked = run("normal"), run("block")
    assert normal["config"] == "ClosedLoopHPLifeConfig" and blocked["config"] == "DisabledLifeConfig"
    assert blocked["loaded"] is False
    assert (blocked["spec"], blocked["run"]) == (normal["spec"], normal["run"])
