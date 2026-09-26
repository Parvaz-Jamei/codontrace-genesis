"""Three-arm host–parasite ecology path bound to the Genesis life-loop.

Morran et al. (Science 2011, doi:10.1126/science.1206360) and Slowinski et al.
(Evolution 2016, doi:10.1111/evo.13048) used control / fixed / copassaged
antagonist regimes when asking whether sex is maintained under coevolution.
This module maps those ecology labels onto tip passages without collapsing
``absent`` into ``frozen`` or into pure zero-debit / ``costless`` (Pearl,
Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669).

ENGINE-BIND (HP-ARM01-ENGINE-BIND)
---------------------------------
Each ecology arm runs on the real CodonTrace life-loop:

1. ``PopulationRunner.step_generation`` — same inner clock as
   ``GenesisEngine.run_ticks`` (domain-free population step).
2. Phase B sexual chamber — ``ReproductionMode.SEXUAL_CROSSOVER`` with the
   existing outcross locus (mating-effort ATP). Maynard Smith's two-fold cost
   (``SexualRecombinationConfig.two_fold_cost_sex``) remains unpaid / default
   off; this path does not silently claim Hamilton.
3. ``HostParasiteEnv`` — contact / debit for that same arm. Holling
   ``handling_time`` ablation must use the campaign env, not a disconnected
   probe. HP physics stays in the env/plugin; ``engine.py`` stays domain-free.

Primary ecology estimand (HP-ARM01-SLOWINSKI-INVASION)
-----------------------------------------------------
Resident obligate-outcross deme + low-frequency selfing-capable introduction.
Per-arm digest-backed clocks (genotype, mating-mode, match-class, and
selfing-rate / allele-frequency series). Accept path: selfing invades under
avirulent and fixed, stays rarer under copassaged. Morran outcrossing
maintenance is secondary, not a substitute PASS. Shared-modifier terminal
inequality is refused as a Slowinski PASS. Honest FAIL on short CI horizons
is recorded; confirmatory length is locked in closed_loop_hp_arm01_confirm.

Claim ceiling stays ``runtime_observation`` until life-loop bind + per-arm
clocks + the invasion contrast all hold, then at most ``candidate_evidence``.
``red_queen_proved`` / ``biological_red_queen_proved`` stay false. Sealed
101–108 / P7 prereg untouched. SPC/CUSUM/observer are fail-closed measurement
clauses only after per-arm clocks exist — never the ecology accept path.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Iterable, Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.closed_loop_p6 import run_match_arm
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_COSTLESS,
    PASSAGE_FROZEN,
    assert_passage_taxonomy,
    evaluate_pearl_spc_clauses,
)
from codontrace.genesis.host_parasite_env import HostParasiteEnv
from codontrace.genesis.host_parasite_life_plugin import (
    MATCH_BIT_START,
    MATCH_BIT_WIDTH,
    OUTCROSS_OUT_BITS,
    OUTCROSS_SELFING_BITS,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    assert_single_atp_owner,
    decode_outcross,
    decode_recognition,
    role_of,
    silence_outcross_locus,
    with_inherited_birth_roles,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MetabolicConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME
from codontrace.genome import SemanticGenome
from codontrace.rng import RNGManager
from codontrace.world import World2D

HP_ARM01_REVISION = "hp-arm01-engine-bind-20260926"
HP_ARM01_ESTIMAND = "slowinski_selfing_invasion_into_obligate_outcross"
CLAIM_CEILING_OBSERVATION = "runtime_observation"
CLAIM_CEILING_CANDIDATE = "candidate_evidence"
ALLOWED_CEILINGS = frozenset({CLAIM_CEILING_OBSERVATION, CLAIM_CEILING_CANDIDATE})

# Primary substrate identity. Shared-modifier census is explicitly not this.
SUBSTRATE_LIFE_LOOP = "population_runner_phase_b_host_parasite_env"
SUBSTRATE_FORBIDDEN_PRIMARY = "run_shared_modifier"

ARM_AVIRULENT = "avirulent"
ARM_FIXED = "fixed"
ARM_COPASSAGED = "copassaged"

ECOLOGY_ARMS = (ARM_AVIRULENT, ARM_FIXED, ARM_COPASSAGED)

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
CLOCK_SELFING_RATE = "selfing_rate"
CLOCK_ALLELE_FREQ = "allele_frequency"
REQUIRED_CLOCKS = (CLOCK_GENOTYPE, CLOCK_MATING_MODE, CLOCK_MATCH_CLASS)
INVASION_CLOCKS = (CLOCK_SELFING_RATE, CLOCK_ALLELE_FREQ)

HP_ENV_MATCH_REASON = "hp_arm01_env_match_cost"
_KAPPA_QUIET = "100000"
_PROGRAM = f"{LIFE_LOOP_EATER_GENOME}{_KAPPA_QUIET}"
_DEFAULT_BIRTH_ATP = 40.0
_DEFAULT_PARASITE_N = 8
_DEFAULT_HANDLING_TIME = 0.0
_DEFAULT_BASAL_ATP_COST = 0.05
_DEFAULT_SOFT_CARRYING_CAPACITY = 64
_DEFAULT_RESOURCE_BOLUS_AMOUNT = 0.0  # off: sealed Slowinski path unchanged
_DEFAULT_PASSAGE_REFILL_MODE = "off"
_DEFAULT_FOOD_PATCHES: tuple[tuple[int, int], ...] = tuple(
    (x, y) for x in range(4) for y in range(2)
)
PASSAGE_REFILL_GENERATION_BOUNDARY = "generation_boundary_resource_bolus"
PASSAGE_REFILL_OFF = "off"
_ALLELE_TASK_PREFIX = "allele_"

# Slowinski invasion founders: resident obligate outcross + rare selfing intro.
# Intro frequency = 2/10 = 0.2. Not a locked confirmatory prereg.
_INVASION_FOUNDERS: tuple[tuple[str, str], ...] = (
    ("outcross", "000111"),
    ("outcross", "000111"),
    ("outcross", "000111"),
    ("outcross", "111000"),
    ("outcross", "111000"),
    ("outcross", "111000"),
    ("outcross", "000111"),
    ("outcross", "111000"),
    ("selfing", "000111"),
    ("selfing", "111000"),
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
    *,
    allowed_names: Sequence[str] | None = None,
) -> FrequencyClock:
    """Build one clock. Empty series fail closed (no digest grant)."""

    allowed = tuple(allowed_names) if allowed_names is not None else REQUIRED_CLOCKS
    if not isinstance(name, str) or name.strip() not in allowed:
        raise ConfigurationError(f"frequency clock name must be one of {list(allowed)}")
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
    """Match-class clock: paid match vs unpaid contact per generation."""

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


def selfing_rate_clock_from_counts(
    outcross_by_generation: Sequence[int],
    selfing_by_generation: Sequence[int],
) -> FrequencyClock:
    """Selfing-rate clock as integer milli-frequencies (digest-stable ints)."""

    if len(outcross_by_generation) != len(selfing_by_generation):
        raise ConfigurationError("selfing-rate series lengths must match")
    if not outcross_by_generation:
        raise ConfigurationError("selfing-rate clock requires a non-empty series")
    series: list[tuple[tuple[str, int], ...]] = []
    for out_n, self_n in zip(outcross_by_generation, selfing_by_generation):
        denom = int(out_n) + int(self_n)
        if denom <= 0:
            series.append(())
            continue
        milli = int(round(1000.0 * int(self_n) / denom))
        series.append((("selfing_milli", milli), ("denom", denom)))
    return build_frequency_clock(
        CLOCK_SELFING_RATE, series, allowed_names=(*REQUIRED_CLOCKS, *INVASION_CLOCKS)
    )


def allele_frequency_clock_from_windows(
    host_frequencies: Sequence[Sequence[tuple[str, object]]],
) -> FrequencyClock:
    """Allele-frequency clock (recognition windows) for the invasion estimand."""

    return build_frequency_clock(
        CLOCK_ALLELE_FREQ,
        host_frequencies,
        allowed_names=(*REQUIRED_CLOCKS, *INVASION_CLOCKS),
    )


def required_clocks_complete(clocks: Mapping[str, FrequencyClock] | Sequence[FrequencyClock]) -> bool:
    """True only when all three required clocks are present with digests."""

    if isinstance(clocks, Mapping):
        items = list(clocks.values())
    else:
        items = list(clocks)
    by_name = {clock.name: clock for clock in items}
    if not set(REQUIRED_CLOCKS).issubset(set(by_name)):
        return False
    return all(
        isinstance(by_name[name].digest, str)
        and len(by_name[name].digest) == 64
        and by_name[name].series
        for name in REQUIRED_CLOCKS
    )


def per_arm_clocks_complete(
    clocks_by_arm: Mapping[str, Mapping[str, FrequencyClock]],
) -> bool:
    """True when every ecology arm carries the three required clocks."""

    if set(clocks_by_arm) != set(ECOLOGY_ARMS):
        return False
    return all(required_clocks_complete(clocks) for clocks in clocks_by_arm.values())


def max_allowed_claim_ceiling(
    *,
    clocks_complete: bool = False,
    treatment_control_present: bool = False,
    substrate_life_loop_bound: bool = False,
    per_arm_clocks_ok: bool = False,
    slowinski_invasion_holds: bool = False,
) -> str:
    """Ceiling cap. Candidate only on life-loop bind + per-arm clocks + invasion.

    Non-empty clock fields or a shared-modifier contrast alone never grant
    ``candidate_evidence`` (ClaimCritic harden).
    """

    for flag in (
        clocks_complete,
        treatment_control_present,
        substrate_life_loop_bound,
        per_arm_clocks_ok,
        slowinski_invasion_holds,
    ):
        if not isinstance(flag, bool):
            raise ConfigurationError("ceiling predicate flags must be bools")
    if (
        substrate_life_loop_bound
        and per_arm_clocks_ok
        and clocks_complete
        and treatment_control_present
        and slowinski_invasion_holds
    ):
        return CLAIM_CEILING_CANDIDATE
    return CLAIM_CEILING_OBSERVATION


def slowinski_selfing_invasion_contrast(
    *,
    selfing_freq_avirulent: float | None,
    selfing_freq_fixed: float | None,
    selfing_freq_copassaged: float | None,
) -> bool:
    """Legacy three-frequency contrast. Not the invasion accept path.

    Kept for measurement continuity. Must never be reported as Slowinski PASS
    for the ecology accept path; use ``slowinski_invasion_contrast`` instead.
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


