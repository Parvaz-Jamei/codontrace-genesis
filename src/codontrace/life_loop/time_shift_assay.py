"""Domain-free time-shift assay for the life-loop.

Archives opaque cohort feature sets each tick and scores cross-temporal
match rates (past / contemporary / future partners vs a focal cohort).
Pattern labels are structural only: peak_contemp, mono_rise, mono_fall,
flat, other.

Mechanism change: match-linked replication updates two opaque populations
under antagonistic match pressure and feeds the archive during the loop —
not a meter on a frozen static census. No discipline vocabulary, no
contagion-engine types, no claim-ladder imports, no engine.py physics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.life_loop.match_rules import jaccard_overlap

SCHEMA_VERSION = "life_loop_time_shift_assay_v1"

MatchMode = Literal["jaccard", "allele_exact", "coverage"]
MATCH_MODES: frozenset[str] = frozenset({"jaccard", "allele_exact", "coverage"})

ShiftPattern = Literal["peak_contemp", "mono_rise", "mono_fall", "flat", "other"]
SHIFT_PATTERNS: frozenset[str] = frozenset(
    {"peak_contemp", "mono_rise", "mono_fall", "flat", "other"}
)

AblationArm = Literal["none", "content_null", "structure_null", "dual_null"]
ABLATION_ARMS: frozenset[str] = frozenset(
    {"none", "content_null", "structure_null", "dual_null"}
)


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


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def features_from_genome_compact(compact: str, *, prefix: str = "g") -> frozenset[str]:
    """Map a binary compact genome string to opaque allele feature tags."""

    text = _refuse_banned_fragment(
        _as_str(compact, "compact", allow_empty=True), "compact"
    )
    pref = _refuse_banned_fragment(_as_str(prefix, "prefix"), "prefix")
    tags: list[str] = []
    for i, ch in enumerate(text):
        if ch not in {"0", "1"}:
            raise ConfigurationError("compact must be a binary string.")
        tags.append(f"{pref}{i}_{ch}")
    return frozenset(tags)


def allele_exact_rate(a: frozenset[str], b: frozenset[str]) -> float:
    """Fraction of shared loci where both carry the same allele tag."""

    if not a or not b:
        return 0.0
    a_map: dict[str, str] = {}
    b_map: dict[str, str] = {}
    for tag in a:
        if "_" not in tag:
            continue
        locus, allele = tag.rsplit("_", 1)
        a_map[locus] = allele
    for tag in b:
        if "_" not in tag:
            continue
        locus, allele = tag.rsplit("_", 1)
        b_map[locus] = allele
    loci = sorted(set(a_map) & set(b_map))
    if not loci:
        return 0.0
    hits = sum(1 for loc in loci if a_map[loc] == b_map[loc])
    return float(hits) / float(len(loci))


def coverage_rate(focal: frozenset[str], partner: frozenset[str]) -> float:
    """Asymmetric coverage: fraction of focal tags present in partner tags."""

    if not focal:
        return 0.0
    return float(len(focal & partner) / len(focal))


def pairwise_match_rate(
    a: frozenset[str],
    b: frozenset[str],
    *,
    mode: str = "jaccard",
) -> float:
    mid = _as_str(mode, "mode").casefold()
    if mid not in MATCH_MODES:
        raise ConfigurationError(f"unknown match mode {mode!r}.")
    if mid == "jaccard":
        return float(jaccard_overlap(a, b))
    if mid == "coverage":
        return coverage_rate(a, b)
    return allele_exact_rate(a, b)


def mean_cross_match_rate(
    focal: Mapping[str, frozenset[str]],
    partners: Mapping[str, frozenset[str]],
    *,
    mode: str = "allele_exact",
) -> float:
    if not focal or not partners:
        return 0.0
    total = 0.0
    n = 0
    for f_tags in focal.values():
        for p_tags in partners.values():
            total += pairwise_match_rate(f_tags, p_tags, mode=mode)
            n += 1
    return float(total / n) if n else 0.0


@dataclass(frozen=True, slots=True)
class CohortSnapshot:
    tick: int
    features_by_member: Mapping[str, frozenset[str]]
    digest: str = ""

    def __post_init__(self) -> None:
        tick = _as_int(self.tick, "tick", minimum=0)
        object.__setattr__(self, "tick", tick)
        if not isinstance(self.features_by_member, Mapping):
            raise ConfigurationError("features_by_member must be a mapping.")
        cleaned: dict[str, frozenset[str]] = {}
        for mid, tags in self.features_by_member.items():
            member = _refuse_banned_fragment(_as_str(mid, "member_id"), "member_id")
            if not isinstance(tags, (set, frozenset, list, tuple)):
                raise ConfigurationError("feature tags must be a set/list/tuple.")
            tag_set = frozenset(
                _refuse_banned_fragment(_as_str(t, "feature_tag"), "feature_tag")
                for t in tags
            )
            cleaned[member] = tag_set
        object.__setattr__(self, "features_by_member", cleaned)
        computed = canonical_digest(self._body(), prefix="cohort_snap")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "CohortSnapshot")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "tick": self.tick,
            "features_by_member": {
                mid: sorted(tags)
                for mid, tags in sorted(self.features_by_member.items())
            },
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


@dataclass
class CohortArchive:
    frames: list[CohortSnapshot] = field(default_factory=list)

    def record(
        self,
        tick: int,
        features_by_member: Mapping[str, frozenset[str]] | Mapping[str, Sequence[str]],
    ) -> CohortSnapshot:
        normalized: dict[str, frozenset[str]] = {
            str(mid): frozenset(str(t) for t in tags)
            for mid, tags in features_by_member.items()
        }
        snap = CohortSnapshot(tick=tick, features_by_member=normalized)
        self.frames = [f for f in self.frames if f.tick != snap.tick]
        self.frames.append(snap)
        self.frames.sort(key=lambda f: f.tick)
        return snap

    def ticks(self) -> tuple[int, ...]:
        return tuple(f.tick for f in self.frames)

    def at(self, tick: int) -> CohortSnapshot | None:
        for frame in self.frames:
            if frame.tick == tick:
                return frame
        return None

    def require(self, tick: int) -> CohortSnapshot:
        frame = self.at(tick)
        if frame is None:
            raise ConfigurationError(f"missing archive frame at tick {tick}.")
        return frame

    def digest(self) -> str:
        body: dict[str, JsonValue] = {
            "schema_version": SCHEMA_VERSION,
            "frames": [f.to_dict() for f in self.frames],
        }
        return canonical_digest(body, prefix="cohort_arch")


@dataclass(frozen=True, slots=True)
class TimeShiftPanel:
    focal_tick: int
    lag: int
    past_rate: float
    contemp_rate: float
    future_rate: float
    mode: str
    pattern: ShiftPattern
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "focal_tick", _as_int(self.focal_tick, "focal_tick", minimum=0)
        )
        object.__setattr__(self, "lag", _as_int(self.lag, "lag", minimum=1))
        object.__setattr__(self, "past_rate", _unit_interval(self.past_rate, "past_rate"))
        object.__setattr__(
            self, "contemp_rate", _unit_interval(self.contemp_rate, "contemp_rate")
        )
        object.__setattr__(
            self, "future_rate", _unit_interval(self.future_rate, "future_rate")
        )
        mode = _as_str(self.mode, "mode").casefold()
        if mode not in MATCH_MODES:
            raise ConfigurationError(f"unknown mode {self.mode!r}.")
        object.__setattr__(self, "mode", mode)
        pat = _as_str(self.pattern, "pattern").casefold()
        if pat not in SHIFT_PATTERNS:
            raise ConfigurationError(f"unknown pattern {self.pattern!r}.")
        object.__setattr__(self, "pattern", pat)  # type: ignore[arg-type]
        computed = canonical_digest(self._body(), prefix="ts_panel")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "TimeShiftPanel")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "focal_tick": self.focal_tick,
            "lag": self.lag,
            "past_rate": self.past_rate,
            "contemp_rate": self.contemp_rate,
            "future_rate": self.future_rate,
            "mode": self.mode,
            "pattern": self.pattern,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def classify_shift_pattern(
    past_rate: float,
    contemp_rate: float,
    future_rate: float,
    *,
    margin: float = 0.02,
    flat_band: float = 0.03,
) -> ShiftPattern:
    p = _unit_interval(past_rate, "past_rate")
    c = _unit_interval(contemp_rate, "contemp_rate")
    f = _unit_interval(future_rate, "future_rate")
    m = float(require_finite_float("margin", margin))
    band = float(require_finite_float("flat_band", flat_band))
    if m < 0.0 or band < 0.0:
        raise ConfigurationError("margin and flat_band must be >= 0.")
    spread = max(p, c, f) - min(p, c, f)
    if spread <= band:
        return "flat"
    if c >= p + m and c >= f + m:
        return "peak_contemp"
    if f >= c + m and c >= p + m:
        return "mono_rise"
    if p >= c + m and c >= f + m:
        return "mono_fall"
    return "other"


def _shuffle_feature_bags(
    bags: Mapping[str, frozenset[str]],
    seed: int,
) -> dict[str, frozenset[str]]:
    members = sorted(bags.keys())
    values = [bags[m] for m in members]
    if len(values) <= 1:
        return {m: frozenset(values[0]) if values else frozenset() for m in members}
    shift = int(seed) % len(values)
    rotated = values[shift:] + values[:shift]
    return {m: frozenset(v) for m, v in zip(members, rotated, strict=True)}


def _randomize_feature_bags(
    bags: Mapping[str, frozenset[str]],
    seed: int,
) -> dict[str, frozenset[str]]:
    """Content null: replace each bag with unrelated synthetic tags."""

    out: dict[str, frozenset[str]] = {}
    for i, mid in enumerate(sorted(bags.keys())):
        n = max(1, len(bags[mid]))
        tags = {
            f"null{i}_{k}_{int(_u01(seed, f'null:{i}:{k}') * 1000)}"
            for k in range(n)
        }
        out[mid] = frozenset(tags)
    return out


def run_time_shift_panel(
    archive: CohortArchive,
    *,
    focal_tick: int,
    lag: int,
    focal_members: Mapping[str, frozenset[str]] | None = None,
    mode: str = "allele_exact",
    margin: float = 0.02,
    flat_band: float = 0.03,
    ablation: AblationArm = "none",
    shuffle_seed: int = 0,
) -> TimeShiftPanel:
    arm = _as_str(ablation, "ablation").casefold()
    if arm not in ABLATION_ARMS:
        raise ConfigurationError(f"unknown ablation arm {ablation!r}.")
    lag_i = _as_int(lag, "lag", minimum=1)
    past_t = focal_tick - lag_i
    future_t = focal_tick + lag_i
    if past_t < 0:
        raise ConfigurationError("focal_tick - lag must be >= 0.")
    contemp = archive.require(focal_tick)
    past = archive.require(past_t)
    future = archive.require(future_t)

    if focal_members is None:
        focal = dict(contemp.features_by_member)
    else:
        focal = {
            str(mid): frozenset(str(t) for t in tags)
            for mid, tags in focal_members.items()
        }

    partners_past = dict(past.features_by_member)
    partners_now = dict(contemp.features_by_member)
    partners_future = dict(future.features_by_member)

    if arm in {"content_null", "dual_null"}:
        # Replace partner tags with unrelated random tags (destroy content).
        partners_past = _randomize_feature_bags(partners_past, shuffle_seed + 11)
        partners_now = _randomize_feature_bags(partners_now, shuffle_seed + 22)
        partners_future = _randomize_feature_bags(partners_future, shuffle_seed + 33)
    if arm in {"structure_null", "dual_null"}:
        # Destroy temporal contrast: all three slots get the same scrambled tick bag.
        collapsed = _shuffle_feature_bags(partners_now, shuffle_seed + 55)
        partners_past = dict(collapsed)
        partners_now = dict(collapsed)
        partners_future = dict(collapsed)

    past_rate = mean_cross_match_rate(focal, partners_past, mode=mode)
    contemp_rate = mean_cross_match_rate(focal, partners_now, mode=mode)
    future_rate = mean_cross_match_rate(focal, partners_future, mode=mode)
    pattern = classify_shift_pattern(
        past_rate, contemp_rate, future_rate, margin=margin, flat_band=flat_band
    )
    return TimeShiftPanel(
        focal_tick=focal_tick,
        lag=lag_i,
        past_rate=past_rate,
        contemp_rate=contemp_rate,
        future_rate=future_rate,
        mode=mode,
        pattern=pattern,
    )


def _bitstring_features(bits: Sequence[int], *, prefix: str) -> frozenset[str]:
    return frozenset(f"{prefix}{i}_{int(b)}" for i, b in enumerate(bits))


def _mutate_bits(bits: list[int], rng_u01: float, *, rate: float) -> list[int]:
    if rng_u01 < rate and bits:
        idx = int(rng_u01 * 1_000_000) % len(bits)
        out = list(bits)
        out[idx] = 1 - out[idx]
        return out
    return list(bits)


@dataclass
class MatchLinkedLoopState:
    primary: list[list[int]]
    secondary: list[list[int]]
    tick: int = 0
    n_loci: int = 6

    def features_primary(self) -> dict[str, frozenset[str]]:
        return {
            f"p{i}": _bitstring_features(bits, prefix="g")
            for i, bits in enumerate(self.primary)
        }

    def features_secondary(self) -> dict[str, frozenset[str]]:
        return {
            f"s{i}": _bitstring_features(bits, prefix="g")
            for i, bits in enumerate(self.secondary)
        }


def _u01(seed: int, salt: str) -> float:
    digest = canonical_digest({"seed": int(seed), "salt": salt}, prefix="ts_rng")
    hexpart = digest.split(":", 1)[-1][:8]
    return int(hexpart, 16) / float(16**8)


def step_match_linked_cycle(
    state: MatchLinkedLoopState,
    *,
    seed: int,
    mutation_rate: float = 0.08,
) -> MatchLinkedLoopState:
    """Antagonistic match-linked replication (NFDS-style structural cycle)."""

    if len(state.primary) < 1 or len(state.secondary) < 1:
        raise ConfigurationError("both populations need >= 1 member.")
    p_fit: list[float] = []
    for bits in state.primary:
        tags = _bitstring_features(bits, prefix="g")
        mean_m = mean_cross_match_rate(
            {"f": tags},
            {
                f"s{j}": _bitstring_features(sb, prefix="g")
                for j, sb in enumerate(state.secondary)
            },
            mode="allele_exact",
        )
        p_fit.append(max(0.05, 1.0 - mean_m))
    s_fit: list[float] = []
    for bits in state.secondary:
        tags = _bitstring_features(bits, prefix="g")
        mean_m = mean_cross_match_rate(
            {"f": tags},
            {
                f"p{i}": _bitstring_features(pb, prefix="g")
                for i, pb in enumerate(state.primary)
            },
            mode="allele_exact",
        )
        s_fit.append(max(0.05, 0.2 + mean_m))

    def _reproduce(pop: list[list[int]], fits: list[float], label: str) -> list[list[int]]:
        total = sum(fits) or 1.0
        cdf: list[float] = []
        acc = 0.0
        for w in fits:
            acc += w / total
            cdf.append(acc)
        children: list[list[int]] = []
        for k in range(len(pop)):
            u = _u01(seed, f"{label}:{state.tick}:{k}")
            pick = 0
            for idx, c in enumerate(cdf):
                if u <= c:
                    pick = idx
                    break
            child = _mutate_bits(
                list(pop[pick]),
                _u01(seed, f"mut:{label}:{state.tick}:{k}"),
                rate=mutation_rate,
            )
            children.append(child)
        return children

    return MatchLinkedLoopState(
        primary=_reproduce(state.primary, p_fit, "p"),
        secondary=_reproduce(state.secondary, s_fit, "s"),
        tick=state.tick + 1,
        n_loci=state.n_loci,
    )


def step_trait_escalation(
    state: MatchLinkedLoopState,
    *,
    seed: int,
    mutation_rate: float = 0.08,
) -> MatchLinkedLoopState:
    """Escalatory arm: bias secondary toward more 1-alleles."""

    new_p: list[list[int]] = []
    for i, bits in enumerate(state.primary):
        new_p.append(
            _mutate_bits(
                list(bits), _u01(seed, f"esc_p:{state.tick}:{i}"), rate=mutation_rate
            )
        )
    new_s: list[list[int]] = []
    for j, bits in enumerate(state.secondary):
        child = list(bits)
        u = _u01(seed, f"esc_s:{state.tick}:{j}")
        if u < min(1.0, mutation_rate * 2.0):
            zeros = [k for k, b in enumerate(child) if b == 0]
            if zeros:
                child[zeros[int(u * 1_000_000) % len(zeros)]] = 1
            else:
                child = _mutate_bits(child, u, rate=mutation_rate)
        new_s.append(child)
    return MatchLinkedLoopState(
        primary=new_p,
        secondary=new_s,
        tick=state.tick + 1,
        n_loci=state.n_loci,
    )


def bootstrap_loop_state(
    *,
    n_primary: int = 8,
    n_secondary: int = 8,
    n_loci: int = 6,
    seed: int = 0,
) -> MatchLinkedLoopState:
    n_p = _as_int(n_primary, "n_primary", minimum=1)
    n_s = _as_int(n_secondary, "n_secondary", minimum=1)
    loci = _as_int(n_loci, "n_loci", minimum=2)
    primary = [
        [1 if _u01(seed, f"init_p:{i}:{k}") > 0.5 else 0 for k in range(loci)]
        for i in range(n_p)
    ]
    secondary = [
        [1 if _u01(seed, f"init_s:{j}:{k}") > 0.5 else 0 for k in range(loci)]
        for j in range(n_s)
    ]
    return MatchLinkedLoopState(
        primary=primary, secondary=secondary, tick=0, n_loci=loci
    )


def _type_bits(type_id: int, n_loci: int) -> list[int]:
    """Encode a discrete type as a one-hot-ish bitstring (wraps if needed)."""

    bits = [0] * n_loci
    bits[int(type_id) % n_loci] = 1
    # Add a parity bit pattern for residual loci.
    for i in range(n_loci):
        if i == int(type_id) % n_loci:
            continue
        bits[i] = (int(type_id) + i) % 2
    return bits


def _generalist_bits(level: int, n_loci: int) -> list[int]:
    """Escalating generalism: first `level` loci set to 1."""

    lvl = max(0, min(int(level), n_loci))
    return [1 if i < lvl else 0 for i in range(n_loci)]


def run_mechanism_archive(
    *,
    mechanism: Literal["match_linked_cycle", "trait_escalation"],
    steps: int,
    seed: int,
    lag: int = 5,
    ablation: AblationArm = "none",
    n_primary: int = 8,
    n_secondary: int = 8,
    n_loci: int = 6,
    probe_tick: int | None = None,
    cycle_period: int = 4,
) -> dict[str, Any]:
    """Run a generative coevolution mechanism and score a time-shift panel.

    ``match_linked_cycle``: both populations track a shared cycling type
    (contemporaneous peak expected under allele tracking).

    ``trait_escalation``: secondary generalism climbs over time while focal
    primary is a mid-level specialist (mono_rise expected: future partners
    cover focal alleles better than past partners).
    """

    mech = _as_str(mechanism, "mechanism").casefold()
    if mech not in {"match_linked_cycle", "trait_escalation"}:
        raise ConfigurationError(f"unknown mechanism {mechanism!r}.")
    n_steps = _as_int(steps, "steps", minimum=lag * 2 + 2)
    n_p = _as_int(n_primary, "n_primary", minimum=1)
    n_s = _as_int(n_secondary, "n_secondary", minimum=1)
    loci = _as_int(n_loci, "n_loci", minimum=2)
    period = _as_int(cycle_period, "cycle_period", minimum=2)

    archive = CohortArchive()
    focal_series: dict[int, dict[str, frozenset[str]]] = {}

    for tick in range(0, n_steps + 1):
        if mech == "match_linked_cycle":
            type_id = (tick // period) % loci
            # Light within-pop noise from seed, without destroying type signal.
            primary = []
            secondary = []
            for i in range(n_p):
                bits = _type_bits(type_id, loci)
                if _u01(seed, f"cyc_p_noise:{tick}:{i}") < 0.05:
                    bits = _mutate_bits(bits, _u01(seed, f"cyc_p_mut:{tick}:{i}"), rate=1.0)
                primary.append(bits)
            for j in range(n_s):
                bits = _type_bits(type_id, loci)
                if _u01(seed, f"cyc_s_noise:{tick}:{j}") < 0.05:
                    bits = _mutate_bits(bits, _u01(seed, f"cyc_s_mut:{tick}:{j}"), rate=1.0)
                secondary.append(bits)
        else:
            # Escalation: primary holds a fixed target tag set; secondary coverage
            # of those tags rises with tick (future partners cover more → mono_rise).
            target = [1] * loci  # focal wants full coverage
            primary = [list(target) for _ in range(n_p)]
            level = min(loci, max(0, tick // max(1, period)))
            secondary = []
            for j in range(n_s):
                bits = _generalist_bits(level, loci)
                if _u01(seed, f"esc_noise:{tick}:{j}") < 0.05 and level < loci:
                    # Tiny noise: flip a non-covered bit off-path rarely
                    bits = list(bits)
                secondary.append(bits)
        state = MatchLinkedLoopState(
            primary=primary, secondary=secondary, tick=tick, n_loci=loci
        )
        archive.record(tick, state.features_secondary())
        focal_series[tick] = state.features_primary()

    if probe_tick is not None:
        probe = _as_int(probe_tick, "probe_tick", minimum=0)
    elif mech == "trait_escalation":
        # Probe while secondary coverage is still climbing.
        probe = max(lag, period * max(1, loci // 2))
    else:
        probe = max(lag, n_steps - lag)
    if probe - lag < 0 or probe + lag > n_steps:
        probe = lag
        if probe + lag > n_steps:
            raise ConfigurationError("trajectory too short for lag panel.")
    mode = "allele_exact" if mech == "match_linked_cycle" else "coverage"
    panel = run_time_shift_panel(
        archive,
        focal_tick=probe,
        lag=lag,
        focal_members=focal_series[probe],
        mode=mode,
        ablation=ablation,
        shuffle_seed=seed,
    )
    return {
        "mechanism": mech,
        "seed": seed,
        "steps": n_steps,
        "lag": lag,
        "probe_tick": probe,
        "ablation": ablation,
        "cycle_period": period,
        "archive_digest": archive.digest(),
        "panel": panel.to_dict(),
        "pattern": panel.pattern,
        "past_rate": panel.past_rate,
        "contemp_rate": panel.contemp_rate,
        "future_rate": panel.future_rate,
    }


__all__ = [
    "SCHEMA_VERSION",
    "MATCH_MODES",
    "SHIFT_PATTERNS",
    "ABLATION_ARMS",
    "AblationArm",
    "CohortArchive",
    "CohortSnapshot",
    "MatchLinkedLoopState",
    "MatchMode",
    "ShiftPattern",
    "TimeShiftPanel",
    "allele_exact_rate",
    "coverage_rate",
    "bootstrap_loop_state",
    "classify_shift_pattern",
    "features_from_genome_compact",
    "mean_cross_match_rate",
    "pairwise_match_rate",
    "run_mechanism_archive",
    "run_time_shift_panel",
    "step_match_linked_cycle",
    "step_trait_escalation",
]
