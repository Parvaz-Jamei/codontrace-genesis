"""ILW-4 locked preregistration hooks (before campaign outcomes).

Design constants and digests are frozen here. A tiny pilot harness stub
refuses confirmatory / held-out seeds until pilot gates pass (fail-first).
No large campaign is executed from this module.

ClaimGate ceiling remains ``runtime_observation``. Scientific name remains
``integrated eco-evolutionary runtime`` (never intelligence / AGI /
collective_intelligence).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.ilw.dag import CLAIM_CEILING, SCIENTIFIC_NAME
from codontrace.genesis.text_digest import sha256_text_file

PREREG_VERSION = "ilw_prereg_v1"
PREREG_RELATIVE_PATH = "docs/ILW_PREREG_V1.md"
EXPERIMENT_ID = "ilw_integrated_eco_evolutionary_runtime"

SeedRole = Literal["pilot", "confirmatory", "smoke"]

# ---------------------------------------------------------------------------
# Seed policy (locked before outcomes). Pilot and confirmatory are disjoint.
# Smoke may use a subset of pilot seeds only.
# ---------------------------------------------------------------------------

PILOT_SEEDS: tuple[int, ...] = tuple(range(3100, 3108))  # 3100..3107
CONFIRMATORY_HELD_OUT_SEEDS: tuple[int, ...] = tuple(range(4100, 4108))  # 4100..4107
SMOKE_SEEDS: tuple[int, ...] = (3100,)

# ---------------------------------------------------------------------------
# Scale ladder S0–S4 with explicit stop rules (numbers locked pre-outcome).
# ---------------------------------------------------------------------------

SCALE_LADDER: dict[str, dict[str, Any]] = {
    "S0": {
        "label": "S0",
        "role": "unit",
        "width": 4,
        "height": 4,
        "tick_horizon": 6,
        "population_cap": 8,
        "niche_count": 2,
        "min_generation_turnovers": 0,
        "notes": "Component unit only; never a full-world claim.",
    },
    "S1": {
        "label": "S1",
        "role": "integrated_smoke",
        "width": 16,
        "height": 16,
        "tick_horizon": 32,
        "population_cap": 24,
        "niche_count": 4,
        "min_generation_turnovers": 1,
        "notes": "ILW-3 smoke scale; ≥1 birth/death when dynamics allow.",
    },
    "S2": {
        "label": "S2",
        "role": "multi_generation_pilot",
        "width": 32,
        "height": 32,
        "tick_horizon": 128,
        "population_cap": 64,
        "niche_count": 4,
        "min_generation_turnovers": 3,
        "notes": "Pilot only; uses PILOT_SEEDS; no confirmatory inference.",
    },
    "S3": {
        "label": "S3",
        "role": "research",
        "width": 64,
        "height": 64,
        "tick_horizon": 512,
        "population_cap": 128,
        "niche_count": 6,
        "min_generation_turnovers": 10,
        "notes": "Research scale after pilot gates; still ClaimGate runtime_observation.",
    },
    "S4": {
        "label": "S4",
        "role": "finite_size_challenge",
        "widths": (32, 64, 96),
        "heights": (32, 64, 96),
        "tick_horizons": (128, 256, 512),
        "population_caps": (64, 128, 192),
        "niche_count": 6,
        "min_generation_turnovers_per_cell": 3,
        "notes": "≥3 sizes × ≥3 horizons; report effect-direction retention or honest failure.",
    },
}

STOP_RULES: tuple[str, ...] = (
    "stop_escalate_if_replay_fails",
    "stop_escalate_if_conservation_fails",
    "stop_escalate_if_required_edge_coverage_lt_1",
    "stop_escalate_if_pom_patterns_incomplete_at_current_scale",
    "stop_confirmatory_if_pilot_gates_fail",
    "stop_campaign_if_claim_ceiling_would_rise",
    "stop_s4_cell_if_finite_size_effect_direction_reverses_without_prereg_amendment",
    "never_promote_s0_or_s1_to_science_claim",
)

# ---------------------------------------------------------------------------
# Horizon definitions (not ticks alone).
# ---------------------------------------------------------------------------

HORIZON_DEFINITIONS: dict[str, str] = {
    "ticks": "Scheduler tick count under one run_id / WorldSpec.",
    "generation_turnover": (
        "Count of completed birth→death cycles (unique organism ids that both "
        "appeared via reproduction and later died), averaged per seed."
    ),
    "lineage_depth": (
        "Maximum ancestry-chain length from a living organism to the oldest "
        "recorded ancestor in the organism phylogeny."
    ),
    "regime_changes": (
        "Count of discrete resource-regime shifts applied by the world "
        "(stale information may expire)."
    ),
}

# ---------------------------------------------------------------------------
# Pattern-Oriented Modeling acceptance patterns (§گیت چندالگویی).
# ATP mean alone is never sufficient (Grimm & Railsback 2012).
# ---------------------------------------------------------------------------

POM_ACCEPTANCE_PATTERNS: tuple[dict[str, str], ...] = (
    {
        "id": "pom_1_toolchain_phenotype",
        "statement": "Toolchain and phenotype are valid under the integrated run.",
    },
    {
        "id": "pom_2_conservation",
        "statement": "Energy/resource conservation assays pass.",
    },
    {
        "id": "pom_3_multigen_turnover",
        "statement": "Multi-generation persistence with real turnover (not fixture).",
    },
    {
        "id": "pom_4_diversity",
        "statement": "Non-token genetic/phenotypic diversity is observable.",
    },
    {
        "id": "pom_5_eco_evo_feedback",
        "statement": "Competition, niches, and eco-evolutionary feedback emerge.",
    },
    {
        "id": "pom_6_capsule_causal",
        "statement": "Capsule transfer changes action and descendant fitness proxy.",
    },
    {
        "id": "pom_7_null_yoked_break",
        "statement": "Path breaks predictably under null/yoked/edge-off controls.",
    },
    {
        "id": "pom_8_scale_direction",
        "statement": "Effect direction retained across scales, or failure reported honestly.",
    },
)

# Mesoudi & Thornton (2018) CCE core criteria — ALL four required before any CCE claim.
MESOUDI_CCE_CRITERIA: tuple[dict[str, str], ...] = (
    {"id": "cce_innovation", "statement": "Behavioural novelty or modification (innovation)."},
    {
        "id": "cce_social_transmission",
        "statement": "Transfer via social learning / capsule channel.",
    },
    {
        "id": "cce_performance_improvement",
        "statement": "Learned behaviour improves a fitness-proxy performance measure.",
    },
    {
        "id": "cce_sequential_improvement",
        "statement": "Repeated transmission yields sequential improvement across generations.",
    },
)

# ---------------------------------------------------------------------------
# Interactions to estimate (OAT alone insufficient).
# ---------------------------------------------------------------------------

INTERACTIONS_TO_ESTIMATE: tuple[str, ...] = (
    "toolchain × capsule",
    "capsule × ecology",
    "mutation × capsule",
    "heterogeneity × population_size",
)

# ---------------------------------------------------------------------------
# Edge knockouts + sham/yoked controls plan.
# ---------------------------------------------------------------------------

EDGE_KNOCKOUTS: tuple[str, ...] = (
    "toolchain_to_action_off",
    "experience_to_capsule_off",
    "capsule_transport_off",
    "capsule_to_policy_off",
    "mutation_off",
    "ecological_feedback_off",
    "lineage_inheritance_off",
)

SHAM_YOKED_CONTROLS: dict[str, str] = {
    "sham_cost_match": (
        "When an edge is knocked out, apply matching compute/move/copy cost so "
        "throughput/cost alone cannot explain outcome differences."
    ),
    "yoked_timing": (
        "Yoked control preserves attempt timing/rate of the intact edge while "
        "severing informational content (no oracle fitness shortcut)."
    ),
    "one_edge_per_knockout": (
        "Each knockout severs exactly one declared cut set; never multi-edge "
        "silent cuts in the same arm."
    ),
    "no_outcome_injection": (
        "Fixture/oracle/treatment-oracle/fitness-shortcut injection remains forbidden."
    ),
}

# ---------------------------------------------------------------------------
# Design of experiments: Morris EE screening → fractional-factorial / DSD.
# DOIs are those already cited in the ILW plan (verified via literature refresh).
# ---------------------------------------------------------------------------

DOE_PLAN: dict[str, Any] = {
    "phase_1_screening": {
        "method": "Morris elementary effects (EE)",
        "purpose": "Screen continuous/knob factors; reject OAT-only inference.",
        "cite_doi": "10.1016/j.envsoft.2010.04.012",
        "cite_note": "Saltelli & Annoni 2010 — OAT weakness; prefer EE/Morris trajectories.",
        "supporting_doi": "10.1016/j.envsoft.2006.10.004",
        "supporting_note": "Campolongo, Cariboni & Saltelli 2007 — revised EE screening.",
        "min_trajectories": 4,
        "outputs": ["mu_star", "sigma", "factor_ranking"],
    },
    "phase_2a_toggles": {
        "method": "fractional-factorial (2-level) on edge toggles / knockouts",
        "purpose": "Estimate declared interactions among binary edge factors.",
        "factors": list(EDGE_KNOCKOUTS),
        "interactions": list(INTERACTIONS_TO_ESTIMATE),
    },
    "phase_2b_continuous": {
        "method": "Definitive Screening Design (three-level)",
        "purpose": "Main effects unbiased by second-order; curvature + interactions.",
        "cite_doi": "10.1080/00224065.2011.11917841",
        "cite_note": "Jones & Nachtsheim 2011 — DSD three-level screening.",
        "example_continuous_factors": [
            "mutation_rate",
            "capsule_adopt_threshold",
            "resource_renewal_rate",
            "heterogeneity_index",
            "population_size",
            "regime_shift_interval",
        ],
    },
    "pom_cite_doi": "10.1098/rstb.2011.0180",
    "pom_cite_note": "Grimm & Railsback 2012 — Pattern-Oriented Modelling multi-pattern gate.",
    "cce_cite_doi": "10.1098/rspb.2018.0712",
    "cce_cite_note": "Mesoudi & Thornton 2018 — four core CCE criteria (all required).",
}

FORBIDDEN_CLAIM_LABELS: frozenset[str] = frozenset(
    {
        "intelligence",
        "agi",
        "collective_intelligence",
        "proved_collective_intelligence",
        "tokyo_type1_passed",
        "avida_replacement",
    }
)


class IlwPreregError(ConfigurationError):
    """Raised when ILW prereg constants or digests are inconsistent."""


class PilotGateError(ConfigurationError):
    """Raised when confirmatory work is attempted before pilot gates pass."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def prereg_document_path() -> Path:
    return _repo_root() / PREREG_RELATIVE_PATH


