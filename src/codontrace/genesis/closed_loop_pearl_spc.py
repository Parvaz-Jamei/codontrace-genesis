"""Pearl-pair and debit-stream gates: Pearl-pair knockouts and debit-stream capability gates.

Sealed confirmatory seeds 101–108 used ``frozen`` and ``absent`` under the
P7 prereg and returned an honest FAIL (0/8 separate, 0/8 mixed) at tip
``610f46f``. That prereg is not rewritten here.

This module is additive for *new* campaign cells. It wires the pure Pearl
pair ``frozen`` (update off, debit on) and ``costless`` (debit off, update
on) as the intervention knockouts, and keeps ``absent`` as antagonist
removal — not a pure zero-debit cut (Pearl, Biometrika 82:669–688, 1995,
doi:10.1093/biomet/82.4.669).

Optional Shewhart / CUSUM / observer-residual predicates gate whether a
debit-backed cycle *clause* may hold. They are fail-closed, stay at
``runtime_observation``, and never set ``red_queen_proved`` or
``biological_red_queen_proved``. SPC cannot grant a Red Queen claim
(Shewhart 1931; Western Electric rules; Kalman 1960 residual honesty as a
ledger check, not a second world).

Frequency clocks, Slowinski invasion, MFA, CRN, R2R, ATP carryover, and
queue-timing stacks are out of scope. ``engine.py`` is untouched.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import (
    debit_backed_cycle,
    holling_type2_cost,
)

CLAIM_CEILING = "runtime_observation"
XF_WP1_REVISION = "xf-wp1-20260926"

# Passage taxonomy. Names are distinct; aliases are refused.
PASSAGE_COEVOLVE = "coevolve"
PASSAGE_FROZEN = "frozen"
PASSAGE_COSTLESS = "costless"
PASSAGE_ABSENT = "absent"

PEARL_KNOCKOUTS = frozenset({PASSAGE_FROZEN, PASSAGE_COSTLESS})
ANTAGONIST_REMOVAL = frozenset({PASSAGE_ABSENT})
ALL_PASSAGES = frozenset(
    {PASSAGE_COEVOLVE, PASSAGE_FROZEN, PASSAGE_COSTLESS, PASSAGE_ABSENT}
)

PASSAGE_MEANING = {
    PASSAGE_COEVOLVE: "update on, debit on",
    PASSAGE_FROZEN: "update off, debit on (Pearl freeze / hold type-update)",
    PASSAGE_COSTLESS: "update on, debit off (Pearl zero-debit / do(debit=0))",
    PASSAGE_ABSENT: "antagonist removal; not a pure zero-debit intervention",
}


def pearl_knockout_passages() -> tuple[str, str]:
    """Pure Pearl pair for new confirmatory / WP-RQ-1 cells."""

    return (PASSAGE_FROZEN, PASSAGE_COSTLESS)


def antagonist_removal_passage() -> str:
    """Overloaded removal arm. Not interchangeable with ``costless``."""

    return PASSAGE_ABSENT


def assert_passage_taxonomy(*, refuse_aliases: bool = True) -> dict[str, str]:
    """Document that ``absent``, ``frozen``, and ``costless`` are not aliases.

    Returns the meaning table. Raises if a caller tries to collapse the
    taxonomy (for example by treating ``absent`` as ``costless``).
    """

    if not refuse_aliases:
        raise ConfigurationError("refuse_aliases must stay true; aliases are forbidden")
    frozen_m = PASSAGE_MEANING[PASSAGE_FROZEN]
    costless_m = PASSAGE_MEANING[PASSAGE_COSTLESS]
    absent_m = PASSAGE_MEANING[PASSAGE_ABSENT]
    if frozen_m == costless_m or frozen_m == absent_m or costless_m == absent_m:
        raise ConfigurationError("passage meanings must stay distinct")
    if PASSAGE_ABSENT in PEARL_KNOCKOUTS:
        raise ConfigurationError("absent must not sit in the Pearl knockout set")
    if PASSAGE_FROZEN == PASSAGE_COSTLESS or PASSAGE_ABSENT == PASSAGE_COSTLESS:
        raise ConfigurationError("passage names must stay distinct")
    return dict(PASSAGE_MEANING)


def require_pearl_knockout(passage: str) -> str:
    """Accept only ``frozen`` or ``costless`` as a Pearl knockout label."""

    if not isinstance(passage, str) or not passage.strip():
        raise ConfigurationError("passage must be a non-empty string")
    name = passage.strip().lower()
    if name == PASSAGE_ABSENT:
        raise ConfigurationError(
            "absent is antagonist removal, not a pure Pearl zero-debit knockout"
        )
    if name not in PEARL_KNOCKOUTS:
        raise ConfigurationError(
            f"Pearl knockout must be {PASSAGE_FROZEN!r} or {PASSAGE_COSTLESS!r}, got {passage!r}"
        )
    return name


def _as_float_series(values: Sequence[object] | Iterable[object], *, name: str) -> tuple[float, ...]:
    series = tuple(values) if not isinstance(values, tuple) else values
    out: list[float] = []
    for index, raw in enumerate(series):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConfigurationError(f"{name}[{index}] must be a finite number")
        number = float(raw)
        if not math.isfinite(number):
            raise ConfigurationError(f"{name}[{index}] must be a finite number")
        out.append(number)
    return tuple(out)


def shewhart_in_control(
    match_debits: Sequence[object],
    *,
    center: float,
    sigma: float,
    limit_sigma: float = 3.0,
) -> bool:
    """Shewhart X-chart in-control predicate on the match-debit series.

    Fail-closed: empty series, non-finite limits, or ``sigma <= 0`` refuse
    in-control. A point outside ``center ± limit_sigma * sigma`` fails.
    Does not set any Red Queen flag.
    """

    series = _as_float_series(match_debits, name="match_debits")
    if not series:
        return False
    if isinstance(center, bool) or not isinstance(center, (int, float)):
        return False
    if isinstance(sigma, bool) or not isinstance(sigma, (int, float)):
        return False
    if isinstance(limit_sigma, bool) or not isinstance(limit_sigma, (int, float)):
        return False
    c = float(center)
    s = float(sigma)
    k = float(limit_sigma)
    if not math.isfinite(c) or not math.isfinite(s) or not math.isfinite(k):
        return False
    if s <= 0.0 or k <= 0.0:
        return False
    upper = c + k * s
    lower = c - k * s
    return all(lower <= value <= upper for value in series)


def cusum_onset_declared(
    match_debits: Sequence[object],
    *,
    reference: float,
    slack_k: float,
    decision_h: float,
) -> bool:
    """One-sided positive CUSUM onset on match debits.

    Fail-closed: empty series or non-positive ``decision_h`` / invalid
    ``slack_k`` refuse onset. Onset is declared only when the CUSUM
    crosses ``decision_h``. Does not name virulence thresholds from a
    development seed, and does not set any Red Queen flag.
    """

    series = _as_float_series(match_debits, name="match_debits")
    if not series:
        return False
    for label, raw in (
        ("reference", reference),
        ("slack_k", slack_k),
        ("decision_h", decision_h),
    ):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return False
        if not math.isfinite(float(raw)):
            return False
    ref = float(reference)
    k = float(slack_k)
    h = float(decision_h)
    if h <= 0.0 or k < 0.0:
        return False
    s_plus = 0.0
    for value in series:
        s_plus = max(0.0, s_plus + (value - ref) - k)
        if s_plus >= h:
            return True
    return False


def predicted_match_cost(
    *,
    virulence: float,
    type_count: int,
    specificity_weight: float = 1.0,
) -> float:
    """Predicted Holling type II cost × specificity weight (ledger check)."""

    if isinstance(specificity_weight, bool) or not isinstance(specificity_weight, (int, float)):
        raise ConfigurationError("specificity_weight must be a finite number")
    weight = float(specificity_weight)
    if not math.isfinite(weight) or weight < 0.0 or weight > 1.0:
        raise ConfigurationError("specificity_weight must be in [0, 1]")
    return holling_type2_cost(virulence, type_count) * weight


def observer_residual_coherent(
    realized: Sequence[object],
    predicted: Sequence[object],
    *,
    band: float,
) -> bool:
    """Ledger residual coherence: |realized − predicted| ≤ band each step.

    Fail-closed on length mismatch, empty series, or non-finite / negative
    band. Residual audits the ATP match-debit story; it is not a parallel
    population. Does not set any Red Queen flag.
    """

    real = _as_float_series(realized, name="realized")
    pred = _as_float_series(predicted, name="predicted")
    if not real or len(real) != len(pred):
        return False
    if isinstance(band, bool) or not isinstance(band, (int, float)):
        return False
    width = float(band)
    if not math.isfinite(width) or width < 0.0:
        return False
    return all(abs(r - p) <= width for r, p in zip(real, pred))


def debit_backed_cycle_capability(
    history: Sequence[Sequence[str]] | Sequence[tuple[str, ...]],
    match_debits: Sequence[object],
    *,
    require_shewhart: bool = False,
    shewhart_center: float | None = None,
    shewhart_sigma: float | None = None,
    shewhart_limit_sigma: float = 3.0,
    require_cusum_onset: bool = False,
    cusum_reference: float | None = None,
    cusum_slack_k: float | None = None,
    cusum_decision_h: float | None = None,
    require_observer: bool = False,
    predicted_debits: Sequence[object] | None = None,
    observer_band: float | None = None,
) -> bool:
    """``debit_backed_cycle`` plus optional fail-closed capability gates.

    Biological name-set + paid-return detection remains primary. SPC and
    residual clauses can only deny a cycle; they cannot invent one, and
    they never promote ``red_queen_proved``.
    """

    hist = tuple(tuple(state) for state in history)
    debits = _as_float_series(match_debits, name="match_debits")
    # debit_backed_cycle expects integer-like counts; coerce carefully.
    int_debits: list[int] = []
    for index, value in enumerate(debits):
        if abs(value - round(value)) > 1e-9:
            raise ConfigurationError(f"match_debits[{index}] must be an integer count")
        int_debits.append(int(round(value)))
    if not debit_backed_cycle(hist, tuple(int_debits)):
        return False
    if require_shewhart:
        if shewhart_center is None or shewhart_sigma is None:
            return False
        if not shewhart_in_control(
            debits,
            center=shewhart_center,
            sigma=shewhart_sigma,
            limit_sigma=shewhart_limit_sigma,
        ):
            return False
    if require_cusum_onset:
        if cusum_reference is None or cusum_slack_k is None or cusum_decision_h is None:
            return False
        if not cusum_onset_declared(
            debits,
            reference=cusum_reference,
            slack_k=cusum_slack_k,
            decision_h=cusum_decision_h,
        ):
            return False
    if require_observer:
        if predicted_debits is None or observer_band is None:
            return False
        if not observer_residual_coherent(
            debits, predicted_debits, band=observer_band
        ):
            return False
    return True


def pearl_pair_survival_gap_absent(
    *,
    frozen_outcross_extinct: bool,
    frozen_selfing_extinct: bool,
    costless_outcross_extinct: bool,
    costless_selfing_extinct: bool,
) -> bool:
    """True when the extinct/persist gap is absent under both Pearl knockouts.

    Gap means outcross alive and selfing extinct. Both ``frozen`` and
    ``costless`` must lack that gap for the knockout clause to hold.
    """

    for label, value in (
        ("frozen_outcross_extinct", frozen_outcross_extinct),
        ("frozen_selfing_extinct", frozen_selfing_extinct),
        ("costless_outcross_extinct", costless_outcross_extinct),
        ("costless_selfing_extinct", costless_selfing_extinct),
    ):
        if not isinstance(value, bool):
            raise ConfigurationError(f"{label} must be a bool")
    gap_frozen = (not frozen_outcross_extinct) and frozen_selfing_extinct
    gap_costless = (not costless_outcross_extinct) and costless_selfing_extinct
    return (not gap_frozen) and (not gap_costless)


@dataclass(frozen=True, slots=True)
class XfWp1ClauseReport:
    """Harness clause outcomes. Flags stay false; ceiling is observational."""

    pearl_taxonomy_ok: bool
    pearl_gap_absent: bool
    debit_backed_cycle_raw: bool
    debit_backed_cycle_gated: bool
    shewhart_in_control: bool | None
    cusum_onset: bool | None
    observer_coherent: bool | None
    red_queen_proved: bool
    biological_red_queen_proved: bool
    claim_ceiling: str
    revision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "pearl_taxonomy_ok": self.pearl_taxonomy_ok,
            "pearl_gap_absent": self.pearl_gap_absent,
            "debit_backed_cycle_raw": self.debit_backed_cycle_raw,
            "debit_backed_cycle_gated": self.debit_backed_cycle_gated,
            "shewhart_in_control": self.shewhart_in_control,
            "cusum_onset": self.cusum_onset,
            "observer_coherent": self.observer_coherent,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "claim_ceiling": self.claim_ceiling,
            "revision": self.revision,
            "pearl_knockouts": list(pearl_knockout_passages()),
            "antagonist_removal": antagonist_removal_passage(),
            "passage_meanings": assert_passage_taxonomy(),
        }


def evaluate_pearl_spc_clauses(
    *,
    history: Sequence[Sequence[str]] | Sequence[tuple[str, ...]],
    match_debits: Sequence[object],
    frozen_outcross_extinct: bool,
    frozen_selfing_extinct: bool,
    costless_outcross_extinct: bool,
    costless_selfing_extinct: bool,
    shewhart_center: float | None = None,
    shewhart_sigma: float | None = None,
    cusum_reference: float | None = None,
    cusum_slack_k: float | None = None,
    cusum_decision_h: float | None = None,
    predicted_debits: Sequence[object] | None = None,
    observer_band: float | None = None,
) -> XfWp1ClauseReport:
    """Record Pearl + capability clauses without promoting RQ flags.

    Optional SPC / residual inputs are evaluated when supplied; missing
    optional inputs leave the corresponding field ``None`` and do not
    open the gated cycle by themselves.
    """

    taxonomy_ok = True
    try:
        assert_passage_taxonomy()
    except ConfigurationError:
        taxonomy_ok = False
    gap_absent = pearl_pair_survival_gap_absent(
        frozen_outcross_extinct=frozen_outcross_extinct,
        frozen_selfing_extinct=frozen_selfing_extinct,
        costless_outcross_extinct=costless_outcross_extinct,
        costless_selfing_extinct=costless_selfing_extinct,
    )
    hist = tuple(tuple(state) for state in history)
    debits = _as_float_series(match_debits, name="match_debits")
    int_debits = tuple(int(round(v)) for v in debits)
    raw_cycle = bool(debit_backed_cycle(hist, int_debits)) if len(int_debits) == len(hist) else False

    shewhart: bool | None = None
    if shewhart_center is not None and shewhart_sigma is not None:
        shewhart = shewhart_in_control(
            debits, center=shewhart_center, sigma=shewhart_sigma
        )
    cusum: bool | None = None
    if (
        cusum_reference is not None
        and cusum_slack_k is not None
        and cusum_decision_h is not None
    ):
        cusum = cusum_onset_declared(
            debits,
            reference=cusum_reference,
            slack_k=cusum_slack_k,
            decision_h=cusum_decision_h,
        )
    observer: bool | None = None
    if predicted_debits is not None and observer_band is not None:
        observer = observer_residual_coherent(
            debits, predicted_debits, band=observer_band
        )

    gated = debit_backed_cycle_capability(
        hist,
        debits,
        require_shewhart=shewhart is not None,
        shewhart_center=shewhart_center,
        shewhart_sigma=shewhart_sigma,
        require_cusum_onset=cusum is not None,
        cusum_reference=cusum_reference,
        cusum_slack_k=cusum_slack_k,
        cusum_decision_h=cusum_decision_h,
        require_observer=observer is not None,
        predicted_debits=predicted_debits,
        observer_band=observer_band,
    )
    return XfWp1ClauseReport(
        pearl_taxonomy_ok=taxonomy_ok,
        pearl_gap_absent=gap_absent,
        debit_backed_cycle_raw=raw_cycle,
        debit_backed_cycle_gated=gated,
        shewhart_in_control=shewhart,
        cusum_onset=cusum,
        observer_coherent=observer,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        claim_ceiling=CLAIM_CEILING,
        revision=XF_WP1_REVISION,
    )


__all__ = [
    "ALL_PASSAGES",
    "ANTAGONIST_REMOVAL",
    "CLAIM_CEILING",
    "PASSAGE_ABSENT",
    "PASSAGE_COEVOLVE",
    "PASSAGE_COSTLESS",
    "PASSAGE_FROZEN",
    "PASSAGE_MEANING",
    "PEARL_KNOCKOUTS",
    "XF_WP1_REVISION",
    "XfWp1ClauseReport",
    "antagonist_removal_passage",
    "assert_passage_taxonomy",
    "cusum_onset_declared",
    "debit_backed_cycle_capability",
    "evaluate_pearl_spc_clauses",
    "observer_residual_coherent",
    "pearl_knockout_passages",
    "pearl_pair_survival_gap_absent",
    "predicted_match_cost",
    "require_pearl_knockout",
    "shewhart_in_control",
]
