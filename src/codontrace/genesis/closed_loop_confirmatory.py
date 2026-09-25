"""Confirmatory seeds locked before they were run.

The rule is in ``docs/handoff/CLOSED_LOOP_P7_ROADMAP_PREREG_20260925.md``.
Seeds 101–108 are not seed 7. Mutation stays 0.7, the horizon stays 48
generations, and birth ATP stays 10 on the primary endpoint. The primary
virulence is 32. Virulence 8 is only the low-debit check. The strict
separate block and the mixed census are ``run_confirmatory_partial``.
``graded_block`` repeats that block with locus overlap. ``run_sensitivity``
is the virulence and birth-ATP table, and it is not a new endpoint.
``red_queen_proved`` stays false unless every block clears 6 of 8.
"""

from __future__ import annotations

from dataclasses import dataclass

from codontrace.genesis.closed_loop_p6 import (
    MatchArmRecord,
    SharedModifierRecord,
    run_match_arm,
    run_shared_modifier,
)

CONFIRMATORY_SEEDS = (101, 102, 103, 104, 105, 106, 107, 108)
PRIMARY_VIRULENCE = 32.0
LOW_VIRULENCE = 8.0
CONFIRMATORY_GENERATIONS = 48
CONFIRMATORY_MUTATION = 0.7
CONFIRMATORY_BIRTH_ATP = 10.0
PASS_BAR = 6
_MIXED_FOUNDERS = (
    ("selfing", "000111"),
    ("selfing", "000111"),
    ("selfing", "111000"),
    ("outcross", "000111"),
    ("outcross", "111000"),
)


@dataclass(frozen=True, slots=True)
class SeparateSeed:
    seed: int
    outcross_coevolve_extinct: bool
    outcross_coevolve_cycles: bool
    selfing_coevolve_extinct: bool
    outcross_frozen_extinct: bool
    outcross_frozen_cycles: bool
    selfing_frozen_extinct: bool
    outcross_absent_extinct: bool
    selfing_absent_extinct: bool
    selfing_coevolve_extinct_at_8: bool
    specificity: str
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "outcross_coevolve_extinct": self.outcross_coevolve_extinct,
            "outcross_coevolve_cycles": self.outcross_coevolve_cycles,
            "selfing_coevolve_extinct": self.selfing_coevolve_extinct,
            "outcross_frozen_extinct": self.outcross_frozen_extinct,
            "outcross_frozen_cycles": self.outcross_frozen_cycles,
            "selfing_frozen_extinct": self.selfing_frozen_extinct,
            "outcross_absent_extinct": self.outcross_absent_extinct,
            "selfing_absent_extinct": self.selfing_absent_extinct,
            "selfing_coevolve_extinct_at_8": self.selfing_coevolve_extinct_at_8,
            "specificity": self.specificity,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class MixedSeed:
    seed: int
    coevolve_outcross: int
    coevolve_selfing: int
    frozen_outcross: int
    frozen_selfing: int
    unmated_at_0: int
    coevolve_frequency: float | None
    frozen_frequency: float | None
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "coevolve_outcross": self.coevolve_outcross,
            "coevolve_selfing": self.coevolve_selfing,
            "frozen_outcross": self.frozen_outcross,
            "frozen_selfing": self.frozen_selfing,
            "unmated_at_0": self.unmated_at_0,
            "coevolve_frequency": self.coevolve_frequency,
            "frozen_frequency": self.frozen_frequency,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class ConfirmatoryReport:
    """Partial campaign. Graded overlap is not in this report."""

    separate: tuple[SeparateSeed, ...]
    mixed: tuple[MixedSeed, ...]
    separate_passes: int
    mixed_passes: int
    separate_block: bool
    mixed_block: bool
    graded_ran: bool
    red_queen_proved: bool
    biological_red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "seeds": list(CONFIRMATORY_SEEDS),
            "virulence": PRIMARY_VIRULENCE,
            "low_virulence": LOW_VIRULENCE,
            "generations": CONFIRMATORY_GENERATIONS,
            "parasite_mutation": CONFIRMATORY_MUTATION,
            "birth_atp": CONFIRMATORY_BIRTH_ATP,
            "specificity": "strict",
            "separate": [row.to_dict() for row in self.separate],
            "mixed": [row.to_dict() for row in self.mixed],
            "separate_passes": self.separate_passes,
            "mixed_passes": self.mixed_passes,
            "separate_block": self.separate_block,
            "mixed_block": self.mixed_block,
            "graded_ran": self.graded_ran,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
        }


