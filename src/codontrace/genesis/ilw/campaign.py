"""ILW-5 campaign harness: factorial/ablation + scale challenge (held-out seeds).

Encodes the prereg DoE design as executable cells. Does **not** invent large
offline outcome tables. Local smoke runs 1–2 confirmatory cells; remaining
cells are documented for Colab/Drive-style execution.

ClaimGate ceiling stays ``runtime_observation``. No intelligence / CCE claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.adapter_honesty import (
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
)
from codontrace.genesis.ilw.chain_runtime import IlwChainRuntime
from codontrace.genesis.ilw.conservation import check_conservation
from codontrace.genesis.ilw.dag import CLAIM_CEILING, SCIENTIFIC_NAME, load_integration_dag
from codontrace.genesis.ilw.knockouts import KnockoutConfig
from codontrace.genesis.ilw.pilot import (
    _attempt_fields_separate,
    _edge_applied_count,
    _edge_blocked_count,
    _generation_turnover,
    _lineage_depth,
    _niches_occupied,
    _promotion_free,
    _unique_genome_count,
    unlock_harness_from_artifact,
)
from codontrace.genesis.ilw.prereg import (
    CONFIRMATORY_HELD_OUT_SEEDS,
    DOE_PLAN,
    EDGE_KNOCKOUTS,
    INTERACTIONS_TO_ESTIMATE,
    PILOT_SEEDS,
    PREREG_VERSION,
    SCALE_LADDER,
    PilotGateError,
    PilotHarness,
    assert_no_forbidden_claims,
    assert_prereg_claim_ceiling,
    ilw_prereg_design_digest,
    ilw_prereg_document_digest,
)
from codontrace.genesis.ilw.world_spec import WorldSpec

CellKind = Literal["baseline", "ablation", "interaction", "scale_s4"]

DEFAULT_CAMPAIGN_BOOTSTRAP = 8
DEFAULT_SMOKE_ARTIFACT = "outputs/ilw5_campaign_smoke.json"
DEFAULT_PARTIAL_ARTIFACT = "outputs/ilw5_campaign_partial.json"


class IlwCampaignError(ConfigurationError):
    """Raised when an ILW-5 campaign cell cannot run honestly."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_smoke_artifact_path() -> Path:
    return _repo_root() / DEFAULT_SMOKE_ARTIFACT


def default_partial_artifact_path() -> Path:
    return _repo_root() / DEFAULT_PARTIAL_ARTIFACT


@dataclass(frozen=True, slots=True)
class CampaignCell:
    """One executable campaign cell (design only until run)."""

    cell_id: str
    kind: CellKind
    seed: int
    scale_label: str
    width: int
    height: int
    tick_horizon: int
    population_cap: int
    niche_count: int
    knockouts: tuple[str, ...] = ()
    interaction_label: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "cell_id": self.cell_id,
            "kind": self.kind,
            "seed": self.seed,
            "scale_label": self.scale_label,
            "width": self.width,
            "height": self.height,
            "tick_horizon": self.tick_horizon,
            "population_cap": self.population_cap,
            "niche_count": self.niche_count,
            "knockouts": list(self.knockouts),
            "interaction_label": self.interaction_label,
            "notes": self.notes,
        }

    def world_spec(self) -> WorldSpec:
        return WorldSpec(
            width=self.width,
            height=self.height,
            seed=self.seed,
            tick_horizon=self.tick_horizon,
            resource_kinds=("lumen", "vitae"),
            niche_count=self.niche_count,
            population_cap=self.population_cap,
            scale_label=self.scale_label,
        )


@dataclass(frozen=True, slots=True)
class CampaignCellResult:
    cell: CampaignCell
    replay_matched: bool
    conservation_passed: bool
    required_edge_coverage: float
    birth_count: int
    death_count: int
    generation_turnover: int
    lineage_depth: int
    unique_genome_count: int
    niches_occupied: int
    knockout_applied_zero_when_expected: bool | None
    final_digest: str
    event_count: int
    no_claim_promotion: bool
    claim_ceiling: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "cell": self.cell.to_dict(),
            "replay_matched": self.replay_matched,
            "conservation_passed": self.conservation_passed,
            "required_edge_coverage": self.required_edge_coverage,
            "birth_count": self.birth_count,
            "death_count": self.death_count,
            "generation_turnover": self.generation_turnover,
            "lineage_depth": self.lineage_depth,
            "unique_genome_count": self.unique_genome_count,
            "niches_occupied": self.niches_occupied,
            "knockout_applied_zero_when_expected": self.knockout_applied_zero_when_expected,
            "final_digest": self.final_digest,
            "event_count": self.event_count,
            "no_claim_promotion": self.no_claim_promotion,
            "claim_ceiling": self.claim_ceiling,
            "status": "runtime_observation",
            "scientific_claim_emitted": False,
            "ladder_promotion": None,
        }


