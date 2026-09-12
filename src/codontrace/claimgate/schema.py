"""claimgate_bundle_v1 — simulator-agnostic evidence bundle.

The auditor grades claims given this evidence. It does not run a world,
grant OEE / Tokyo Type 1, or replace ASME V&V 40 context-of-use review.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import (
    canonical_digest,
    canonical_payload,
    is_real_evidence_digest,
    require_finite_float,
)

SCHEMA_VERSION = "claimgate_bundle_v1"
ARM_ROLES: frozenset[str] = frozenset(
    {
        "treatment",
        "mechanism_ablation",
        "channel_off",
        "negative_control",
        "dose",
        "positive_control",
    }
)
SOFTWARE_PACKAGE_DOI = "10.5281/zenodo.20337435"


def _as_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be a mapping.")
    return value


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _optional_finite(value: object, name: str) -> float | None:
    if value is None:
        return None
    return require_finite_float(name, value)


def _sha256_hex(value: object, name: str) -> str:
    text = _as_str(value, name)
    if not is_real_evidence_digest(text):
        raise ConfigurationError(f"{name} must be a real 64-hex digest.")
    return text.lower()


@dataclass(frozen=True, slots=True)
class ClaimgateSoftware:
    name: str
    version: str
    commit: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "version": self.version, "commit": self.commit}


@dataclass(frozen=True, slots=True)
class ClaimgateArm:
    name: str
    role: str
    n: int

    def __post_init__(self) -> None:
        if self.role not in ARM_ROLES:
            raise ConfigurationError(
                "arm role must be treatment, mechanism_ablation, "
                "channel_off, negative_control, or dose."
            )
        if self.n < 0:
            raise ConfigurationError("arm n must be >= 0.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"name": self.name, "role": self.role, "n": self.n}


@dataclass(frozen=True, slots=True)
class ClaimgateOutcome:
    metric: str
    values_by_arm: Mapping[str, tuple[float, ...]]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric": self.metric,
            "values_by_arm": {
                name: list(values) for name, values in sorted(self.values_by_arm.items())
            },
        }


@dataclass(frozen=True, slots=True)
class ClaimgateComparison:
    a: str
    b: str
    effect_size: float | None
    ci_low: float | None
    ci_high: float | None
    p: float | None
    test: str
    correction: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "a": self.a,
            "b": self.b,
            "effect_size": self.effect_size,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p": self.p,
            "test": self.test,
            "correction": self.correction,
        }


@dataclass(frozen=True, slots=True)
class ClaimgateReplay:
    verified: bool
    digests: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"verified": self.verified, "digests": list(self.digests)}


@dataclass(frozen=True, slots=True)
class ClaimgateArtifact:
    path: str
    sha256: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class ClaimgateBundle:
    """Simulator-agnostic evidence bundle (claimgate_bundle_v1)."""

    software: ClaimgateSoftware
    seeds: tuple[int, ...]
    config_digest: str
    arms: tuple[ClaimgateArm, ...]
    outcomes: tuple[ClaimgateOutcome, ...]
    comparisons: tuple[ClaimgateComparison, ...]
    replay: ClaimgateReplay
    artifacts: tuple[ClaimgateArtifact, ...]
    limitations: tuple[str, ...]
    preregistration_digest: str | None = None
    doi: str | None = None
    extra: Mapping[str, JsonValue] | None = None
    schema: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema": self.schema,
            "software": self.software.to_dict(),
            "seeds": list(self.seeds),
            "config_digest": self.config_digest,
            "arms": [item.to_dict() for item in self.arms],
            "outcomes": [item.to_dict() for item in self.outcomes],
            "comparisons": [item.to_dict() for item in self.comparisons],
            "replay": self.replay.to_dict(),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "limitations": list(self.limitations),
        }
        if self.preregistration_digest is not None:
            payload["preregistration_digest"] = self.preregistration_digest
        if self.doi is not None:
            payload["doi"] = self.doi
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    def digest(self) -> str:
        return canonical_digest(canonical_payload(self.to_dict()))


def _parse_software(raw: object) -> ClaimgateSoftware:
    data = _as_mapping(raw, "software")
    return ClaimgateSoftware(
        name=_as_str(data.get("name"), "software.name"),
        version=_as_str(data.get("version"), "software.version"),
        commit=_as_str(data.get("commit", ""), "software.commit", allow_empty=True),
    )


def _parse_seeds(raw: object) -> tuple[int, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConfigurationError("seeds must be a list of integers.")
    seeds: list[int] = []
    for index, item in enumerate(raw):
        seeds.append(_as_int(item, f"seeds[{index}]"))
    return tuple(seeds)


def _parse_arms(raw: object) -> tuple[ClaimgateArm, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConfigurationError("arms must be a list.")
    arms: list[ClaimgateArm] = []
    for index, item in enumerate(raw):
        data = _as_mapping(item, f"arms[{index}]")
        arms.append(
            ClaimgateArm(
                name=_as_str(data.get("name"), f"arms[{index}].name"),
                role=_as_str(data.get("role"), f"arms[{index}].role"),
                n=_as_int(data.get("n"), f"arms[{index}].n", minimum=0),
            )
        )
    return tuple(arms)


def _parse_outcomes(raw: object) -> tuple[ClaimgateOutcome, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConfigurationError("outcomes must be a list.")
    outcomes: list[ClaimgateOutcome] = []
    for index, item in enumerate(raw):
        data = _as_mapping(item, f"outcomes[{index}]")
        values_raw = _as_mapping(data.get("values_by_arm"), f"outcomes[{index}].values_by_arm")
        values: dict[str, tuple[float, ...]] = {}
        for arm, series in values_raw.items():
            if not isinstance(series, Sequence) or isinstance(series, (str, bytes)):
                raise ConfigurationError(
                    f"outcomes[{index}].values_by_arm[{arm}] must be a list."
                )
            parsed: list[float] = []
            for pos, value in enumerate(series):
                parsed.append(
                    require_finite_float(
                        f"outcomes[{index}].values_by_arm[{arm}][{pos}]", value
                    )
                )
            values[str(arm)] = tuple(parsed)
        outcomes.append(
            ClaimgateOutcome(
                metric=_as_str(data.get("metric"), f"outcomes[{index}].metric"),
                values_by_arm=values,
            )
        )
    return tuple(outcomes)


def _parse_comparisons(raw: object) -> tuple[ClaimgateComparison, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConfigurationError("comparisons must be a list.")
    comparisons: list[ClaimgateComparison] = []
    for index, item in enumerate(raw):
        data = _as_mapping(item, f"comparisons[{index}]")
        p_value = _optional_finite(data.get("p"), f"comparisons[{index}].p")
        if p_value is not None and not 0.0 <= p_value <= 1.0:
            raise ConfigurationError(f"comparisons[{index}].p must be in [0, 1].")
        comparisons.append(
            ClaimgateComparison(
                a=_as_str(data.get("a"), f"comparisons[{index}].a"),
                b=_as_str(data.get("b"), f"comparisons[{index}].b"),
                effect_size=_optional_finite(
                    data.get("effect_size"), f"comparisons[{index}].effect_size"
                ),
                ci_low=_optional_finite(data.get("ci_low"), f"comparisons[{index}].ci_low"),
                ci_high=_optional_finite(data.get("ci_high"), f"comparisons[{index}].ci_high"),
                p=p_value,
                test=_as_str(data.get("test", ""), f"comparisons[{index}].test", allow_empty=True),
                correction=_as_str(
                    data.get("correction", ""),
                    f"comparisons[{index}].correction",
                    allow_empty=True,
                ),
            )
        )
    return tuple(comparisons)


def _parse_replay(raw: object) -> ClaimgateReplay:
    data = _as_mapping(raw, "replay")
    digests_raw = data.get("digests", ())
    if not isinstance(digests_raw, Sequence) or isinstance(digests_raw, (str, bytes)):
        raise ConfigurationError("replay.digests must be a list.")
    digests: list[str] = []
    for index, item in enumerate(digests_raw):
        text = _as_str(item, f"replay.digests[{index}]")
        if is_real_evidence_digest(text):
            digests.append(text.lower())
        else:
            raise ConfigurationError(f"replay.digests[{index}] must be a real digest.")
    verified = data.get("verified")
    if not isinstance(verified, bool):
        raise ConfigurationError("replay.verified must be a boolean.")
    return ClaimgateReplay(verified=verified, digests=tuple(digests))


def _parse_artifacts(raw: object) -> tuple[ClaimgateArtifact, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConfigurationError("artifacts must be a list.")
    artifacts: list[ClaimgateArtifact] = []
    for index, item in enumerate(raw):
        data = _as_mapping(item, f"artifacts[{index}]")
        artifacts.append(
            ClaimgateArtifact(
                path=_as_str(data.get("path"), f"artifacts[{index}].path"),
                sha256=_sha256_hex(data.get("sha256"), f"artifacts[{index}].sha256"),
            )
        )
    return tuple(artifacts)


def _parse_limitations(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ConfigurationError("limitations must be a list.")
    return tuple(_as_str(item, f"limitations[{index}]") for index, item in enumerate(raw))


def parse_claimgate_bundle(payload: Mapping[str, Any] | ClaimgateBundle) -> ClaimgateBundle:
    """Parse and validate a claimgate_bundle_v1 mapping."""

    if isinstance(payload, ClaimgateBundle):
        return payload
    data = _as_mapping(payload, "bundle")
    schema = _as_str(data.get("schema", SCHEMA_VERSION), "schema")
    if schema != SCHEMA_VERSION:
        raise ConfigurationError(f"bundle schema must be {SCHEMA_VERSION}.")
    prereg = data.get("preregistration_digest")
    prereg_digest = None if prereg in (None, "") else _sha256_hex(prereg, "preregistration_digest")
    doi_raw = data.get("doi")
    doi = None if doi_raw in (None, "") else _as_str(doi_raw, "doi")
    reserved = {
        "schema",
        "software",
        "seeds",
        "config_digest",
        "preregistration_digest",
        "arms",
        "outcomes",
        "comparisons",
        "replay",
        "artifacts",
        "limitations",
        "doi",
    }
    extra_raw = {str(key): data[key] for key in data if key not in reserved}
    extra: Mapping[str, JsonValue] | None = None
    if extra_raw:
        parsed_extra = canonical_payload(extra_raw)
        extra = parsed_extra if isinstance(parsed_extra, dict) else None
    return ClaimgateBundle(
        software=_parse_software(data.get("software")),
        seeds=_parse_seeds(data.get("seeds")),
        config_digest=_sha256_hex(data.get("config_digest"), "config_digest"),
        arms=_parse_arms(data.get("arms")),
        outcomes=_parse_outcomes(data.get("outcomes")),
        comparisons=_parse_comparisons(data.get("comparisons")),
        replay=_parse_replay(data.get("replay")),
        artifacts=_parse_artifacts(data.get("artifacts")),
        limitations=_parse_limitations(data.get("limitations")),
        preregistration_digest=prereg_digest,
        doi=doi,
        extra=extra,
        schema=schema,
    )
