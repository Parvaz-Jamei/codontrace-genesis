"""De-toy D7: measurement-honesty pack + resource→phenotype-target dual-null.

(a) Channon / MODES comparator: measurement-only ALLOWED vocabulary;
    tokyo_type1_passed and modes_passed* stay False forever on this port.
(b) resource_productivity modulates abstract phenotype target harshness
    (Lopez Pascua honesty map); dual-null kills the slope.

Literature:
- Channon doi:10.1162/artl_a_00430
- Dolson MODES doi:10.1162/artl_a_00280
- Lopez Pascua doi:10.1111/j.1420-9101.2008.01501.x
- ELE doi:10.1111/ele.12337

Port-only; ClaimGate refuse list fail-closed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_abstract_phenotype import (
    decode_abstract_phenotype,
    default_target_phenotype,
)
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_measurement_resource_target_v1"
DOMAIN_PROFILE = "host_parasite"
DEFAULT_SEEDS: tuple[int, ...] = (7, 14, 21, 28, 35)
DEFAULT_SEPARATION_THRESHOLD = 0.015
RESOURCE_LEVELS = ("low", "high")
_RESOURCE_VALUES = {"low": 0.4, "high": 2.0}

# Measurement-only ALLOWED (observation / comparator labels — never "passed").
MEASUREMENT_ALLOWED = frozenset(
    {
        "runtime_observation",
        "candidate_evidence",
        "channon_tokyo_type1_procedure_cited",
        "modes_toolbox_comparator_cited",
        "pineau_seed_table_disclosed",
        "measurement_only",
    }
)
MEASUREMENT_REFUSED = frozenset(
    {
        "tokyo_type1_passed",
        "modes_passed",
        "modes_passed_change",
        "modes_passed_novelty",
        "modes_passed_complexity",
        "modes_passed_ecology",
        "oee_proved",
        "intelligence_proved",
        "collective_intelligence_proved",
        "clinical_pathogen_model",
        "phage_therapy_cleared",
        "red_queen_proved",
    }
)


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _genome_for(seed: int) -> SemanticGenome:
    return SemanticGenome.random(length=12, seed=int(seed) * 4099 + 13)


def harshness_from_resource(productivity: float) -> float:
    """Map resource productivity → target harshness in (0, 1].

    Higher resources → softer target (lower harshness) — Lopez Pascua honesty
    map as a *digital* phenotype-target knob, not wet chemostat physics.
    """

    p = max(0.05, float(productivity))
    # harshness = 1 / (1 + p) scaled into a useful band
    return round(max(0.15, min(1.0, 1.15 / (1.0 + p))), 10)


def target_under_resource(
    *,
    n_bins: int = 16,
    productivity: float,
    seed: int = 20260924,
    null_kind: str = "none",
) -> tuple[float, ...]:
    """Build phenotype target; harshness scales deviation from a flat midline.

    structure_null: ignore productivity (fixed mid harshness).
    content_null: replace with a productivity-independent scrambled flat target
    so the resource→harshness path cannot create a low-vs-high error slope.
    """

    base = list(default_target_phenotype(n_bins=n_bins, seed=seed))
    mid = 0.5
    if null_kind == "content_null":
        digest = hashlib.sha256(f"content_null_flat|{seed}|{n_bins}".encode()).digest()
        # Flat-ish scrambled target: no productivity dependence.
        scaled = [
            round(0.45 + 0.10 * (digest[i % len(digest)] / 255.0), 10)
            for i in range(n_bins)
        ]
        return tuple(scaled)
    if null_kind == "structure_null":
        h = 0.55  # productivity path disabled
    else:
        h = harshness_from_resource(productivity)
    # Pull toward 0.5 by (1-h); pull toward extreme base by h.
    scaled = [round(mid + (b - mid) * h, 10) for b in base]
    return tuple(scaled)


def error_under_resource(
    genome: SemanticGenome,
    *,
    productivity: float,
    null_kind: str = "none",
    n_bins: int = 16,
) -> dict[str, object]:
    tgt = target_under_resource(
        n_bins=n_bins, productivity=productivity, null_kind=null_kind
    )
    ph = decode_abstract_phenotype(genome, n_bins=n_bins, target=tgt)
    return {
        "productivity": float(productivity),
        "null_kind": null_kind,
        "harshness": harshness_from_resource(productivity)
        if null_kind != "structure_null"
        else 0.55,
        "metabolic_error": float(ph["metabolic_error"]),
        "phenotype_digest": ph["phenotype_digest"],
        "aevol_identity": False,
        "wet_metabolism_claim": False,
    }


def _resource_slope_trial(seed: int) -> dict[str, object]:
    g = _genome_for(seed)
    low = error_under_resource(g, productivity=_RESOURCE_VALUES["low"], null_kind="none")
    high = error_under_resource(g, productivity=_RESOURCE_VALUES["high"], null_kind="none")
    # Expected: low resource (harsher) → higher error than high resource.
    intact_delta = round(float(low["metabolic_error"]) - float(high["metabolic_error"]), 10)

    # structure_null: same harshness both arms → delta ≈ 0
    low_s = error_under_resource(
        g, productivity=_RESOURCE_VALUES["low"], null_kind="structure_null"
    )
    high_s = error_under_resource(
        g, productivity=_RESOURCE_VALUES["high"], null_kind="structure_null"
    )
    structure_delta = round(
        float(low_s["metabolic_error"]) - float(high_s["metabolic_error"]), 10
    )

    # content_null: shuffled target — slope should collapse toward 0 vs intact
    low_c = error_under_resource(
        g, productivity=_RESOURCE_VALUES["low"], null_kind="content_null"
    )
    high_c = error_under_resource(
        g, productivity=_RESOURCE_VALUES["high"], null_kind="content_null"
    )
    content_delta = round(
        float(low_c["metabolic_error"]) - float(high_c["metabolic_error"]), 10
    )

    return {
        "seed": int(seed),
        "intact_low_error": low["metabolic_error"],
        "intact_high_error": high["metabolic_error"],
        "intact_delta_low_minus_high": intact_delta,
        "structure_null_delta": structure_delta,
        "content_null_delta": content_delta,
        "intact_minus_structure": round(abs(intact_delta) - abs(structure_delta), 10),
        "intact_minus_content": round(abs(intact_delta) - abs(content_delta), 10),
        "harshness_low": low["harshness"],
        "harshness_high": high["harshness"],
    }


def build_measurement_honesty_pack() -> dict[str, object]:
    """Declare measurement-only ALLOWED / pass REFUSED; all pass flags False."""

    flags = {name: False for name in sorted(MEASUREMENT_REFUSED)}
    return {
        "measurement_only": True,
        "allowed_labels": sorted(MEASUREMENT_ALLOWED),
        "refused_labels": sorted(MEASUREMENT_REFUSED),
        "flags": flags,
        "tokyo_type1_passed": False,
        "modes_passed": False,
        "channon_procedure_doi": "10.1162/artl_a_00430",
        "modes_comparator_doi": "10.1162/artl_a_00280",
        "honesty": (
            "Measurement-only comparator pack. Citing Channon Tokyo Type 1 "
            "procedure or MODES toolbox does not grant tokyo_type1_passed or "
            "modes_passed*."
        ),
    }


def run_measurement_resource_target_campaign(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    separation_threshold: float = DEFAULT_SEPARATION_THRESHOLD,
) -> dict[str, Any]:
    """D7 campaign: refuse pack green + resource→target dual-null slope."""

    if not (0.0 < float(separation_threshold) < 1.0):
        raise ConfigurationError("separation_threshold must be in (0, 1)")

    measurement = build_measurement_honesty_pack()
    # Hard assert refuse flags closed inside the builder result.
    for name in MEASUREMENT_REFUSED:
        if measurement["flags"][name] is not False:
            raise ConfigurationError(f"refuse flag must stay False: {name}")
        if measurement.get(name) not in (False, None) and name in (
            "tokyo_type1_passed",
            "modes_passed",
        ):
            raise ConfigurationError(f"top-level pass flag must stay False: {name}")

    trials = [_resource_slope_trial(int(s)) for s in seeds]
    mean_intact = round(
        sum(float(t["intact_delta_low_minus_high"]) for t in trials) / len(trials), 10
    )
    mean_sep_structure = round(
        sum(float(t["intact_minus_structure"]) for t in trials) / len(trials), 10
    )
    mean_sep_content = round(
        sum(float(t["intact_minus_content"]) for t in trials) / len(trials), 10
    )
    # Intact slope should be positive (low resource → higher error) and separate.
    slope_ok = (
        mean_intact >= float(separation_threshold)
        and mean_sep_structure >= float(separation_threshold) * 0.5
        and mean_sep_content >= 0.0  # content shuffle must not amplify slope beyond intact
    )
    refuse_ok = (
        measurement["tokyo_type1_passed"] is False
        and measurement["modes_passed"] is False
        and all(v is False for v in measurement["flags"].values())
    )
    success = slope_ok and refuse_ok
    partial = refuse_ok and not success
    result = "SUCCESS" if success else ("PARTIAL" if partial else "FAIL")

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "seeds": list(seeds),
        "separation_threshold": float(separation_threshold),
        "resource_levels": list(RESOURCE_LEVELS),
        "resource_values": dict(_RESOURCE_VALUES),
        "measurement_honesty": measurement,
        "resource_trials": trials,
        "metrics": {
            "mean_intact_delta_low_minus_high": mean_intact,
            "mean_intact_minus_structure": mean_sep_structure,
            "mean_intact_minus_content": mean_sep_content,
            "slope_ok": slope_ok,
            "refuse_ok": refuse_ok,
        },
        "result": result,
        "doi_measurement": ["10.1162/artl_a_00430", "10.1162/artl_a_00280"],
        "doi_resource": [
            "10.1111/j.1420-9101.2008.01501.x",
            "10.1111/ele.12337",
        ],
        "red_queen_proved": False,
        "tokyo_type1_passed": False,
        "modes_passed": False,
        "phage_therapy_cleared": False,
        "clinical_pathogen_model": False,
        "intelligence_proved": False,
        "collective_intelligence_proved": False,
        "aevol_identity": False,
        "wet_metabolism_claim": False,
        "claimgate_refuses": sorted(MEASUREMENT_REFUSED),
        "engine_infection_physics": "not_in_engine_core",
        "honesty": (
            "Measurement-only ALLOWED pack with hard REFUSE for Tokyo/MODES pass; "
            "resource productivity modulates abstract phenotype target harshness "
            "with dual-null; not wet ecology or OEE proof."
        ),
    }
    body["campaign_digest"] = _digest_body(body)
    return body


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "MEASUREMENT_ALLOWED",
    "MEASUREMENT_REFUSED",
    "build_measurement_honesty_pack",
    "error_under_resource",
    "harshness_from_resource",
    "run_measurement_resource_target_campaign",
    "target_under_resource",
]