def assert_seed_policy_disjoint() -> None:
    pilot = set(PILOT_SEEDS)
    conf = set(CONFIRMATORY_HELD_OUT_SEEDS)
    smoke = set(SMOKE_SEEDS)
    if pilot & conf:
        raise IlwPreregError(
            "Pilot and confirmatory held-out seeds must be disjoint; "
            f"overlap={sorted(pilot & conf)}"
        )
    if not smoke.issubset(pilot):
        raise IlwPreregError("SMOKE_SEEDS must be a subset of PILOT_SEEDS.")
    if smoke & conf:
        raise IlwPreregError("SMOKE_SEEDS must not intersect confirmatory held-out seeds.")


def locked_design_dict() -> dict[str, Any]:
    """Frozen design payload used for ``ilw_prereg_design`` digest (no outcomes)."""

    assert_seed_policy_disjoint()
    return {
        "prereg_version": PREREG_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_name": SCIENTIFIC_NAME,
        "forbidden_claim_labels": sorted(FORBIDDEN_CLAIM_LABELS),
        "pilot_seeds": list(PILOT_SEEDS),
        "confirmatory_held_out_seeds": list(CONFIRMATORY_HELD_OUT_SEEDS),
        "smoke_seeds": list(SMOKE_SEEDS),
        "scale_ladder": SCALE_LADDER,
        "stop_rules": list(STOP_RULES),
        "horizon_definitions": HORIZON_DEFINITIONS,
        "pom_acceptance_patterns": [dict(item) for item in POM_ACCEPTANCE_PATTERNS],
        "mesoudi_cce_criteria": [dict(item) for item in MESOUDI_CCE_CRITERIA],
        "interactions_to_estimate": list(INTERACTIONS_TO_ESTIMATE),
        "edge_knockouts": list(EDGE_KNOCKOUTS),
        "sham_yoked_controls": dict(SHAM_YOKED_CONTROLS),
        "doe_plan": DOE_PLAN,
        "prereg_path": PREREG_RELATIVE_PATH,
    }