def slowinski_invasion_contrast(
    *,
    intro_selfing_freq: float,
    final_selfing_avirulent: float | None,
    final_selfing_fixed: float | None,
    final_selfing_copassaged: float | None,
) -> bool:
    """Slowinski invasion estimand into an obligate-outcross resident deme.

    Requires finite frequencies in ``[0, 1]``. Returns True only when selfing
    rises above introduction under both control arms and stays at or below
    introduction under copassage (and strictly below both controls). Missing
    frequencies fail closed. Does not set any Red Queen flag.
    """

    if isinstance(intro_selfing_freq, bool) or not isinstance(intro_selfing_freq, (int, float)):
        raise ConfigurationError("intro_selfing_freq must be a finite number")
    intro = float(intro_selfing_freq)
    if intro != intro or intro in (float("inf"), float("-inf")):
        raise ConfigurationError("intro_selfing_freq must be finite")
    if intro < 0.0 or intro > 1.0:
        raise ConfigurationError("intro_selfing_freq must be in [0, 1]")
    values = (
        ("avirulent", final_selfing_avirulent),
        ("fixed", final_selfing_fixed),
        ("copassaged", final_selfing_copassaged),
    )
    parsed: dict[str, float] = {}
    for label, raw in values:
        if raw is None:
            return False
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ConfigurationError(f"final_selfing_{label} must be a finite number or None")
        number = float(raw)
        if number != number or number in (float("inf"), float("-inf")):
            raise ConfigurationError(f"final_selfing_{label} must be finite")
        if number < 0.0 or number > 1.0:
            raise ConfigurationError(f"final_selfing_{label} must be in [0, 1]")
        parsed[label] = number
    invaded_avirulent = parsed[ARM_AVIRULENT] > intro
    invaded_fixed = parsed[ARM_FIXED] > intro
    stayed_rare = (
        parsed[ARM_COPASSAGED] <= intro
        and parsed[ARM_COPASSAGED] < parsed[ARM_AVIRULENT]
        and parsed[ARM_COPASSAGED] < parsed[ARM_FIXED]
    )
    return invaded_avirulent and invaded_fixed and stayed_rare


