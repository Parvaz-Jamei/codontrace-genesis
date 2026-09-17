"""IsolationAssay for HARD_EXPERIMENT_03 (Goldsby-style secondary readout).

Re-score evolved specialists alone vs group context. Isolation drop is a
**secondary** confirmatory metric of lost lower-level autonomy — not a license
for collective_intelligence* / AGI claims.

Informed by reproductive-isolation / solo-competence literature (Montanier;
Boumaza 2021) only as assay design context.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

CLAIM_CEILING = "runtime_observation"


@dataclass(frozen=True, slots=True)
class IsolationAssayConfig:
    """Opt-in isolation probe (HE03 secondary assay). Default off."""

    enabled: bool = False
    min_group_performance: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "min_group_performance",
            require_finite_float(
                "min_group_performance", self.min_group_performance, non_negative=True
            ),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "min_group_performance": self.min_group_performance,
            "claim_ceiling": CLAIM_CEILING,
            "collective_intelligence": False,
            "secondary_assay": True,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> IsolationAssayConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            min_group_performance=float(data.get("min_group_performance", 0.0)),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class IsolationAssayRecord:
    """One organism's group vs solo performance comparison."""

    organism_id: str
    group_performance: float
    solo_performance: float
    isolation_drop: float
    isolation_drop_ratio: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "group_performance": self.group_performance,
            "solo_performance": self.solo_performance,
            "isolation_drop": self.isolation_drop,
            "isolation_drop_ratio": self.isolation_drop_ratio,
            "collective_intelligence": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class IsolationAssayResult:
    """Digest-backed summary of an isolation probe."""

    enabled: bool
    n_organisms: int
    mean_group_performance: float
    mean_solo_performance: float
    mean_isolation_drop: float
    mean_isolation_drop_ratio: float
    records: tuple[IsolationAssayRecord, ...]
    claim_ceiling: str = CLAIM_CEILING
    collective_intelligence: bool = False
    secondary_assay: bool = True
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling != CLAIM_CEILING:
            raise ConfigurationError(
                "IsolationAssayResult.claim_ceiling must stay runtime_observation."
            )
        if self.collective_intelligence:
            raise ConfigurationError(
                "IsolationAssayResult must not claim collective_intelligence."
            )
        payload = self._payload()
        computed = canonical_digest(payload)
        if self.digest and self.digest != computed:
            raise ConfigurationError("IsolationAssayResult digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "n_organisms": self.n_organisms,
            "mean_group_performance": self.mean_group_performance,
            "mean_solo_performance": self.mean_solo_performance,
            "mean_isolation_drop": self.mean_isolation_drop,
            "mean_isolation_drop_ratio": self.mean_isolation_drop_ratio,
            "records": [item.to_dict() for item in self.records],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "secondary_assay": True,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_isolation_assay(
    *,
    group_scores: Mapping[str, float],
    solo_scores: Mapping[str, float],
    config: IsolationAssayConfig | None = None,
) -> IsolationAssayResult:
    """Compare group-context vs solo performance per organism.

    ``isolation_drop = group - solo`` (positive ⇒ lost solo competence).
    ``isolation_drop_ratio = solo / group`` when group > 0 else 0.
    """

    resolved = config or IsolationAssayConfig(enabled=True)
    if not resolved.enabled:
        return IsolationAssayResult(
            enabled=False,
            n_organisms=0,
            mean_group_performance=0.0,
            mean_solo_performance=0.0,
            mean_isolation_drop=0.0,
            mean_isolation_drop_ratio=0.0,
            records=(),
        )
    ids = sorted(set(group_scores) | set(solo_scores))
    if not ids:
        raise ConfigurationError("IsolationAssay requires at least one organism score.")
    records: list[IsolationAssayRecord] = []
    for organism_id in ids:
        group = require_finite_float(
            "group_performance", float(group_scores.get(organism_id, 0.0))
        )
        solo = require_finite_float(
            "solo_performance", float(solo_scores.get(organism_id, 0.0)), non_negative=True
        )
        drop = round(group - solo, 10)
        ratio = 0.0 if group <= 0.0 else round(solo / group, 10)
        records.append(
            IsolationAssayRecord(
                organism_id=str(organism_id),
                group_performance=round(group, 10),
                solo_performance=round(solo, 10),
                isolation_drop=drop,
                isolation_drop_ratio=ratio,
            )
        )
    n = len(records)
    mean_group = round(sum(item.group_performance for item in records) / n, 10)
    mean_solo = round(sum(item.solo_performance for item in records) / n, 10)
    mean_drop = round(sum(item.isolation_drop for item in records) / n, 10)
    mean_ratio = round(sum(item.isolation_drop_ratio for item in records) / n, 10)
    return IsolationAssayResult(
        enabled=True,
        n_organisms=n,
        mean_group_performance=mean_group,
        mean_solo_performance=mean_solo,
        mean_isolation_drop=mean_drop,
        mean_isolation_drop_ratio=mean_ratio,
        records=tuple(records),
    )
