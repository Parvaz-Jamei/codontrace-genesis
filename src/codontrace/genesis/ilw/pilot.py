"""ILW S2 pilot runner (gates before confirmatory / ILW-5).

Runs prereg pilot seeds at S2, records POM acceptance rows, evaluates the six
pilot gates, and writes a durable artifact. Does **not** invent campaign
outcomes or raise ClaimGate above ``runtime_observation``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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
from codontrace.genesis.ilw.prereg import (
    PILOT_SEEDS,
    POM_ACCEPTANCE_PATTERNS,
    PREREG_VERSION,
    SCALE_LADDER,
    PilotGateError,
    PilotGateStatus,
    PilotHarness,
    assert_no_forbidden_claims,
    assert_prereg_claim_ceiling,
    assert_seed_policy_disjoint,
    ilw_prereg_design_digest,
    ilw_prereg_document_digest,
)
from codontrace.genesis.ilw.world_spec import WorldSpec

PomVerdict = Literal["pass", "fail", "inconclusive"]

DEFAULT_PILOT_BOOTSTRAP_POPULATION = 8
DEFAULT_KNOCKOUT_ID = "capsule_to_policy_off"
DEFAULT_ARTIFACT_RELATIVE = "outputs/ilw_pilot_s2.json"


class IlwPilotError(ConfigurationError):
    """Raised when the ILW S2 pilot cannot complete honestly."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_artifact_path() -> Path:
    return _repo_root() / DEFAULT_ARTIFACT_RELATIVE


def _generation_turnover(runtime: IlwChainRuntime) -> int:
    """Unique organism ids that both appeared via reproduction and later died."""

    return sum(
        1
        for org in runtime.organisms
        if org.parent_id is not None and not org.alive
    )


def _lineage_depth(runtime: IlwChainRuntime) -> int:
    max_depth = 0
    by_id = {org.organism_id: org for org in runtime.organisms}
    for org in by_id.values():
        depth = 0
        cur = org.parent_id
        seen: set[str] = set()
        while cur and cur not in seen:
            seen.add(cur)
            depth += 1
            parent = by_id.get(cur)
            cur = parent.parent_id if parent is not None else None
        if depth > max_depth:
            max_depth = depth
    return max_depth


def _unique_genome_count(runtime: IlwChainRuntime) -> int:
    return len({org.genome_digest for org in runtime.organisms})


def _niches_occupied(runtime: IlwChainRuntime) -> int:
    """Niches visited by any organism over the run (not end-alive only)."""

    world = runtime.world
    occupied: set[int] = set()
    for org in runtime.organisms:
        occupied.add(world.niche_id(org.x, org.y))
    return len(occupied)


def _edge_applied_count(runtime: IlwChainRuntime, edge_id: str) -> int:
    return sum(
        1
        for event in runtime.ledger.events
        if event.edge_id == edge_id and int(event.payload.get("applied", 0) or 0) == 1
    )


def _edge_blocked_count(runtime: IlwChainRuntime, edge_id: str) -> int:
    return sum(
        1
        for event in runtime.ledger.events
        if event.edge_id == edge_id and event.payload.get("blocked_reason")
    )


def _attempt_fields_separate(runtime: IlwChainRuntime) -> bool:
    for event in runtime.ledger.events:
        payload = event.payload
        if "attempted" not in payload or "accepted" not in payload or "applied" not in payload:
            return False
        for banned in (
            "attempt_accepted_applied",
            "attempt_success",
            "attempts_accepted_applied",
        ):
            if banned in payload:
                return False
    return True


def _promotion_free(summary: Mapping[str, Any]) -> bool:
    if summary.get("claim_promotions") not in ([], (), None):
        return False
    if summary.get("ladder_promotion") is not None:
        return False
    if summary.get("scientific_claim_emitted") is True:
        return False
    banned = {
        "ladder_promoted_to",
        "claim_ladder_promotion",
        "promoted_claim_level",
        "claimgate_promotion",
        "strong_claim_ladder_result",
        "tokyo_type1_passed",
        "collective_intelligence_candidate",
        "intelligence",
        "agi",
        "collective_intelligence",
    }
    return not any(key in summary for key in banned)


