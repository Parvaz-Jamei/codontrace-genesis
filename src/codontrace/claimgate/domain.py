"""Domain profiles for ClaimGate. The engine stays domain-agnostic.

A profile is a named set of blocked aliases and default limitations.
It does not change tick semantics, grant a claim, or certify a device.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.claimgate.schema import (
    ClaimgateArm,
    ClaimgateBundle,
    ClaimgateComparison,
    ClaimgateOutcome,
    ClaimgateReplay,
    ClaimgateSoftware,
    parse_claimgate_bundle,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload


@dataclass(frozen=True, slots=True)
class DomainProfile:
    """Port: how an evidence table is labeled, not how the world runs."""

    name: str
    blocked_claims: frozenset[str]
    limitations: tuple[str, ...]
    extra_defaults: Mapping[str, str]


ALIFE = DomainProfile(
    name="alife",
    blocked_claims=frozenset(
        {
            "intelligence",
            "collective_intelligence",
            "agi",
            "tokyo_type1_passed",
            "avida_replacement",
        }
    ),
    limitations=(
        "Genesis engine ticks are domain-agnostic; this profile only labels claims.",
        "Not an Avida replacement or intelligence proof.",
    ),
    extra_defaults={"engine": "genesis_ticks", "certification": "none"},
)

BIOMEDICAL = DomainProfile(
    name="biomedical",
    blocked_claims=frozenset(
        {
            "medical_device",
            "samd_certified",
            "simd_certified",
            "fda_cleared",
            "ce_marked",
            "clinical_validated",
            "asme_vv40_passed",
            "vvuq_40_1_passed",
            "iec_62304_certified",
            "imdrf_n81_passed",
            "in_silico_trial_validated",
            "digital_twin_certified",
            "patient_safe",
        }
    ),
    limitations=(
        "Not a medical device, SaMD, SiMD, IVD, or diagnostic tool.",
        "Not an ASME V&V 40-2018 / VVUQ 40.1 implementation or certification.",
        "Not IEC 62304 classification, IMDRF N12/N81 categorization, or FDA clearance.",
        "Question of interest, context of use, and risk labels are user-declared.",
        "FDA 2023 CM&S guidance covers physics-based or mechanistic models, not standalone ML.",
        "A ClaimGate grade is a claim ceiling, not clinical validity.",
    ),
    extra_defaults={
        "asme_vv40": "complement_only",
        "fda_2023": "declared_labels_only",
        "imdrf_n81": "characterization_analog_only",
        "iec_62304": "label_only",
        "certification": "none",
        "engine": "unused_for_table_wrap",
    },
)

HARDWARE = DomainProfile(
    name="hardware",
    blocked_claims=frozenset({"physical_robot_platform", "esp32_validated"}),
    limitations=(
        "Hardware bridge is an engineering stub unless a transport actually ran.",
        "A score table is not a robot experiment.",
    ),
    extra_defaults={"engine": "optional_bridge", "certification": "none"},
)

HOST_PARASITE = DomainProfile(
    name="host_parasite",
    blocked_claims=frozenset(
        {
            "vaccine_efficacy_proved",
            "antiviral_therapy_validated",
            "clinical_pathogen_model",
            "epidemic_forecast_certified",
            "phage_therapy_cleared",
            "virulence_optimized_for_humans",
            "biosafety_level_certified",
            # CRISPR identity / therapy cosplay stays fail-closed even when
            # external CRISPR–phage papers are cited as comparators only.
            "crispr_identity_proved",
            "crispr_therapy_validated",
            # Dynamics labels may be declared later; "proved" stays blocked.
            "red_queen_proved",
            "major_transition_proved",
            # Reuse intelligence / replacement blocks so this port cannot
            # silently inherit ALife overclaims either.
            "intelligence",
            "intelligence_proved",
            "collective_intelligence",
            "agi",
            "tokyo_type1_passed",
            "avida_replacement",
            # Wave-5/6 matrix refuse-list must be fail-closed on claimed=, not
            # documentation-only. OEE/MODES are comparators (Dolson/Channon);
            # complexity/gene identity stay campaign flags, never claim ceilings.
            "modes_passed_proved",
            "modes_passed",
            "oee_type1_proved",
            "oee_modes_passed",
            "complexity_emergence_proved",
            "gene_identity_proved",
            # Cornish intervention_supported is a campaign honesty flag, never
            # a public claimed= ceiling string.
            "intervention_supported",
        }
    ),
    limitations=(
        "DomainProfile port for digital host–parasite / microbe–virus claim labeling; not a second engine.",
        "Not a clinical pathogen model, vaccine, antiviral, phage-therapy, or epidemic-forecast certificate.",
        "Not a biosafety-level certification or virulence-optimization tool for humans.",
        "Not a CRISPR-identity or CRISPR-therapy proof; external CRISPR–phage papers are comparators only.",
        "Not a Red Queen or major-transition proof; optional ARD/FSD labels stay undeclared until evidenced.",
        "Not an OEE Type-1 or MODES “passed” proof; Dolson/Channon rows stay comparators only.",
        "Not a complexity-emergence or gene-identity proof; those flags stay False on digests.",
        "Infection / transmission physics are not implemented in the engine; optional HostParasiteEnv is outside core.",
        "A ClaimGate grade is a claim ceiling for declared digital coevolution evidence, not wet-lab validity.",
        "FDA 2023 CM&S / ASME V&V 40 language may be reused as COU risk labels only; not device clearance.",
    ),
    extra_defaults={
        "asme_vv40": "complement_only",
        "fda_2023": "declared_labels_only",
        "certification": "none",
        "engine": "unused_for_table_wrap",
        "infection_physics": "not_implemented",
        "clinical_scope": "blocked",
    },
)

PROFILES: dict[str, DomainProfile] = {
    ALIFE.name: ALIFE,
    BIOMEDICAL.name: BIOMEDICAL,
    HARDWARE.name: HARDWARE,
    HOST_PARASITE.name: HOST_PARASITE,
}

# FDA 2023 CM&S guidance Table 2. Declared labels only; not a submission.
FDA_2023_EVIDENCE_CATEGORIES: dict[int, str] = {
    1: "code_verification",
    2: "model_calibration",
    3: "bench_test_validation",
    4: "in_vivo_validation",
    5: "population_based_validation",
    6: "emergent_model_behaviour",
    7: "model_plausibility",
    8: "calculation_verification_uq_cou",
}

DEVICE_SOFTWARE_KINDS = frozenset({"none", "analog_table", "simd_declared", "samd_declared"})
IEC_62304_CLASSES = frozenset({"undeclared", "A", "B", "C"})
IMDRF_N12_CATEGORIES = frozenset({"undeclared", "I", "II", "III", "IV"})


def _grade_int(name: str, value: int) -> int:
    if value not in (1, 2, 3):
        raise ConfigurationError(f"{name} must be 1, 2, or 3 (user-declared).")
    return value


def _finite_series(name: str, values: Sequence[float]) -> tuple[float, ...]:
    if len(values) < 1:
        raise ConfigurationError(f"{name} must contain at least one finite score.")
    out: list[float] = []
    for item in values:
        number = float(item)
        if number != number or number in (float("inf"), float("-inf")):
            raise ConfigurationError(f"{name} must be finite.")
        out.append(number)
    return tuple(out)


def bundle_from_declared_scores(
    *,
    profile: DomainProfile | str,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    metric: str = "declared_score",
    software_name: str = "external-score-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
    device_software_kind: str = "analog_table",
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
) -> ClaimgateBundle:
    """Wrap two score series plus a declared COU. Engine is not invoked."""

    resolved = PROFILES[profile] if isinstance(profile, str) else profile
    qoi = question_of_interest.strip()
    cou = context_of_use.strip()
    if not qoi or not cou:
        raise ConfigurationError("question_of_interest and context_of_use are required.")
    claim = claimed.strip().lower()
    if claim in resolved.blocked_claims:
        raise ConfigurationError(
            f"{claimed!r} is blocked on domain profile {resolved.name!r}."
        )
    influence = _grade_int("model_influence", model_influence)
    consequence = _grade_int("decision_consequence", decision_consequence)
    treatment = _finite_series("treatment_scores", treatment_scores)
    control = _finite_series("control_scores", control_scores)
    kind = device_software_kind.strip().lower()
    if kind not in DEVICE_SOFTWARE_KINDS:
        raise ConfigurationError(
            "device_software_kind must be none, analog_table, simd_declared, or samd_declared."
        )
    iec = iec_62304_class.strip()
    if iec not in IEC_62304_CLASSES:
        raise ConfigurationError("iec_62304_class must be undeclared, A, B, or C.")
    imdrf = imdrf_n12_category.strip()
    if imdrf not in IMDRF_N12_CATEGORIES:
        raise ConfigurationError("imdrf_n12_category must be undeclared or I–IV.")
    evidence = tuple(int(item) for item in fda_2023_evidence)
    if any(item not in FDA_2023_EVIDENCE_CATEGORIES for item in evidence):
        raise ConfigurationError("fda_2023_evidence items must be integers 1–8.")
    extra = {
        "domain": resolved.name,
        "question_of_interest": qoi,
        "context_of_use": cou,
        "model_influence": influence,
        "decision_consequence": consequence,
        "model_risk": max(influence, consequence),
        "requested_claim": claim,
        "device_software_kind": kind,
        "iec_62304_class": iec,
        "imdrf_n12_category": imdrf,
        "fda_2023_evidence": list(evidence),
        "fda_2023_evidence_names": [
            FDA_2023_EVIDENCE_CATEGORIES[item] for item in evidence
        ],
        "physics_based": bool(physics_based),
        "fda_2023_scope": (
            "physics_mechanistic" if physics_based else "out_of_scope_standalone_ml"
        ),
        **dict(resolved.extra_defaults),
    }
    limitations = resolved.limitations + (f"Requested claim stays {claim!r}.",)
    if kind in {"simd_declared", "samd_declared"}:
        limitations += (
            "Device-software kind is a user-declared analog, not a regulatory class.",
        )
    if evidence and not physics_based:
        limitations += (
            "Declared FDA 2023 evidence categories do not bring standalone ML into guidance scope.",
        )
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(
            name=software_name,
            version=software_version,
            commit="",
        ),
        seeds=tuple(range(1, min(len(treatment), len(control)) + 1)),
        config_digest=canonical_digest(canonical_payload(extra)),
        arms=(
            ClaimgateArm(name="declared_model", role="treatment", n=len(treatment)),
            ClaimgateArm(name="declared_baseline", role="negative_control", n=len(control)),
        ),
        outcomes=(
            ClaimgateOutcome(
                metric=metric,
                values_by_arm={
                    "declared_model": treatment,
                    "declared_baseline": control,
                },
            ),
        ),
        comparisons=(
            ClaimgateComparison(
                a="declared_model",
                b="declared_baseline",
                effect_size=None,
                ci_low=None,
                ci_high=None,
                p=None,
                test="",
                correction="",
            ),
        ),
        replay=ClaimgateReplay(verified=False, digests=()),
        artifacts=(),
        limitations=limitations,
        extra=extra,
    )
    return parse_claimgate_bundle(bundle)
