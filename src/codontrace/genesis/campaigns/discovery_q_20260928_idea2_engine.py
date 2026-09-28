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


def _pressure_from_ecology(eco: Mapping[str, float], *, generation_index: int) -> float:
    """Shared realised antagonist pressure from closed-loop ecology (not smoke RNG)."""

    scale = ecology_scale(eco)
    # Continuous phase walk driven by live ecology meters.
    drive = (
        0.35 * math.tanh(float(eco.get("mean_atp", 0.0)) / 8.0)
        + 0.25 * math.tanh(float(eco.get("n_alive", 0.0)) / 4.0)
        + 0.15 * math.sin(float(eco.get("resource_loc_fp", 0.0)) / 13.0)
        + 0.10 * scale
    )
    return float((0.2 * generation_index + drive * math.pi) % (2.0 * math.pi))


def _arm_step_energy(
    *,
    arm: str,
    energy: float,
    realised: float,
    predicted: float,
    pressure: float,
    kappa: float,
    ledger: Any,
    generation_index: int,
    cell: str,
    causal_do_enabled: bool,
    state: dict[str, Any],
) -> tuple[float, bool]:
    """Update one arm's energy under shared realised pressure; may issue ledger do."""

    atp_debit = float(DECISION_BUDGET) * float(kappa)
    do_on_nc = bool(state.get("do_on_nc", False))

    if arm == "gene":
        gene_match = float(state.get("gene_match", 0.0))
        gene_match += 0.08 * (math.sin(realised) - gene_match)
        state["gene_match"] = gene_match
        fit = max(0.0, 1.0 - abs(gene_match - math.sin(realised)))
        energy += fit * 0.35 - atp_debit * 0.15 - pressure * 0.2
    elif arm == "pattern":
        pattern_memory = float(state.get("pattern_memory", predicted))
        pattern_memory = 0.7 * pattern_memory + 0.3 * predicted
        state["pattern_memory"] = pattern_memory
        align = 1.0 - min(
            1.0,
            abs((predicted - realised + math.pi) % (2 * math.pi) - math.pi) / math.pi,
        )
        energy += align * 0.45 - atp_debit * 0.15 - pressure * 0.25
    else:  # causal
        fit = 0.25
        if causal_do_enabled and generation_index % 3 == 0:
            target = sorted(NAMED_CONTACT_SET)[generation_index % len(NAMED_CONTACT_SET)]
            ledger.mask_named_contacts([target], one_generation=True)
            do_on_nc = True
            fit = 0.55 + 0.2 * (1.0 - abs(math.sin(realised)))
        elif cell == "sham_predphase":
            fit = 0.22
        else:
            fit = 0.28
        energy += fit * 0.5 - atp_debit * 0.2 - pressure * 0.15

    nc_atp = sum(
        ledger.edges[eid].atp_yield
        for eid in NAMED_CONTACT_SET
        if eid in ledger.edges and ledger.edges[eid].present and not ledger.edges[eid].masked
    )
    energy += 0.02 * float(nc_atp)
    state["do_on_nc"] = do_on_nc
    return float(energy), do_on_nc