@dataclass(frozen=True, slots=True)
class SeedPilotResult:
    """Per-seed S2 pilot observation (runtime only)."""

    seed: int
    run_id: str
    replay_matched: bool
    conservation_passed: bool
    required_edge_coverage: float
    missing_edge_ids: tuple[str, ...]
    birth_count: int
    death_count: int
    generation_turnover: int
    lineage_depth: int
    regime_changes: int
    unique_genome_count: int
    niches_occupied: int
    capsule_to_policy_applied: int
    event_count: int
    organism_count: int
    alive_count: int
    attempt_fields_separate: bool
    no_claim_promotion: bool
    claim_ceiling: str
    primary_final_digest: str
    replay_final_digest: str
    world_spec_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "run_id": self.run_id,
            "replay_matched": self.replay_matched,
            "conservation_passed": self.conservation_passed,
            "required_edge_coverage": self.required_edge_coverage,
            "missing_edge_ids": list(self.missing_edge_ids),
            "birth_count": self.birth_count,
            "death_count": self.death_count,
            "generation_turnover": self.generation_turnover,
            "lineage_depth": self.lineage_depth,
            "regime_changes": self.regime_changes,
            "unique_genome_count": self.unique_genome_count,
            "niches_occupied": self.niches_occupied,
            "capsule_to_policy_applied": self.capsule_to_policy_applied,
            "event_count": self.event_count,
            "organism_count": self.organism_count,
            "alive_count": self.alive_count,
            "attempt_fields_separate": self.attempt_fields_separate,
            "no_claim_promotion": self.no_claim_promotion,
            "claim_ceiling": self.claim_ceiling,
            "primary_final_digest": self.primary_final_digest,
            "replay_final_digest": self.replay_final_digest,
            "world_spec_digest": self.world_spec_digest,
        }


@dataclass(frozen=True, slots=True)
class PomPatternRecord:
    pattern_id: str
    verdict: PomVerdict
    note: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "id": self.pattern_id,
            "verdict": self.verdict,
            "note": self.note,
        }


@dataclass
class PilotCampaignReport:
    """Aggregate S2 pilot report + gates (no science claim)."""

    seed_results: list[SeedPilotResult] = field(default_factory=list)
    pom_records: list[PomPatternRecord] = field(default_factory=list)
    knockout_probe: dict[str, JsonValue] = field(default_factory=dict)
    scale_probe: dict[str, JsonValue] = field(default_factory=dict)
    gates: PilotGateStatus = field(default_factory=PilotGateStatus)
    design_digest: str = ""
    document_digest: str = ""
    prereg_version: str = PREREG_VERSION
    scale_label: str = "S2"
    scientific_name: str = SCIENTIFIC_NAME
    claim_ceiling: str = CLAIM_CEILING
    status: str = "incomplete"
    stop_rules_triggered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "milestone": "ILW-pilot-S2",
            "status": self.status,
            "prereg_version": self.prereg_version,
            "scale_label": self.scale_label,
            "claim_ceiling": self.claim_ceiling,
            "scientific_name": self.scientific_name,
            "ilw_prereg_design_digest": self.design_digest,
            "ilw_prereg_document_digest": self.document_digest,
            "gates": self.gates.to_dict(),
            "gates_all_passed": self.gates.all_passed,
            "pom_patterns": [item.to_dict() for item in self.pom_records],
            "seed_results": [item.to_dict() for item in self.seed_results],
            "knockout_probe": dict(self.knockout_probe),
            "scale_probe": dict(self.scale_probe),
            "stop_rules_triggered": list(self.stop_rules_triggered),
            "ladder_promotion": None,
            "scientific_claim_emitted": False,
            "claim_promotions": [],
            "cce_claimed": False,
            "intelligence_claimed": False,
        }


