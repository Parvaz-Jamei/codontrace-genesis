"""Phase 7 — Host–parasite metrics / prereg on life_loop hooks (no new physics).

PreregSpec freezes phenomenon → metrics → dual-null → seed plan → CI → refuse
list. MetricSummary is refuse-safe observation only: never soft-passes proved
claims. Domain labels stay on this module; HookMeter keys stay domain-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.hook_meters import HookMeterSnapshot

SCHEMA_VERSION = "host_parasite_prereg_spec_v1"
SUMMARY_SCHEMA = "host_parasite_metric_summary_v1"

METRIC_IDS: frozenset[str] = frozenset(
    {
        "role_density_primary",
        "role_density_secondary",
        "attach_prevalence",
        "coupling_total",
        "contact_success_rate",
        "hook_birth_count",
        "hook_death_count",
        "hook_contact_count",
        "hook_resource_count",
        "diversity_proxy_unique_payloads",
    }
)

ClaimRole = Literal["primary", "exploratory", "smoke"]
Ceiling = Literal["runtime_observation", "candidate_evidence"]

_CORE_REFUSES: frozenset[str] = frozenset(
    {
        "red_queen_proved",
        "modes_passed_proved",
        "tokyo_type1_passed",
        "price_as_causality",
        "crispr_identity_proved",
        "phage_therapy_cleared",
        "vaccine_efficacy_proved",
        "epidemic_forecast_certified",
        "biosafety_level_certified",
        "major_transition_proved",
        "intelligence",
    }
)

SCIENCE_MIN_SEEDS = 30


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


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a bool.")
    return value


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class SeedPlanSpec:
    """Science-N seed plan with explicit smoke override."""

    seeds: tuple[int, ...]
    smoke_only: bool = False
    min_seeds: int = SCIENCE_MIN_SEEDS
    digest: str = ""

    def __post_init__(self) -> None:
        seeds = tuple(_as_int(s, "seed", minimum=0) for s in self.seeds)
        if len(seeds) != len(set(seeds)):
            raise ConfigurationError("SeedPlanSpec seeds must be unique.")
        smoke = _as_bool(self.smoke_only, "smoke_only")
        minimum = _as_int(self.min_seeds, "min_seeds", minimum=1)
        if not smoke and len(seeds) < minimum:
            raise ConfigurationError(
                f"SeedPlanSpec requires >= {minimum} seeds unless smoke_only."
            )
        if not seeds:
            raise ConfigurationError("SeedPlanSpec seeds must be non-empty.")
        object.__setattr__(self, "seeds", seeds)
        object.__setattr__(self, "smoke_only", smoke)
        object.__setattr__(self, "min_seeds", minimum)
        computed = canonical_digest(self._body(), prefix="hp_seed_plan")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "SeedPlanSpec")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "seeds": list(self.seeds),
            "smoke_only": self.smoke_only,
            "min_seeds": self.min_seeds,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SeedPlanSpec:
        raw_seeds = data.get("seeds")
        if not isinstance(raw_seeds, Sequence) or isinstance(raw_seeds, (str, bytes)):
            raise ConfigurationError("seeds must be a sequence of ints.")
        return cls(
            seeds=tuple(int(s) for s in raw_seeds),
            smoke_only=bool(data.get("smoke_only", False)),
            min_seeds=int(data.get("min_seeds", SCIENCE_MIN_SEEDS)),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    @classmethod
    def science_default(cls, n: int = SCIENCE_MIN_SEEDS) -> SeedPlanSpec:
        count = _as_int(n, "n", minimum=SCIENCE_MIN_SEEDS)
        return cls(seeds=tuple(range(count)), smoke_only=False)

    @classmethod
    def smoke(cls, seeds: Sequence[int] = (0, 1, 2)) -> SeedPlanSpec:
        return cls(seeds=tuple(seeds), smoke_only=True, min_seeds=1)


@dataclass(frozen=True, slots=True)
class HostParasitePreregSpec:
    """Frozen prereg envelope attachable to HostParasiteWorld."""

    prereg_id: str
    phenomenon: str
    metric_ids: tuple[str, ...]
    dual_null_required: bool
    seed_plan: SeedPlanSpec
    ci_plan: str = "bootstrap_percentile_or_normal_approx"
    refuse_list: tuple[str, ...] = ()
    planned_claim_ceiling: str = "runtime_observation"
    digest: str = ""

    def __post_init__(self) -> None:
        pid = _as_str(self.prereg_id, "prereg_id")
        phen = _as_str(self.phenomenon, "phenomenon")
        if not self.metric_ids:
            raise ConfigurationError("metric_ids must be non-empty.")
        metrics = tuple(
            _as_str(m, f"metric_ids[{i}]") for i, m in enumerate(self.metric_ids)
        )
        for m in metrics:
            if m not in METRIC_IDS:
                raise ConfigurationError(f"unknown metric_id: {m!r}")
        if not isinstance(self.seed_plan, SeedPlanSpec):
            raise ConfigurationError("seed_plan must be a SeedPlanSpec.")
        dual = _as_bool(self.dual_null_required, "dual_null_required")
        if self.seed_plan.smoke_only and dual is False:
            # smoke may omit dual-null; primary path still gated at summary build
            pass
        ceiling = _as_str(self.planned_claim_ceiling, "planned_claim_ceiling").lower()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "planned_claim_ceiling must be runtime_observation or candidate_evidence."
            )
        refuses = tuple(
            sorted(
                {
                    *(
                        _as_str(r, "refuse").lower()
                        for r in (self.refuse_list or ())
                    ),
                    *_CORE_REFUSES,
                }
            )
        )
        ci = _as_str(self.ci_plan, "ci_plan")
        object.__setattr__(self, "prereg_id", pid)
        object.__setattr__(self, "phenomenon", phen)
        object.__setattr__(self, "metric_ids", metrics)
        object.__setattr__(self, "dual_null_required", dual)
        object.__setattr__(self, "ci_plan", ci)
        object.__setattr__(self, "refuse_list", refuses)
        object.__setattr__(self, "planned_claim_ceiling", ceiling)
        computed = canonical_digest(self._body(), prefix="hp_prereg")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "HostParasitePreregSpec"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "prereg_id": self.prereg_id,
            "phenomenon": self.phenomenon,
            "metric_ids": list(self.metric_ids),
            "dual_null_required": self.dual_null_required,
            "seed_plan": self.seed_plan.to_dict(),
            "ci_plan": self.ci_plan,
            "refuse_list": list(self.refuse_list),
            "planned_claim_ceiling": self.planned_claim_ceiling,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> HostParasitePreregSpec:
        raw_metrics = data.get("metric_ids")
        if not isinstance(raw_metrics, Sequence) or isinstance(raw_metrics, (str, bytes)):
            raise ConfigurationError("metric_ids must be a sequence.")
        raw_refuse = data.get("refuse_list") or ()
        if not isinstance(raw_refuse, Sequence) or isinstance(raw_refuse, (str, bytes)):
            raise ConfigurationError("refuse_list must be a sequence.")
        raw_plan = data.get("seed_plan")
        if not isinstance(raw_plan, Mapping):
            raise ConfigurationError("seed_plan must be a mapping.")
        return cls(
            prereg_id=_as_str(data.get("prereg_id"), "prereg_id"),
            phenomenon=_as_str(data.get("phenomenon"), "phenomenon"),
            metric_ids=tuple(str(m) for m in raw_metrics),
            dual_null_required=bool(data.get("dual_null_required", False)),
            seed_plan=SeedPlanSpec.from_dict(raw_plan),
            ci_plan=str(data.get("ci_plan") or "bootstrap_percentile_or_normal_approx"),
            refuse_list=tuple(str(r) for r in raw_refuse),
            planned_claim_ceiling=str(
                data.get("planned_claim_ceiling") or "runtime_observation"
            ),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class HostParasiteMetricSummary:
    """Refuse-safe observation summary derived from hook meters."""

    summary_id: str
    claim_role: str
    metrics: Mapping[str, float]
    meter_digest: str
    prereg_digest: str | None
    science_grade: bool
    ablation_preset: str
    labels: Mapping[str, str]
    digest: str = ""
    red_queen_proved: bool = False
    raises_claim_ladder: bool = False

    def __post_init__(self) -> None:
        sid = _as_str(self.summary_id, "summary_id")
        role = _as_str(self.claim_role, "claim_role").lower()
        if role not in {"primary", "exploratory", "smoke"}:
            raise ConfigurationError("claim_role must be primary, exploratory, or smoke.")
        if self.red_queen_proved:
            raise ConfigurationError("MetricSummary refuses red_queen_proved=True.")
        if self.raises_claim_ladder:
            raise ConfigurationError("MetricSummary refuses raises_claim_ladder=True.")
        metrics: dict[str, float] = {}
        if not isinstance(self.metrics, Mapping):
            raise ConfigurationError("metrics must be a mapping.")
        for key, value in self.metrics.items():
            k = _as_str(key, "metric_key")
            if k not in METRIC_IDS:
                raise ConfigurationError(f"unknown metric_id: {k!r}")
            metrics[k] = float(require_finite_float(k, value))
        labels = {
            _as_str(k, "label_key"): _as_str(v, "label_value", allow_empty=True)
            for k, v in dict(self.labels).items()
        }
        science = _as_bool(self.science_grade, "science_grade")
        if role == "smoke" and science:
            raise ConfigurationError("smoke claim_role cannot be science_grade.")
        if role == "primary" and not science:
            # primary may still be non-science if seed plan is incomplete — allow False
            pass
        object.__setattr__(self, "summary_id", sid)
        object.__setattr__(self, "claim_role", role)
        object.__setattr__(self, "metrics", dict(sorted(metrics.items())))
        object.__setattr__(self, "labels", dict(sorted(labels.items())))
        object.__setattr__(self, "science_grade", science)
        object.__setattr__(self, "ablation_preset", _as_str(self.ablation_preset, "ablation_preset"))
        object.__setattr__(
            self, "meter_digest", _as_str(self.meter_digest, "meter_digest")
        )
        if self.prereg_digest is not None:
            object.__setattr__(
                self, "prereg_digest", _as_str(self.prereg_digest, "prereg_digest")
            )
        object.__setattr__(self, "red_queen_proved", False)
        object.__setattr__(self, "raises_claim_ladder", False)
        computed = canonical_digest(self._body(), prefix="hp_metric_sum")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "HostParasiteMetricSummary"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SUMMARY_SCHEMA,
            "summary_id": self.summary_id,
            "claim_role": self.claim_role,
            "metrics": dict(self.metrics),
            "meter_digest": self.meter_digest,
            "prereg_digest": self.prereg_digest,
            "science_grade": self.science_grade,
            "ablation_preset": self.ablation_preset,
            "labels": dict(self.labels),
            "red_queen_proved": False,
            "raises_claim_ladder": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def _require_primary_dual_null(
    *,
    claim_role: str,
    prereg: HostParasitePreregSpec | None,
    ablation_preset: str,
) -> None:
    if claim_role != "primary":
        return
    if prereg is None:
        raise ConfigurationError("primary metric summary requires an attached prereg.")
    if prereg.seed_plan.smoke_only:
        raise ConfigurationError("primary metric summary refuses smoke_only seed plans.")
    if not prereg.dual_null_required:
        raise ConfigurationError(
            "primary metric summary requires prereg.dual_null_required=True."
        )
    if ablation_preset != "dual_null":
        raise ConfigurationError(
            "primary metric summary requires ablation_preset='dual_null'."
        )


def build_metric_summary(
    *,
    summary_id: str,
    meter: HookMeterSnapshot,
    census: Mapping[str, int],
    ablation_preset: str,
    prereg: HostParasitePreregSpec | None = None,
    claim_role: str = "exploratory",
    unique_payloads: int = 0,
    labels: Mapping[str, str] | None = None,
) -> HostParasiteMetricSummary:
    """Build a refuse-safe summary from a HookMeter snapshot + role census."""

    role = _as_str(claim_role, "claim_role").lower()
    _require_primary_dual_null(
        claim_role=role, prereg=prereg, ablation_preset=ablation_preset
    )
    primary = int(census.get("primary", 0))
    secondary = int(census.get("secondary", 0))
    hooks = meter.hook_counts
    related = meter.related_counts
    totals = meter.related_totals
    occ = int(related.get("attach_occupancy", 0))
    cap = int(related.get("attach_capacity", 0))
    prevalence = (float(occ) / float(cap)) if cap > 0 else 0.0
    success = int(related.get("contact_success", 0))
    fail = int(related.get("contact_fail", 0))
    attempts = success + fail
    contact_rate = (float(success) / float(attempts)) if attempts > 0 else 0.0
    metrics = {
        "role_density_primary": float(primary),
        "role_density_secondary": float(secondary),
        "attach_prevalence": prevalence,
        "coupling_total": float(totals.get("coupling_total", 0.0)),
        "contact_success_rate": contact_rate,
        "hook_birth_count": float(hooks.get("on_birth", 0)),
        "hook_death_count": float(hooks.get("on_death", 0)),
        "hook_contact_count": float(hooks.get("on_contact", 0)),
        "hook_resource_count": float(hooks.get("on_resource", 0)),
        "diversity_proxy_unique_payloads": float(
            _as_int(unique_payloads, "unique_payloads", minimum=0)
        ),
    }
    # Filter to prereg metric_ids when present.
    if prereg is not None:
        metrics = {k: metrics[k] for k in prereg.metric_ids if k in metrics}
    science = bool(
        prereg is not None
        and not prereg.seed_plan.smoke_only
        and len(prereg.seed_plan.seeds) >= prereg.seed_plan.min_seeds
        and role == "primary"
    )
    if role == "smoke":
        science = False
    return HostParasiteMetricSummary(
        summary_id=summary_id,
        claim_role=role,
        metrics=metrics,
        meter_digest=meter.digest,
        prereg_digest=None if prereg is None else prereg.digest,
        science_grade=science,
        ablation_preset=ablation_preset,
        labels=dict(labels or {}),
    )


__all__ = [
    "METRIC_IDS",
    "SCHEMA_VERSION",
    "SCIENCE_MIN_SEEDS",
    "SUMMARY_SCHEMA",
    "HostParasiteMetricSummary",
    "HostParasitePreregSpec",
    "SeedPlanSpec",
    "build_metric_summary",
]
