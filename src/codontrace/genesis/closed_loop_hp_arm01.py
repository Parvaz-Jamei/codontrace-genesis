"""Three-arm host–parasite ecology path with digest-backed frequency clocks.

Morran et al. (Science 2011, doi:10.1126/science.1206360) and Slowinski et al.
(Evolution 2016, doi:10.1111/evo.13048) used control / fixed / copassaged
antagonist regimes when asking whether sex is maintained under coevolution.
This module maps those ecology labels onto the tip passage names already on
the closed-loop ledger, without collapsing ``absent`` into ``frozen`` or into
pure zero-debit / ``costless`` (Pearl, Biometrika 82:669–688, 1995,
doi:10.1093/biomet/82.4.669).

Ecology arm → tip passage
- ``avirulent`` → ``absent`` (antagonist removal; not a Pearl zero-debit cut)
- ``fixed`` → ``frozen`` (update off, debit on)
- ``copassaged`` → ``coevolve`` (update on, debit on)

Required fields are digest-backed genotype, mating-mode, and match-class
frequency clocks. They are measurements, not caller-booleans that write
``red_queen_proved``. The primary ecology accept path is a Slowinski-style
selfing-invasion / mating-mode frequency contrast across the three arms.
Pearl ``frozen``+``costless`` knockouts and debit-stream capability gates may
be attached as thin measurement clauses only after the frequency clocks exist;
they are not the ecology accept path.

Claim ceiling stays ``runtime_observation`` until clocks and treatment/control
arms are both present, then at most ``candidate_evidence``.
``red_queen_proved`` and ``biological_red_queen_proved`` stay false.
``engine.py`` is untouched.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import (
    run_match_arm,
    run_shared_modifier,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_COSTLESS,
    PASSAGE_FROZEN,
    assert_passage_taxonomy,
    evaluate_pearl_spc_clauses,
)

HP_ARM01_REVISION = "hp-arm01-20260926"
CLAIM_CEILING_OBSERVATION = "runtime_observation"
CLAIM_CEILING_CANDIDATE = "candidate_evidence"
ALLOWED_CEILINGS = frozenset({CLAIM_CEILING_OBSERVATION, CLAIM_CEILING_CANDIDATE})

ARM_AVIRULENT = "avirulent"
ARM_FIXED = "fixed"
ARM_COPASSAGED = "copassaged"

ECOLOGY_ARMS = (ARM_AVIRULENT, ARM_FIXED, ARM_COPASSAGED)

# Science label → tip passage. Avirulent is antagonist removal, not costless.
ARM_TO_PASSAGE: dict[str, str] = {
    ARM_AVIRULENT: PASSAGE_ABSENT,
    ARM_FIXED: PASSAGE_FROZEN,
    ARM_COPASSAGED: PASSAGE_COEVOLVE,
}

PASSAGE_TO_ARM: dict[str, str] = {passage: arm for arm, passage in ARM_TO_PASSAGE.items()}

ARM_MEANING = {
    ARM_AVIRULENT: "antagonist removal (tip passage absent); not zero-debit",
    ARM_FIXED: "update off, debit on (tip passage frozen)",
    ARM_COPASSAGED: "update on, debit on (tip passage coevolve)",
}

CLOCK_GENOTYPE = "genotype"
CLOCK_MATING_MODE = "mating_mode"
CLOCK_MATCH_CLASS = "match_class"
REQUIRED_CLOCKS = (CLOCK_GENOTYPE, CLOCK_MATING_MODE, CLOCK_MATCH_CLASS)

_SLOWINSKI_FOUNDERS: tuple[tuple[str, str], ...] = (
    ("selfing", "000111"),
    ("selfing", "000111"),
    ("selfing", "111000"),
    ("outcross", "000111"),
    ("outcross", "111000"),
)


def _digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _as_freq_table(
    counts: Mapping[str, object] | Sequence[tuple[str, object]] | Iterable[tuple[str, object]],
    *,
    name: str,
) -> tuple[tuple[str, int], ...]:
    if isinstance(counts, Mapping):
        items = list(counts.items())
    else:
        items = list(counts)
    out: list[tuple[str, int]] = []
    for index, entry in enumerate(items):
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ConfigurationError(f"{name}[{index}] must be a (label, count) pair")
        label, raw = entry
        if not isinstance(label, str) or not label.strip():
            raise ConfigurationError(f"{name}[{index}] label must be a non-empty string")
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ConfigurationError(f"{name}[{index}] count must be an int")
        if raw < 0:
            raise ConfigurationError(f"{name}[{index}] count must be >= 0")
        out.append((label.strip(), raw))
    out.sort(key=lambda item: item[0])
    return tuple(out)


def ecology_arm_to_passage(arm: str) -> str:
    """Map a Morran–Slowinski ecology label to a tip passage name."""

    if not isinstance(arm, str) or not arm.strip():
        raise ConfigurationError("ecology arm must be a non-empty string")
    key = arm.strip().lower()
    if key == PASSAGE_COSTLESS or key in {"zero_debit", "costless"}:
        raise ConfigurationError(
            "avirulent / control must not alias to costless or zero_debit; "
            "use absent for antagonist removal"
        )
    if key in ARM_TO_PASSAGE:
        return ARM_TO_PASSAGE[key]
    if key in PASSAGE_TO_ARM:
        return key
    raise ConfigurationError(
        f"ecology arm must be one of {list(ECOLOGY_ARMS)}, got {arm!r}"
    )


def passage_to_ecology_arm(passage: str) -> str:
    """Inverse map. Refuses Pearl-only ``costless`` as an ecology arm."""

    if not isinstance(passage, str) or not passage.strip():
        raise ConfigurationError("passage must be a non-empty string")
    key = passage.strip().lower()
    if key == PASSAGE_COSTLESS:
        raise ConfigurationError(
            "costless is a Pearl debit knockout, not a Morran–Slowinski ecology arm"
        )
    if key not in PASSAGE_TO_ARM:
        raise ConfigurationError(
            f"passage must be one of {sorted(PASSAGE_TO_ARM)}, got {passage!r}"
        )
    return PASSAGE_TO_ARM[key]


def assert_ecology_arm_taxonomy(*, refuse_aliases: bool = True) -> dict[str, str]:
    """Document that avirulent ≠ fixed ≠ copassaged and ≠ costless."""

    if not refuse_aliases:
        raise ConfigurationError("refuse_aliases must stay true; aliases are forbidden")
    assert_passage_taxonomy()
    if ARM_TO_PASSAGE[ARM_AVIRULENT] != PASSAGE_ABSENT:
        raise ConfigurationError("avirulent must map to absent")
    if ARM_TO_PASSAGE[ARM_FIXED] != PASSAGE_FROZEN:
        raise ConfigurationError("fixed must map to frozen")
    if ARM_TO_PASSAGE[ARM_COPASSAGED] != PASSAGE_COEVOLVE:
        raise ConfigurationError("copassaged must map to coevolve")
    if PASSAGE_COSTLESS in ARM_TO_PASSAGE.values():
        raise ConfigurationError("costless must not sit in the ecology arm map")
    meanings = dict(ARM_MEANING)
    if len(set(meanings.values())) != 3:
        raise ConfigurationError("ecology arm meanings must stay distinct")
    return meanings


@dataclass(frozen=True, slots=True)
class FrequencyClock:
    """Digest-backed frequency series for one named clock."""

    name: str
    series: tuple[tuple[tuple[str, int], ...], ...]
    digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "series": [[list(pair) for pair in state] for state in self.series],
            "digest": self.digest,
            "writes_red_queen_flag": False,
        }


def build_frequency_clock(
    name: str,
    series: Sequence[Mapping[str, object] | Sequence[tuple[str, object]]],
) -> FrequencyClock:
    """Build one required clock. Empty series fail closed (no digest grant)."""

    if not isinstance(name, str) or name.strip() not in REQUIRED_CLOCKS:
        raise ConfigurationError(
            f"frequency clock name must be one of {list(REQUIRED_CLOCKS)}"
        )
    key = name.strip()
    if not series:
        raise ConfigurationError(f"{key} clock requires a non-empty frequency series")
    states: list[tuple[tuple[str, int], ...]] = []
    for index, raw in enumerate(series):
        states.append(_as_freq_table(raw, name=f"{key}[{index}]"))
    payload = {
        "name": key,
        "series": [[list(pair) for pair in state] for state in states],
        "revision": HP_ARM01_REVISION,
    }
    return FrequencyClock(name=key, series=tuple(states), digest=_digest(payload))


def genotype_clock_from_windows(
    host_frequencies: Sequence[Sequence[tuple[str, object]]],
) -> FrequencyClock:
    """Genotype clock from recognition-window frequency tables."""

    return build_frequency_clock(CLOCK_GENOTYPE, host_frequencies)


def mating_mode_clock_from_counts(
    outcross_by_generation: Sequence[int],
    selfing_by_generation: Sequence[int],
) -> FrequencyClock:
    """Mating-mode clock from outcross / selfing headcounts."""

    if len(outcross_by_generation) != len(selfing_by_generation):
        raise ConfigurationError("mating-mode series lengths must match")
    if not outcross_by_generation:
        raise ConfigurationError("mating-mode clock requires a non-empty series")
    series = [
        (("outcross", int(out_n)), ("selfing", int(self_n)))
        for out_n, self_n in zip(outcross_by_generation, selfing_by_generation)
    ]
    return build_frequency_clock(CLOCK_MATING_MODE, series)


def match_class_clock_from_contacts(
    *,
    match_debits_by_generation: Sequence[int],
    host_frequencies: Sequence[Sequence[tuple[str, object]]],
    parasite_frequencies: Sequence[Sequence[tuple[str, object]]],
) -> FrequencyClock:
    """Match-class clock: paid match vs unpaid contact per generation.

    Class labels are ``matched`` (debit > 0) and ``unmatched`` (debit == 0)
    when hosts remain; extinct generations are recorded as empty tables so the
    digest still covers the path. Not a caller-boolean for Red Queen flags.
    """

    n = len(match_debits_by_generation)
    if n == 0:
        raise ConfigurationError("match-class clock requires a non-empty debit series")
    if len(host_frequencies) != n or len(parasite_frequencies) != n:
        raise ConfigurationError(
            "match-class clock needs aligned host, parasite, and debit series"
        )
    series: list[tuple[tuple[str, int], ...]] = []
    for index, debit in enumerate(match_debits_by_generation):
        if isinstance(debit, bool) or not isinstance(debit, int) or debit < 0:
            raise ConfigurationError(f"match_debits_by_generation[{index}] must be int >= 0")
        hosts = _as_freq_table(host_frequencies[index], name=f"host_frequencies[{index}]")
        host_n = sum(count for _, count in hosts)
        if host_n <= 0:
            series.append(())
            continue
        matched = min(int(debit), host_n)
        unmatched = host_n - matched
        series.append((("matched", matched), ("unmatched", unmatched)))
    return build_frequency_clock(CLOCK_MATCH_CLASS, series)


def required_clocks_complete(clocks: Mapping[str, FrequencyClock] | Sequence[FrequencyClock]) -> bool:
    """True only when all three required clocks are present with digests."""

    if isinstance(clocks, Mapping):
        items = list(clocks.values())
    else:
        items = list(clocks)
    by_name = {clock.name: clock for clock in items}
    if set(by_name) != set(REQUIRED_CLOCKS):
        return False
    return all(
        isinstance(clock.digest, str)
        and len(clock.digest) == 64
        and clock.series
        for clock in by_name.values()
    )


def max_allowed_claim_ceiling(
    *,
    clocks_complete: bool,
    treatment_control_present: bool,
) -> str:
    """Ceiling cap. Candidate only when clocks and treatment/control exist."""

    if not isinstance(clocks_complete, bool) or not isinstance(treatment_control_present, bool):
        raise ConfigurationError("clock and treatment flags must be bools")
    if clocks_complete and treatment_control_present:
        return CLAIM_CEILING_CANDIDATE
    return CLAIM_CEILING_OBSERVATION


def slowinski_selfing_invasion_contrast(
    *,
    selfing_freq_avirulent: float | None,
    selfing_freq_fixed: float | None,
    selfing_freq_copassaged: float | None,
) -> bool:
    """Slowinski-style contrast: selfing rises on controls, stays rarer under copassage.

    Requires finite frequencies in ``[0, 1]``. Returns True only when selfing
    under copassage is strictly below both control arms. Missing frequencies
    fail closed. Does not set any Red Queen flag.
    """

    values = (
        ("avirulent", selfing_freq_avirulent),
        ("fixed", selfing_freq_fixed),
        ("copassaged", selfing_freq_copassaged),
    )
    parsed: dict[str, float] = {}
    for label, raw in values:
        if raw is None:
            return False
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConfigurationError(f"selfing_freq_{label} must be a finite number or None")
        number = float(raw)
        if number != number or number in (float("inf"), float("-inf")):
            raise ConfigurationError(f"selfing_freq_{label} must be finite")
        if number < 0.0 or number > 1.0:
            raise ConfigurationError(f"selfing_freq_{label} must be in [0, 1]")
        parsed[label] = number
    return (
        parsed[ARM_COPASSAGED] < parsed[ARM_AVIRULENT]
        and parsed[ARM_COPASSAGED] < parsed[ARM_FIXED]
    )


def _terminal_selfing_frequency(record: object) -> float | None:
    out_series = getattr(record, "outcross_by_generation", ())
    self_series = getattr(record, "selfing_by_generation", ())
    if not out_series or not self_series:
        return None
    out_n = int(out_series[-1])
    self_n = int(self_series[-1])
    denom = out_n + self_n
    if denom <= 0:
        return None
    return self_n / denom


@dataclass(frozen=True, slots=True)
class ThreeArmCampaignReport:
    """Scaffolding report for the three ecology arms. Flags stay false."""

    arms_present: tuple[str, ...]
    passage_map: dict[str, str]
    clocks: dict[str, FrequencyClock]
    clocks_complete: bool
    treatment_control_present: bool
    slowinski_contrast_holds: bool
    selfing_freq_by_arm: dict[str, float | None]
    pearl_measurement_attached: bool
    claim_ceiling: str
    max_allowed_ceiling: str
    red_queen_proved: bool
    biological_red_queen_proved: bool
    revision: str
    digest: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "arms_present": list(self.arms_present),
            "passage_map": dict(self.passage_map),
            "arm_meanings": dict(ARM_MEANING),
            "clocks": {name: clock.to_dict() for name, clock in sorted(self.clocks.items())},
            "clocks_complete": self.clocks_complete,
            "treatment_control_present": self.treatment_control_present,
            "slowinski_contrast_holds": self.slowinski_contrast_holds,
            "selfing_freq_by_arm": dict(self.selfing_freq_by_arm),
            "pearl_measurement_attached": self.pearl_measurement_attached,
            "claim_ceiling": self.claim_ceiling,
            "max_allowed_ceiling": self.max_allowed_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "revision": self.revision,
            "accept_path": "slowinski_selfing_invasion_mating_mode_contrast",
            "sexual_maintenance_claimed": False,
        }
        payload["digest"] = self.digest
        return payload


def run_three_arm_frequency_campaign(
    *,
    virulence: float = 32.0,
    generations: int = 8,
    seed: int = 101,
    attach_pearl_measurement: bool = False,
) -> ThreeArmCampaignReport:
    """Run the three ecology arms and record required frequency clocks.

    Uses the shared-modifier census so mating-mode frequencies are first-class.
    Short generation counts are scaffolding, not a confirmatory claim.
    Prefer honest FAIL on the Slowinski contrast over soft-pass theater.
    """

    assert_ecology_arm_taxonomy()
    if attach_pearl_measurement:
        # Pearl clauses are measurement-only and require clocks first.
        pass

    shared_by_arm: dict[str, object] = {}
    for arm in ECOLOGY_ARMS:
        passage = ecology_arm_to_passage(arm)
        shared_by_arm[arm] = run_shared_modifier(
            _SLOWINSKI_FOUNDERS,
            passage=passage,
            virulence=virulence,
            generations=generations,
            seed=seed,
        )

    # Clocks are required fields: build from the copassaged arm path (treatment)
    # and keep control arms for contrast. Genotype / match-class also recorded
    # from copassaged; mating-mode series concatenated across arms for digest
    # coverage of the full campaign skeleton.
    treatment = shared_by_arm[ARM_COPASSAGED]
    genotype = genotype_clock_from_windows(treatment.host_frequencies)
    mating_series_out: list[int] = []
    mating_series_self: list[int] = []
    for arm in ECOLOGY_ARMS:
        record = shared_by_arm[arm]
        mating_series_out.extend(int(v) for v in record.outcross_by_generation)
        mating_series_self.extend(int(v) for v in record.selfing_by_generation)
    mating = mating_mode_clock_from_counts(mating_series_out, mating_series_self)
    match_class = match_class_clock_from_contacts(
        match_debits_by_generation=treatment.match_debits_by_generation,
        host_frequencies=treatment.host_frequencies,
        parasite_frequencies=treatment.parasite_frequencies,
    )
    clocks = {
        CLOCK_GENOTYPE: genotype,
        CLOCK_MATING_MODE: mating,
        CLOCK_MATCH_CLASS: match_class,
    }
    clocks_ok = required_clocks_complete(clocks)
    arms_present = tuple(ECOLOGY_ARMS)
    treatment_control = set(arms_present) == set(ECOLOGY_ARMS)
    freqs = {
        arm: _terminal_selfing_frequency(shared_by_arm[arm]) for arm in ECOLOGY_ARMS
    }
    contrast = slowinski_selfing_invasion_contrast(
        selfing_freq_avirulent=freqs[ARM_AVIRULENT],
        selfing_freq_fixed=freqs[ARM_FIXED],
        selfing_freq_copassaged=freqs[ARM_COPASSAGED],
    )
    ceiling_cap = max_allowed_claim_ceiling(
        clocks_complete=clocks_ok,
        treatment_control_present=treatment_control,
    )
    # Reported ceiling stays observational until an accept path actually holds.
    reported_ceiling = (
        CLAIM_CEILING_CANDIDATE
        if contrast and ceiling_cap == CLAIM_CEILING_CANDIDATE
        else CLAIM_CEILING_OBSERVATION
    )

    pearl_attached = False
    if attach_pearl_measurement:
        if not clocks_ok:
            raise ConfigurationError(
                "Pearl measurement clauses require complete frequency clocks first"
            )
        # Thin reuse: evaluate Pearl pair gap on short pure arms without
        # promoting flags. Ecology accept path remains Slowinski contrast.
        frozen_out = run_match_arm(
            mating="outcross", passage=PASSAGE_FROZEN, virulence=virulence,
            generations=min(generations, 4), seed=seed,
        )
        frozen_self = run_match_arm(
            mating="selfing", passage=PASSAGE_FROZEN, virulence=virulence,
            generations=min(generations, 4), seed=seed,
        )
        costless_out = run_match_arm(
            mating="outcross", passage=PASSAGE_COSTLESS, virulence=virulence,
            generations=min(generations, 4), seed=seed,
        )
        costless_self = run_match_arm(
            mating="selfing", passage=PASSAGE_COSTLESS, virulence=virulence,
            generations=min(generations, 4), seed=seed,
        )
        pearl = evaluate_pearl_spc_clauses(
            history=frozen_out.window_history,
            match_debits=frozen_out.match_debits_by_generation,
            frozen_outcross_extinct=frozen_out.extinct,
            frozen_selfing_extinct=frozen_self.extinct,
            costless_outcross_extinct=costless_out.extinct,
            costless_selfing_extinct=costless_self.extinct,
        )
        if pearl.red_queen_proved or pearl.biological_red_queen_proved:
            raise ConfigurationError("Pearl measurement must not set Red Queen flags")
        pearl_attached = True

    note = (
        "slowinski_contrast_holds"
        if contrast
        else "slowinski_contrast_fail_recorded_honestly"
    )
    report = ThreeArmCampaignReport(
        arms_present=arms_present,
        passage_map=dict(ARM_TO_PASSAGE),
        clocks=clocks,
        clocks_complete=clocks_ok,
        treatment_control_present=treatment_control,
        slowinski_contrast_holds=contrast,
        selfing_freq_by_arm=freqs,
        pearl_measurement_attached=pearl_attached,
        claim_ceiling=reported_ceiling,
        max_allowed_ceiling=ceiling_cap,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        revision=HP_ARM01_REVISION,
        digest="",
        notes=note,
    )
    digest = _digest({k: v for k, v in report.to_dict().items() if k != "digest"})
    return ThreeArmCampaignReport(
        arms_present=report.arms_present,
        passage_map=report.passage_map,
        clocks=report.clocks,
        clocks_complete=report.clocks_complete,
        treatment_control_present=report.treatment_control_present,
        slowinski_contrast_holds=report.slowinski_contrast_holds,
        selfing_freq_by_arm=report.selfing_freq_by_arm,
        pearl_measurement_attached=report.pearl_measurement_attached,
        claim_ceiling=report.claim_ceiling,
        max_allowed_ceiling=report.max_allowed_ceiling,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        revision=report.revision,
        digest=digest,
        notes=report.notes,
    )


def handling_ablation_digests(
    *,
    handling_off: Mapping[str, object],
    handling_on: Mapping[str, object],
) -> dict[str, object]:
    """Compare HostParasiteEnv snapshots with handling-time off vs on.

    Thin Holling handling lives only in the HP env port. Digests must differ
    when handling changes outcomes; identical digests fail the ablation pair.
    Does not raise claim ceilings or set Red Queen flags.
    """

    off_digest = handling_off.get("digest")
    on_digest = handling_on.get("digest")
    if not isinstance(off_digest, str) or not isinstance(on_digest, str):
        raise ConfigurationError("handling ablation requires snapshot digests")
    if not off_digest or not on_digest:
        raise ConfigurationError("handling ablation digests must be non-empty")
    distinct = off_digest != on_digest
    return {
        "schema": "hp_arm01_handling_ablation_v1",
        "handling_off_digest": off_digest,
        "handling_on_digest": on_digest,
        "digests_distinct": distinct,
        "claim_ceiling": CLAIM_CEILING_OBSERVATION,
        "red_queen_proved": False,
        "biological_red_queen_proved": False,
        "revision": HP_ARM01_REVISION,
    }


__all__ = [
    "ALLOWED_CEILINGS",
    "ARM_AVIRULENT",
    "ARM_COPASSAGED",
    "ARM_FIXED",
    "ARM_MEANING",
    "ARM_TO_PASSAGE",
    "CLAIM_CEILING_CANDIDATE",
    "CLAIM_CEILING_OBSERVATION",
    "CLOCK_GENOTYPE",
    "CLOCK_MATCH_CLASS",
    "CLOCK_MATING_MODE",
    "ECOLOGY_ARMS",
    "HP_ARM01_REVISION",
    "REQUIRED_CLOCKS",
    "FrequencyClock",
    "ThreeArmCampaignReport",
    "assert_ecology_arm_taxonomy",
    "build_frequency_clock",
    "ecology_arm_to_passage",
    "genotype_clock_from_windows",
    "handling_ablation_digests",
    "match_class_clock_from_contacts",
    "mating_mode_clock_from_counts",
    "max_allowed_claim_ceiling",
    "passage_to_ecology_arm",
    "required_clocks_complete",
    "run_three_arm_frequency_campaign",
    "slowinski_selfing_invasion_contrast",
]