def run_seed_pilot(
    seed: int,
    *,
    bootstrap_population: int = DEFAULT_PILOT_BOOTSTRAP_POPULATION,
    run_replay: bool = True,
) -> SeedPilotResult:
    """Execute one S2 pilot seed with optional independent replay."""

    assert_seed_policy_disjoint()
    if seed not in PILOT_SEEDS:
        raise PilotGateError(
            f"pilot seed {seed} not in PILOT_SEEDS={list(PILOT_SEEDS)}"
        )
    assert_claim_ceiling_runtime_observation()
    assert_prereg_claim_ceiling()

    spec = WorldSpec.s2_pilot(seed=seed)
    run_id = f"ilw-pilot-s2-{seed}"
    primary = IlwChainRuntime(run_id=run_id, world_spec=spec)
    primary.bootstrap(population=bootstrap_population)
    primary_summary = primary.run()
    assert_no_fixture_outcome_injection(primary_summary)
    if not _promotion_free(primary_summary):
        raise IlwPilotError(f"seed {seed}: claim promotion markers present.")

    dag = load_integration_dag()
    observed = frozenset(primary.ledger.observed_edge_ids)
    missing = tuple(sorted(dag.required_edge_ids - observed))
    coverage = (
        1.0
        if not dag.required_edge_ids
        else float(len(dag.required_edge_ids & observed)) / float(len(dag.required_edge_ids))
    )
    conservation = check_conservation(primary, raise_on_fail=False)
    if not _attempt_fields_separate(primary):
        raise IlwPilotError(f"seed {seed}: attempted/accepted/applied not separate.")

    primary_digest = primary.final_digest()
    replay_matched = False
    replay_digest = ""
    if run_replay:
        replay = IlwChainRuntime(run_id=run_id, world_spec=spec)
        replay.bootstrap(population=bootstrap_population)
        replay_summary = replay.run()
        assert_no_fixture_outcome_injection(replay_summary)
        if not _promotion_free(replay_summary):
            raise IlwPilotError(f"seed {seed}: replay emitted claim promotion.")
        replay_digest = replay.final_digest()
        replay_matched = primary_digest == replay_digest

    return SeedPilotResult(
        seed=seed,
        run_id=run_id,
        replay_matched=replay_matched if run_replay else False,
        conservation_passed=bool(conservation.passed),
        required_edge_coverage=float(coverage),
        missing_edge_ids=missing,
        birth_count=int(primary_summary.get("birth_count", 0) or 0),
        death_count=int(primary_summary.get("death_count", 0) or 0),
        generation_turnover=_generation_turnover(primary),
        lineage_depth=_lineage_depth(primary),
        regime_changes=0,  # discrete regime shifter not yet wired; honest zero
        unique_genome_count=_unique_genome_count(primary),
        niches_occupied=_niches_occupied(primary),
        capsule_to_policy_applied=_edge_applied_count(primary, "capsule_to_policy"),
        event_count=int(primary_summary.get("event_count", 0) or 0),
        organism_count=int(primary_summary.get("organism_count", 0) or 0),
        alive_count=int(primary_summary.get("alive_count", 0) or 0),
        attempt_fields_separate=True,
        no_claim_promotion=True,
        claim_ceiling=CLAIM_CEILING,
        primary_final_digest=primary_digest,
        replay_final_digest=replay_digest,
        world_spec_digest=spec.digest(),
    )


def _run_knockout_probe(
    seed: int,
    *,
    knockout_id: str = DEFAULT_KNOCKOUT_ID,
    bootstrap_population: int = DEFAULT_PILOT_BOOTSTRAP_POPULATION,
) -> dict[str, JsonValue]:
    spec = WorldSpec.s2_pilot(seed=seed)
    intact = IlwChainRuntime(run_id=f"ilw-pilot-ko-intact-{seed}", world_spec=spec)
    intact.bootstrap(population=bootstrap_population)
    intact.run()
    ko = IlwChainRuntime(
        run_id=f"ilw-pilot-ko-{knockout_id}-{seed}",
        world_spec=spec,
        knockouts=KnockoutConfig.only(knockout_id),
    )
    ko.bootstrap(population=bootstrap_population)
    ko.run()
    edge = "capsule_to_policy"
    intact_applied = _edge_applied_count(intact, edge)
    ko_applied = _edge_applied_count(ko, edge)
    ko_blocked = _edge_blocked_count(ko, edge)
    broke = intact_applied > 0 and ko_applied == 0 and ko_blocked > 0
    return {
        "seed": seed,
        "knockout_id": knockout_id,
        "edge_id": edge,
        "intact_applied": intact_applied,
        "knockout_applied": ko_applied,
        "knockout_blocked": ko_blocked,
        "path_broke_as_predicted": broke,
    }


