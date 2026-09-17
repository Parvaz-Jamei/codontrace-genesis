"""CodonTrace Genesis adapter: HardExperiment03Campaign / results_v1.json.

Reads a committed campaign artifact when present. Does not import the Genesis
engine or population modules. Does not unlock claims.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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

PRODUCT_NAME = "CodonTrace Genesis"
ARM_ROLES: dict[str, str] = {
    "cost_0": "control",
    "cost_moderate": "treatment",
    "cost_high": "treatment",
    "channel_off": "mechanism_ablation",
    "isolation_probe": "secondary_assay",
}
DEFAULT_RESULTS = Path("docs/hard_experiment_03/results_v1.json")
PRIMARY_METRIC_FALLBACK = "d_sym"
ASSAY_FAILURE_PREFIX = "assay_failed_"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def committed_results_v1_path() -> Path:
    return _repo_root() / DEFAULT_RESULTS


def committed_pilot_v1_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_03" / "pilot_v1.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    if hasattr(source, "to_dict") and callable(getattr(source, "to_dict")):
        payload = source.to_dict()
        if not isinstance(payload, Mapping):
            raise ConfigurationError("campaign.to_dict() must return a mapping.")
        return payload, None
    return _as_mapping(source, "campaign"), None


def _seeds(data: Mapping[str, Any]) -> tuple[int, ...]:
    raw = data.get("seeds", ())
    if not isinstance(raw, (list, tuple)):
        raise ConfigurationError("campaign.seeds must be a sequence.")
    return tuple(int(item) for item in raw)


def _primary_metric_name(data: Mapping[str, Any]) -> str:
    value = data.get("primary_outcome") or data.get("primary_metric") or PRIMARY_METRIC_FALLBACK
    return str(value)


def _assay_failure_codes(data: Mapping[str, Any]) -> tuple[str, ...]:
    raw = data.get("assay_failures", ())
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(str(item) for item in raw if str(item).startswith(ASSAY_FAILURE_PREFIX) or str(item).startswith("assay_failed"))


def _arm_means(data: Mapping[str, Any], metric: str) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {arm: [] for arm in ARM_ROLES}
    for seed_record in data.get("seed_records", ()) or ():
        if not isinstance(seed_record, Mapping):
            continue
        for arm in ARM_ROLES:
            arm_payload = seed_record.get(arm)
            if not isinstance(arm_payload, Mapping):
                continue
            if metric == "d_sym" and arm_payload.get("d_sym") is not None:
                values[arm].append(float(arm_payload["d_sym"]))
            elif arm_payload.get(metric) is not None:
                values[arm].append(float(arm_payload[metric]))
    return values


def bundle_from_hard_experiment_03(
    source: Mapping[str, Any] | object | Path | str | None = None,
) -> ClaimgateBundle:
    """Build a claimgate_bundle_v1 from HARD_EXPERIMENT_03 campaign JSON."""

    if source is None:
        source = committed_results_v1_path()
        if not Path(source).is_file():
            source = committed_pilot_v1_path()
    data, path = _campaign_mapping(source)
    seeds = _seeds(data)
    config = data.get("protocol_digest") or data.get("digest")
    if not isinstance(config, str) or not is_real_evidence_digest(config):
        raise ConfigurationError("campaign is missing a real config/protocol digest.")
    prereg = data.get("prereg_digest")
    primary_metric = _primary_metric_name(data)
    values_by_arm = _arm_means(data, primary_metric)
    means = [sum(v) / len(v) for v in values_by_arm.values() if v]
    means_identical = len(means) >= 2 and all(item == means[0] for item in means)
    manipulation_failures = _assay_failure_codes(data)
    assay_invalid = bool(data.get("assay_failed")) or means_identical or bool(manipulation_failures)
    arms = tuple(
        ClaimgateArm(name=name, role=role)
        for name, role in ARM_ROLES.items()
    )
    outcomes = (
        ClaimgateOutcome(
            metric=primary_metric,
            values_by_arm={key: tuple(vals) for key, vals in values_by_arm.items() if vals},
        ),
    )
    artifacts: list[ClaimgateArtifact] = []
    if path is not None and path.is_file():
        artifacts.append(
            ClaimgateArtifact(
                path=str(path),
                sha256=_sha256_file(path),
                role="campaign_json",
            )
        )
    bundle = ClaimgateBundle(
        software=ClaimgateSoftware(name=PRODUCT_NAME, version=str(data.get("schema_version", "hard_experiment_03_v1"))),
        config_digest=str(config).lower(),
        preregistration_digest=None if not isinstance(prereg, str) else prereg.lower(),
        arms=arms,
        outcomes=outcomes,
        comparisons=(),
        replay=ClaimgateReplay(verified=False, digests=()),
        artifacts=tuple(artifacts),
        extras={
            "adapter": "codontrace_hard_experiment_03",
            "experiment_id": data.get("experiment_id"),
            "claim_ceiling": data.get("claim_ceiling", "runtime_observation"),
            "primary_outcome": primary_metric,
            "assay_invalid": assay_invalid,
            "assay_failures": list(manipulation_failures),
            "collective_intelligence": False,
            "intelligence": False,
            "agi": False,
            "seeds": list(seeds),
        },
    )
    return parse_claimgate_bundle(bundle.to_dict())