def refuse_shared_modifier_as_slowinski_pass(*, substrate: str, contrast_holds: bool) -> None:
    """Hard refuse: shared-modifier inequality must never be Slowinski PASS."""

    if substrate == SUBSTRATE_FORBIDDEN_PRIMARY and contrast_holds:
        raise ConfigurationError(
            "shared-modifier terminal inequality must never report Slowinski PASS"
        )


def _tape(mating_bits: str, window: str) -> str:
    if len(window) != MATCH_BIT_WIDTH:
        raise ConfigurationError("recognition window must be 6 bits")
    if mating_bits not in {OUTCROSS_SELFING_BITS, OUTCROSS_OUT_BITS}:
        raise ConfigurationError("mating locus must be selfing 000 or outcross 001")
    return f"{_PROGRAM}{mating_bits}{window}"


def _window(organism: GenesisOrganism) -> str:
    return decode_recognition(organism.genome.to_compact())


def _mating_name(organism: GenesisOrganism) -> str:
    if decode_outcross(organism.genome.to_compact()):
        return "outcross"
    return "selfing"


def _allele_task(window: str) -> str:
    return f"{_ALLELE_TASK_PREFIX}{window.lower()}"


def _frequency_state(organisms: Sequence[GenesisOrganism]) -> tuple[tuple[str, int], ...]:
    counts = Counter(_window(org) for org in organisms)
    return tuple(sorted(counts.items()))


def _parasite_freq(windows: Sequence[str]) -> tuple[tuple[str, int], ...]:
    counts = Counter(windows)
    return tuple(sorted(counts.items()))


def _modal_window(windows: Sequence[str]) -> str:
    counts = Counter(windows)
    if not counts:
        raise ConfigurationError("modal window requires a living stock")
    best = max(counts.values())
    winners = sorted(window for window, count in counts.items() if count == best)
    return winners[0]


def _mutate_window(window: str, rng: RNGManager) -> str:
    if len(window) != MATCH_BIT_WIDTH:
        raise ConfigurationError("recognition window must be 6 bits")
    index = rng.randrange(0, MATCH_BIT_WIDTH)
    bit = "1" if window[index] == "0" else "0"
    return window[:index] + bit + window[index + 1 :]


