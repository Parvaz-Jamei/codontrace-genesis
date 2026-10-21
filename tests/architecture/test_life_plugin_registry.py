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
    BUILTIN_LIFE_PLUGINS,
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
    assert BUILTIN_LIFE_PLUGINS["host_parasite"].endswith(":PLUGIN")


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