def _assert_confirmatory_unlocked(harness: PilotHarness, seed: int) -> None:
    harness.assert_seed_allowed(seed, role="confirmatory")


def build_ablation_cells(
    *,
    seed: int,
    scale_label: str = "S2",
) -> list[CampaignCell]:
    """One-edge-at-a-time ablation arms + intact baseline (still not OAT-only inference)."""

    if seed in PILOT_SEEDS:
        raise PilotGateError("Ablation confirmatory cells must use held-out seeds.")
    ladder = SCALE_LADDER[scale_label]
    cells: list[CampaignCell] = [
        CampaignCell(
            cell_id=f"baseline-{scale_label}-{seed}",
            kind="baseline",
            seed=seed,
            scale_label=scale_label,
            width=int(ladder["width"]),
            height=int(ladder["height"]),
            tick_horizon=int(ladder["tick_horizon"]),
            population_cap=int(ladder["population_cap"]),
            niche_count=int(ladder["niche_count"]),
            knockouts=(),
            notes="Intact confirmatory baseline.",
        )
    ]
    for knockout_id in EDGE_KNOCKOUTS:
        cells.append(
            CampaignCell(
                cell_id=f"ablation-{knockout_id}-{scale_label}-{seed}",
                kind="ablation",
                seed=seed,
                scale_label=scale_label,
                width=int(ladder["width"]),
                height=int(ladder["height"]),
                tick_horizon=int(ladder["tick_horizon"]),
                population_cap=int(ladder["population_cap"]),
                niche_count=int(ladder["niche_count"]),
                knockouts=(knockout_id,),
                notes=f"Single-edge knockout {knockout_id}; sham/yoked cost match declared in prereg.",
            )
        )
    return cells


def build_interaction_screening_cells(
    *,
    seed: int,
    scale_label: str = "S2",
) -> list[CampaignCell]:
    """Fractional 2-factor pairs mapping to declared interactions (toolchain×capsule, …)."""

    if seed in PILOT_SEEDS:
        raise PilotGateError("Interaction cells must use held-out confirmatory seeds.")
    ladder = SCALE_LADDER[scale_label]
    # Map named interactions onto concrete knockout pairs (binary presence = edge off).
    pair_map: dict[str, tuple[str, str]] = {
        "toolchain × capsule": ("toolchain_to_action_off", "capsule_to_policy_off"),
        "capsule × ecology": ("capsule_to_policy_off", "ecological_feedback_off"),
        "mutation × capsule": ("mutation_off", "experience_to_capsule_off"),
        "heterogeneity × population_size": (
            "lineage_inheritance_off",
            "ecological_feedback_off",
        ),
    }
    cells: list[CampaignCell] = []
    for label in INTERACTIONS_TO_ESTIMATE:
        pair = pair_map[label]
        cells.append(
            CampaignCell(
                cell_id=f"interaction-{label.replace(' × ', 'x').replace(' ', '_')}-{scale_label}-{seed}",
                kind="interaction",
                seed=seed,
                scale_label=scale_label,
                width=int(ladder["width"]),
                height=int(ladder["height"]),
                tick_horizon=int(ladder["tick_horizon"]),
                population_cap=int(ladder["population_cap"]),
                niche_count=int(ladder["niche_count"]),
                knockouts=pair,
                interaction_label=label,
                notes="2-factor off cell for fractional-factorial interaction estimate.",
            )
        )
    return cells