def _frequency(outcross: int, selfing: int) -> float | None:
    living = outcross + selfing
    if living <= 0:
        return None
    return outcross / living


def separate_seed(seed: int, *, specificity: str = "strict") -> SeparateSeed:
    """One confirmatory seed at the locked primary endpoint."""

    def arm(mating: str, passage: str, virulence: float) -> MatchArmRecord:
        return run_match_arm(
            mating=mating,
            passage=passage,
            virulence=virulence,
            generations=CONFIRMATORY_GENERATIONS,
            birth_atp=CONFIRMATORY_BIRTH_ATP,
            seed=seed,
            parasite_mutation=CONFIRMATORY_MUTATION,
            specificity=specificity,
        )

    oc = arm("outcross", "coevolve", PRIMARY_VIRULENCE)
    sc = arm("selfing", "coevolve", PRIMARY_VIRULENCE)
    of_ = arm("outcross", "frozen", PRIMARY_VIRULENCE)
    sf = arm("selfing", "frozen", PRIMARY_VIRULENCE)
    oa = arm("outcross", "absent", PRIMARY_VIRULENCE)
    sa = arm("selfing", "absent", PRIMARY_VIRULENCE)
    low = arm("selfing", "coevolve", LOW_VIRULENCE)
    passed = (
        (not oc.extinct)
        and oc.cycles
        and sc.extinct
        and (not of_.extinct)
        and (not of_.cycles)
        and (not sf.extinct)
        and (not oa.extinct)
        and (not sa.extinct)
        and (not low.extinct)
    )
    return SeparateSeed(
        seed=seed,
        outcross_coevolve_extinct=oc.extinct,
        outcross_coevolve_cycles=oc.cycles,
        selfing_coevolve_extinct=sc.extinct,
        outcross_frozen_extinct=of_.extinct,
        outcross_frozen_cycles=of_.cycles,
        selfing_frozen_extinct=sf.extinct,
        outcross_absent_extinct=oa.extinct,
        selfing_absent_extinct=sa.extinct,
        selfing_coevolve_extinct_at_8=low.extinct,
        specificity=specificity,
        passed=passed,
    )


def mixed_seed(seed: int) -> MixedSeed:
    """Outcross frequency at generation 48, coevolve against frozen."""

    def census(passage: str) -> SharedModifierRecord:
        return run_shared_modifier(
            _MIXED_FOUNDERS,
            passage=passage,
            virulence=PRIMARY_VIRULENCE,
            generations=CONFIRMATORY_GENERATIONS,
            birth_atp=CONFIRMATORY_BIRTH_ATP,
            seed=seed,
            parasite_mutation=CONFIRMATORY_MUTATION,
            specificity="strict",
        )

    chased = census("coevolve")
    held = census("frozen")
    co_out = chased.outcross_by_generation[-1]
    co_self = chased.selfing_by_generation[-1]
    fr_out = held.outcross_by_generation[-1]
    fr_self = held.selfing_by_generation[-1]
    co_freq = _frequency(co_out, co_self)
    fr_freq = _frequency(fr_out, fr_self)
    unmated = chased.unmated_outcross_by_generation[0]
    passed = (
        unmated == 0
        and held.unmated_outcross_by_generation[0] == 0
        and co_freq is not None
        and fr_freq is not None
        and co_freq > fr_freq
    )
    return MixedSeed(
        seed=seed,
        coevolve_outcross=co_out,
        coevolve_selfing=co_self,
        frozen_outcross=fr_out,
        frozen_selfing=fr_self,
        unmated_at_0=unmated,
        coevolve_frequency=co_freq,
        frozen_frequency=fr_freq,
        passed=passed,
    )


