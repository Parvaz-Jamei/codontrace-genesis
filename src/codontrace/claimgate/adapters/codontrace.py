"""CodonTrace Genesis adapter: HardExperiment01Campaign / results_v2.json.

Reads the committed campaign artifact. Does not import the Genesis engine
or population modules. Does not unlock claims.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from codontrace.claimgate.adapters.he01_arm_roles import ARM_ROLES, canonical_role
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
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import is_real_evidence_digest
from codontrace.genesis.text_digest import sha256_text_file

PRODUCT_NAME = "CodonTrace Genesis"
DEFAULT_RESULTS = Path("docs/hard_experiment_01/results_v3.json")
# Names of the primary outcome across schema versions (v1/v2 composite
# selection fitness; v3 receiver mean terminal runtime ATP). The arm record
# field is ``terminal_mean_fitness`` in every version; ``primary_outcome``
# names what it measures.
PRIMARY_METRIC_FALLBACK = "terminal_mean_fitness"
# Manipulation-check codes (Wave 1c) that make a campaign assay_invalid
# regardless of p-values. Anything starting with this prefix counts.
ASSAY_FAILURE_PREFIX = "assay_failed_"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def committed_results_v3_path() -> Path:
    return _repo_root() / DEFAULT_RESULTS


def committed_results_v2_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_01" / "results_v2.json"


def _sha256_file(path: Path) -> str:
    return sha256_text_file(path)


def _as_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be a mapping.")
    return value


def _campaign_mapping(
    source: Mapping[str, Any] | object | Path | str,
) -> tuple[Mapping[str, Any], Path | None]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise ConfigurationError(f"campaign artifact not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ConfigurationError("campaign artifact must be a JSON object.")
        return data, path
    to_dict = getattr(source, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        return _as_mapping(raw, "campaign"), None
    return _as_mapping(source, "campaign"), None


def _software(data: Mapping[str, Any]) -> ClaimgateSoftware:
    extra = data.get("software")
    version = "0.3.0b4.dev0"
    commit = ""
    if isinstance(extra, Mapping):
        version = str(extra.get("version") or version)
        commit = str(extra.get("commit") or "")
    return ClaimgateSoftware(name=PRODUCT_NAME, version=version, commit=commit)


def _seeds(data: Mapping[str, Any]) -> tuple[int, ...]:
    raw = data.get("seeds")
    if not isinstance(raw, list):
        raise ConfigurationError("campaign.seeds must be a list.")
    return tuple(int(item) for item in raw)


def _arms(data: Mapping[str, Any], seed_count: int) -> tuple[ClaimgateArm, ...]:
    arms: list[ClaimgateArm] = []
    interventions = data.get("interventions")
    if isinstance(interventions, list):
        for item in interventions:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("arm") or "")
            role = canonical_role(name, str(item.get("role") or ""))
            if name and role:
                arms.append(ClaimgateArm(name=name, role=role, n=seed_count))
    if not arms:
        summaries = data.get("arm_summaries")
        if isinstance(summaries, list):
            for item in summaries:
                if not isinstance(item, Mapping):
                    continue
                name = str(item.get("arm") or "")
                mapped_role = canonical_role(name, str(item.get("role") or ""))
                n = item.get("n", seed_count)
                if name and mapped_role:
                    arms.append(ClaimgateArm(name=name, role=mapped_role, n=int(n)))
    dose_records = data.get("dose_records")
    if isinstance(dose_records, list) and dose_records:
        arms.append(ClaimgateArm(name="dose_ladder", role="dose", n=len(dose_records)))
    if not arms:
        raise ConfigurationError("campaign is missing arm records.")
    return tuple(arms)


def _primary_metric_name(data: Mapping[str, Any]) -> str:
    raw = data.get("primary_outcome")
    return str(raw) if isinstance(raw, str) and raw.strip() else PRIMARY_METRIC_FALLBACK


def _assay_failure_codes(data: Mapping[str, Any]) -> tuple[str, ...]:
    raw = data.get("assay_failures")
    if not isinstance(raw, list):
        return ()
    return tuple(str(item) for item in raw if str(item).startswith(ASSAY_FAILURE_PREFIX))


def _outcomes(data: Mapping[str, Any]) -> tuple[ClaimgateOutcome, ...]:
    records = data.get("seed_records")
    if not isinstance(records, list):
        raise ConfigurationError("campaign.seed_records must be a list.")
    fitness: dict[str, list[float]] = {name: [] for name in ARM_ROLES}
    adoptions: dict[str, list[float]] = {name: [] for name in ARM_ROLES}
    for item in records:
        if not isinstance(item, Mapping):
            continue
        for name in ARM_ROLES:
            arm = item.get(name)
            if not isinstance(arm, Mapping):
                continue
            value = arm.get("terminal_mean_fitness")
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                fitness[name].append(float(value))
            adopted = arm.get("capsule_adoptions")
            if isinstance(adopted, (int, float)) and not isinstance(adopted, bool):
                adoptions[name].append(float(adopted))
    return (
        ClaimgateOutcome(
            metric=_primary_metric_name(data),
            values_by_arm={name: tuple(values) for name, values in fitness.items() if values},
        ),
        ClaimgateOutcome(
            metric="capsule_adoptions",
            values_by_arm={name: tuple(values) for name, values in adoptions.items() if values},
        ),
    )


def _comparisons(data: Mapping[str, Any]) -> tuple[ClaimgateComparison, ...]:
    raw = data.get("paired_contrasts")
    if not isinstance(raw, list):
        raise ConfigurationError("campaign.paired_contrasts must be a list.")
    comparisons: list[ClaimgateComparison] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        treatment = str(item.get("treatment_arm") or "")
        baseline = str(item.get("baseline_arm") or "")
        if not treatment or not baseline:
            continue
        correction = "holm" if item.get("p_holm") is not None else ""
        p_value = item.get("p_holm")
        if p_value is None:
            p_value = item.get("p_raw")
        effect = item.get("dz")
        if effect is None:
            paired = item.get("paired_result")
            if isinstance(paired, Mapping):
                effect = paired.get("effect_size")
        comparisons.append(
            ClaimgateComparison(
                a=treatment,
                b=baseline,
                effect_size=None if effect is None else float(effect),
                ci_low=None if item.get("ci_low") is None else float(item["ci_low"]),
                ci_high=None if item.get("ci_high") is None else float(item["ci_high"]),
                p=None if p_value is None else float(p_value),
                test="paired_sign_flip_bca",
                correction=correction,
            )
        )
    return tuple(comparisons)


def _replay(data: Mapping[str, Any]) -> ClaimgateReplay:
    records = data.get("replay_records")
    digests: list[str] = []
    matched = bool(data.get("replay_matched") is True)
    if isinstance(records, list):
        for item in records:
            if not isinstance(item, Mapping):
                continue
            if item.get("matched") is not True:
                matched = False
            for key in ("result_digest", "spec_digest"):
                digest = item.get(key)
                if isinstance(digest, str) and is_real_evidence_digest(digest):
                    digests.append(digest.lower())
    campaign_digest = data.get("digest")
    if isinstance(campaign_digest, str) and is_real_evidence_digest(campaign_digest):
        digests.append(campaign_digest.lower())
    return ClaimgateReplay(verified=matched and bool(digests), digests=tuple(digests))


def _artifacts(data: Mapping[str, Any], source_path: Path | None) -> tuple[ClaimgateArtifact, ...]:
    artifacts: list[ClaimgateArtifact] = []
    if source_path is not None and source_path.is_file():
        artifacts.append(
            ClaimgateArtifact(
                path=str(source_path.as_posix()),
                sha256=_sha256_file(source_path),
            )
        )
    digest = data.get("digest")
    if isinstance(digest, str) and is_real_evidence_digest(digest):
        artifacts.append(
            ClaimgateArtifact(path="hard_experiment_01_campaign", sha256=digest.lower())
        )
    prereg = data.get("prereg_digest")
    if isinstance(prereg, str) and is_real_evidence_digest(prereg):
        artifacts.append(
            ClaimgateArtifact(
                path=str(data.get("prereg_path") or "docs/HARD_EXPERIMENT_01_PREREG.md"),
                sha256=prereg.lower(),
            )
        )
    if not artifacts:
        raise ConfigurationError("campaign produced no artifact digests.")
    return tuple(artifacts)


def _limitations(data: Mapping[str, Any]) -> tuple[str, ...]:
    raw = data.get("limitations")
    if isinstance(raw, list):
        return tuple(str(item) for item in raw if str(item).strip())
    return (
        "hard_experiment_01_is_runtime_observation",
        "assay_invalid_manipulation_not_realized",
    )


def bundle_from_hard_experiment_01(
    source: Mapping[str, Any] | object | Path | str | None = None,
) -> ClaimgateBundle:
    """Build a claimgate_bundle_v1 from HARD_EXPERIMENT_01 v2 (or equivalent)."""

    if source is None:
        source = committed_results_v3_path()
        if not source.is_file():
            source = committed_results_v2_path()
    data, path = _campaign_mapping(source)
    seeds = _seeds(data)
    config = data.get("protocol_digest") or data.get("digest")
    if not isinstance(config, str) or not is_real_evidence_digest(config):
        raise ConfigurationError("campaign is missing a real config/protocol digest.")
    prereg = data.get("prereg_digest")
    outcomes = _outcomes(data)
    primary_metric = _primary_metric_name(data)
    fitness_means: list[float] = []
    for outcome in outcomes:
        if outcome.metric != primary_metric:
            continue
        for values in outcome.values_by_arm.values():
            if values:
                fitness_means.append(sum(values) / len(values))
    means_identical = len(fitness_means) >= 2 and all(
        item == fitness_means[0] for item in fitness_means
    )
    manipulation_failures = _assay_failure_codes(data)
    assay_invalid = means_identical or bool(manipulation_failures)
    extra: dict[str, Any] = {
        "adapter": "codontrace_hard_experiment_01",
        "experiment_id": data.get("experiment_id"),
        "claim_ceiling": data.get("claim_ceiling"),
        "primary_outcome": primary_metric,
        "assay_failed": data.get("assay_failed"),
        "assay_invalid": assay_invalid,
        "assay_manipulation_failures": list(manipulation_failures),
        "decision_rule_passed": data.get("decision_rule_passed"),
        "collective_intelligence": False,
        "intelligence": False,
        "agi": False,
        "tokyo_type1_passed": False,
        "avida_replacement": False,
        "full_avida_support": False,
        "full_mabe2_support": False,
    }
    bundle = ClaimgateBundle(
        software=_software(data),
        seeds=seeds,
        config_digest=str(config).lower(),
        arms=_arms(data, len(seeds)),
        outcomes=outcomes,
        comparisons=_comparisons(data),
        replay=_replay(data),
        artifacts=_artifacts(data, path),
        limitations=_limitations(data),
        preregistration_digest=(
            str(prereg).lower()
            if isinstance(prereg, str) and is_real_evidence_digest(prereg)
            else None
        ),
        extra=extra,
    )
    return parse_claimgate_bundle(bundle)