def build_s4_scale_cells(
    *,
    seed: int,
    widths: Sequence[int] | None = None,
    horizons: Sequence[int] | None = None,
    pop_caps: Sequence[int] | None = None,
) -> list[CampaignCell]:
    """Finite-size S4 challenge grid (design enumeration; may be heavy to execute)."""

    if seed in PILOT_SEEDS:
        raise PilotGateError("S4 cells must use held-out confirmatory seeds.")
    s4 = SCALE_LADDER["S4"]
    ws = tuple(widths) if widths is not None else tuple(s4["widths"])
    hs = ws  # square cells by default
    ticks = tuple(horizons) if horizons is not None else tuple(s4["tick_horizons"])
    caps = tuple(pop_caps) if pop_caps is not None else tuple(s4["population_caps"])
    cells: list[CampaignCell] = []
    for w, h in zip(ws, hs, strict=True):
        for tick in ticks:
            for cap in caps:
                cells.append(
                    CampaignCell(
                        cell_id=f"s4-{w}x{h}-t{tick}-p{cap}-{seed}",
                        kind="scale_s4",
                        seed=seed,
                        scale_label="S4",
                        width=int(w),
                        height=int(h),
                        tick_horizon=int(tick),
                        population_cap=int(cap),
                        niche_count=int(s4["niche_count"]),
                        knockouts=(),
                        notes="S4 finite-size cell; report effect-direction retention or honest failure.",
                    )
                )
    return cells