def run_confirmatory_partial() -> ConfirmatoryReport:
    """Separate-population block, then the mixed census. No graded clause."""

    separate = tuple(separate_seed(seed) for seed in CONFIRMATORY_SEEDS)
    mixed = tuple(mixed_seed(seed) for seed in CONFIRMATORY_SEEDS)
    separate_passes = sum(row.passed for row in separate)
    mixed_passes = sum(row.passed for row in mixed)
    return ConfirmatoryReport(
        separate=separate,
        mixed=mixed,
        separate_passes=separate_passes,
        mixed_passes=mixed_passes,
        separate_block=separate_passes >= PASS_BAR,
        mixed_block=mixed_passes >= PASS_BAR,
        graded_ran=False,
        red_queen_proved=False,
        biological_red_queen_proved=False,
    )


VIRULENCE_STEP = tuple(float(value) for value in range(8, 42, 2))
BIRTH_ATPS = (8.0, 10.0, 12.0)


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    """Descriptive count across the eight confirmatory seeds. Not a new endpoint."""

    virulence: float
    birth_atp: float
    selfing_coevolve_extinct: int
    outcross_coevolve_cycles: int
    conjunction: int

    def to_dict(self) -> dict[str, object]:
        return {
            "virulence": self.virulence,
            "birth_atp": self.birth_atp,
            "selfing_coevolve_extinct": self.selfing_coevolve_extinct,
            "outcross_coevolve_cycles": self.outcross_coevolve_cycles,
            "conjunction": self.conjunction,
        }


def graded_block() -> tuple[SeparateSeed, ...]:
    """The same six lines as the strict block, with graded overlap. Not a refit."""

    return tuple(separate_seed(seed, specificity="graded") for seed in CONFIRMATORY_SEEDS)


def _sensitivity_cell(virulence: float, birth_atp: float) -> SensitivityCell:
    extinct = 0
    cycles = 0
    conjunction = 0
    for seed in CONFIRMATORY_SEEDS:
        def arm(mating: str, passage: str, seed: int = seed) -> MatchArmRecord:
            return run_match_arm(
                mating=mating,
                passage=passage,
                virulence=virulence,
                generations=CONFIRMATORY_GENERATIONS,
                birth_atp=birth_atp,
                seed=seed,
                parasite_mutation=CONFIRMATORY_MUTATION,
                specificity="strict",
            )

        oc = arm("outcross", "coevolve")
        sc = arm("selfing", "coevolve")
        of_ = arm("outcross", "frozen")
        sf = arm("selfing", "frozen")
        if sc.extinct:
            extinct += 1
        if oc.cycles:
            cycles += 1
        if (
            (not oc.extinct)
            and oc.cycles
            and sc.extinct
            and (not of_.extinct)
            and (not of_.cycles)
            and (not sf.extinct)
        ):
            conjunction += 1
    return SensitivityCell(
        virulence=virulence,
        birth_atp=birth_atp,
        selfing_coevolve_extinct=extinct,
        outcross_coevolve_cycles=cycles,
        conjunction=conjunction,
    )


def run_sensitivity() -> tuple[SensitivityCell, ...]:
    """Virulence every 2 from 8 to 40, birth ATP 8, 10, and 12. Strict weight."""

    return tuple(
        _sensitivity_cell(virulence, birth_atp)
        for birth_atp in BIRTH_ATPS
        for virulence in VIRULENCE_STEP
    )


def locked_flag(separate_passes: int, mixed_passes: int, graded_passes: int) -> bool:
    """The flag needs every block. A sensitivity cell cannot reopen it."""

    return (
        separate_passes >= PASS_BAR
        and mixed_passes >= PASS_BAR
        and graded_passes >= PASS_BAR
    )

