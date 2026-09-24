"""Phase 24 — Wave 6 journal packet integration smoke (Phases 18–23).

One prereg-bound bundle attaches Wave-5 digests in order and audits that the
ClaimGate ladder does not rise while representative blocked claims stay
fail-closed. Soft-complete inventory hygiene only — no new biology claims,
no infection physics in engine.py, no BAIC pin edits.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed,
    attach_ard_fsd_transition,
    attach_journal_attach_registry,
    attach_multi_seed_contingency,
    attach_resource_dynamics_factorial,
    attach_scanlan_mutator_campaign,
    attach_sequential_cornish_campaign,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_ard_fsd_transition import (
    run_ard_fsd_transition_campaign,
)
from codontrace.genesis.host_parasite_attach_registry import (
    BLOCKED_CLAIM_MATRIX,
    WAVE5_ATTACH_KEYS,
    assert_wave5_attach_surface_wired,
    build_journal_attach_registry_packet,
)
from codontrace.genesis.host_parasite_contingency import (
    run_multi_seed_contingency_campaign,
)
from codontrace.genesis.host_parasite_cornish_sequential import (
    run_sequential_cornish_campaign,
)
from codontrace.genesis.host_parasite_mutator import run_scanlan_mutator_campaign
from codontrace.genesis.host_parasite_resource_dynamics import (
    run_resource_dynamics_factorial,
)

SCHEMA = "host_parasite_wave6_journal_smoke_v1"
ATTACH_ORDER: tuple[str, ...] = (
    "journal_attach_registry",
    "ard_fsd_transition",
    "resource_dynamics_factorial",
    "multi_seed_contingency",
    "cornish_sequential_campaign",
    "scanlan_mutator_campaign",
)
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_SPOT_CHECK_BLOCKED = (
    "red_queen_proved",
    "phage_therapy_cleared",
    "crispr_identity_proved",
    "clinical_pathogen_model",
)


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


@dataclass(frozen=True, slots=True)
class Wave6JournalSmokeResult:
    """One-bundle Wave-5 attach smoke + ladder / blocked-claim audit."""

    schema: str
    attach_order: tuple[str, ...]
    attached_keys: tuple[str, ...]
    campaign_digests: tuple[tuple[str, str], ...]
    ladder_before: str
    ladder_after: str
    ladder_unchanged: bool
    blocked_spot_check: tuple[tuple[str, bool], ...]
    claim_ceiling: str
    raises_claim_ladder: bool
    red_queen_proved: bool
    complexity_emergence_proved: bool
    intervention_supported: bool
    gene_identity_proved: bool
    soft_complete_wave5_surface: bool
    smoke_digest: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "attach_order": list(self.attach_order),
            "attached_keys": list(self.attached_keys),
            "campaign_digests": {k: v for k, v in self.campaign_digests},
            "ladder_before": self.ladder_before,
            "ladder_after": self.ladder_after,
            "ladder_unchanged": self.ladder_unchanged,
            "blocked_spot_check": {
                claim: blocked for claim, blocked in self.blocked_spot_check
            },
            "claim_ceiling": self.claim_ceiling,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "complexity_emergence_proved": False,
            "intervention_supported": False,
            "gene_identity_proved": False,
            "soft_complete_wave5_surface": self.soft_complete_wave5_surface,
            "wave": 6,
            "phase": 24,
            "note": (
                "Integration smoke: Phases 18–23 attaches on one prereg-bound "
                "bundle. Fail-closed claims stay blocked; ladder must not rise."
            ),
            "domain_profile": "host_parasite",
        }
        body["smoke_digest"] = self.smoke_digest or _digest_body(
            {
                k: body[k]
                for k in body
                if k not in {"smoke_digest", "digest", "campaign_digest"}
            }
        )
        body["campaign_digest"] = body["smoke_digest"]
        body["digest"] = body["smoke_digest"]
        return body


def _spot_check_blocked() -> tuple[tuple[str, bool], ...]:
    out: list[tuple[str, bool]] = []
    for claim in _SPOT_CHECK_BLOCKED:
        blocked = False
        try:
            assert_claim_allowed(claim)
        except ConfigurationError:
            blocked = True
        if not blocked:
            raise ConfigurationError(f"{claim} must stay blocked on host_parasite.")
        out.append((claim, True))
    missing = [c for c, _ in out if c not in BLOCKED_CLAIM_MATRIX]
    if missing:
        raise ConfigurationError(f"blocked matrix missing spot-check claims: {missing}")
    return tuple(out)


def run_wave6_journal_smoke(
    *,
    seeds: Sequence[int] = (101, 202, 303),
    request_claim_ceiling: str = "runtime_observation",
) -> Wave6JournalSmokeResult:
    """Attach Phases 18–23 on one bundle; refuse ladder rise and open claims."""

    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )
    seed_tuple = tuple(int(s) for s in seeds)
    if len(seed_tuple) < 3:
        raise ConfigurationError("wave6 journal smoke requires at least 3 seeds.")

    assert_wave5_attach_surface_wired()
    missing = [k for k in ATTACH_ORDER if k not in WAVE5_ATTACH_KEYS]
    if missing:
        raise ConfigurationError(f"ATTACH_ORDER drifts from WAVE5_ATTACH_KEYS: {missing}")

    blocked_spot = _spot_check_blocked()

    prereg = host_parasite_preregistration(
        question_of_interest=(
            "Do Phases 18–23 attach digests stay ClaimGate-honest on one bundle?"
        ),
        context_of_use=(
            "Wave 6 Phase 24 journal smoke; soft-complete inventory hygiene only."
        ),
        arms=ATTACH_ORDER,
        success_metrics=("smoke_digest", "ladder_unchanged", "blocked_spot_check"),
        forbidden_claims=(
            "red_queen_proved",
            "phage_therapy_cleared",
            "crispr_identity_proved",
            "major_transition_proved",
        ),
    )
    prereg_digest = str(prereg.to_dict()["digest"])

    bundle = bundle_from_host_parasite_cou(
        question_of_interest=(
            "Do Phases 18–23 attach digests stay ClaimGate-honest on one bundle?"
        ),
        context_of_use=(
            "Wave 6 Phase 24 journal smoke; soft-complete inventory hygiene only."
        ),
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.15,),
        control_scores=(1.0,),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    ladder_before = str(audit_bundle(ready).achieved_level)

    packet = build_journal_attach_registry_packet(request_claim_ceiling=ceiling)
    ready = attach_journal_attach_registry(ready, packet)

    ard = run_ard_fsd_transition_campaign(
        seeds=seed_tuple[:2],
        n_slices=4,
        request_claim_ceiling=ceiling,
    )
    ready = attach_ard_fsd_transition(ready, ard)

    resource = run_resource_dynamics_factorial(
        seeds=seed_tuple[:2],
        request_claim_ceiling=ceiling,
    )
    ready = attach_resource_dynamics_factorial(ready, resource)

    contingency = run_multi_seed_contingency_campaign(
        seeds=seed_tuple,
        request_claim_ceiling=ceiling,
    )
    ready = attach_multi_seed_contingency(ready, contingency)

    cornish = run_sequential_cornish_campaign(
        seeds=seed_tuple[:2],
        request_claim_ceiling=ceiling,
        preregistration_digest=prereg_digest,
    )
    ready = attach_sequential_cornish_campaign(ready, cornish)

    mutator = run_scanlan_mutator_campaign(
        seeds=seed_tuple[:2],
        steps=2,
        request_claim_ceiling=ceiling,
    )
    ready = attach_scanlan_mutator_campaign(ready, mutator)

    ladder_after = str(audit_bundle(ready).achieved_level)
    if ladder_after != ladder_before:
        raise ConfigurationError(
            f"ClaimGate ladder rose during Wave-6 smoke: {ladder_before} -> {ladder_after}"
        )

    extra = dict(ready.extra or {})
    attached = tuple(k for k in ATTACH_ORDER if k in extra)
    if attached != ATTACH_ORDER:
        raise ConfigurationError(
            f"smoke missing attach keys; got {attached}, want {ATTACH_ORDER}"
        )

    digests: list[tuple[str, str]] = []
    for key in ATTACH_ORDER:
        record = extra[key]
        if not isinstance(record, Mapping):
            raise ConfigurationError(f"attach record {key} must be a mapping.")
        digest = (
            record.get("registry_digest")
            or record.get("campaign_digest")
            or record.get("factorial_digest")
            or record.get("digest")
        )
        if not isinstance(digest, str) or not digest:
            raise ConfigurationError(f"attach record {key} missing digest.")
        digests.append((key, digest))

    if extra["multi_seed_contingency"].get("complexity_emergence_proved"):
        raise ConfigurationError("complexity_emergence_proved must stay False.")
    if extra["cornish_sequential_campaign"].get("intervention_supported"):
        raise ConfigurationError("intervention_supported must stay False.")
    if extra["scanlan_mutator_campaign"].get("gene_identity_proved"):
        raise ConfigurationError("gene_identity_proved must stay False.")
    if any(
        isinstance(extra.get(k), Mapping) and extra[k].get("red_queen_proved")
        for k in ATTACH_ORDER
    ):
        raise ConfigurationError("red_queen_proved must stay False on all attaches.")

    preview = {
        "schema": SCHEMA,
        "attach_order": list(ATTACH_ORDER),
        "attached_keys": list(attached),
        "campaign_digests": {k: v for k, v in digests},
        "ladder_before": ladder_before,
        "ladder_after": ladder_after,
        "ladder_unchanged": True,
        "blocked_spot_check": {c: blocked for c, blocked in blocked_spot},
        "claim_ceiling": ceiling,
        "raises_claim_ladder": False,
        "red_queen_proved": False,
        "complexity_emergence_proved": False,
        "intervention_supported": False,
        "gene_identity_proved": False,
        "soft_complete_wave5_surface": True,
        "wave": 6,
        "phase": 24,
        "domain_profile": "host_parasite",
        "preregistration_digest": prereg_digest,
    }
    smoke_digest = _digest_body(preview)
    return Wave6JournalSmokeResult(
        schema=SCHEMA,
        attach_order=ATTACH_ORDER,
        attached_keys=attached,
        campaign_digests=tuple(digests),
        ladder_before=ladder_before,
        ladder_after=ladder_after,
        ladder_unchanged=True,
        blocked_spot_check=blocked_spot,
        claim_ceiling=ceiling,
        raises_claim_ladder=False,
        red_queen_proved=False,
        complexity_emergence_proved=False,
        intervention_supported=False,
        gene_identity_proved=False,
        soft_complete_wave5_surface=True,
        smoke_digest=smoke_digest,
    )


__all__ = [
    "ATTACH_ORDER",
    "SCHEMA",
    "Wave6JournalSmokeResult",
    "run_wave6_journal_smoke",
]