def _run_scale_probe(
    seed: int,
    *,
    bootstrap_population: int = DEFAULT_PILOT_BOOTSTRAP_POPULATION,
) -> dict[str, JsonValue]:
    """Compare S1 vs S2 on one pilot seed for pom_8 direction retention (honest)."""

    s1 = WorldSpec.s1_smoke(seed=seed)
    s2 = WorldSpec.s2_pilot(seed=seed)
    r1 = IlwChainRuntime(run_id=f"ilw-pilot-scale-s1-{seed}", world_spec=s1)
    r1.bootstrap(population=min(bootstrap_population, s1.population_cap))
    sum1 = r1.run()
    r2 = IlwChainRuntime(run_id=f"ilw-pilot-scale-s2-{seed}", world_spec=s2)
    r2.bootstrap(population=bootstrap_population)
    sum2 = r2.run()
    dag = load_integration_dag()
    cov1 = float(len(dag.required_edge_ids & frozenset(r1.ledger.observed_edge_ids))) / float(
        len(dag.required_edge_ids)
    )
    cov2 = float(len(dag.required_edge_ids & frozenset(r2.ledger.observed_edge_ids))) / float(
        len(dag.required_edge_ids)
    )
    direction_retained = (
        cov1 == 1.0
        and cov2 == 1.0
        and int(sum1.get("birth_count", 0) or 0) >= 1
        and int(sum2.get("birth_count", 0) or 0) >= 1
    )
    return {
        "seed": seed,
        "s1_coverage": cov1,
        "s2_coverage": cov2,
        "s1_births": int(sum1.get("birth_count", 0) or 0),
        "s2_births": int(sum2.get("birth_count", 0) or 0),
        "effect_direction_retained": direction_retained,
        "note": "Coverage+births retention S1→S2; not a finite-size S4 claim.",
    }


def evaluate_pom_patterns(
    seed_results: Sequence[SeedPilotResult],
    *,
    knockout_probe: Mapping[str, Any],
    scale_probe: Mapping[str, Any],
) -> list[PomPatternRecord]:
    """Record all eight POM rows (pass/fail/inconclusive) — recording is the gate."""

    if not seed_results:
        return [
            PomPatternRecord(p["id"], "inconclusive", "no seed results")
            for p in POM_ACCEPTANCE_PATTERNS
        ]

    min_turnover = min(r.generation_turnover for r in seed_results)
    min_lineage = min(r.lineage_depth for r in seed_results)
    min_genomes = min(r.unique_genome_count for r in seed_results)
    min_niches = min(r.niches_occupied for r in seed_results)
    all_replay = all(r.replay_matched for r in seed_results)
    all_cons = all(r.conservation_passed for r in seed_results)
    all_cov = all(r.required_edge_coverage >= 1.0 for r in seed_results)
    all_c2p = all(r.capsule_to_policy_applied > 0 for r in seed_results)
    ladder_min = int(SCALE_LADDER["S2"]["min_generation_turnovers"])

    records: list[PomPatternRecord] = []
    for pattern in POM_ACCEPTANCE_PATTERNS:
        pid = pattern["id"]
        if pid == "pom_1_toolchain_phenotype":
            verdict: PomVerdict = "pass" if all_cov else "fail"
            note = "required-edge coverage includes toolchain→phenotype→action chain"
        elif pid == "pom_2_conservation":
            verdict = "pass" if all_cons else "fail"
            note = "resource/energy conservation assays across pilot seeds"
        elif pid == "pom_3_multigen_turnover":
            ok = min_turnover >= ladder_min and min_lineage >= 1
            verdict = "pass" if ok else "fail"
            note = (
                f"min generation_turnover={min_turnover} "
                f"(need ≥{ladder_min}); min lineage_depth={min_lineage}"
            )
        elif pid == "pom_4_diversity":
            verdict = "pass" if min_genomes >= 2 else "fail"
            note = f"min unique_genome_count={min_genomes}"
        elif pid == "pom_5_eco_evo_feedback":
            ok = min_niches >= 2 and all_cov
            verdict = "pass" if ok else "fail"
            note = f"min niches_occupied={min_niches}; ecological_feedback edge covered"
        elif pid == "pom_6_capsule_causal":
            verdict = "pass" if all_c2p else "fail"
            note = "capsule_to_policy applied>0 on each pilot seed (descendant fitness proxy via policy bias)"
        elif pid == "pom_7_null_yoked_break":
            broke = bool(knockout_probe.get("path_broke_as_predicted"))
            verdict = "pass" if broke else "fail"
            note = f"knockout probe: {dict(knockout_probe)}"
        elif pid == "pom_8_scale_direction":
            retained = bool(scale_probe.get("effect_direction_retained"))
            verdict = "pass" if retained else "fail"
            note = f"S1→S2 probe: {dict(scale_probe)}"
        else:
            verdict = "inconclusive"
            note = "unknown pattern id"
        records.append(PomPatternRecord(pid, verdict, note))
    return records