@dataclass
class LifeLoopEcologyArm:
    """One Morran–Slowinski arm on life-loop + Phase B + HostParasiteEnv."""

    arm: str
    passage: str
    runner: PopulationRunner
    roles: dict[str, str]
    hp_env: HostParasiteEnv
    parasite_windows: list[str]
    ancestral_window: str
    seed: int
    virulence: float
    parasite_mutation: float
    tick_index: int = 0
    outcross_by_generation: list[int] = field(default_factory=list)
    selfing_by_generation: list[int] = field(default_factory=list)
    match_debits_by_generation: list[int] = field(default_factory=list)
    host_frequencies: list[tuple[tuple[str, int], ...]] = field(default_factory=list)
    parasite_frequencies: list[tuple[tuple[str, int], ...]] = field(default_factory=list)
    intro_selfing_freq: float = 0.0
    two_fold_cost_sex_applied: bool = False
    birth_atp: float = _DEFAULT_BIRTH_ATP
    basal_runtime_atp_cost: float = _DEFAULT_BASAL_ATP_COST
    soft_carrying_capacity: int = _DEFAULT_SOFT_CARRYING_CAPACITY
    passage_refill_mode: str = _DEFAULT_PASSAGE_REFILL_MODE
    resource_bolus_amount: float = _DEFAULT_RESOURCE_BOLUS_AMOUNT
    food_patches: tuple[tuple[int, int], ...] = _DEFAULT_FOOD_PATCHES
    cumulative_resource_bolus_placed: float = 0.0
    passage_refill_sync: str = "none"
    mating_locus_lock: bool = False
    selfing_birth_atp_endowment: float = 0.0
    mate_search_radius: int | None = None
    outcross_mates_per_generation_cap: int | None = None

    @classmethod
    def boot(
        cls,
        *,
        arm: str,
        virulence: float = 8.0,
        seed: int = 101,
        handling_time: float = _DEFAULT_HANDLING_TIME,
        birth_atp: float = _DEFAULT_BIRTH_ATP,
        parasite_n: int = _DEFAULT_PARASITE_N,
        parasite_mutation: float = 0.5,
        founders: Sequence[tuple[str, str]] | None = None,
        world_size: int = 12,
        steal_fraction: float = 0.8,
        soft_carrying_capacity: int = _DEFAULT_SOFT_CARRYING_CAPACITY,
        basal_runtime_atp_cost: float = _DEFAULT_BASAL_ATP_COST,
        passage_refill_mode: str = _DEFAULT_PASSAGE_REFILL_MODE,
        resource_bolus_amount: float = _DEFAULT_RESOURCE_BOLUS_AMOUNT,
        food_patches: Sequence[tuple[int, int]] | None = None,
        founder_spatial_policy: str = "legacy_row",
        two_fold_cost_sex: bool = False,
        mating_locus_lock: bool = False,
        selfing_birth_atp_endowment: float = 0.0,
        mate_search_radius: int | None = None,
        outcross_mates_per_generation_cap: int | None = None,
        chamber_max_birth_wait_ticks: int | None = None,
        chamber_timeout_policy: str = "asexual_fallback",
    ) -> LifeLoopEcologyArm:
        passage = ecology_arm_to_passage(arm)
        founder_rows = tuple(founders) if founders is not None else _INVASION_FOUNDERS
        if not founder_rows:
            raise ConfigurationError("invasion founders require at least one host")
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        out_n = 0
        self_n = 0
        for index, (mating, window) in enumerate(founder_rows):
            if mating == "outcross":
                bits = OUTCROSS_OUT_BITS
                out_n += 1
            elif mating == "selfing":
                bits = OUTCROSS_SELFING_BITS
                self_n += 1
            else:
                raise ConfigurationError("mating must be outcross or selfing")
            oid = f"h{index}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _tape(bits, window),
                    initial_runtime_atp=birth_atp,
                    position=(index % world_size, index // world_size),
                )
            )
            roles[oid] = ROLE_PRIMARY
        spatial = str(founder_spatial_policy).strip() or "legacy_row"
        if spatial not in {"legacy_row", "food_patch_interleaved"}:
            raise ConfigurationError(
                "founder_spatial_policy must be legacy_row or food_patch_interleaved"
            )
        if spatial == "food_patch_interleaved":
            patch_list = list(
                food_patches if food_patches is not None else _DEFAULT_FOOD_PATCHES
            )
            if not patch_list:
                raise ConfigurationError(
                    "food_patch_interleaved requires a non-empty food patch set"
                )
            for index, org in enumerate(organisms):
                org.position = patch_list[index % len(patch_list)]
        intro = self_n / max(1, out_n + self_n)
        ancestral = _modal_window([window for _, window in founder_rows])
        parasite_windows = [ancestral for _ in range(parasite_n)]
        # Secondary role reserved for bookkeeping; parasites live in the env stock.
        roles["parasite_stock"] = ROLE_SECONDARY

        life = ClosedLoopHPLifeConfig(
            enabled=True,
            mutate_both_roles=True,
            role_by_id=tuple(sorted(roles.items())),
            kappa_enabled=False,
            outcross_enabled=True,
            outcross_runtime_atp=1.0,
            outcross_same_role_only=True,
            match_locus_enabled=True,
            mutation_stream_lock_roles=(),
            mating_locus_lock=bool(mating_locus_lock),
            selfing_birth_atp_endowment=float(selfing_birth_atp_endowment),
            mate_search_radius=mate_search_radius,
            outcross_mates_per_generation_cap=outcross_mates_per_generation_cap,
        )
        for org in organisms:
            silence_outcross_locus(org, life)
        assert_single_atp_owner(organisms)

        two_fold = bool(two_fold_cost_sex)
        soft_k = int(soft_carrying_capacity)
        if soft_k < 1:
            raise ConfigurationError("soft_carrying_capacity must be >= 1")
        basal = float(basal_runtime_atp_cost)
        if basal < 0.0:
            raise ConfigurationError("basal_runtime_atp_cost must be >= 0")
        refill_mode = str(passage_refill_mode).strip() or PASSAGE_REFILL_OFF
        bolus = float(resource_bolus_amount)
        if bolus < 0.0:
            raise ConfigurationError("resource_bolus_amount must be >= 0")
        patches = tuple(food_patches) if food_patches is not None else _DEFAULT_FOOD_PATCHES
        if refill_mode not in {PASSAGE_REFILL_OFF, PASSAGE_REFILL_GENERATION_BOUNDARY}:
            raise ConfigurationError(
                f"passage_refill_mode must be {PASSAGE_REFILL_OFF!r} or "
                f"{PASSAGE_REFILL_GENERATION_BOUNDARY!r}"
            )
        if refill_mode == PASSAGE_REFILL_OFF and bolus > 0.0:
            raise ConfigurationError(
                "resource_bolus_amount requires generation_boundary_resource_bolus mode"
            )
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(
                enabled=True,
                reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
                min_runtime_atp=1.0,
                parent_atp_cost=1.0,
                offspring_atp_fraction=0.25,
                max_population=soft_k,
            ),
            mutation=MutationConfig(bit_flip_rate=0.0),
            metabolism=MetabolicConfig(enabled=True, basal_runtime_atp_cost=basal),
            ticks_per_generation=2,
            sexual_recombination=SexualRecombinationConfig(
                enabled=True,
                same_length_only=True,
                recombination_prob=1.0,
                two_fold_cost_sex=two_fold,
                diploid_meiosis=False,
                max_birth_wait_ticks=chamber_max_birth_wait_ticks,
                timeout_policy=str(chamber_timeout_policy),
            ),
            closed_loop_hp_life=life,
        )
        world = World2D(width=world_size, height=world_size)
        for x in range(min(4, world_size)):
            for y in range(min(2, world_size)):
                world.place_resource((x, y), 4.0)
        runner = PopulationRunner(
            population=PopulationState(
                generation=0,
                tick=0,
                organisms=tuple(organisms),
                lineage=(),
                fitness=(),
            ),
            world=world,
            configs=configs,
        )
        hp_env = HostParasiteEnv(
            steal_fraction=steal_fraction,
            handling_time=float(handling_time),
        )
        sync = (
            "generation_boundary"
            if refill_mode == PASSAGE_REFILL_GENERATION_BOUNDARY
            else "none"
        )
        return cls(
            arm=arm,
            passage=passage,
            runner=runner,
            roles=dict(roles),
            hp_env=hp_env,
            parasite_windows=list(parasite_windows),
            ancestral_window=ancestral,
            seed=seed,
            virulence=float(virulence),
            parasite_mutation=float(parasite_mutation),
            intro_selfing_freq=float(intro),
            two_fold_cost_sex_applied=two_fold,
            birth_atp=float(birth_atp),
            basal_runtime_atp_cost=basal,
            soft_carrying_capacity=soft_k,
            passage_refill_mode=refill_mode,
            resource_bolus_amount=bolus,
            food_patches=patches,
            cumulative_resource_bolus_placed=0.0,
            passage_refill_sync=sync,
            mating_locus_lock=bool(mating_locus_lock),
            selfing_birth_atp_endowment=float(selfing_birth_atp_endowment),
            mate_search_radius=mate_search_radius,
            outcross_mates_per_generation_cap=outcross_mates_per_generation_cap,
        )

    def _hosts(self) -> list[GenesisOrganism]:
        return [
            org
            for org in self.runner.population.organisms
            if self.roles.get(org.id) == ROLE_PRIMARY
            or role_of(org.id, self.runner.configs.closed_loop_hp_life.role_map()) == ROLE_PRIMARY
        ]

    def _record_births(self, result) -> None:
        known = set(self.roles)
        lineage_by_id = {rec.organism_id: rec for rec in result.population.lineage}
        new_births: list[tuple[str, str]] = []
        for org in result.population.organisms:
            if org.id in known:
                continue
            rec = lineage_by_id.get(org.id)
            if rec is not None and rec.parent_id:
                new_births.append((rec.parent_id, org.id))
            else:
                # Orphan birth: treat as primary host for ecology census.
                self.roles[org.id] = ROLE_PRIMARY
        if new_births:
            life = with_inherited_birth_roles(
                self.runner.configs.closed_loop_hp_life, new_births
            )
            self.runner.configs = replace(self.runner.configs, closed_loop_hp_life=life)
            for parent_id, child_id in new_births:
                self.roles[child_id] = self.roles.get(parent_id, ROLE_PRIMARY)
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        for org in self.runner.population.organisms:
            mapped = role_of(org.id, role_map)
            if mapped is not None:
                self.roles[org.id] = mapped
        life = self.runner.configs.closed_loop_hp_life
        for org in self.runner.population.organisms:
            silence_outcross_locus(org, life)

    def _reset_env_hosts(self) -> None:
        self.hp_env.hosts.clear()
        self.hp_env.attempts.clear()
        self.hp_env.replication_events.clear()
        self.hp_env._handling_busy_remaining = 0.0

    def _apply_hp_env_contact(self) -> tuple[int, list[str]]:
        """Contact/debit via the arm's HostParasiteEnv. Returns debit count + matched windows."""

        if self.passage == PASSAGE_ABSENT:
            return 0, []
        hosts = self._hosts()
        if not hosts or not self.parasite_windows:
            return 0, []
        self._reset_env_hosts()
        for org in hosts:
            window = _window(org)
            task = _allele_task(window) if window else "allele_empty"
            self.hp_env.add_host(org.id, [task])

        matched_windows: list[str] = []
        debit_count = 0
        # Pair parasites round-robin onto hosts; inject succeeds only on allele overlap.
        for p_index, p_window in enumerate(self.parasite_windows):
            if not hosts:
                break
            host = hosts[p_index % len(hosts)]
            p_task = _allele_task(p_window)
            attempt = self.hp_env.try_horizontal_inject(
                host_id=host.id,
                parasite_id=f"p{self.tick_index}-{p_index}",
                parasite_tasks=[p_task],
                payload=(1,),
            )
            if not attempt.injected:
                continue
            retained = self.hp_env.host_retained_cpu(host.id)
            # Antagonistic steal magnitude → ATP debit scaled by virulence.
            steal = max(0.0, 1.0 - float(retained))
            debit = float(self.virulence) * steal
            if debit > 0.0:
                payable = min(host.atp_state.runtime_available, debit)
                if payable > 0.0:
                    host.atp_state.debit_runtime(
                        payable,
                        tick=self.tick_index,
                        organism_id=host.id,
                        codon="000",
                        action="HP_ENV_MATCH",
                        reason=HP_ENV_MATCH_REASON,
                    )
                    debit_count += 1
                    matched_windows.append(_window(host))
        # Drop hosts that exhausted ATP after contact.
        survivors = [
            org
            for org in self.runner.population.organisms
            if org.atp_state.runtime_available > 0.0
            or self.roles.get(org.id) != ROLE_PRIMARY
        ]
        self.runner.population = replace(
            self.runner.population, organisms=tuple(survivors)
        )
        return debit_count, matched_windows

    def _passage_update(self, matched_windows: Sequence[str], rng: RNGManager) -> None:
        if self.passage == PASSAGE_ABSENT:
            self.parasite_windows = []
            return
        if self.passage == PASSAGE_FROZEN:
            self.parasite_windows = [self.ancestral_window for _ in range(len(self.parasite_windows) or _DEFAULT_PARASITE_N)]
            return
        if self.passage != PASSAGE_COEVOLVE:
            return
        n = len(self.parasite_windows) or _DEFAULT_PARASITE_N
        source = list(matched_windows) if matched_windows else list(self.parasite_windows)
        if not source:
            source = [self.ancestral_window]
        nxt: list[str] = []
        for _ in range(n):
            parent = source[rng.randrange(0, len(source))]
            window = parent
            if self.parasite_mutation > 0.0 and rng.random() < self.parasite_mutation:
                window = _mutate_window(window, rng)
            nxt.append(window)
        self.parasite_windows = nxt

    def _census(self) -> None:
        hosts = self._hosts()
        out_n = sum(1 for org in hosts if _mating_name(org) == "outcross")
        self_n = sum(1 for org in hosts if _mating_name(org) == "selfing")
        self.outcross_by_generation.append(out_n)
        self.selfing_by_generation.append(self_n)
        self.host_frequencies.append(_frequency_state(hosts))
        self.parasite_frequencies.append(_parasite_freq(self.parasite_windows))

    def _apply_passage_refill(self) -> None:
        """Elena–Lenski generation-boundary resource bolus (plugin/env only)."""

        if self.passage_refill_mode != PASSAGE_REFILL_GENERATION_BOUNDARY:
            return
        if self.resource_bolus_amount <= 0.0:
            return
        placed = 0.0
        for pos in self.food_patches:
            self.runner.world.place_resource(pos, float(self.resource_bolus_amount))
            placed += float(self.resource_bolus_amount)
        self.cumulative_resource_bolus_placed += placed

    def living_host_census(self) -> int:
        hosts = self._hosts()
        return sum(1 for org in hosts if _mating_name(org) in {"outcross", "selfing"})

    def run_generations(self, generations: int) -> dict[str, object]:
        generations = int(generations)
        if generations < 1:
            raise ConfigurationError("generations must be >= 1")
        rng = RNGManager(seed=self.seed, namespace=f"hp-arm01-{self.arm}")
        for _ in range(generations):
            # CPS refill sync: bolus at generation boundary before population step.
            self._apply_passage_refill()
            result = self.runner.step_generation(seed=self.seed + self.tick_index + 1)
            self._record_births(result)
            debit_count, matched = self._apply_hp_env_contact()
            self.match_debits_by_generation.append(int(debit_count))
            self._passage_update(matched, rng.fork(f"passage/{self.tick_index}"))
            self._census()
            self.tick_index += 1
            assert_single_atp_owner(self.runner.population.organisms)
        return self.summary()

    def terminal_selfing_freq(self) -> float | None:
        if not self.outcross_by_generation or not self.selfing_by_generation:
            return None
        out_n = int(self.outcross_by_generation[-1])
        self_n = int(self.selfing_by_generation[-1])
        denom = out_n + self_n
        if denom <= 0:
            return None
        return self_n / denom

    def build_clocks(self) -> dict[str, FrequencyClock]:
        genotype = genotype_clock_from_windows(self.host_frequencies)
        mating = mating_mode_clock_from_counts(
            self.outcross_by_generation, self.selfing_by_generation
        )
        match_class = match_class_clock_from_contacts(
            match_debits_by_generation=self.match_debits_by_generation,
            host_frequencies=self.host_frequencies,
            parasite_frequencies=self.parasite_frequencies,
        )
        selfing_rate = selfing_rate_clock_from_counts(
            self.outcross_by_generation, self.selfing_by_generation
        )
        allele = allele_frequency_clock_from_windows(self.host_frequencies)
        return {
            CLOCK_GENOTYPE: genotype,
            CLOCK_MATING_MODE: mating,
            CLOCK_MATCH_CLASS: match_class,
            CLOCK_SELFING_RATE: selfing_rate,
            CLOCK_ALLELE_FREQ: allele,
        }

    def summary(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "passage": self.passage,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "clock_api": "PopulationRunner.step_generation",
            "phase_b_sexual_crossover": True,
            "hp_env_handling_time": self.hp_env.handling_time,
            "hp_env_id": id(self.hp_env),
            "two_fold_cost_sex_applied": self.two_fold_cost_sex_applied,
            "two_fold_cost_sex_note": (
                "SexualRecombinationConfig.two_fold_cost_sex remains False; "
                "mating-effort ATP is paid, Maynard Smith / Hamilton two-fold is unpaid"
            ),
            "intro_selfing_freq": self.intro_selfing_freq,
            "terminal_selfing_freq": self.terminal_selfing_freq(),
            "terminal_host_census": self.living_host_census(),
            "birth_atp": self.birth_atp,
            "basal_runtime_atp_cost": self.basal_runtime_atp_cost,
            "soft_carrying_capacity": self.soft_carrying_capacity,
            "passage_refill_mode": self.passage_refill_mode,
            "resource_bolus_amount": self.resource_bolus_amount,
            "passage_refill_sync": self.passage_refill_sync,
            "cumulative_resource_bolus_placed": self.cumulative_resource_bolus_placed,
            "food_patches": [list(p) for p in self.food_patches],
            "outcross_by_generation": list(self.outcross_by_generation),
            "selfing_by_generation": list(self.selfing_by_generation),
            "match_debits_by_generation": list(self.match_debits_by_generation),
            "generations_run": self.tick_index,
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "estimand": HP_ARM01_ESTIMAND,
            "revision": HP_ARM01_REVISION,
        }


