"""Measurement definitions required before a discovery claim.

``genotype_set`` is presence of genome digests. That is the identity
quantity in this design. It is not abundance: class sizes can swap and
the set stays the same. Abundance is ``genotype_counts``.

The Red Queen barrier is absolute magnitude. It holds only while
``abs(score) < 0.20``. Sign is a separate question. A negative score
past 0.20 does not hold the barrier and does not accept the positive
direction. The locked synthetic score stays −0.148. This module does
not raise it and does not set ``red_queen_proved``.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from codontrace.errors import ConfigurationError

RQ_SYNTHETIC_SCORE = -0.148
RQ_ACCEPT_THRESHOLD = 0.20

# Presence set is the identity quantity. It is not the abundance estimand.
GENOTYPE_SET_IS_PRESENCE_ONLY = True
GENOTYPE_SET_IS_ABUNDANCE = False

PHASE_ORDER: tuple[str, ...] = (
    "search",
    "pre_build_rounds",
    "build",
    "post_build_critiques",
    "test",
    "result_readings",
)

# Lexical order is temporal only for this shape. Unpadded dates are rejected.
_PHASE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?$")


def _phase_date(value: object) -> str | None:
    text = str(value).strip()
    if _PHASE_DATE.fullmatch(text) is None:
        return None
    return text


def genotype_set(digests: Iterable[str]) -> frozenset[str]:
    """Presence of genome digests. Multiplicity is ignored on purpose."""

    return frozenset(str(item) for item in digests)


def genotype_counts(digests: Iterable[str]) -> dict[str, int]:
    """Abundance of each digest. Not the identity set."""

    counts = Counter(str(item) for item in digests)
    return {key: int(counts[key]) for key in sorted(counts)}


def same_genotype_set(
    left: Iterable[str],
    right: Iterable[str],
) -> bool:
    return genotype_set(left) == genotype_set(right)


def same_genotype_counts(
    left: Iterable[str],
    right: Iterable[str],
) -> bool:
    return genotype_counts(left) == genotype_counts(right)


def rq_magnitude(score: float) -> float:
    return abs(float(score))


def rq_barrier_holds(score: float = RQ_SYNTHETIC_SCORE) -> bool:
    """True only while ``abs(score)`` is strictly below the accept threshold.

    Direction is not part of this boolean. The preregistered sign of the
    swap-signal is ``S < 0`` (PREREG_V2, T9 floor 0.20). A positive score
    is the opposite sign. Neither crossing is a proof.
    """

    return rq_magnitude(score) < float(RQ_ACCEPT_THRESHOLD)


def rq_preregistered_direction_reaches_threshold(score: float) -> bool:
    """True when ``S <= -0.20``.

    That is the preregistered direction and the mechanism floor. It is not
    Red Queen proved, and it does not replace the delay, frozen-antagonist,
    or population controls.
    """

    return float(score) <= -float(RQ_ACCEPT_THRESHOLD)


def rq_positive_direction_reaches_threshold(score: float) -> bool:
    """True for ``S >= +0.20``.

    This is the opposite of the preregistered sign. It is not acceptance.
    """

    return float(score) >= float(RQ_ACCEPT_THRESHOLD)


RQ_REQUIRED_CONTROLS: tuple[str, ...] = (
    "delay_control",
    "frozen_antagonist_arm",
    "population_conditions",
)


def rq_controls_present(controls: object) -> bool:
    """Delay, frozen antagonist, and population conditions, each recorded true."""

    if not isinstance(controls, Mapping):
        return False
    return all(controls.get(name) is True for name in RQ_REQUIRED_CONTROLS)


def rq_claim_inputs_sufficient(score: float, controls: object = None) -> bool:
    """Arithmetic predicate on a supplied mapping. Not a record that arms ran.

    Still not a proof. ``red_queen_proved_from_score`` stays false. This
    codebase does not record the three controls; use ``rq_model_decision``.
    """

    return bool(
        (not rq_barrier_holds(score))
        and rq_preregistered_direction_reaches_threshold(score)
        and rq_controls_present(controls)
    )


# These three arms are not in this model. A caller dict cannot invent them.
RQ_MODEL_CONTROLS: dict[str, bool] = {
    "delay_control": False,
    "frozen_antagonist_arm": False,
    "population_conditions": False,
}


def rq_model_decision(score: float = RQ_SYNTHETIC_SCORE) -> dict[str, bool]:
    """Decision for this model. The controls are absent, so inputs are not sufficient.

    Crossing 0.20 in the preregistered direction is not Red Queen proved.
    The positive direction is not acceptance.
    """

    return {
        "barrier_holds": bool(rq_barrier_holds(score)),
        "preregistered_direction_reaches_threshold": bool(
            rq_preregistered_direction_reaches_threshold(score)
        ),
        "positive_direction_is_acceptance": False,
        "controls_recorded_in_model": False,
        "claim_inputs_sufficient": False,
        "red_queen_proved": False,
    }


def red_queen_proved_from_score(score: float = RQ_SYNTHETIC_SCORE) -> bool:
    """Threshold arithmetic is not a proof."""

    del score
    return False


def assert_record_not_a_discovery(record: Mapping[str, object]) -> None:
    """Refuse records that would read as a finished scientific claim."""

    if record.get("hypothesis_supported") is not False:
        raise ConfigurationError("hypothesis_supported must stay false.")
    if record.get("red_queen_proved") is not False:
        raise ConfigurationError("red_queen_proved must stay false.")
    if record.get("scientific_result") is True:
        raise ConfigurationError("this record is not a scientific result.")
    idea_raw = record.get("idea_id", -1)
    try:
        idea_id = int(idea_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        idea_id = -1
    if idea_id == 2 and record.get("hypothesis_test_eligible") is not False:
        raise ConfigurationError(
            "Idea 2 output is not a host-parasite hypothesis test."
        )
    if record.get("data_class") == "scaffold" and record.get("scientific_result") is not False:
        raise ConfigurationError("scaffold data must set scientific_result false.")


def _nonempty_texts(value: object, *, minimum: int) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    texts = [str(item).strip() for item in value]
    if len(texts) < minimum or any(not text for text in texts):
        return None
    return texts


def process_cycle_complete(record: Mapping[str, object]) -> bool:
    """True only for a dated, referenced phase trail. Text stubs are not enough.

    Requires five distinct pre-build rounds, two post-build notes, a test
    note, two result notes, a dated search with references, a lead and at
    least two roles, an independent critique that is not a copy of the
    pre-rounds, the locked phase order, two retry slots, and dated events
    in temporal and phase order covering every phase. A true result checks
    the shape of a trail. It does not audit this campaign and it does not
    support a hypothesis.
    """

    texts = _nonempty_texts(record.get("pre_rounds"), minimum=5)
    if texts is None or len(set(texts)) < 5:
        return False
    post = _nonempty_texts(record.get("post_build"), minimum=2)
    results = _nonempty_texts(record.get("result_notes"), minimum=2)
    if post is None or results is None:
        return False
    if not str(record.get("test_note", "")).strip():
        return False

    search = record.get("search_record")
    if not isinstance(search, Mapping):
        return False
    search_date = _phase_date(search.get("date", ""))
    if search_date is None:
        return False
    refs = search.get("references")
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        return False
    ref_texts = [str(item).strip() for item in refs]
    if not ref_texts or any(not item for item in ref_texts):
        return False

    labor = record.get("labor_split")
    if not isinstance(labor, Mapping):
        return False
    if not str(labor.get("lead", "")).strip():
        return False
    roles = labor.get("roles")
    if not isinstance(roles, Mapping) or len(roles) < 2:
        return False
    if any(not str(name).strip() or not str(duty).strip() for name, duty in roles.items()):
        return False

    critique = _nonempty_texts(record.get("independent_critique"), minimum=1)
    if critique is None or set(critique) <= set(texts):
        return False

    order = record.get("phase_order")
    if not isinstance(order, Sequence) or isinstance(order, (str, bytes)):
        return False
    if [str(item) for item in order] != list(PHASE_ORDER):
        return False

    retries = record.get("retry_slots")
    if not isinstance(retries, Sequence) or isinstance(retries, (str, bytes)):
        return False
    if len(list(retries)) != 2:
        return False
    for slot in retries:
        if not isinstance(slot, Mapping):
            return False
        if not isinstance(slot.get("used"), bool):
            return False
        if _phase_date(slot.get("date", "")) is None:
            return False
        if slot.get("used") is True and not str(slot.get("note", "")).strip():
            return False

    events = record.get("dated_events")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return False
    parsed: list[tuple[str, str]] = []
    for event in events:
        if not isinstance(event, Mapping):
            return False
        date = _phase_date(event.get("date", ""))
        phase = str(event.get("phase", "")).strip()
        if date is None or phase not in PHASE_ORDER:
            return False
        parsed.append((date, phase))
    if len(parsed) < len(PHASE_ORDER):
        return False
    if parsed != sorted(parsed, key=lambda item: item[0]):
        return False
    indexes = [PHASE_ORDER.index(phase) for _, phase in parsed]
    if indexes != sorted(indexes):
        return False
    if {phase for _, phase in parsed} != set(PHASE_ORDER):
        return False
    search_events = [date for date, phase in parsed if phase == "search"]
    if search_date not in search_events:
        return False
    return True