def evaluate_pilot_gates(
    seed_results: Sequence[SeedPilotResult],
    pom_records: Sequence[PomPatternRecord],
) -> PilotGateStatus:
    replay_ok = bool(seed_results) and all(r.replay_matched for r in seed_results)
    conservation_ok = bool(seed_results) and all(r.conservation_passed for r in seed_results)
    edge_coverage_ok = bool(seed_results) and all(
        r.required_edge_coverage >= 1.0 and not r.missing_edge_ids for r in seed_results
    )
    expected_ids = {p["id"] for p in POM_ACCEPTANCE_PATTERNS}
    recorded_ids = {p.pattern_id for p in pom_records}
    pom_patterns_recorded = expected_ids <= recorded_ids and len(pom_records) >= 8
    no_claim_promotion = bool(seed_results) and all(r.no_claim_promotion for r in seed_results)
    claim_ceiling_ok = CLAIM_CEILING == "runtime_observation" and all(
        r.claim_ceiling == "runtime_observation" for r in seed_results
    )
    return PilotGateStatus(
        replay_ok=replay_ok,
        conservation_ok=conservation_ok,
        edge_coverage_ok=edge_coverage_ok,
        pom_patterns_recorded=pom_patterns_recorded,
        no_claim_promotion=no_claim_promotion,
        claim_ceiling_ok=claim_ceiling_ok,
    )


def run_s2_pilot(
    seeds: Sequence[int] | None = None,
    *,
    bootstrap_population: int = DEFAULT_PILOT_BOOTSTRAP_POPULATION,
    run_replay: bool = True,
    knockout_seed: int | None = None,
    scale_seed: int | None = None,
    write_artifact: bool = True,
    artifact_path: Path | None = None,
) -> PilotCampaignReport:
    """Run the locked S2 pilot (PILOT_SEEDS), evaluate gates, optionally persist."""

    assert_seed_policy_disjoint()
    assert_prereg_claim_ceiling()
    assert_no_forbidden_claims([])
    selected = tuple(seeds) if seeds is not None else tuple(PILOT_SEEDS)
    for seed in selected:
        if seed not in PILOT_SEEDS:
            raise PilotGateError(
                f"Refusing non-pilot seed {seed}; PILOT_SEEDS={list(PILOT_SEEDS)}"
            )

    seed_results = [
        run_seed_pilot(
            seed,
            bootstrap_population=bootstrap_population,
            run_replay=run_replay,
        )
        for seed in selected
    ]

    ko_seed = int(knockout_seed if knockout_seed is not None else selected[0])
    sc_seed = int(scale_seed if scale_seed is not None else selected[0])
    knockout_probe = _run_knockout_probe(
        ko_seed, bootstrap_population=bootstrap_population
    )
    scale_probe = _run_scale_probe(sc_seed, bootstrap_population=bootstrap_population)

    pom_records = evaluate_pom_patterns(
        seed_results, knockout_probe=knockout_probe, scale_probe=scale_probe
    )
    gates = evaluate_pilot_gates(seed_results, pom_records)

    stop_rules: list[str] = []
    if not gates.replay_ok:
        stop_rules.append("stop_escalate_if_replay_fails")
    if not gates.conservation_ok:
        stop_rules.append("stop_escalate_if_conservation_fails")
    if not gates.edge_coverage_ok:
        stop_rules.append("stop_escalate_if_required_edge_coverage_lt_1")
    if not gates.pom_patterns_recorded:
        stop_rules.append("stop_escalate_if_pom_patterns_incomplete_at_current_scale")
    if not gates.all_passed:
        stop_rules.append("stop_confirmatory_if_pilot_gates_fail")

    report = PilotCampaignReport(
        seed_results=list(seed_results),
        pom_records=pom_records,
        knockout_probe=dict(knockout_probe),
        scale_probe=dict(scale_probe),
        gates=gates,
        design_digest=ilw_prereg_design_digest(),
        document_digest=ilw_prereg_document_digest(),
        status="PASS" if gates.all_passed else "FAIL",
        stop_rules_triggered=stop_rules,
    )

    if write_artifact:
        path = artifact_path or default_artifact_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n")
        _write_markdown_summary(report, path.with_suffix(".md"))

    return report