def campaign_handling_ablation_pair(
    *,
    virulence: float = 8.0,
    seed: int = 101,
    generations: int = 2,
) -> dict[str, object]:
    """Holling ablation on the SAME HostParasiteEnv path the campaign uses."""

    off_arm = LifeLoopEcologyArm.boot(
        arm=ARM_COPASSAGED, virulence=virulence, seed=seed, handling_time=0.0
    )
    on_arm = LifeLoopEcologyArm.boot(
        arm=ARM_COPASSAGED, virulence=virulence, seed=seed, handling_time=2.0
    )
    off_arm.run_generations(generations)
    on_arm.run_generations(generations)
    off_snap = off_arm.hp_env.snapshot()
    on_snap = on_arm.hp_env.snapshot()
    return handling_ablation_digests(handling_off=off_snap, handling_on=on_snap)


@dataclass(frozen=True, slots=True)
class ThreeArmCampaignReport:
    """Life-loop-bound three-arm report. Flags stay false."""

    arms_present: tuple[str, ...]
    passage_map: dict[str, str]
    clocks: dict[str, FrequencyClock]
    clocks_by_arm: dict[str, dict[str, FrequencyClock]]
    clocks_complete: bool
    per_arm_clocks_ok: bool
    treatment_control_present: bool
    substrate: str
    life_loop_bound: bool
    estimand: str
    slowinski_contrast_holds: bool
    slowinski_invasion_holds: bool
    legacy_three_freq_contrast_holds: bool
    selfing_freq_by_arm: dict[str, float | None]
    intro_selfing_freq: float
    pearl_measurement_attached: bool
    two_fold_cost_sex_applied: bool
    claim_ceiling: str
    max_allowed_ceiling: str
    red_queen_proved: bool
    biological_red_queen_proved: bool
    confirmatory_horizon_deferred: bool
    revision: str
    digest: str
    notes: str
    hp_env_ids_by_arm: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "arms_present": list(self.arms_present),
            "passage_map": dict(self.passage_map),
            "arm_meanings": dict(ARM_MEANING),
            "clocks": {name: clock.to_dict() for name, clock in sorted(self.clocks.items())},
            "clocks_by_arm": {
                arm: {name: clock.to_dict() for name, clock in sorted(clocks.items())}
                for arm, clocks in sorted(self.clocks_by_arm.items())
            },
            "clocks_complete": self.clocks_complete,
            "per_arm_clocks_ok": self.per_arm_clocks_ok,
            "treatment_control_present": self.treatment_control_present,
            "substrate": self.substrate,
            "life_loop_bound": self.life_loop_bound,
            "estimand": self.estimand,
            "accept_path": HP_ARM01_ESTIMAND,
            "slowinski_invasion_holds": self.slowinski_invasion_holds,
            "slowinski_contrast_holds": self.slowinski_contrast_holds,
            "legacy_three_freq_contrast_holds": self.legacy_three_freq_contrast_holds,
            "legacy_three_freq_is_accept_path": False,
            "selfing_freq_by_arm": dict(self.selfing_freq_by_arm),
            "intro_selfing_freq": self.intro_selfing_freq,
            "pearl_measurement_attached": self.pearl_measurement_attached,
            "two_fold_cost_sex_applied": self.two_fold_cost_sex_applied,
            "two_fold_cost_sex_note": (
                "unpaid; mating-effort ATP only; not Maynard Smith / Hamilton two-fold"
            ),
            "claim_ceiling": self.claim_ceiling,
            "max_allowed_ceiling": self.max_allowed_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "confirmatory_horizon_deferred": self.confirmatory_horizon_deferred,
            "sexual_maintenance_claimed": False,
            "morral_outcrossing_maintenance_is_secondary": True,
            "shared_modifier_refused_as_primary_substrate": True,
            "hp_env_ids_by_arm": dict(self.hp_env_ids_by_arm),
            "revision": self.revision,
        }
        payload["digest"] = self.digest
        return payload


