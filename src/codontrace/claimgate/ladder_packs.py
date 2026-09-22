"""Deterministic nine-pack ClaimGate sanity fixtures.

These packs reconstruct the BAIC table-3 *design*. Levels are whatever
``audit_bundle`` returns today. They are not a population error rate and
not an external rater study.
"""

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256

from codontrace.claimgate.auditor import audit_bundle
from codontrace.claimgate.schema import (
    ClaimgateArm,
    ClaimgateArtifact,
    ClaimgateBundle,
    ClaimgateComparison,
    ClaimgateOutcome,
    ClaimgateReplay,
    ClaimgateSoftware,
    parse_claimgate_bundle,
)
from codontrace.genesis.canonical import canonical_digest, canonical_payload

REAL_HEX = sha256(b"codontrace-ladder-pack-config").hexdigest()
REPLAY_HEX = sha256(b"codontrace-ladder-pack-replay").hexdigest()
ARTIFACT_HEX = sha256(b"codontrace-ladder-pack-artifact").hexdigest()
PLACEHOLDER_HEX = sha256(b"placeholder").hexdigest()
ARCHIVE_DOI = "10.5281/zenodo.20337435"

TreatmentValues = tuple[float, ...]
ControlValues = tuple[float, ...]


def _seeds(n: int) -> tuple[int, ...]:
    return tuple(range(11, 11 + n))


def _values(n: int, start: float, step: float) -> tuple[float, ...]:
    return tuple(start + step * index for index in range(n))


def _base(
    *,
    n: int = 16,
    treatment: TreatmentValues | None = None,
    control: ControlValues | None = None,
    ablation: ControlValues | None = None,
    include_negative: bool = True,
    include_ablation: bool = True,
    comparisons: tuple[ClaimgateComparison, ...] | None = None,
    replay: ClaimgateReplay | None = None,
    artifacts: tuple[ClaimgateArtifact, ...] | None = None,
    limitations: tuple[str, ...] | None = None,
    extra: dict[str, object] | None = None,
) -> ClaimgateBundle:
    count = n
    treat = treatment if treatment is not None else _values(count, 40.0, 0.25)
    base_ctrl = control if control is not None else _values(count, 23.0, 0.10)
    base_abl = ablation if ablation is not None else _values(count, 28.0, 0.05)
    arms = [ClaimgateArm(name="gated_on", role="treatment", n=count)]
    if include_ablation:
        arms.append(ClaimgateArm(name="channel_off", role="channel_off", n=count))
    if include_negative:
        arms.append(ClaimgateArm(name="content_null", role="negative_control", n=count))
    values_by_arm = {"gated_on": treat}
    if include_ablation:
        values_by_arm["channel_off"] = base_abl
    if include_negative:
        values_by_arm["content_null"] = base_ctrl
    if comparisons is None:
        pair = (
            ClaimgateComparison(
                a="gated_on",
                b="channel_off" if include_ablation else "content_null",
                effect_size=2.37,
                ci_low=14.25,
                ci_high=19.14,
                p=4.99975e-5,
                test="sign_flip",
                correction="holm",
            ),
        )
    else:
        pair = comparisons
    payload_extra = {
        "suite": "claimgate_ladder_validation_v1",
        "not_a_population_error_rate": True,
        **(extra or {}),
    }
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(
            name="codontrace",
            version="from-pyproject",
            commit="ladder-validation",
        ),
        seeds=_seeds(count),
        config_digest=REAL_HEX,
        arms=tuple(arms),
        outcomes=(
            ClaimgateOutcome(
                metric="receiver_mean_terminal_runtime_atp",
                values_by_arm=values_by_arm,
            ),
        ),
        comparisons=pair,
        replay=replay
        if replay is not None
        else ClaimgateReplay(verified=True, digests=(REPLAY_HEX,)),
        artifacts=artifacts
        if artifacts is not None
        else (ClaimgateArtifact(path="docs/hard_experiment_01/results_v7.json", sha256=ARTIFACT_HEX),),
        limitations=limitations
        if limitations is not None
        else ("Synthetic sanity pack. Not clinical validity.",),
        extra=payload_extra,
    )
    return parse_claimgate_bundle(bundle)


