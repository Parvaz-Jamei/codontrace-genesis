"""Discovery questions 2026-09-28 — Idea 2 ENGINE closed-loop cells.

Gene / pattern / causal arms under coevolving antagonist pressure derived from
GenesisEngine ecology via GenerationBoundaryObserver + ContactAtpLedger.
Distinct from harness smoke-ledger RNG path. Claim ceiling phase2_design.
hypothesis_supported=False; red_queen_proved=False. Sham ≠ NC-*.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.campaigns.discovery_q_20260928_idea2 import (
    ARMS,
    CHANNEL_MARGIN,
    CLAIM_CEILING,
    DECEPTION_PHASE,
    DECISION_BUDGET,
    IDEA2_SCORED_CELLS,
    KAPPA_SMOKE,
    MECHANISM_COMPETITORS,
    NAMED_CONTACT_SET,
    SCORED_HORIZON_T,
    SHAM_ID,
    require_kappa,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    build_idea4_engine_spec,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.life_loop.contact_atp_ledger import (
    NAMED_CONTACT_EDGE_IDS,
    build_idea2_engine_scaffold_ledger,
)
from codontrace.life_loop.engine_ledger_coupler import ecology_scale, sample_ecology

SCHEMA = "discovery_q_20260928_idea2_engine_cell_v1"
ENGINE_PATH = "genesis_life_loop_observer_coupled"
IDEA2_ENGINE_CELLS: tuple[str, ...] = IDEA2_SCORED_CELLS
ENGINE_HORIZON_T = SCORED_HORIZON_T  # 24


def _new_host_population(*, founders: int = 6) -> dict[str, Any]:
    """Independent host lineages plus a parasite count. Not an energy score."""

    n = int(founders)
    return {
        "hosts": [{"lineage": i, "seq": i, "alive": True} for i in range(n)],
        "parasites": 1,
        "next_seq": n,
        "founded": n,
    }


def _step_host_population(
    pop: dict[str, Any], *, births: int, extra_kills: int = 0
) -> tuple[int, int]:
    """Birth, then kill by parasite count plus cue-error pressure."""

    alive = [host for host in pop["hosts"] if host["alive"]]
    if int(births) > 0 and alive:
        parent = sorted(alive, key=lambda item: int(item["seq"]))[0]
        pop["hosts"].append(
            {
                "lineage": int(parent["lineage"]),
                "seq": int(pop["next_seq"]),
                "alive": True,
            }
        )
        pop["next_seq"] = int(pop["next_seq"]) + 1
    alive = [host for host in pop["hosts"] if host["alive"]]
    kills = min(len(alive), int(pop["parasites"]) + max(0, int(extra_kills)))
    for host in sorted(alive, key=lambda item: int(item["seq"]))[:kills]:
        host["alive"] = False
    alive_n = sum(1 for host in pop["hosts"] if host["alive"])
    if alive_n >= 5 and int(pop["parasites"]) < 2:
        pop["parasites"] = int(pop["parasites"]) + 1
    elif alive_n <= 2 and int(pop["parasites"]) > 0:
        pop["parasites"] = int(pop["parasites"]) - 1
    elif alive_n == 0:
        pop["parasites"] = 0
    alive_lineages = {
        int(host["lineage"]) for host in pop["hosts"] if host["alive"]
    }
    return len(alive_lineages), int(pop["parasites"])