def run_idea2_engine_cell(
    *,
    seed: int,
    cell: str,
    kappa: float | None = KAPPA_SMOKE,
    generations: int = ENGINE_HORIZON_T,
    population: int = 8,
) -> list[dict[str, JsonValue]]:
    """Score all three arms for one cell on a shared engine closed-loop pressure.

    One GenesisEngine run supplies the shared realised pressure series via
    GenerationBoundaryObserver; arms are scored against that series (N=run per
    arm record). Sham is SHAM-CUE-PREDPHASE-V1 only (never NC-*).
    """

    k = require_kappa(kappa)
    if cell not in IDEA2_ENGINE_CELLS:
        raise ConfigurationError(f"unknown Idea2 cell {cell!r}.")
    if int(generations) < 4:
        raise ConfigurationError("engine Idea2 generations must be >= 4.")

    gens = int(generations)
    ledger = build_idea2_engine_scaffold_ledger(seed=int(seed))
    holder: dict[str, Any] = {"engine": None}
    pressure_series: list[float] = []
    predicted_series: list[float] = []
    arm_state: dict[str, dict[str, Any]] = {
        arm: {
            "energy": 1.0,
            "survived_steps": 0,
            "do_on_nc": False,
            "gene_match": 0.0,
            "pattern_memory": 0.0,
            "population": _new_host_population(),
            "parasite_series": [],
        }
        for arm in ARMS
    }
    causal_do_enabled = cell != "do_ablation"

    def _boundary(*, generation_index: int) -> None:
        engine = holder["engine"]
        if engine is None:
            raise ConfigurationError("engine holder empty in Idea2 observer.")
        eco = sample_ecology(engine)
        realised = _pressure_from_ecology(eco, generation_index=int(generation_index))
        if cell == "pi_deception":
            predicted = realised + DECEPTION_PHASE
        elif cell == "sham_predphase":
            ledger.realised_pressure_phase = float(realised)
            ledger.sham_cue_predphase(offset=DECEPTION_PHASE)
            predicted = float(ledger.predicted_pressure_phase)
        else:
            # Small ecology-tied cue noise (not independent harness smoke RNG stream).
            predicted = realised + 0.05 * math.sin(float(eco.get("resource_loc_fp", 0.0)))
        ledger.realised_pressure_phase = float(realised)
        ledger.predicted_pressure_phase = float(predicted)
        pressure = 0.5 + 0.5 * abs(math.sin(realised))
        pressure_series.append(float(realised))
        predicted_series.append(float(predicted))

        for arm in ARMS:
            st = arm_state[arm]
            energy, do_flag = _arm_step_energy(
                arm=arm,
                energy=float(st["energy"]),
                realised=float(realised),
                predicted=float(predicted),
                pressure=float(pressure),
                kappa=k,
                ledger=ledger,
                generation_index=int(generation_index),
                cell=str(cell),
                causal_do_enabled=causal_do_enabled,
                state=st,
            )
            st["energy"] = energy
            st["do_on_nc"] = bool(st["do_on_nc"] or do_flag)
            # Reproduction follows the live resource layout. Deaths follow this
            # arm's parasite count, not a tanh of ecology indexes.
            loc = abs(float(eco.get("resource_loc_fp", 0.0)))
            err = abs((float(predicted) - float(realised) + math.pi) % (2.0 * math.pi) - math.pi)
            intervened = (
                arm == "causal"
                and causal_do_enabled
                and int(generation_index) % 3 == 0
            )
            if arm == "gene":
                births = 1 if int(loc) % 5 < 3 else 0
            elif arm == "pattern":
                # Pattern trusts the cue. A large phase error blocks the birth.
                births = 1 if int(generation_index) % 2 == 0 and err < 0.5 else 0
            else:
                births = 1 if intervened or (err < 0.5 and int(loc) % 2 == 0) else 0
            extra_kills = 0 if intervened or err <= 1.0 else 1
            alive_lineages, parasites = _step_host_population(
                st["population"], births=births, extra_kills=extra_kills
            )
            st["alive_lineages"] = int(alive_lineages)
            st["parasite_series"].append(int(parasites))
        ledger.advance_generation()

    class _Idea2Observer:
        def __init__(self) -> None:
            self.fire_count = 0

        def __call__(self, *, generation_index: int) -> None:
            _boundary(generation_index=int(generation_index))
            self.fire_count += 1

    idea2_obs = _Idea2Observer()
    spec = build_idea4_engine_spec(
        seed=int(seed), tick_count=gens, population=int(population)
    )
    # Annotate metadata for Idea2.
    from dataclasses import replace as _replace

    spec = _replace(
        spec,
        metadata={
            **dict(spec.metadata),
            "idea_id": 2,
            "idea2_cell": str(cell),
            "engine_path": ENGINE_PATH,
        },
    )
    engine = GenesisEngine.from_spec(spec, generation_boundary_observers=(idea2_obs,))
    holder["engine"] = engine
    result = engine.run_ticks()

    if int(idea2_obs.fire_count) != gens:
        raise ConfigurationError(
            f"Idea2 observer fire count {idea2_obs.fire_count} != generations {gens}."
        )

    arm_stats: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        st = arm_state[arm]
        founded = int(st["population"]["founded"])
        alive_lineages = int(st.get("alive_lineages", 0))
        survival = float(alive_lineages) / float(founded) if founded else 0.0
        arm_stats[arm] = {
            "survival_to_T": float(survival),
            "do_on_NC": bool(st["do_on_nc"]),
            "energy_end": float(st["energy"]),
            "hosts_founded": founded,
            "host_lineages_alive": alive_lineages,
            "parasite_end": int(st["population"]["parasites"]),
            "parasite_series": [int(x) for x in st["parasite_series"]],
        }

    records: list[dict[str, JsonValue]] = []
    for arm in ARMS:
        surv = float(arm_stats[arm]["survival_to_T"])
        rivals = [float(arm_stats[a]["survival_to_T"]) for a in ARMS if a != arm]
        best_rival = max(rivals) if rivals else 0.0
        margin = float(surv - best_rival)
        rec: dict[str, JsonValue] = {
            "schema": SCHEMA,
            "idea_id": 2,
            "engine_path": ENGINE_PATH,
            "seed": int(seed),
            "run_id": f"idea2-engine-s{int(seed)}-{cell}-{arm}",
            "cell": str(cell),
            "arm": str(arm),
            "survival_to_T": surv,
            "margin_vs_best_rival": margin,
            "channel_margin_threshold": CHANNEL_MARGIN,
            "estimand": "host_lineages_alive_over_founded",
            "hosts_founded": int(arm_stats[arm]["hosts_founded"]),
            "host_lineages_alive": int(arm_stats[arm]["host_lineages_alive"]),
            "parasite_end": int(arm_stats[arm]["parasite_end"]),
            "sham_id": SHAM_ID,
            "do_on_NC": bool(arm_stats[arm]["do_on_NC"]),
            "decision_budget": DECISION_BUDGET,
            "kappa": k,
            "T_horizon": gens,
            "mechanism_competitors": list(MECHANISM_COMPETITORS),
            "mechanism_label_deferred": True,
            "claim_ceiling": CLAIM_CEILING,
            "hypothesis_supported": False,
            "red_queen_proved": False,
            "honesty": (
                "Engine closed-loop Idea2 cell under phase2_design. "
                "survival_to_T is host lineages still alive divided by founders. "
                "Parasite pressure is that arm's parasite count, not an ecology index. "
                "Not G2/M0–M3 sealed evidence. "
                "Sham is SHAM-CUE-PREDPHASE-V1 only (never NC-*). "
                "hypothesis_supported stays false."
            ),
            "n_unit": "run",
            "observer_fire_count": int(idea2_obs.fire_count),
            "engine_result_digest": result.snapshot.digest(),
            "ledger_digest": ledger.digest(),
            "named_contact_edge_ids": sorted(NAMED_CONTACT_EDGE_IDS),
            "pressure_series_tail": [int(x) for x in arm_stats[arm]["parasite_series"][-5:]],
            "predicted_series_tail": [float(x) for x in predicted_series[-5:]],
        }
        if cell == "sham_predphase":
            rec["sham_targets_nc"] = False
        records.append(rec)
    return records


def idea2_engine_constants() -> Mapping[str, Any]:
    return {
        "schema": SCHEMA,
        "engine_path": ENGINE_PATH,
        "claim_ceiling": CLAIM_CEILING,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "scored_cells": list(IDEA2_ENGINE_CELLS),
        "arms": list(ARMS),
        "engine_horizon_T": ENGINE_HORIZON_T,
        "sham_id": SHAM_ID,
        "channel_margin": CHANNEL_MARGIN,
        "named_contact_edge_ids": list(NAMED_CONTACT_SET),
    }