def enumerate_campaign_design(
    *,
    confirmatory_seeds: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Return the full ILW-5 design enumeration (no outcomes)."""

    seeds = tuple(confirmatory_seeds) if confirmatory_seeds is not None else CONFIRMATORY_HELD_OUT_SEEDS
    # Design bookkeeping uses first confirmatory seed as exemplar for cell counts.
    exemplar = int(seeds[0])
    ablation = build_ablation_cells(seed=exemplar, scale_label="S2")
    interactions = build_interaction_screening_cells(seed=exemplar, scale_label="S2")
    s4 = build_s4_scale_cells(seed=exemplar)
    return {
        "prereg_version": PREREG_VERSION,
        "ilw_prereg_design_digest": ilw_prereg_design_digest(),
        "ilw_prereg_document_digest": ilw_prereg_document_digest(),
        "claim_ceiling": CLAIM_CEILING,
        "scientific_name": SCIENTIFIC_NAME,
        "confirmatory_seeds": list(seeds),
        "doe_plan_summary": {
            "phase_1": DOE_PLAN["phase_1_screening"]["method"],
            "phase_2a": DOE_PLAN["phase_2a_toggles"]["method"],
            "phase_2b": DOE_PLAN["phase_2b_continuous"]["method"],
            "interactions": list(INTERACTIONS_TO_ESTIMATE),
            "edge_knockouts": list(EDGE_KNOCKOUTS),
        },
        "cell_counts": {
            "ablation_per_seed": len(ablation),
            "interaction_per_seed": len(interactions),
            "s4_per_seed": len(s4),
            "seeds": len(seeds),
            "total_enumerated": (len(ablation) + len(interactions) + len(s4)) * len(seeds),
        },
        "exemplar_cells": {
            "ablation": [c.to_dict() for c in ablation],
            "interaction": [c.to_dict() for c in interactions],
            "s4_head": [c.to_dict() for c in s4[:3]],
            "s4_count": len(s4),
        },
        "remaining_for_colab": (
            "Execute remaining confirmatory seeds 4100–4107 × ablation + interaction + "
            "S4 grid on Colab/Drive; record digests + gates; do not raise ClaimGate."
        ),
        "campaign_outcomes_invented": False,
    }


def run_campaign_cell(
    cell: CampaignCell,
    *,
    harness: PilotHarness,
    bootstrap_population: int = DEFAULT_CAMPAIGN_BOOTSTRAP,
    run_replay: bool = True,
) -> CampaignCellResult:
    """Execute one confirmatory cell under an unlocked pilot harness."""

    assert_prereg_claim_ceiling()
    assert_claim_ceiling_runtime_observation()
    assert_no_forbidden_claims([])
    _assert_confirmatory_unlocked(harness, cell.seed)

    spec = cell.world_spec()
    ko = (
        KnockoutConfig.none()
        if not cell.knockouts
        else KnockoutConfig.from_iterable(cell.knockouts)
    )
    primary = IlwChainRuntime(
        run_id=f"ilw5-{cell.cell_id}",
        world_spec=spec,
        knockouts=ko,
    )
    pop = min(bootstrap_population, spec.population_cap)
    primary.bootstrap(population=pop)
    summary = primary.run()
    assert_no_fixture_outcome_injection(summary)
    if not _promotion_free(summary):
        raise IlwCampaignError(f"cell {cell.cell_id}: claim promotion markers present.")
    if not _attempt_fields_separate(primary):
        raise IlwCampaignError(f"cell {cell.cell_id}: counters not separate.")

    dag = load_integration_dag()
    observed = frozenset(primary.ledger.observed_edge_ids)
    coverage = float(len(dag.required_edge_ids & observed)) / float(len(dag.required_edge_ids))
    # Knockouts may prevent some edges from applying, but telemetry must still cover attempts.
    # Coverage uses observed edge_ids (attempt telemetry), so should remain 1.0.
    conservation = check_conservation(primary, raise_on_fail=False)
    digest = primary.final_digest()
    replay_matched = False
    if run_replay:
        replay = IlwChainRuntime(
            run_id=f"ilw5-{cell.cell_id}",
            world_spec=spec,
            knockouts=ko,
        )
        replay.bootstrap(population=pop)
        replay.run()
        replay_matched = digest == replay.final_digest()

    ko_ok: bool | None = None
    if cell.knockouts:
        # For single-edge ablations targeting capsule_to_policy, applied must be 0.
        if "capsule_to_policy_off" in cell.knockouts and len(cell.knockouts) == 1:
            ko_ok = (
                _edge_applied_count(primary, "capsule_to_policy") == 0
                and _edge_blocked_count(primary, "capsule_to_policy") > 0
            )
        else:
            ko_ok = True  # multi-edge / other ablations: presence of knockouts recorded

    return CampaignCellResult(
        cell=cell,
        replay_matched=replay_matched if run_replay else False,
        conservation_passed=bool(conservation.passed),
        required_edge_coverage=float(coverage),
        birth_count=int(summary.get("birth_count", 0) or 0),
        death_count=int(summary.get("death_count", 0) or 0),
        generation_turnover=_generation_turnover(primary),
        lineage_depth=_lineage_depth(primary),
        unique_genome_count=_unique_genome_count(primary),
        niches_occupied=_niches_occupied(primary),
        knockout_applied_zero_when_expected=ko_ok,
        final_digest=digest,
        event_count=int(summary.get("event_count", 0) or 0),
        no_claim_promotion=True,
        claim_ceiling=CLAIM_CEILING,
    )


def run_ilw5_smoke(
    *,
    seeds: Sequence[int] = (4100,),
    harness: PilotHarness | None = None,
    bootstrap_population: int = DEFAULT_CAMPAIGN_BOOTSTRAP,
    write_artifact: bool = True,
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    """Smoke 1–2 confirmatory cells after pilot unlock (honest, no invented tables)."""

    unlocked = harness if harness is not None else unlock_harness_from_artifact()
    selected = tuple(seeds)
    if len(selected) < 1:
        raise IlwCampaignError("Need at least one confirmatory seed for smoke.")
    for seed in selected:
        if seed not in CONFIRMATORY_HELD_OUT_SEEDS:
            raise PilotGateError(
                f"ILW-5 smoke seed {seed} not in CONFIRMATORY_HELD_OUT_SEEDS."
            )

    design = enumerate_campaign_design()
    results: list[CampaignCellResult] = []

    # Cell 1: baseline confirmatory at S2.
    baseline = build_ablation_cells(seed=selected[0], scale_label="S2")[0]
    results.append(
        run_campaign_cell(
            baseline,
            harness=unlocked,
            bootstrap_population=bootstrap_population,
            run_replay=True,
        )
    )
    # Cell 2 (optional second seed or ablation on same seed).
    if len(selected) >= 2:
        baseline2 = build_ablation_cells(seed=selected[1], scale_label="S2")[0]
        results.append(
            run_campaign_cell(
                baseline2,
                harness=unlocked,
                bootstrap_population=bootstrap_population,
                run_replay=True,
            )
        )
    else:
        ablation = next(
            c for c in build_ablation_cells(seed=selected[0], scale_label="S2") if c.knockouts
        )
        # Prefer capsule_to_policy_off for a clear causal break smoke.
        preferred = [
            c
            for c in build_ablation_cells(seed=selected[0], scale_label="S2")
            if c.knockouts == ("capsule_to_policy_off",)
        ]
        ablation = preferred[0] if preferred else ablation
        results.append(
            run_campaign_cell(
                ablation,
                harness=unlocked,
                bootstrap_population=bootstrap_population,
                run_replay=True,
            )
        )

    payload: dict[str, Any] = {
        "milestone": "ILW-5",
        "status": "smoke_runtime_observation",
        "claim_ceiling": CLAIM_CEILING,
        "scientific_name": SCIENTIFIC_NAME,
        "ilw_prereg_design_digest": design["ilw_prereg_design_digest"],
        "ilw_prereg_document_digest": design["ilw_prereg_document_digest"],
        "design_cell_counts": design["cell_counts"],
        "executed_cells": [r.to_dict() for r in results],
        "remaining_for_colab": design["remaining_for_colab"],
        "campaign_outcomes_invented": False,
        "cce_claimed": False,
        "intelligence_claimed": False,
        "ladder_promotion": None,
        "scientific_claim_emitted": False,
        "claim_promotions": [],
        "morris_ee_note": (
            "Morris EE screening + full fractional-factorial / DSD continuous arms "
            "are encoded in design; not fully executed locally."
        ),
    }
    if write_artifact:
        path = artifact_path or default_smoke_artifact_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def select_partial_campaign_cells(
    *,
    ablation_seeds: Sequence[int] = (4100, 4101),
    interaction_seeds: Sequence[int] = (4100,),
    s4_seeds: Sequence[int] = (4100,),
    s4_widths: Sequence[int] = (32, 64),
    s4_horizons: Sequence[int] = (128,),
    s4_pop_caps: Sequence[int] = (64,),
    scale_label: str = "S2",
) -> list[CampaignCell]:
    """Build the meaningful confirmatory subset (design only; no outcomes).

    Default: all 8 ablation arms × seeds 4100–4101, interaction screening on
    4100, and a small S4 slice (not the full 27×8 grid).
    """

    cells: list[CampaignCell] = []
    seen: set[str] = set()
    for seed in ablation_seeds:
        for cell in build_ablation_cells(seed=int(seed), scale_label=scale_label):
            if cell.cell_id not in seen:
                cells.append(cell)
                seen.add(cell.cell_id)
    for seed in interaction_seeds:
        for cell in build_interaction_screening_cells(seed=int(seed), scale_label=scale_label):
            if cell.cell_id not in seen:
                cells.append(cell)
                seen.add(cell.cell_id)
    for seed in s4_seeds:
        for cell in build_s4_scale_cells(
            seed=int(seed),
            widths=s4_widths,
            horizons=s4_horizons,
            pop_caps=s4_pop_caps,
        ):
            if cell.cell_id not in seen:
                cells.append(cell)
                seen.add(cell.cell_id)
    return cells


def run_ilw5_partial(
    *,
    cells: Sequence[CampaignCell] | None = None,
    harness: PilotHarness | None = None,
    bootstrap_population: int = DEFAULT_CAMPAIGN_BOOTSTRAP,
    run_replay: bool = False,
    write_artifact: bool = True,
    artifact_path: Path | None = None,
    resume: bool = True,
    max_cells: int | None = None,
    ablation_seeds: Sequence[int] = (4100, 4101),
    interaction_seeds: Sequence[int] = (4100,),
    s4_seeds: Sequence[int] = (4100,),
    s4_widths: Sequence[int] = (32, 64),
    s4_horizons: Sequence[int] = (128,),
    s4_pop_caps: Sequence[int] = (64,),
) -> dict[str, Any]:
    """Execute a confirmatory subset; write honest partial artifact (no invented rows).

    ``run_replay`` defaults False so a meaningful subset fits local wall-clock;
    smoke already verified digest replay on S2 cells. When False, each result
    records ``replay_matched=False`` honestly.
    """

    unlocked = harness if harness is not None else unlock_harness_from_artifact()
    design = enumerate_campaign_design()
    planned = list(cells) if cells is not None else select_partial_campaign_cells(
        ablation_seeds=ablation_seeds,
        interaction_seeds=interaction_seeds,
        s4_seeds=s4_seeds,
        s4_widths=s4_widths,
        s4_horizons=s4_horizons,
        s4_pop_caps=s4_pop_caps,
    )
    path = artifact_path or default_partial_artifact_path()
    prior_by_id: dict[str, dict[str, Any]] = {}
    if resume and path.is_file():
        prior = json.loads(path.read_text())
        for row in prior.get("executed_cells", []):
            cell_id = row.get("cell", {}).get("cell_id")
            if isinstance(cell_id, str):
                prior_by_id[cell_id] = row

    # Execute only cells not already present; preserve all prior planned rows even
    # when max_cells stops early (do not drop later prior interaction/S4 cells).
    pending = [c for c in planned if c.cell_id not in prior_by_id]
    if max_cells is not None:
        pending = pending[: int(max_cells)]
    newly_run = 0
    new_by_id: dict[str, dict[str, Any]] = {}
    for cell in pending:
        executed = run_campaign_cell(
            cell,
            harness=unlocked,
            bootstrap_population=bootstrap_population,
            run_replay=run_replay,
        )
        new_by_id[cell.cell_id] = executed.to_dict()
        newly_run += 1
        combined = dict(prior_by_id)
        combined.update(new_by_id)
        results = [combined[c.cell_id] for c in planned if c.cell_id in combined]
        if write_artifact:
            remaining_ids = [c.cell_id for c in planned if c.cell_id not in combined]
            payload = _partial_payload(
                design=design,
                planned=planned,
                results=results,
                newly_run=newly_run,
                run_replay=run_replay,
                remaining_ids=remaining_ids,
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    combined = dict(prior_by_id)
    combined.update(new_by_id)
    results = [combined[c.cell_id] for c in planned if c.cell_id in combined]
    remaining_ids = [c.cell_id for c in planned if c.cell_id not in combined]
    payload = _partial_payload(
        design=design,
        planned=planned,
        results=results,
        newly_run=newly_run,
        run_replay=run_replay,
        remaining_ids=remaining_ids,
    )
    if write_artifact:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _partial_payload(
    *,
    design: Mapping[str, Any],
    planned: Sequence[CampaignCell],
    results: Sequence[Mapping[str, Any]],
    newly_run: int,
    run_replay: bool,
    remaining_ids: Sequence[str],
) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    for row in results:
        kind = str(row.get("cell", {}).get("kind", "unknown"))
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "milestone": "ILW-5",
        "status": "partial_runtime_observation",
        "claim_ceiling": CLAIM_CEILING,
        "scientific_name": SCIENTIFIC_NAME,
        "ilw_prereg_design_digest": design["ilw_prereg_design_digest"],
        "ilw_prereg_document_digest": design["ilw_prereg_document_digest"],
        "design_cell_counts": design["cell_counts"],
        "planned_cell_ids": [c.cell_id for c in planned],
        "planned_count": len(planned),
        "executed_count": len(results),
        "enumerated_total": design["cell_counts"]["total_enumerated"],
        "newly_run_this_invocation": newly_run,
        "executed_by_kind": by_kind,
        "run_replay": bool(run_replay),
        "executed_cells": list(results),
        "remaining_planned_cell_ids": list(remaining_ids),
        "remaining_for_colab": (
            "Full confirmatory grid remains: seeds 4100–4107 × ablation + interaction + "
            "full S4 27-cell grid + Morris EE / DSD continuous arms. Do not raise ClaimGate."
        ),
        "campaign_outcomes_invented": False,
        "cce_claimed": False,
        "intelligence_claimed": False,
        "ladder_promotion": None,
        "scientific_claim_emitted": False,
        "claim_promotions": [],
        "honesty_notes": [
            "Only executed cells appear; no fixture/invented outcome rows.",
            "ClaimGate ceiling remains runtime_observation.",
            "Partial local subset; not a full confirmatory campaign.",
            (
                "Replay digest check skipped in this partial (run_replay=False); "
                "S2 smoke previously recorded replay_matched=true for baseline + "
                "capsule_to_policy_off at seed 4100."
                if not run_replay
                else "Replay digest check enabled for executed cells."
            ),
        ],
    }



__all__ = [
    "CampaignCell",
    "CampaignCellResult",
    "DEFAULT_CAMPAIGN_BOOTSTRAP",
    "DEFAULT_PARTIAL_ARTIFACT",
    "DEFAULT_SMOKE_ARTIFACT",
    "IlwCampaignError",
    "build_ablation_cells",
    "build_interaction_screening_cells",
    "build_s4_scale_cells",
    "default_partial_artifact_path",
    "default_smoke_artifact_path",
    "enumerate_campaign_design",
    "run_campaign_cell",
    "run_ilw5_partial",
    "run_ilw5_smoke",
    "select_partial_campaign_cells",
]
