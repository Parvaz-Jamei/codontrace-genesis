"""Generate PROPOSED_CHANGE_2.patch: additive persistence-safe ecology for D-2."""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT / "codontrace-genesis"
TARGET = REPO / "src" / "codontrace" / "genesis" / "campaigns" / "discovery_q_20260928_idea4_engine.py"

OLD_SIG = '''def build_idea4_engine_spec(
    *,
    seed: int,
    tick_count: int,
    population: int = 8,
) -> Any:'''
NEW_SIG = '''def build_idea4_engine_spec(
    *,
    seed: int,
    tick_count: int,
    population: int = 8,
    ecology: str = "standing",
) -> Any:'''

OLD_BODY = '''    new_rrp = RuntimeResourcePolicy(
        respawn_enabled=True, respawn_rate=1.0, max_resources=12, amount=8.0
    )
    metab = cfg.metabolism if cfg.metabolism is not None else MetabolicConfig()
    new_metab = replace(metab, basal_runtime_atp_cost=0.4)'''
NEW_BODY = '''    new_rrp = RuntimeResourcePolicy(
        respawn_enabled=True, respawn_rate=1.0, max_resources=12, amount=8.0
    )
    metab = cfg.metabolism if cfg.metabolism is not None else MetabolicConfig()
    new_metab = replace(metab, basal_runtime_atp_cost=0.4)
    # D-2 patch 2 (additive, default preserves every standing number): a
    # persistence-safe ecology so the control arm keeps a positive census
    # through the T = 40 checkpoint horizon and therefore has a recovery
    # opportunity.  The standing profile is byte-identical when the default
    # "standing" is used, so no recorded number changes.
    if ecology == "persistence_safe":
        for pos in SOFT_FOOD_CELLS + ((2, 2), (3, 0), (0, 1), (1, 1), (4, 1), (5, 2), (0, 2), (2, 1)):
            if 0 <= pos[0] < world.width and 0 <= pos[1] < world.height:
                world.place_resource(pos, 12.0)
        new_rrp = RuntimeResourcePolicy(
            respawn_enabled=True, respawn_rate=1.0, max_resources=24, amount=12.0
        )
        new_metab = replace(metab, basal_runtime_atp_cost=0.15)
    elif ecology != "standing":
        raise ConfigurationError(f"unknown ecology profile {ecology!r}.")'''
OLD_REPRO = '''            reproduction=replace(
                cfg.reproduction, min_runtime_atp=4.0, parent_atp_cost=0.5
            ),'''
NEW_REPRO = '''            reproduction=replace(
                cfg.reproduction,
                min_runtime_atp=3.0 if ecology == "persistence_safe" else 4.0,
                parent_atp_cost=0.5,
            ),'''
OLD_ATP = "        initial_runtime_atp=20.0,"
NEW_ATP = '        initial_runtime_atp=24.0 if ecology == "persistence_safe" else 20.0,'


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    patched = text
    for old, new in (
        (OLD_SIG, NEW_SIG),
        (OLD_BODY, NEW_BODY),
        (OLD_REPRO, NEW_REPRO),
        (OLD_ATP, NEW_ATP),
    ):
        assert old in patched, old[:60]
        patched = patched.replace(old, new, 1)
    diff = "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile="a/src/codontrace/genesis/campaigns/discovery_q_20260928_idea4_engine.py",
            tofile="b/src/codontrace/genesis/campaigns/discovery_q_20260928_idea4_engine.py",
            n=3,
        )
    )
    out = ROOT / "test-runs" / "d2" / "PROPOSED_CHANGE_2.patch"
    out.write_text(diff, encoding="utf-8")
    print("wrote", out.name, "lines", diff.count("\n"), "sha", hashlib.sha256(diff.encode()).hexdigest()[:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