def ilw_prereg_design_digest() -> str:
    """Canonical digest of the locked design dict (independent of markdown prose)."""

    return canonical_digest(locked_design_dict(), prefix="ilw_prereg_design")


def ilw_prereg_document_digest() -> str:
    """SHA-256 of the frozen preregistration markdown (UTF-8 bytes)."""

    path = prereg_document_path()
    if not path.is_file():
        raise IlwPreregError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return sha256_text_file(path)


@dataclass(frozen=True, slots=True)
class PilotGateStatus:
    """Fail-first gates that must pass before confirmatory seeds may run."""

    replay_ok: bool = False
    conservation_ok: bool = False
    edge_coverage_ok: bool = False
    pom_patterns_recorded: bool = False
    no_claim_promotion: bool = False
    claim_ceiling_ok: bool = False

    @property
    def all_passed(self) -> bool:
        return bool(
            self.replay_ok
            and self.conservation_ok
            and self.edge_coverage_ok
            and self.pom_patterns_recorded
            and self.no_claim_promotion
            and self.claim_ceiling_ok
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_ok": self.replay_ok,
            "conservation_ok": self.conservation_ok,
            "edge_coverage_ok": self.edge_coverage_ok,
            "pom_patterns_recorded": self.pom_patterns_recorded,
            "no_claim_promotion": self.no_claim_promotion,
            "claim_ceiling_ok": self.claim_ceiling_ok,
            "all_passed": self.all_passed,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> PilotGateStatus:
        return cls(
            replay_ok=bool(data.get("replay_ok", False)),
            conservation_ok=bool(data.get("conservation_ok", False)),
            edge_coverage_ok=bool(data.get("edge_coverage_ok", False)),
            pom_patterns_recorded=bool(data.get("pom_patterns_recorded", False)),
            no_claim_promotion=bool(data.get("no_claim_promotion", False)),
            claim_ceiling_ok=bool(data.get("claim_ceiling_ok", False)),
        )


@dataclass
class PilotHarness:
    """Tiny stub: accepts pilot/smoke seeds; refuses confirmatory until gates pass.

    Does **not** run a large campaign. Confirmatory role is blocked fail-first
    unless :attr:`gates`.all_passed is true and the seed is held-out confirmatory.
    """

    gates: PilotGateStatus = field(default_factory=PilotGateStatus)

    def assert_seed_allowed(self, seed: int, *, role: SeedRole) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise PilotGateError("seed must be an integer (bool rejected).")
        assert_seed_policy_disjoint()
        if role == "smoke":
            if seed not in SMOKE_SEEDS:
                raise PilotGateError(
                    f"smoke role seed {seed} not in SMOKE_SEEDS={list(SMOKE_SEEDS)}"
                )
            return
        if role == "pilot":
            if seed in CONFIRMATORY_HELD_OUT_SEEDS:
                raise PilotGateError(
                    f"Refusing confirmatory held-out seed {seed} under pilot role."
                )
            if seed not in PILOT_SEEDS:
                raise PilotGateError(
                    f"pilot role seed {seed} not in PILOT_SEEDS={list(PILOT_SEEDS)}"
                )
            return
        if role == "confirmatory":
            if not self.gates.all_passed:
                raise PilotGateError(
                    "Refusing confirmatory seeds until pilot gates pass "
                    f"(status={self.gates.to_dict()})."
                )
            if seed in PILOT_SEEDS:
                raise PilotGateError(
                    f"Refusing pilot seed {seed} under confirmatory role "
                    "(held-out confirmatory seeds only)."
                )
            if seed not in CONFIRMATORY_HELD_OUT_SEEDS:
                raise PilotGateError(
                    f"confirmatory seed {seed} not in "
                    f"CONFIRMATORY_HELD_OUT_SEEDS={list(CONFIRMATORY_HELD_OUT_SEEDS)}"
                )
            return
        raise PilotGateError(f"unknown seed role: {role!r}")

    def run_stub(
        self,
        seed: int,
        *,
        role: SeedRole = "pilot",
        scale_label: str = "S2",
    ) -> dict[str, Any]:
        """Accept a single stub request; never launches ILW-5 campaign work."""

        self.assert_seed_allowed(seed, role=role)
        if scale_label not in SCALE_LADDER:
            raise PilotGateError(f"unknown scale_label: {scale_label!r}")
        if CLAIM_CEILING != "runtime_observation":
            raise PilotGateError("ClaimGate ceiling must remain runtime_observation.")
        return {
            "status": "stub_accepted",
            "role": role,
            "seed": seed,
            "scale_label": scale_label,
            "claim_ceiling": CLAIM_CEILING,
            "scientific_name": SCIENTIFIC_NAME,
            "prereg_version": PREREG_VERSION,
            "design_digest": ilw_prereg_design_digest(),
            "gates": self.gates.to_dict(),
            "campaign_started": False,
            "ilw5_started": False,
        }


def assert_no_forbidden_claims(labels: Iterable[str]) -> None:
    bad = sorted({str(item) for item in labels} & FORBIDDEN_CLAIM_LABELS)
    if bad:
        raise IlwPreregError(
            "Forbidden ILW claim labels (ClaimGate not loosened): " + ", ".join(bad)
        )


def assert_prereg_claim_ceiling() -> None:
    if CLAIM_CEILING != "runtime_observation":
        raise IlwPreregError(
            f"ILW ClaimGate ceiling must remain 'runtime_observation'; got {CLAIM_CEILING!r}."
        )
    if SCIENTIFIC_NAME != "integrated eco-evolutionary runtime":
        raise IlwPreregError(
            f"Scientific name must remain 'integrated eco-evolutionary runtime'; "
            f"got {SCIENTIFIC_NAME!r}."
        )


def summarize_prereg() -> dict[str, Any]:
    """Compact summary for tests / docs (no outcomes)."""

    assert_prereg_claim_ceiling()
    assert_seed_policy_disjoint()
    return {
        "prereg_version": PREREG_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "claim_ceiling": CLAIM_CEILING,
        "scientific_name": SCIENTIFIC_NAME,
        "design_digest": ilw_prereg_design_digest(),
        "pilot_seed_count": len(PILOT_SEEDS),
        "confirmatory_seed_count": len(CONFIRMATORY_HELD_OUT_SEEDS),
        "pom_pattern_count": len(POM_ACCEPTANCE_PATTERNS),
        "interaction_count": len(INTERACTIONS_TO_ESTIMATE),
        "knockout_count": len(EDGE_KNOCKOUTS),
        "scale_labels": list(SCALE_LADDER),
        "stop_rule_count": len(STOP_RULES),
    }


__all__ = [
    "CLAIM_CEILING",
    "CONFIRMATORY_HELD_OUT_SEEDS",
    "DOE_PLAN",
    "EDGE_KNOCKOUTS",
    "EXPERIMENT_ID",
    "FORBIDDEN_CLAIM_LABELS",
    "HORIZON_DEFINITIONS",
    "INTERACTIONS_TO_ESTIMATE",
    "MESOUDI_CCE_CRITERIA",
    "PILOT_SEEDS",
    "POM_ACCEPTANCE_PATTERNS",
    "PREREG_RELATIVE_PATH",
    "PREREG_VERSION",
    "SCALE_LADDER",
    "SCIENTIFIC_NAME",
    "SHAM_YOKED_CONTROLS",
    "SMOKE_SEEDS",
    "STOP_RULES",
    "IlwPreregError",
    "PilotGateError",
    "PilotGateStatus",
    "PilotHarness",
    "assert_no_forbidden_claims",
    "assert_prereg_claim_ceiling",
    "assert_seed_policy_disjoint",
    "ilw_prereg_design_digest",
    "ilw_prereg_document_digest",
    "locked_design_dict",
    "prereg_document_path",
    "summarize_prereg",
]
