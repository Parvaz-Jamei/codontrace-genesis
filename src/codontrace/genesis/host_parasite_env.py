"""Optional host–parasite environment helpers outside the engine core.

Fortuna / Zaman-inspired digital rules for *optional* campaign wiring:

- task-overlap infection eligibility
- one parasite seat per host
- horizontal injection into an empty seat
- configurable CPU-steal fraction (literature default analogy ~0.8)

This module does **not** modify ``engine.py`` tick semantics and does not
certify vaccines, antivirals, phage therapy, epidemics, BSL, CRISPR identity,
or Red Queen dynamics. Scores produced here are digital-scope outcomes for
ClaimGate labeling, not wet-lab validity.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

DEFAULT_STEAL_FRACTION = 0.8
_TRANSMISSION_MODES = frozenset({"horizontal", "vertical", "mixed"})
_SPATIAL_MODES = frozenset({"well_mixed", "local_neighborhood"})
_NULL_KINDS = frozenset({"none", "content_null", "structure_null", "dual_null"})


def _finite_unit_interval(name: str, value: float) -> float:
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ConfigurationError(f"{name} must be finite.")
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _finite_signed_unit(name: str, value: float) -> float:
    """Validate interaction value in [-1, +1] (antagonism → mutualism)."""

    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ConfigurationError(f"{name} must be finite.")
    if number < -1.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [-1, +1].")
    return number


def _task_set(raw: Sequence[str], field: str) -> frozenset[str]:
    if isinstance(raw, (str, bytes)):
        raise ConfigurationError(f"{field} must be a sequence of task names.")
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ConfigurationError(f"{field}[{index}] must be a non-empty string.")
        name = item.strip().lower()
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return frozenset(out)


@dataclass(frozen=True, slots=True)
class HostState:
    """Digital host seat: task repertoire plus at most one parasite."""

    host_id: str
    tasks: frozenset[str]
    parasite_id: str | None = None
    parasite_tasks: frozenset[str] = frozenset()
    parasite_payload: tuple[int, ...] = ()
    row: int | None = None
    col: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "host_id": self.host_id,
            "tasks": sorted(self.tasks),
            "parasite_id": self.parasite_id,
            "parasite_tasks": sorted(self.parasite_tasks),
            "parasite_payload": list(self.parasite_payload),
            "occupied": self.parasite_id is not None,
            "row": self.row,
            "col": self.col,
        }


@dataclass(frozen=True, slots=True)
class InfectionAttempt:
    """Record of one eligibility / inject attempt."""

    host_id: str
    parasite_id: str
    eligible: bool
    injected: bool
    reason: str
    overlap_tasks: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "host_id": self.host_id,
            "parasite_id": self.parasite_id,
            "eligible": self.eligible,
            "injected": self.injected,
            "reason": self.reason,
            "overlap_tasks": list(self.overlap_tasks),
        }


@dataclass(frozen=True, slots=True)
class DualNullTemplate:
    """Campaign template: content-null × structure-null controls.

    Content-null destroys parasite payload while preserving seats / overlap.
    Structure-null breaks task-overlap eligibility while optionally preserving
    payload bytes. Dual-null applies both. None of these prove Red Queen
    dynamics or clinical effects.
    """

    kind: str
    content_null: bool
    structure_null: bool
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "host_parasite_dual_null_template_v1",
            "kind": self.kind,
            "content_null": self.content_null,
            "structure_null": self.structure_null,
            "description": self.description,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
        }


def dual_null_template(kind: str = "dual_null") -> DualNullTemplate:
    """Return a named dual-null / single-null template."""

    if not isinstance(kind, str) or not kind.strip():
        raise ConfigurationError("dual null kind must be a non-empty string.")
    key = kind.strip().lower()
    if key not in _NULL_KINDS:
        raise ConfigurationError(f"dual null kind must be one of {sorted(_NULL_KINDS)}.")
    content = key in {"content_null", "dual_null"}
    structure = key in {"structure_null", "dual_null"}
    descriptions = {
        "none": "No null control; interaction and payload remain as declared.",
        "content_null": "Replace parasite payload with empty content; keep overlap seats.",
        "structure_null": "Break task-overlap eligibility; payload may remain.",
        "dual_null": "Apply content-null and structure-null together.",
    }
    return DualNullTemplate(key, content, structure, descriptions[key])


@dataclass(slots=True)
class HostParasiteEnv:
    """Optional env outside engine core for digital host–parasite wiring."""

    steal_fraction: float = DEFAULT_STEAL_FRACTION
    transmission_mode: str = "horizontal"
    null_template: DualNullTemplate = field(default_factory=lambda: dual_null_template("none"))
    hosts: dict[str, HostState] = field(default_factory=dict)
    attempts: list[InfectionAttempt] = field(default_factory=list)
    claim_ceiling: str = "runtime_observation"
    spatial_mode: str = "well_mixed"
    grid_rows: int = 1
    grid_cols: int = 1
    vertical_transmission_probability: float = 0.0
    resource_productivity: float = 1.0
    interaction_value: float = -1.0
    replication_events: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.steal_fraction = _finite_unit_interval("steal_fraction", self.steal_fraction)
        mode = self.transmission_mode.strip().lower()
        if mode not in _TRANSMISSION_MODES:
            raise ConfigurationError(
                f"transmission_mode must be one of {sorted(_TRANSMISSION_MODES)}."
            )
        self.transmission_mode = mode
        if self.claim_ceiling.strip().lower() != "runtime_observation":
            raise ConfigurationError(
                "HostParasiteEnv claim_ceiling is fixed at runtime_observation."
            )
        self.claim_ceiling = "runtime_observation"
        spatial = self.spatial_mode.strip().lower()
        if spatial not in _SPATIAL_MODES:
            raise ConfigurationError(
                f"spatial_mode must be one of {sorted(_SPATIAL_MODES)}."
            )
        self.spatial_mode = spatial
        if isinstance(self.grid_rows, bool) or not isinstance(self.grid_rows, int) or self.grid_rows < 1:
            raise ConfigurationError("grid_rows must be a positive int.")
        if isinstance(self.grid_cols, bool) or not isinstance(self.grid_cols, int) or self.grid_cols < 1:
            raise ConfigurationError("grid_cols must be a positive int.")
        self.vertical_transmission_probability = _finite_unit_interval(
            "vertical_transmission_probability", self.vertical_transmission_probability
        )
        self.interaction_value = _finite_signed_unit(
            "interaction_value", self.interaction_value
        )
        prod = float(self.resource_productivity)
        if prod != prod or prod in (float("inf"), float("-inf")) or prod <= 0.0:
            raise ConfigurationError("resource_productivity must be a finite value > 0.")
        self.resource_productivity = prod

    def add_host(
        self,
        host_id: str,
        tasks: Sequence[str],
        *,
        row: int | None = None,
        col: int | None = None,
    ) -> HostState:
        if not isinstance(host_id, str) or not host_id.strip():
            raise ConfigurationError("host_id is required.")
        key = host_id.strip()
        if key in self.hosts:
            raise ConfigurationError(f"host {key!r} already exists.")
        task_set = _task_set(tasks, "tasks")
        if not task_set:
            raise ConfigurationError("host tasks must contain at least one task.")
        if self.spatial_mode == "local_neighborhood":
            if row is None or col is None:
                raise ConfigurationError(
                    "local_neighborhood spatial_mode requires row and col on add_host."
                )
            if isinstance(row, bool) or not isinstance(row, int) or row < 0 or row >= self.grid_rows:
                raise ConfigurationError(f"row must be in [0, {self.grid_rows}).")
            if isinstance(col, bool) or not isinstance(col, int) or col < 0 or col >= self.grid_cols:
                raise ConfigurationError(f"col must be in [0, {self.grid_cols}).")
            for existing in self.hosts.values():
                if existing.row == row and existing.col == col:
                    raise ConfigurationError(
                        f"grid seat ({row}, {col}) already occupied by {existing.host_id!r}."
                    )
        elif row is not None or col is not None:
            if row is None or col is None:
                raise ConfigurationError("row and col must be provided together.")
            if isinstance(row, bool) or not isinstance(row, int) or row < 0:
                raise ConfigurationError("row must be a non-negative int.")
            if isinstance(col, bool) or not isinstance(col, int) or col < 0:
                raise ConfigurationError("col must be a non-negative int.")
        state = HostState(host_id=key, tasks=task_set, row=row, col=col)
        self.hosts[key] = state
        return state

    def infection_eligible(
        self, host_tasks: Sequence[str], parasite_tasks: Sequence[str]
    ) -> tuple[bool, tuple[str, ...]]:
        """Task-overlap rule (Fortuna et al. 2021 analogy).

        Structure-null forces ineligibility regardless of overlap.
        """

        if self.null_template.structure_null:
            return False, ()
        host = _task_set(host_tasks, "host_tasks")
        parasite = _task_set(parasite_tasks, "parasite_tasks")
        overlap = tuple(sorted(host & parasite))
        return bool(overlap), overlap

    def _payload(self, payload: Sequence[int]) -> tuple[int, ...]:
        if self.null_template.content_null:
            return ()
        out: list[int] = []
        for index, item in enumerate(payload):
            if isinstance(item, bool) or not isinstance(item, int):
                raise ConfigurationError(f"payload[{index}] must be an int.")
            out.append(item)
        return tuple(out)


    def seed_parasite_seat(
        self,
        *,
        host_id: str,
        parasite_id: str,
        parasite_tasks: Sequence[str],
        payload: Sequence[int] = (),
    ) -> HostState:
        """Setup-only seat occupation for vertical-only assays.

        Bypasses transmission_mode gates so vertical-only campaigns can start
        from an occupied parent before replication. Does not count as a
        horizontal infection attempt and does not raise claim ceilings.
        """

        if host_id not in self.hosts:
            raise ConfigurationError(f"unknown host {host_id!r}.")
        if not isinstance(parasite_id, str) or not parasite_id.strip():
            raise ConfigurationError("parasite_id is required.")
        pid = parasite_id.strip()
        if pid == host_id:
            raise ConfigurationError("parasite_id must differ from host_id.")
        host = self.hosts[host_id]
        if host.parasite_id is not None:
            raise ConfigurationError(f"host {host_id!r} seat already occupied.")
        if self.null_template.structure_null:
            raise ConfigurationError("structure_null blocks seed_parasite_seat.")
        eligible, overlap = self.infection_eligible(sorted(host.tasks), parasite_tasks)
        if not eligible:
            raise ConfigurationError(
                "seed_parasite_seat requires task overlap with the host."
            )
        updated = replace(
            host,
            parasite_id=pid,
            parasite_tasks=_task_set(parasite_tasks, "parasite_tasks"),
            parasite_payload=self._payload(payload),
        )
        self.hosts[host_id] = updated
        return updated

    def try_horizontal_inject(
        self,
        *,
        host_id: str,
        parasite_id: str,
        parasite_tasks: Sequence[str],
        payload: Sequence[int] = (),
    ) -> InfectionAttempt:
        """Inject into an empty seat when eligible; one seat per host."""

        if self.transmission_mode == "vertical":
            # Vertical-only mode refuses horizontal inject (Symbulation continuum knob).
            attempt = InfectionAttempt(
                host_id=host_id,
                parasite_id=parasite_id,
                eligible=False,
                injected=False,
                reason="transmission_mode_vertical_blocks_horizontal_inject",
                overlap_tasks=(),
            )
            self.attempts.append(attempt)
            return attempt
        if not isinstance(parasite_id, str) or not parasite_id.strip():
            raise ConfigurationError("parasite_id is required.")
        pid = parasite_id.strip()
        if host_id not in self.hosts:
            raise ConfigurationError(f"unknown host {host_id!r}.")
        if pid == host_id:
            raise ConfigurationError("parasite_id must differ from host_id.")
        host = self.hosts[host_id]
        eligible, overlap = self.infection_eligible(sorted(host.tasks), parasite_tasks)
        if host.parasite_id is not None:
            attempt = InfectionAttempt(
                host_id=host_id,
                parasite_id=parasite_id.strip(),
                eligible=eligible,
                injected=False,
                reason="seat_occupied",
                overlap_tasks=overlap,
            )
            self.attempts.append(attempt)
            return attempt
        if not eligible:
            reason = (
                "structure_null_blocks_overlap"
                if self.null_template.structure_null
                else "no_task_overlap"
            )
            attempt = InfectionAttempt(
                host_id=host_id,
                parasite_id=parasite_id.strip(),
                eligible=False,
                injected=False,
                reason=reason,
                overlap_tasks=overlap,
            )
            self.attempts.append(attempt)
            return attempt
        resolved_payload = self._payload(payload)
        updated = replace(
            host,
            parasite_id=parasite_id.strip(),
            parasite_tasks=_task_set(parasite_tasks, "parasite_tasks"),
            parasite_payload=resolved_payload,
        )
        self.hosts[host_id] = updated
        attempt = InfectionAttempt(
            host_id=host_id,
            parasite_id=parasite_id.strip(),
            eligible=True,
            injected=True,
            reason="injected",
            overlap_tasks=overlap,
        )
        self.attempts.append(attempt)
        return attempt

    def host_retained_cpu(self, host_id: str) -> float:
        """Host digital outcome after interaction-value–modulated steal/benefit.

        ``interaction_value`` in [-1, +1] spans antagonism → mutualism
        (Symbulation / Gupta–Vostinar continuum analogy). Magnitude is
        ``steal_fraction / resource_productivity``. Negative values subtract
        from the uninfected baseline 1.0; positive values add (mutualism
        benefit). Result is clipped to [0, 2]. Mutualism is not a success
        narrative and does not raise claim ceilings.

        Content-null occupied seats transfer nothing (structure without
        payload drawdown/benefit).
        """

        if host_id not in self.hosts:
            raise ConfigurationError(f"unknown host {host_id!r}.")
        host = self.hosts[host_id]
        if host.parasite_id is None:
            return 1.0
        # Content-null infection still occupies the seat but transfers nothing:
        # payload-dependent drawdown/benefit is gone while structure remains.
        if self.null_template.content_null and not host.parasite_payload:
            return 1.0
        magnitude = min(1.0, self.steal_fraction / self.resource_productivity)
        delta = self.interaction_value * magnitude
        retained = 1.0 + delta
        if retained < 0.0:
            retained = 0.0
        if retained > 2.0:
            retained = 2.0
        return round(retained, 10)

    def population_outcome_score(self) -> float:
        """Digital-scope score: mean retained CPU across hosts.

        Used only to show that null templates change outcomes relative to the
        intact interaction. Not a fitness certificate.
        """

        if not self.hosts:
            raise ConfigurationError("population_outcome_score needs at least one host.")
        total = sum(self.host_retained_cpu(host_id) for host_id in self.hosts)
        return round(total / len(self.hosts), 10)


    def _chebyshev_distance(self, a: HostState, b: HostState) -> int | None:
        if a.row is None or a.col is None or b.row is None or b.col is None:
            return None
        return max(abs(a.row - b.row), abs(a.col - b.col))

    def neighbors(self, host_id: str) -> tuple[str, ...]:
        """Return hosts within Chebyshev distance 1 (local neighborhood)."""

        if host_id not in self.hosts:
            raise ConfigurationError(f"unknown host {host_id!r}.")
        if self.spatial_mode != "local_neighborhood":
            return tuple(sorted(h for h in self.hosts if h != host_id))
        origin = self.hosts[host_id]
        out: list[str] = []
        for other_id, other in self.hosts.items():
            if other_id == host_id:
                continue
            dist = self._chebyshev_distance(origin, other)
            if dist is not None and dist <= 1:
                out.append(other_id)
        return tuple(sorted(out))

    def try_local_inject(
        self,
        *,
        source_host_id: str,
        target_host_id: str,
        parasite_id: str,
        parasite_tasks: Sequence[str],
        payload: Sequence[int] = (),
    ) -> InfectionAttempt:
        """Neighborhood-restricted inject (Symbulation / Brockhurst mixing knob).

        In ``local_neighborhood`` mode, target must be within Chebyshev distance
        1 of source. In ``well_mixed`` mode, any target is allowed (distance check
        skipped). Vertical-only transmission still blocks horizontal inject.
        """

        if source_host_id not in self.hosts:
            raise ConfigurationError(f"unknown source host {source_host_id!r}.")
        if target_host_id not in self.hosts:
            raise ConfigurationError(f"unknown target host {target_host_id!r}.")
        if source_host_id == target_host_id:
            raise ConfigurationError("source_host_id must differ from target_host_id.")
        if self.spatial_mode == "local_neighborhood":
            source = self.hosts[source_host_id]
            target = self.hosts[target_host_id]
            dist = self._chebyshev_distance(source, target)
            if dist is None or dist > 1:
                attempt = InfectionAttempt(
                    host_id=target_host_id,
                    parasite_id=parasite_id,
                    eligible=False,
                    injected=False,
                    reason="outside_local_neighborhood",
                    overlap_tasks=(),
                )
                self.attempts.append(attempt)
                return attempt
        return self.try_horizontal_inject(
            host_id=target_host_id,
            parasite_id=parasite_id,
            parasite_tasks=parasite_tasks,
            payload=payload,
        )

    def replicate_host(
        self,
        *,
        parent_id: str,
        child_id: str,
        draw: float,
        child_row: int | None = None,
        child_col: int | None = None,
    ) -> HostState:
        """Replicate a host; optionally transmit the parasite vertically.

        ``draw`` is a deterministic unit-interval decision value supplied by the
        caller (campaign seed stream). Vertical transmission occurs when
        transmission_mode is ``vertical`` or ``mixed``, the parent is occupied,
        and ``draw < vertical_transmission_probability``. Mixed mode keeps
        horizontal inject available as well — it does not leave vertical as
        ``not_implemented``.
        """

        if parent_id not in self.hosts:
            raise ConfigurationError(f"unknown parent host {parent_id!r}.")
        draw_u = _finite_unit_interval("draw", draw)
        parent = self.hosts[parent_id]
        child = self.add_host(
            child_id,
            sorted(parent.tasks),
            row=child_row,
            col=child_col,
        )
        transmitted = False
        reason = "no_vertical_transmission"
        if self.transmission_mode in {"vertical", "mixed"} and parent.parasite_id is not None:
            if draw_u < self.vertical_transmission_probability:
                if self.null_template.structure_null:
                    reason = "structure_null_blocks_vertical"
                else:
                    payload = () if self.null_template.content_null else parent.parasite_payload
                    child = replace(
                        child,
                        parasite_id=f"{parent.parasite_id}::v",
                        parasite_tasks=parent.parasite_tasks,
                        parasite_payload=payload,
                    )
                    self.hosts[child_id] = child
                    transmitted = True
                    reason = "vertical_transmitted"
            else:
                reason = "vertical_draw_missed"
        elif self.transmission_mode == "horizontal":
            reason = "horizontal_mode_skips_vertical"
        event = {
            "parent_id": parent_id,
            "child_id": child_id,
            "draw": draw_u,
            "transmitted": transmitted,
            "reason": reason,
            "transmission_mode": self.transmission_mode,
        }
        self.replication_events.append(event)
        return child

    def snapshot(self) -> dict[str, object]:
        if self.transmission_mode == "horizontal":
            vertical_component = "not_applicable_horizontal_only"
        elif self.transmission_mode == "vertical":
            vertical_component = "vertical_mode_enabled"
        else:
            # Mode advertises both pathways; replication_events record whether
            # vertical transmission actually fired in this run.
            vertical_component = "mixed_mode_enabled"
        body: dict[str, object] = {
            "schema": "host_parasite_env_snapshot_v1",
            "steal_fraction": self.steal_fraction,
            "transmission_mode": self.transmission_mode,
            "vertical_component": vertical_component,
            "spatial_mode": self.spatial_mode,
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "vertical_transmission_probability": self.vertical_transmission_probability,
            "resource_productivity": self.resource_productivity,
            "interaction_value": self.interaction_value,
            "interaction_continuum": "antagonism_to_mutualism",
            "mutualism_equals_success": False,
            "null_template": self.null_template.to_dict(),
            "claim_ceiling": self.claim_ceiling,
            "hosts": [self.hosts[key].to_dict() for key in sorted(self.hosts)],
            "attempts": [item.to_dict() for item in self.attempts],
            "replication_events": list(self.replication_events),
            "population_outcome_score": (
                self.population_outcome_score() if self.hosts else None
            ),
            "engine_infection_physics": "not_in_engine_core",
            "raises_claim_ladder": False,
            "red_queen_proved": False,
        }
        body["digest"] = canonical_digest(
            canonical_payload({key: body[key] for key in body if key != "digest"})
        )
        return body


def run_dual_null_contrast(
    *,
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    payload: Sequence[int],
    steal_fraction: float = DEFAULT_STEAL_FRACTION,
) -> dict[str, object]:
    """Run intact / content-null / structure-null / dual-null digital contrasts.

    Returns scores that must differ when nulls bite, showing the template is
    not a no-op label. Requires task overlap so the intact arm can inject;
    otherwise the contrast cannot demonstrate a null effect.
    """

    probe = HostParasiteEnv(steal_fraction=steal_fraction)
    eligible, overlap = probe.infection_eligible(host_tasks, parasite_tasks)
    if not eligible:
        raise ConfigurationError(
            "run_dual_null_contrast requires task overlap so the intact arm can inject."
        )
    scores: dict[str, float] = {}
    injected: dict[str, bool] = {}
    reasons: dict[str, str] = {}
    snapshots: dict[str, Mapping[str, object]] = {}
    for kind in ("none", "content_null", "structure_null", "dual_null"):
        env = HostParasiteEnv(
            steal_fraction=steal_fraction,
            null_template=dual_null_template(kind),
        )
        env.add_host("H0", host_tasks)
        attempt = env.try_horizontal_inject(
            host_id="H0",
            parasite_id="P0",
            parasite_tasks=parasite_tasks,
            payload=payload,
        )
        scores[kind] = env.population_outcome_score()
        injected[kind] = attempt.injected
        reasons[kind] = attempt.reason
        snapshots[kind] = env.snapshot()
    score_changed = len(set(scores.values())) > 1
    inject_changed = len(set(injected.values())) > 1
    return {
        "schema": "host_parasite_dual_null_contrast_v1",
        "scores": scores,
        "injected": injected,
        "reasons": reasons,
        "snapshots": {key: dict(value) for key, value in snapshots.items()},
        "nulls_change_outcomes": score_changed or inject_changed,
        "nulls_change_scores": score_changed,
        "nulls_change_injection": inject_changed,
        "raises_claim_ladder": False,
        "red_queen_proved": False,
    }
