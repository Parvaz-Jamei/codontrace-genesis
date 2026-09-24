"""Phase 18 — soft-complete journal ClaimGate attach-registry packet.

Inventory of Phases 1–17 attach keys and the blocked-claim matrix reviewers
expect on a journal-facing host_parasite bundle. Hygiene only: no new biology
claims, no ladder rise, no infection physics in engine.py.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

SCHEMA = "host_parasite_journal_attach_registry_v1"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})

# Attach extra-keys shipped through Phase 17 (Wave 1–4). Phase numbers are
# documentation anchors; some phases share a key or attach via honesty packs.
REQUIRED_ATTACH_KEYS: dict[str, str] = {
    "declared_intervention_menu": "Phase 1 declared intervention menu",
    "host_parasite_preregistration": "Phase 6+ preregistration digest gate",
    "intervention_falsification": "Phase 3 honesty / intervention falsification",
    "multilevel_transition_worksheet": "Phase 3 multilevel caution worksheet",
    "dynamics_labels": "Phase 3 / 5 dynamics label declarations",
    "host_parasite_campaign": "Phase 4 multi-seed campaign digests",
    "coevolution_diagnostics": "Phase 5 ARD/FSD-like range diagnostics",
    "zaman_three_arm_campaign": "Phase 7 freeze/replay/reciprocal",
    "interaction_continuum": "Phase 8 interaction continuum",
    "vt_spatial_factorial": "Phase 8 VT × spatial factorial",
    "evolvability_falsification": "Phase 9 evolvability falsification (S5)",
    "cornish_intervention_campaign": "Phase 9 Cornish observational vs interventional",
    "genome_zaman_campaign": "Phase 10 genome-aware Zaman dual digests",
    "genome_diversity_campaign": "Phase 11 codon-entropy / Hamming dual-null",
    "hgt_compartment_campaign": "Phase 12 HGT-analogue + compartment pack",
    "task_gene_map": "Phase 13 declared task–gene map",
    "transmission_mode_contrast": "Phase 14 transmission-mode contrast",
    "genome_vt_spatial_continuum_factorial": "Phase 15 genome × VT × spatial × continuum",
    "virulence_resistance_quality": "Phase 16 virulence/resistance quality (S7)",
    "price_causality_caution": "Phase 17 Price≠causality refusal (S8)",
}

# Follow-on Wave 5 attach keys (Phases 18–23). Soft-complete Phase 18 packet
# still inventories 1–17; this map documents the Wave 5 surface without
# rewriting the Phase 18 baseline contract.
WAVE5_ATTACH_KEYS: dict[str, str] = {
    "journal_attach_registry": "Phase 18 soft-complete journal attach-registry",
    "ard_fsd_transition": "Phase 19 ARD→FSD transition + cost-of-generalism",
    "resource_dynamics_factorial": "Phase 20 resource × dynamics factorial",
    "multi_seed_contingency": "Phase 21 multi-seed contingency (S1)",
    "cornish_sequential_campaign": "Phase 22 sequential Cornish multi-intervention",
    "scanlan_mutator_campaign": "Phase 23 Scanlan mutator dual-null",
}

# Claims that must remain blocked or explicitly False on journal attach.
BLOCKED_CLAIM_MATRIX: dict[str, str] = {
    "vaccine_efficacy_proved": "profile blocked_claims",
    "antiviral_therapy_validated": "profile blocked_claims",
    "clinical_pathogen_model": "profile blocked_claims",
    "epidemic_forecast_certified": "profile blocked_claims",
    "phage_therapy_cleared": "profile blocked_claims",
    "virulence_optimized_for_humans": "profile blocked_claims",
    "biosafety_level_certified": "profile blocked_claims",
    "crispr_identity_proved": "profile blocked_claims",
    "crispr_therapy_validated": "profile blocked_claims",
    "red_queen_proved": "profile blocked_claims + always False on digests",
    "major_transition_proved": "profile blocked_claims + always False on digests",
    "intelligence": "profile blocked_claims",
    "collective_intelligence": "profile blocked_claims",
    "agi": "profile blocked_claims",
    "tokyo_type1_passed": "profile blocked_claims",
    "avida_replacement": "profile blocked_claims",
    "gene_identity_proved": "campaign flag always False (Phase 13)",
    "complexity_emergence_proved": "campaign flag always False (S1 humility)",
    "oee_type1_proved": "comparator only; never attach as proved",
    "modes_passed_proved": "comparator only; never attach as proved",
}


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


@dataclass(frozen=True, slots=True)
class JournalAttachRegistryPacket:
    """Soft-complete attach-registry inventory for journal reviewers."""

    schema: str
    required_attach_keys: tuple[str, ...]
    blocked_claim_matrix: tuple[tuple[str, str], ...]
    phases_covered: tuple[int, ...]
    claim_ceiling: str
    soft_complete: bool
    raises_claim_ladder: bool
    red_queen_proved: bool
    major_transition_proved: bool
    registry_digest: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "required_attach_keys": list(self.required_attach_keys),
            "blocked_claim_matrix": {
                claim: note for claim, note in self.blocked_claim_matrix
            },
            "phases_covered": list(self.phases_covered),
            "claim_ceiling": self.claim_ceiling,
            "soft_complete": self.soft_complete,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "major_transition_proved": False,
            "wave": 5,
            "phase": 18,
            "note": (
                "Attach-registry hygiene packet. Documents Phases 1–17 attach "
                "surface; does not raise the claim ladder or prove dynamics."
            ),
            "domain_profile": "host_parasite",
        }
        body["registry_digest"] = self.registry_digest or _digest_body(
            {k: body[k] for k in body if k not in {"registry_digest", "digest", "campaign_digest"}}
        )
        body["campaign_digest"] = body["registry_digest"]
        body["digest"] = body["registry_digest"]
        return body


def build_journal_attach_registry_packet(
    *,
    request_claim_ceiling: str = "runtime_observation",
    extra_required_keys: Sequence[str] = (),
) -> JournalAttachRegistryPacket:
    """Build the soft-complete registry packet (hygiene, not innovation lead)."""

    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )
    keys = list(REQUIRED_ATTACH_KEYS.keys())
    for raw in extra_required_keys:
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError("extra_required_keys entries must be non-empty strings.")
        key = raw.strip()
        if key not in keys:
            keys.append(key)
    if len(keys) < len(REQUIRED_ATTACH_KEYS):
        raise ConfigurationError("registry missing required Phase 1–17 attach keys.")
    matrix = tuple(sorted(BLOCKED_CLAIM_MATRIX.items()))
    phases = tuple(range(1, 18))
    preview = {
        "schema": SCHEMA,
        "required_attach_keys": keys,
        "blocked_claim_matrix": {c: n for c, n in matrix},
        "phases_covered": list(phases),
        "claim_ceiling": ceiling,
        "soft_complete": True,
        "raises_claim_ladder": False,
        "red_queen_proved": False,
        "major_transition_proved": False,
        "wave": 5,
        "phase": 18,
        "domain_profile": "host_parasite",
    }
    digest = _digest_body(preview)
    return JournalAttachRegistryPacket(
        schema=SCHEMA,
        required_attach_keys=tuple(keys),
        blocked_claim_matrix=matrix,
        phases_covered=phases,
        claim_ceiling=ceiling,
        soft_complete=True,
        raises_claim_ladder=False,
        red_queen_proved=False,
        major_transition_proved=False,
        registry_digest=digest,
    )


def assert_registry_covers_phases_1_to_17(packet: JournalAttachRegistryPacket) -> None:
    """Fail closed if the soft-complete inventory drifts below Phases 1–17."""

    if not isinstance(packet, JournalAttachRegistryPacket):
        raise ConfigurationError("packet must be a JournalAttachRegistryPacket.")
    missing = [k for k in REQUIRED_ATTACH_KEYS if k not in packet.required_attach_keys]
    if missing:
        raise ConfigurationError(f"registry missing attach keys: {missing}")
    if packet.phases_covered != tuple(range(1, 18)):
        raise ConfigurationError("phases_covered must be 1..17 inclusive.")
    if packet.raises_claim_ladder or packet.red_queen_proved or packet.major_transition_proved:
        raise ConfigurationError("soft-complete packet must not raise ladder or prove dynamics.")
    if not packet.soft_complete:
        raise ConfigurationError("soft_complete must be True for Phase 18 packet.")


# Wave-5 attach extra-keys → ClaimGate adapter callables (Phases 18–23).
# Hygiene only: documents the shipped surface without rewriting the Phase-18
# Phases 1–17 soft-complete baseline contract.

# Wave-6 attach keys (Phases 24–26). Hygiene / earned bridge only; does not
# rewrite Phase-18 soft-complete Phases 1–17 baseline or Wave-5 contracts.
WAVE6_ATTACH_KEYS: dict[str, str] = {
    "wave6_journal_smoke": "Phase 24 Wave-5 one-bundle attach smoke + ladder audit",
    "he_hp_locked_digest_refresh": "Phase 25 HE_HP locked-digest refresh note",
    "entropy_contingency_bridge": "Phase 26 Phase 11×21 entropy×contingency bridge",
}

WAVE6_ATTACH_CALLABLES: dict[str, str] = {
    "wave6_journal_smoke": "attach_wave6_journal_smoke",
    "he_hp_locked_digest_refresh": "attach_he_hp_locked_digest_refresh",
    "entropy_contingency_bridge": "attach_entropy_contingency_bridge",
}

WAVE5_ATTACH_CALLABLES: dict[str, str] = {
    "journal_attach_registry": "attach_journal_attach_registry",
    "ard_fsd_transition": "attach_ard_fsd_transition",
    "resource_dynamics_factorial": "attach_resource_dynamics_factorial",
    "multi_seed_contingency": "attach_multi_seed_contingency",
    "cornish_sequential_campaign": "attach_sequential_cornish_campaign",
    "scanlan_mutator_campaign": "attach_scanlan_mutator_campaign",
}


def assert_wave5_attach_surface_wired() -> None:
    """Fail closed if Wave-5 attach keys drift from adapter callables.

    Does not raise the claim ladder or rewrite Phase-18 soft_complete=True for
    Phases 1–17. Completeness auditors use this to confirm Phases 18–23 remain
    attachable on the single host_parasite DomainProfile.
    """

    missing_keys = [k for k in WAVE5_ATTACH_KEYS if k not in WAVE5_ATTACH_CALLABLES]
    if missing_keys:
        raise ConfigurationError(
            f"WAVE5_ATTACH_KEYS missing callable map entries: {missing_keys}"
        )
    orphan = [k for k in WAVE5_ATTACH_CALLABLES if k not in WAVE5_ATTACH_KEYS]
    if orphan:
        raise ConfigurationError(
            f"WAVE5_ATTACH_CALLABLES has orphan keys not in WAVE5_ATTACH_KEYS: {orphan}"
        )
    # Import locally to avoid circular imports at module load.
    from codontrace.claimgate.adapters import host_parasite as hp_adapter

    missing_fns: list[str] = []
    for key, fn_name in WAVE5_ATTACH_CALLABLES.items():
        if not callable(getattr(hp_adapter, fn_name, None)):
            missing_fns.append(f"{key}->{fn_name}")
    if missing_fns:
        raise ConfigurationError(
            f"Wave-5 attach callables missing on host_parasite adapter: {missing_fns}"
        )



def assert_wave6_attach_surface_wired() -> None:
    """Fail closed if Wave-6 attach keys drift from adapter callables."""

    missing_keys = [k for k in WAVE6_ATTACH_KEYS if k not in WAVE6_ATTACH_CALLABLES]
    if missing_keys:
        raise ConfigurationError(
            f"WAVE6_ATTACH_KEYS missing callable map entries: {missing_keys}"
        )
    orphan = [k for k in WAVE6_ATTACH_CALLABLES if k not in WAVE6_ATTACH_KEYS]
    if orphan:
        raise ConfigurationError(
            f"WAVE6_ATTACH_CALLABLES has orphan keys not in WAVE6_ATTACH_KEYS: {orphan}"
        )
    from codontrace.claimgate.adapters import host_parasite as hp_adapter

    missing_fns: list[str] = []
    for key, fn_name in WAVE6_ATTACH_CALLABLES.items():
        if not callable(getattr(hp_adapter, fn_name, None)):
            missing_fns.append(f"{key}->{fn_name}")
    if missing_fns:
        raise ConfigurationError(
            f"Wave-6 attach callables missing on host_parasite adapter: {missing_fns}"
        )



__all__ = [
    "BLOCKED_CLAIM_MATRIX",
    "REQUIRED_ATTACH_KEYS",
    "WAVE5_ATTACH_CALLABLES",
    "WAVE5_ATTACH_KEYS",
    "WAVE6_ATTACH_CALLABLES",
    "WAVE6_ATTACH_KEYS",
    "SCHEMA",
    "JournalAttachRegistryPacket",
    "assert_registry_covers_phases_1_to_17",
    "assert_wave5_attach_surface_wired",
    "assert_wave6_attach_surface_wired",
    "build_journal_attach_registry_packet",
]