def pack_reference() -> ClaimgateBundle:
    return _base(extra={"pack_id": "reference"})


def pack_identical_arms() -> ClaimgateBundle:
    flat = _values(16, 28.0, 0.0)
    return _base(
        treatment=flat,
        control=flat,
        ablation=flat,
        extra={"pack_id": "identical_arms", "assay_invalid": True},
    )


def pack_zero_width_ci() -> ClaimgateBundle:
    return _base(
        comparisons=(
            ClaimgateComparison(
                a="gated_on",
                b="channel_off",
                effect_size=0.0,
                ci_low=0.0,
                ci_high=0.0,
                p=1.0,
                test="sign_flip",
                correction="holm",
            ),
        ),
        extra={"pack_id": "zero_width_ci"},
    )


def pack_no_paired_comparison() -> ClaimgateBundle:
    return _base(comparisons=(), extra={"pack_id": "no_paired_comparison"})


def pack_no_replay() -> ClaimgateBundle:
    return _base(
        replay=ClaimgateReplay(verified=False, digests=()),
        extra={"pack_id": "no_replay"},
    )


def pack_empty_limitations() -> ClaimgateBundle:
    return _base(limitations=(), extra={"pack_id": "empty_limitations"})


def pack_placeholder_digest() -> ClaimgateBundle:
    return _base(
        artifacts=(
            ClaimgateArtifact(path="placeholder-artifact", sha256=PLACEHOLDER_HEX),
        ),
        extra={"pack_id": "placeholder_digest", "digest_note": "sha256('placeholder') still matches hex grammar"},
    )


def pack_three_seeds() -> ClaimgateBundle:
    return _base(n=3, extra={"pack_id": "three_seeds"})


def pack_drop_confirmatory_keep_sensitivity_role() -> ClaimgateBundle:
    """Confirmatory control removed; a sensitivity arm still uses negative_control."""

    return _base(
        extra={
            "pack_id": "drop_confirmatory_keep_sensitivity_role",
            "confirmatory_negative_removed": True,
            "sensitivity_still_labeled_negative_control": True,
        }
    )


PACK_BUILDERS: tuple[tuple[str, Callable[[], ClaimgateBundle], str], ...] = (
    ("reference", pack_reference, "reference"),
    ("identical_arms", pack_identical_arms, "expected"),
    ("zero_width_ci", pack_zero_width_ci, "expected"),
    ("no_paired_comparison", pack_no_paired_comparison, "expected"),
    ("no_replay", pack_no_replay, "expected"),
    ("empty_limitations", pack_empty_limitations, "expected"),
    ("placeholder_digest", pack_placeholder_digest, "mismatch"),
    ("three_seeds", pack_three_seeds, "needs_definition"),
    ("drop_confirmatory_keep_sensitivity_role", pack_drop_confirmatory_keep_sensitivity_role, "mismatch"),
)

PAPER_TABLE3_LEVELS = {
    "reference": 4,
    "identical_arms": 1,
    "zero_width_ci": 1,
    "no_paired_comparison": 1,
    "no_replay": 2,
    "empty_limitations": 2,
    "placeholder_digest": 4,
    "three_seeds": 3,
    "drop_confirmatory_keep_sensitivity_role": 4,
}


def audit_ladder_packs() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for pack_id, builder, paper_label in PACK_BUILDERS:
        bundle = builder()
        report = audit_bundle(bundle)
        rows.append(
            {
                "pack_id": pack_id,
                "auditor_level": report.achieved_level,
                "public_name": report.public_name,
                "paper_table3_level": PAPER_TABLE3_LEVELS[pack_id],
                "paper_label": paper_label,
                "missing_for_next": list(report.missing_for_next),
                "report_digest": report.digest,
                "bundle_digest": bundle.digest(),
            }
        )
    return rows


def ladder_validation_payload() -> dict[str, object]:
    rows = audit_ladder_packs()
    body = {
        "schema": "claimgate_ladder_validation_v1",
        "n_packs": len(rows),
        "not_a_population_error_rate": True,
        "external_raters": False,
        "rows": rows,
    }
    return {**body, "digest": canonical_digest(canonical_payload(body))}
