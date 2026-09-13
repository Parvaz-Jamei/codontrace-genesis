"""ILW-3 integrated smoke: replay, conservation, edge coverage; no science claim.

Runs the genome→lineage chain at S1-ish scale under one run_id / WorldSpec /
scheduler / ledger, then:

1. Replays and requires bitwise-equal ``final_digest``
2. Checks energy/resource conservation invariants
3. Requires 100% required-edge coverage
4. Keeps attempted / accepted / applied as separate counters
5. Reports birth/death when the honest dynamics produce them
6. Emits **no** ClaimGate ladder promotion / scientific claim

Claim ceiling remains ``runtime_observation``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.adapter_honesty import (
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
)
from codontrace.genesis.ilw.chain_runtime import IlwChainRuntime
from codontrace.genesis.ilw.conservation import ConservationReport, check_conservation
from codontrace.genesis.ilw.dag import CLAIM_CEILING, SCIENTIFIC_NAME, load_integration_dag
from codontrace.genesis.ilw.knockouts import KnockoutConfig
from codontrace.genesis.ilw.world_spec import WorldSpec

# Keys that would indicate a ladder / ClaimGate promotion in smoke output.
_FORBIDDEN_PROMOTION_KEYS: frozenset[str] = frozenset(
    {
        "ladder_promoted_to",
        "claim_ladder_promotion",
        "promoted_claim_level",
        "claimgate_promotion",
        "strong_claim_ladder_result",
        "tokyo_type1_passed",
        "collective_intelligence_candidate",
    }
)


class IlwSmokeError(ConfigurationError):
    """Raised when the ILW-3 integrated smoke cannot pass honestly."""


@dataclass(frozen=True, slots=True)
class IlwSmokeReport:
    """Integrated smoke report (runtime observation only; no claim promotion)."""

    run_id: str
    scale_label: str
    seed: int
    tick_horizon: int
    width: int
    height: int
    primary_final_digest: str
    replay_final_digest: str
    replay_matched: bool
    required_edge_coverage: float
    observed_edge_ids: tuple[str, ...]
    missing_edge_ids: tuple[str, ...]
    conservation: ConservationReport
    birth_count: int
    death_count: int
    alive_count: int
    organism_count: int
    event_count: int
    attempt_fields_separate: bool
    claim_ceiling: str
    scientific_name: str
    claim_promotions: tuple[Any, ...]
    ladder_promotion: None
    scientific_claim_emitted: bool
    primary_summary: Mapping[str, JsonValue] = field(repr=False)
    replay_summary: Mapping[str, JsonValue] = field(repr=False)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "scale_label": self.scale_label,
            "seed": self.seed,
            "tick_horizon": self.tick_horizon,
            "width": self.width,
            "height": self.height,
            "primary_final_digest": self.primary_final_digest,
            "replay_final_digest": self.replay_final_digest,
            "replay_matched": self.replay_matched,
            "required_edge_coverage": self.required_edge_coverage,
            "observed_edge_ids": list(self.observed_edge_ids),
            "missing_edge_ids": list(self.missing_edge_ids),
            "conservation": self.conservation.to_dict(),
            "birth_count": self.birth_count,
            "death_count": self.death_count,
            "alive_count": self.alive_count,
            "organism_count": self.organism_count,
            "event_count": self.event_count,
            "attempt_fields_separate": self.attempt_fields_separate,
            "claim_ceiling": self.claim_ceiling,
            "scientific_name": self.scientific_name,
            "claim_promotions": list(self.claim_promotions),
            "ladder_promotion": self.ladder_promotion,
            "scientific_claim_emitted": self.scientific_claim_emitted,
            # Explicit non-promotion markers for assays / greps.
            "milestone": "ILW-3",
            "status": "runtime_observation",
        }


def _assert_no_promotion_payload(payload: Mapping[str, Any]) -> None:
    banned = sorted(key for key in payload if key in _FORBIDDEN_PROMOTION_KEYS)
    if banned:
        raise IlwSmokeError(
            "ILW-3 smoke must not emit ClaimGate / ladder promotion fields: "
            + ", ".join(banned)
        )
    promotions = payload.get("claim_promotions", [])
    if promotions not in ([], (), None):
        raise IlwSmokeError(
            f"ILW-3 smoke claim_promotions must be empty; got {promotions!r}."
        )
    if payload.get("ladder_promotion") is not None:
        raise IlwSmokeError("ILW-3 smoke ladder_promotion must be None.")
    if payload.get("scientific_claim_emitted") is True:
        raise IlwSmokeError("ILW-3 smoke must not set scientific_claim_emitted=True.")


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
        # Values may differ (never forced equal as a collapsed counter).
        _ = (
            int(payload["attempted"]),
            int(payload["accepted"]),
            int(payload["applied"]),
        )
    return True


def run_integrated_smoke(
    *,
    run_id: str = "ilw3-smoke",
    seed: int = 1,
    population: int = 4,
    world_spec: WorldSpec | None = None,
    knockouts: KnockoutConfig | None = None,
    require_birth_death: bool = True,
    atol: float = 1e-9,
) -> IlwSmokeReport:
    """Execute ILW-3 integrated smoke + independent replay under the same spec.

    Does **not** call ClaimGate, does **not** promote ladder levels, and keeps
    the claim ceiling at ``runtime_observation``.
    """

    assert_claim_ceiling_runtime_observation()
    spec = world_spec if world_spec is not None else WorldSpec.s1_smoke(seed=seed)
    if spec.claim_ceiling != CLAIM_CEILING:
        raise IlwSmokeError("WorldSpec claim ceiling must remain runtime_observation.")
    if spec.width * spec.height <= 4 * 4 and spec.tick_horizon <= 6:
        raise IlwSmokeError(
            "ILW-3 integrated smoke must be larger than S0 unit (4×4 / 6 tick); "
            f"got {spec.width}×{spec.height} / {spec.tick_horizon} tick."
        )

    ko = knockouts or KnockoutConfig.none()
    primary = IlwChainRuntime(run_id=run_id, world_spec=spec, knockouts=ko)
    primary.bootstrap(population=population)
    primary_summary = primary.run()
    assert_no_fixture_outcome_injection(primary_summary)
    _assert_no_promotion_payload(primary_summary)

    dag = load_integration_dag()
    observed = frozenset(primary.ledger.observed_edge_ids)
    missing = tuple(sorted(dag.required_edge_ids - observed))
    coverage = (
        1.0
        if not dag.required_edge_ids
        else float(len(dag.required_edge_ids & observed)) / float(len(dag.required_edge_ids))
    )
    if coverage < 1.0 or missing:
        raise IlwSmokeError(
            f"Required-edge coverage must be 100%; missing: {list(missing)}"
        )
    primary.assert_required_edges_covered()

    if not _attempt_fields_separate(primary):
        raise IlwSmokeError(
            "attempted / accepted / applied must remain separate counters on all events."
        )

    conservation = check_conservation(primary, atol=atol, raise_on_fail=True)

    births = int(primary_summary.get("birth_count", 0) or 0)
    deaths = int(primary_summary.get("death_count", 0) or 0)
    if require_birth_death and (births < 1 or deaths < 1):
        raise IlwSmokeError(
            f"ILW-3 smoke expected ≥1 birth and ≥1 death; got births={births}, deaths={deaths}."
        )

    # Independent replay: new runtime object, same run_id/spec/seed/population.
    replay = IlwChainRuntime(run_id=run_id, world_spec=spec, knockouts=ko)
    replay.bootstrap(population=population)
    replay_summary = replay.run()
    assert_no_fixture_outcome_injection(replay_summary)
    _assert_no_promotion_payload(replay_summary)

    primary_digest = primary.final_digest()
    replay_digest = replay.final_digest()
    if primary_digest != replay_digest:
        raise IlwSmokeError(
            "Replay final_digest mismatch "
            f"(primary={primary_digest!r}, replay={replay_digest!r})."
        )
    if primary_summary.get("final_digest") != replay_summary.get("final_digest"):
        raise IlwSmokeError("Replay summary final_digest mismatch.")

    report = IlwSmokeReport(
        run_id=run_id,
        scale_label=spec.scale_label,
        seed=spec.seed,
        tick_horizon=spec.tick_horizon,
        width=spec.width,
        height=spec.height,
        primary_final_digest=primary_digest,
        replay_final_digest=replay_digest,
        replay_matched=True,
        required_edge_coverage=coverage,
        observed_edge_ids=tuple(sorted(observed)),
        missing_edge_ids=missing,
        conservation=conservation,
        birth_count=births,
        death_count=deaths,
        alive_count=int(primary_summary.get("alive_count", 0) or 0),
        organism_count=int(primary_summary.get("organism_count", 0) or 0),
        event_count=int(primary_summary.get("event_count", 0) or 0),
        attempt_fields_separate=True,
        claim_ceiling=CLAIM_CEILING,
        scientific_name=SCIENTIFIC_NAME,
        claim_promotions=(),
        ladder_promotion=None,
        scientific_claim_emitted=False,
        primary_summary=primary_summary,
        replay_summary=replay_summary,
    )
    _assert_no_promotion_payload(report.to_dict())
    return report