def _write_markdown_summary(report: PilotCampaignReport, path: Path) -> None:
    gates = report.gates.to_dict()
    lines = [
        "# ILW S2 pilot artifact",
        "",
        f"**Status:** `{report.status}`",
        f"**Prereg:** `{report.prereg_version}`",
        f"**ClaimGate ceiling:** `{report.claim_ceiling}` (unchanged)",
        f"**Scientific name:** `{report.scientific_name}`",
        f"**Design digest:** `{report.design_digest}`",
        f"**Document digest:** `{report.document_digest}`",
        "",
        "## Gates",
        "",
        "| Gate | Value |",
        "|------|-------|",
    ]
    for key, value in gates.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## POM patterns", "", "| ID | Verdict | Note |", "|----|---------|------|"])
    for row in report.pom_records:
        note = row.note.replace("|", "\\|")
        lines.append(f"| `{row.pattern_id}` | `{row.verdict}` | {note} |")
    lines.extend(["", "## Seed metrics", "", "| Seed | Replay | Cons | Cov | Turnover | Lineage | Genomes | Births | Deaths |", "|------|--------|------|-----|----------|---------|---------|--------|--------|"])
    for r in report.seed_results:
        lines.append(
            f"| {r.seed} | {r.replay_matched} | {r.conservation_passed} | "
            f"{r.required_edge_coverage:.0%} | {r.generation_turnover} | "
            f"{r.lineage_depth} | {r.unique_genome_count} | {r.birth_count} | {r.death_count} |"
        )
    lines.extend(
        [
            "",
            "## Knockout probe",
            "",
            "```json",
            json.dumps(report.knockout_probe, indent=2, sort_keys=True),
            "```",
            "",
            "## Scale probe (S1→S2)",
            "",
            "```json",
            json.dumps(report.scale_probe, indent=2, sort_keys=True),
            "```",
            "",
            "## Honesty",
            "",
            "- No ClaimGate ladder promotion.",
            "- No CCE / intelligence / AGI claim.",
            "- Confirmatory seeds untouched in this artifact.",
            "- `regime_changes=0` (discrete regime shifter not wired yet; honest).",
            "",
        ]
    )
    if report.stop_rules_triggered:
        lines.append("## Stop rules triggered")
        lines.append("")
        for rule in report.stop_rules_triggered:
            lines.append(f"- `{rule}`")
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


def load_pilot_gates(artifact_path: Path | None = None) -> PilotGateStatus:
    path = artifact_path or default_artifact_path()
    if not path.is_file():
        raise IlwPilotError(f"missing pilot artifact: {path}")
    data = json.loads(path.read_text())
    return PilotGateStatus.from_mapping(data.get("gates", {}))


def unlock_harness_from_artifact(artifact_path: Path | None = None) -> PilotHarness:
    """Return a PilotHarness unlocked iff the on-disk pilot artifact gates all passed."""

    gates = load_pilot_gates(artifact_path)
    if not gates.all_passed:
        raise PilotGateError(
            "Pilot artifact gates did not all pass; confirmatory remains locked "
            f"(status={gates.to_dict()})."
        )
    return PilotHarness(gates=gates)


def unlocked_harness_or_raise(report: PilotCampaignReport) -> PilotHarness:
    if not report.gates.all_passed:
        raise PilotGateError(
            "Refusing to unlock confirmatory harness; pilot gates failed "
            f"(status={report.gates.to_dict()})."
        )
    return PilotHarness(gates=report.gates)


__all__ = [
    "DEFAULT_ARTIFACT_RELATIVE",
    "DEFAULT_KNOCKOUT_ID",
    "DEFAULT_PILOT_BOOTSTRAP_POPULATION",
    "IlwPilotError",
    "PilotCampaignReport",
    "PomPatternRecord",
    "SeedPilotResult",
    "default_artifact_path",
    "evaluate_pilot_gates",
    "evaluate_pom_patterns",
    "load_pilot_gates",
    "run_s2_pilot",
    "run_seed_pilot",
    "unlock_harness_from_artifact",
    "unlocked_harness_or_raise",
]