def run_three_arm_frequency_campaign(
    *,
    virulence: float = 32.0,
    generations: int = 8,
    seed: int = 101,
    attach_pearl_measurement: bool = False,
    handling_time: float = _DEFAULT_HANDLING_TIME,
    parasite_mutation: float = 0.5,
    birth_atp: float = _DEFAULT_BIRTH_ATP,
    parasite_n: int = _DEFAULT_PARASITE_N,
    founders: Sequence[tuple[str, str]] | None = None,
    soft_carrying_capacity: int = _DEFAULT_SOFT_CARRYING_CAPACITY,
    basal_runtime_atp_cost: float = _DEFAULT_BASAL_ATP_COST,
    passage_refill_mode: str = _DEFAULT_PASSAGE_REFILL_MODE,
    resource_bolus_amount: float = _DEFAULT_RESOURCE_BOLUS_AMOUNT,
    food_patches: Sequence[tuple[int, int]] | None = None,
) -> ThreeArmCampaignReport:
    """Run three ecology arms on life-loop + Phase B + HostParasiteEnv.

    Primary substrate is ``PopulationRunner.step_generation`` (GenesisEngine
    clock) with Phase B sexual crossover and per-arm ``HostParasiteEnv``
    contact. ``run_shared_modifier`` is not the primary substrate.

    Short generation counts are scaffolding; confirmatory horizon requires the
    locked prereg in ``closed_loop_hp_arm01_confirm``. Prefer honest FAIL on
    the Slowinski invasion contrast over soft-pass theater.
    """

    assert_ecology_arm_taxonomy()
    arms: dict[str, LifeLoopEcologyArm] = {}
    clocks_by_arm: dict[str, dict[str, FrequencyClock]] = {}
    freqs: dict[str, float | None] = {}
    hp_env_ids: dict[str, int] = {}
    intro_freq = 0.0

    for arm_name in ECOLOGY_ARMS:
        arm = LifeLoopEcologyArm.boot(
            arm=arm_name,
            virulence=virulence,
            seed=seed,
            handling_time=handling_time,
            parasite_mutation=parasite_mutation,
            birth_atp=birth_atp,
            parasite_n=parasite_n,
            founders=founders,
            soft_carrying_capacity=soft_carrying_capacity,
            basal_runtime_atp_cost=basal_runtime_atp_cost,
            passage_refill_mode=passage_refill_mode,
            resource_bolus_amount=resource_bolus_amount,
            food_patches=food_patches,
        )
        arm.run_generations(generations)
        arms[arm_name] = arm
        clocks_by_arm[arm_name] = arm.build_clocks()
        freqs[arm_name] = arm.terminal_selfing_freq()
        hp_env_ids[arm_name] = id(arm.hp_env)
        intro_freq = arm.intro_selfing_freq

    # Campaign-level required clocks: one digest-backed set per clock name,
    # taken as the treatment (copassaged) arm's per-arm clocks — not a
    # concatenation across arms. Mating-mode series must not be concatenated.
    treatment_clocks = clocks_by_arm[ARM_COPASSAGED]
    clocks = {
        CLOCK_GENOTYPE: treatment_clocks[CLOCK_GENOTYPE],
        CLOCK_MATING_MODE: treatment_clocks[CLOCK_MATING_MODE],
        CLOCK_MATCH_CLASS: treatment_clocks[CLOCK_MATCH_CLASS],
    }
    clocks_ok = required_clocks_complete(clocks)
    per_arm_ok = per_arm_clocks_complete(clocks_by_arm)
    arms_present = tuple(ECOLOGY_ARMS)
    treatment_control = set(arms_present) == set(ECOLOGY_ARMS)

    invasion = slowinski_invasion_contrast(
        intro_selfing_freq=intro_freq,
        final_selfing_avirulent=freqs[ARM_AVIRULENT],
        final_selfing_fixed=freqs[ARM_FIXED],
        final_selfing_copassaged=freqs[ARM_COPASSAGED],
    )
    legacy = slowinski_selfing_invasion_contrast(
        selfing_freq_avirulent=freqs[ARM_AVIRULENT],
        selfing_freq_fixed=freqs[ARM_FIXED],
        selfing_freq_copassaged=freqs[ARM_COPASSAGED],
    )
    # Accept path is invasion, not legacy three-freq inequality.
    contrast = invasion
    refuse_shared_modifier_as_slowinski_pass(
        substrate=SUBSTRATE_LIFE_LOOP, contrast_holds=contrast
    )

    life_loop_bound = True
    ceiling_cap = max_allowed_claim_ceiling(
        clocks_complete=clocks_ok,
        treatment_control_present=treatment_control,
        substrate_life_loop_bound=life_loop_bound,
        per_arm_clocks_ok=per_arm_ok,
        slowinski_invasion_holds=invasion,
    )
    reported_ceiling = (
        CLAIM_CEILING_CANDIDATE
        if invasion and ceiling_cap == CLAIM_CEILING_CANDIDATE
        else CLAIM_CEILING_OBSERVATION
    )

    pearl_attached = False
    if attach_pearl_measurement:
        if not per_arm_ok:
            raise ConfigurationError(
                "Pearl / SPC measurement clauses require complete per-arm frequency clocks first"
            )
        # Thin Pearl pair on short pure arms — measurement only, new costless cells.
        frozen_out = run_match_arm(
            mating="outcross",
            passage=PASSAGE_FROZEN,
            virulence=virulence,
            generations=min(generations, 4),
            seed=seed,
        )
        frozen_self = run_match_arm(
            mating="selfing",
            passage=PASSAGE_FROZEN,
            virulence=virulence,
            generations=min(generations, 4),
            seed=seed,
        )
        costless_out = run_match_arm(
            mating="outcross",
            passage=PASSAGE_COSTLESS,
            virulence=virulence,
            generations=min(generations, 4),
            seed=seed,
        )
        costless_self = run_match_arm(
            mating="selfing",
            passage=PASSAGE_COSTLESS,
            virulence=virulence,
            generations=min(generations, 4),
            seed=seed,
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
            raise ConfigurationError("Pearl / SPC measurement must not set Red Queen flags")
        pearl_attached = True

    note = (
        "slowinski_invasion_holds"
        if invasion
        else "slowinski_invasion_fail_recorded_honestly"
    )
    if generations < 48:
        note = f"{note};confirmatory_horizon_deferred_short_scaffold"

    two_fold = any(arm.two_fold_cost_sex_applied for arm in arms.values())
    report = ThreeArmCampaignReport(
        arms_present=arms_present,
        passage_map=dict(ARM_TO_PASSAGE),
        clocks=clocks,
        clocks_by_arm=clocks_by_arm,
        clocks_complete=clocks_ok,
        per_arm_clocks_ok=per_arm_ok,
        treatment_control_present=treatment_control,
        substrate=SUBSTRATE_LIFE_LOOP,
        life_loop_bound=life_loop_bound,
        estimand=HP_ARM01_ESTIMAND,
        slowinski_contrast_holds=contrast,
        slowinski_invasion_holds=invasion,
        legacy_three_freq_contrast_holds=legacy,
        selfing_freq_by_arm=freqs,
        intro_selfing_freq=intro_freq,
        pearl_measurement_attached=pearl_attached,
        two_fold_cost_sex_applied=two_fold,
        claim_ceiling=reported_ceiling,
        max_allowed_ceiling=ceiling_cap,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        confirmatory_horizon_deferred=generations < 48,
        revision=HP_ARM01_REVISION,
        digest="",
        notes=note,
        hp_env_ids_by_arm=hp_env_ids,
    )
    digest = _digest({k: v for k, v in report.to_dict().items() if k != "digest"})
    return ThreeArmCampaignReport(
        arms_present=report.arms_present,
        passage_map=report.passage_map,
        clocks=report.clocks,
        clocks_by_arm=report.clocks_by_arm,
        clocks_complete=report.clocks_complete,
        per_arm_clocks_ok=report.per_arm_clocks_ok,
        treatment_control_present=report.treatment_control_present,
        substrate=report.substrate,
        life_loop_bound=report.life_loop_bound,
        estimand=report.estimand,
        slowinski_contrast_holds=report.slowinski_contrast_holds,
        slowinski_invasion_holds=report.slowinski_invasion_holds,
        legacy_three_freq_contrast_holds=report.legacy_three_freq_contrast_holds,
        selfing_freq_by_arm=report.selfing_freq_by_arm,
        intro_selfing_freq=report.intro_selfing_freq,
        pearl_measurement_attached=report.pearl_measurement_attached,
        two_fold_cost_sex_applied=report.two_fold_cost_sex_applied,
        claim_ceiling=report.claim_ceiling,
        max_allowed_ceiling=report.max_allowed_ceiling,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        confirmatory_horizon_deferred=report.confirmatory_horizon_deferred,
        revision=report.revision,
        digest=digest,
        notes=report.notes,
        hp_env_ids_by_arm=report.hp_env_ids_by_arm,
    )


def handling_ablation_digests(
    *,
    handling_off: Mapping[str, object],
    handling_on: Mapping[str, object],
) -> dict[str, object]:
    """Compare HostParasiteEnv snapshots with handling-time off vs on.

    Thin Holling handling lives only in the HP env port. Digests must differ
    when handling changes outcomes; identical digests fail the ablation pair.
    Prefer ``campaign_handling_ablation_pair`` so ablation uses the campaign
    env path. Does not raise claim ceilings or set Red Queen flags.
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
        "campaign_env_path": True,
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
    "CLOCK_ALLELE_FREQ",
    "CLOCK_GENOTYPE",
    "CLOCK_MATCH_CLASS",
    "CLOCK_MATING_MODE",
    "CLOCK_SELFING_RATE",
    "ECOLOGY_ARMS",
    "HP_ARM01_ESTIMAND",
    "HP_ARM01_REVISION",
    "INVASION_CLOCKS",
    "PASSAGE_REFILL_GENERATION_BOUNDARY",
    "PASSAGE_REFILL_OFF",
    "REQUIRED_CLOCKS",
    "SUBSTRATE_FORBIDDEN_PRIMARY",
    "SUBSTRATE_LIFE_LOOP",
    "FrequencyClock",
    "LifeLoopEcologyArm",
    "ThreeArmCampaignReport",
    "allele_frequency_clock_from_windows",
    "assert_ecology_arm_taxonomy",
    "build_frequency_clock",
    "campaign_handling_ablation_pair",
    "ecology_arm_to_passage",
    "genotype_clock_from_windows",
    "handling_ablation_digests",
    "match_class_clock_from_contacts",
    "mating_mode_clock_from_counts",
    "max_allowed_claim_ceiling",
    "passage_to_ecology_arm",
    "per_arm_clocks_complete",
    "refuse_shared_modifier_as_slowinski_pass",
    "required_clocks_complete",
    "run_three_arm_frequency_campaign",
    "selfing_rate_clock_from_counts",
    "slowinski_invasion_contrast",
    "slowinski_selfing_invasion_contrast",
]
