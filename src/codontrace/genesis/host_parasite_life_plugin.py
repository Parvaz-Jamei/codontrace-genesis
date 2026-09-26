"""Closed-loop HP life plugin hooked from step_population.

Domain-free. Mutates GenesisOrganism genomes via population.mutate_genome + the
live generation RNG stream (no parallel Mutation.point schedule, no parallel ATP bag).

P1 scope (hard): unify + engine-mutate scaffold.
P2 scope: opaque role_by_id map growth on birth (role inheritance).
P3 scope: kappa locus config (transfer lives in closed_loop_p3 via EnergyCoupling).
P4 scope: mutation_stream_lock_roles — skip mutate for locked roles here.
Birth energy partition itself lives in population.reproduce (engine-owned).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from codontrace.errors import ConfigurationError
from codontrace.genesis.organism import GenesisOrganism
from codontrace.rng import RNGManager

ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"
# Stable opaque tags (not parsed from organism id).
ROLE_TAG_PRIMARY = "clp1.role.primary"
ROLE_TAG_SECONDARY = "clp1.role.secondary"

P1_SCOPE = "unify_mutate_scaffold"
P2_SCOPE = "smith_fretwell_n1_birth_partition"
P3_SCOPE = "scalar_genetic_harm_help_kappa"
P4_SCOPE = "mutation_stream_lock_dual_arm_replay"
P5_SCOPE = "outcross_locus_mating_effort_cost"
P6_SCOPE = "matching_allele_passage_on_existing_atp"

# Fixed bit-window for kappa decode (both roles). Post-f(κ) clamp is NOT a gene.
KAPPA_BIT_START = 9
KAPPA_BIT_WIDTH = 6
# Clamp applied after f(κ); never written into gene decode as a default.
KAPPA_TRANSFER_CLAMP = 0.8
# One codon after κ. Width 3 so mutate_genome cannot trim a partial codon.
# "000" is selfing (WAIT). "001" is outcross (SENSE_FOOD). Never "111":
# that codon is COPY_SELF and would add an 8.0 action debit.
OUTCROSS_BIT_START = KAPPA_BIT_START + KAPPA_BIT_WIDTH
OUTCROSS_BIT_WIDTH = 3
OUTCROSS_SELFING_BITS = "000"
OUTCROSS_OUT_BITS = "001"
# Two codons after the mating locus. Silent when match_locus_enabled.
# Exact equality of this window is the individual matching-allele test.
MATCH_BIT_START = OUTCROSS_BIT_START + OUTCROSS_BIT_WIDTH
MATCH_BIT_WIDTH = 6


@dataclass(frozen=True, slots=True)
class ClosedLoopHPLifeConfig:
    """Opt-in closed-loop HP life plugin (P1 unify+mutate; P2 role map growth)."""

    enabled: bool = False
    mutate_both_roles: bool = True
    # Opaque role map: organism_id -> ROLE_PRIMARY|ROLE_SECONDARY (not id-prefix).
    role_by_id: tuple[tuple[str, str], ...] = ()
    # P3: kappa coupling flags (transfer applied outside engine.py).
    kappa_enabled: bool = False
    kappa_ablate: bool = False
    kappa_bit_start: int = KAPPA_BIT_START
    kappa_bit_width: int = KAPPA_BIT_WIDTH
    # P4: roles whose genomes must not be mutated by this plugin.
    mutation_stream_lock_roles: tuple[str, ...] = ()
    # When locks are active, engine MutationConfig should be rate 0 at birth;
    # unlocked roles mutate here at this rate (None → use mutation_config as-is).
    plugin_bit_flip_rate: float | None = None
    # P5: heritable outcross locus. Off leaves P1–P4 byte-identical.
    # Cost is mating-effort ATP, NOT Maynard Smith's two-fold cost
    # (that remains SexualRecombinationConfig.two_fold_cost_sex, default off).
    outcross_enabled: bool = False
    outcross_ablate: bool = False
    outcross_bit_start: int = OUTCROSS_BIT_START
    outcross_bit_width: int = OUTCROSS_BIT_WIDTH
    outcross_runtime_atp: float = 1.0
    outcross_same_role_only: bool = True
    # P6: silent recognition window. Off leaves P1–P5 byte-identical.
    match_locus_enabled: bool = False
    match_bit_start: int = MATCH_BIT_START
    match_bit_width: int = MATCH_BIT_WIDTH
    # Transmission contract / density mate-limitation (default off = prior digests).
    mating_locus_lock: bool = False
    selfing_birth_atp_endowment: float = 0.0
    mate_search_radius: int | None = None
    outcross_mates_per_generation_cap: int | None = None

    def __post_init__(self) -> None:
        if self.outcross_runtime_atp < 0.0:
            raise ConfigurationError("outcross_runtime_atp must be >= 0")
        if self.match_bit_start < 0 or self.match_bit_width <= 0:
            raise ConfigurationError("match window must start at >= 0 and have width > 0")
        if self.selfing_birth_atp_endowment < 0.0:
            raise ConfigurationError("selfing_birth_atp_endowment must be >= 0")
        if self.mate_search_radius is not None and int(self.mate_search_radius) < 0:
            raise ConfigurationError("mate_search_radius must be >= 0 when set")
        if (
            self.outcross_mates_per_generation_cap is not None
            and int(self.outcross_mates_per_generation_cap) < 1
        ):
            raise ConfigurationError(
                "outcross_mates_per_generation_cap must be >= 1 when set"
            )

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "enabled": self.enabled,
            "mutate_both_roles": self.mutate_both_roles,
            "role_by_id": {k: v for k, v in self.role_by_id},
            "kappa_enabled": self.kappa_enabled,
            "kappa_ablate": self.kappa_ablate,
            "kappa_bit_start": self.kappa_bit_start,
            "kappa_bit_width": self.kappa_bit_width,
            "mutation_stream_lock_roles": list(self.mutation_stream_lock_roles),
            "plugin_bit_flip_rate": self.plugin_bit_flip_rate,
            "p1_scope": P1_SCOPE,
            "p2_scope": P2_SCOPE,
            "p3_scope": P3_SCOPE,
            "p4_scope": P4_SCOPE,
        }
        outcross_nondefault = (
            self.outcross_enabled
            or self.outcross_ablate
            or self.outcross_bit_start != OUTCROSS_BIT_START
            or self.outcross_bit_width != OUTCROSS_BIT_WIDTH
            or self.outcross_runtime_atp != 1.0
            or self.outcross_same_role_only is not True
        )
        if outcross_nondefault:
            payload["outcross_enabled"] = self.outcross_enabled
            payload["outcross_ablate"] = self.outcross_ablate
            payload["outcross_bit_start"] = self.outcross_bit_start
            payload["outcross_bit_width"] = self.outcross_bit_width
            payload["outcross_runtime_atp"] = self.outcross_runtime_atp
            payload["outcross_same_role_only"] = self.outcross_same_role_only
            payload["p5_scope"] = P5_SCOPE
        match_nondefault = (
            self.match_locus_enabled
            or self.match_bit_start != MATCH_BIT_START
            or self.match_bit_width != MATCH_BIT_WIDTH
        )
        if match_nondefault:
            payload["match_locus_enabled"] = self.match_locus_enabled
            payload["match_bit_start"] = self.match_bit_start
            payload["match_bit_width"] = self.match_bit_width
            payload["p6_scope"] = P6_SCOPE
        tx_nondefault = (
            self.mating_locus_lock
            or self.selfing_birth_atp_endowment != 0.0
            or self.mate_search_radius is not None
            or self.outcross_mates_per_generation_cap is not None
        )
        if tx_nondefault:
            payload["mating_locus_lock"] = self.mating_locus_lock
            payload["selfing_birth_atp_endowment"] = self.selfing_birth_atp_endowment
            payload["mate_search_radius"] = self.mate_search_radius
            payload["outcross_mates_per_generation_cap"] = (
                self.outcross_mates_per_generation_cap
            )
        return payload

    def locked_roles(self) -> frozenset[str]:
        return frozenset(self.mutation_stream_lock_roles)

    @classmethod
    def from_dict(cls, data: object) -> ClosedLoopHPLifeConfig:
        if not isinstance(data, dict):
            return cls()
        raw_roles = data.get("role_by_id", {})
        roles: tuple[tuple[str, str], ...] = ()
        if isinstance(raw_roles, Mapping):
            roles = tuple((str(k), str(v)) for k, v in raw_roles.items())
        raw_locks = data.get("mutation_stream_lock_roles", ())
        locks: tuple[str, ...] = ()
        if isinstance(raw_locks, (list, tuple)):
            locks = tuple(str(item) for item in raw_locks)
        rate_raw = data.get("plugin_bit_flip_rate", None)
        rate: float | None
        if rate_raw is None:
            rate = None
        else:
            rate = float(rate_raw)
        return cls(
            enabled=bool(data.get("enabled", False)),
            mutate_both_roles=bool(data.get("mutate_both_roles", True)),
            role_by_id=roles,
            kappa_enabled=bool(data.get("kappa_enabled", False)),
            kappa_ablate=bool(data.get("kappa_ablate", False)),
            kappa_bit_start=int(data.get("kappa_bit_start", KAPPA_BIT_START)),
            kappa_bit_width=int(data.get("kappa_bit_width", KAPPA_BIT_WIDTH)),
            mutation_stream_lock_roles=locks,
            plugin_bit_flip_rate=rate,
            outcross_enabled=bool(data.get("outcross_enabled", False)),
            outcross_ablate=bool(data.get("outcross_ablate", False)),
            outcross_bit_start=int(data.get("outcross_bit_start", OUTCROSS_BIT_START)),
            outcross_bit_width=int(data.get("outcross_bit_width", OUTCROSS_BIT_WIDTH)),
            outcross_runtime_atp=float(data.get("outcross_runtime_atp", 1.0)),
            outcross_same_role_only=bool(data.get("outcross_same_role_only", True)),
            match_locus_enabled=bool(data.get("match_locus_enabled", False)),
            match_bit_start=int(data.get("match_bit_start", MATCH_BIT_START)),
            match_bit_width=int(data.get("match_bit_width", MATCH_BIT_WIDTH)),
            mating_locus_lock=bool(data.get("mating_locus_lock", False)),
            selfing_birth_atp_endowment=float(
                data.get("selfing_birth_atp_endowment", 0.0)
            ),
            mate_search_radius=(
                None
                if data.get("mate_search_radius", None) is None
                else int(data.get("mate_search_radius"))
            ),
            outcross_mates_per_generation_cap=(
                None
                if data.get("outcross_mates_per_generation_cap", None) is None
                else int(data.get("outcross_mates_per_generation_cap"))
            ),
        )

    def role_map(self) -> dict[str, str]:
        return dict(self.role_by_id)


def role_of(organism_id: str, role_by_id: Mapping[str, str] | None = None) -> str | None:
    """Resolve opaque role from explicit map only (never id-prefix parsing)."""

    if role_by_id is None:
        return None
    role = role_by_id.get(organism_id)
    if role in {ROLE_PRIMARY, ROLE_SECONDARY}:
        return role
    return None


def assert_single_atp_owner(organisms: Sequence[GenesisOrganism]) -> None:
    """Every organism must expose atp_state (no parallel HP accounts bag)."""

    for org in organisms:
        if not hasattr(org, "atp_state") or org.atp_state is None:
            raise ConfigurationError(
                f"organism {org.id} missing atp_state (two energy clocks)"
            )


def inherit_roles_for_births(
    role_by_id: Mapping[str, str],
    births: Sequence[tuple[str, str]],
) -> dict[str, str]:
    """Grow opaque role map: each child inherits its parent's role.

    ``births`` entries are ``(parent_id, child_id)``. Unmapped parents are skipped
    (child stays unmapped). Existing child entries are left unchanged.
    """

    roles = dict(role_by_id)
    for parent_id, child_id in births:
        if child_id in roles:
            continue
        parent_role = role_of(parent_id, roles)
        if parent_role is None:
            continue
        roles[child_id] = parent_role
    return roles


def with_inherited_birth_roles(
    config: ClosedLoopHPLifeConfig,
    births: Sequence[tuple[str, str]],
) -> ClosedLoopHPLifeConfig:
    """Return a new config whose role_by_id includes inherited child roles."""

    grown = inherit_roles_for_births(config.role_map(), births)
    return replace(config, role_by_id=tuple(sorted(grown.items())))



def decode_kappa(
    genome_bits: str,
    *,
    bit_start: int = KAPPA_BIT_START,
    bit_width: int = KAPPA_BIT_WIDTH,
    ablate: bool = False,
) -> float:
    """Decode κ ∈ [-1, +1] from a fixed bit window. Ablate forces 0.

    The transfer clamp (0.8) is intentionally NOT part of this decode.
    """

    if ablate:
        return 0.0
    if bit_width <= 0:
        raise ConfigurationError("kappa bit_width must be > 0")
    if bit_start < 0:
        raise ConfigurationError("kappa bit_start must be >= 0")
    bits = str(genome_bits)
    window = bits[bit_start : bit_start + bit_width]
    if len(window) < bit_width:
        window = window.ljust(bit_width, "0")
    if not window or any(ch not in "01" for ch in window):
        return 0.0
    unsigned = int(window, 2)
    max_u = (1 << bit_width) - 1
    if max_u <= 0:
        return 0.0
    return 2.0 * (unsigned / max_u) - 1.0


def kappa_transfer_amount(kappa: float, donor_available: float) -> float:
    """|transfer| = clamp(|f(κ)| × available, 0.8 × donor); f = identity."""

    available = float(donor_available)
    if available <= 0.0:
        return 0.0
    raw = abs(float(kappa)) * available
    ceiling = KAPPA_TRANSFER_CLAMP * available
    return min(raw, ceiling)


def decode_outcross(
    genome_bits: str,
    *,
    bit_start: int = OUTCROSS_BIT_START,
    bit_width: int = OUTCROSS_BIT_WIDTH,
    ablate: bool = False,
) -> bool:
    """True when the outcross codon is non-zero. Ablate or a short window is selfing."""

    if ablate:
        return False
    if bit_width <= 0:
        raise ConfigurationError("outcross bit_width must be > 0")
    if bit_start < 0:
        raise ConfigurationError("outcross bit_start must be >= 0")
    window = str(genome_bits)[bit_start : bit_start + bit_width]
    if len(window) < bit_width or any(ch not in "01" for ch in window):
        return False
    return int(window, 2) != 0


def outcross_runtime_cost(genome_bits: str, config: ClosedLoopHPLifeConfig) -> float:
    """Mating-effort ATP. Zero unless the locus is on. Not the two-fold cost."""

    if not config.outcross_enabled:
        return 0.0
    if not decode_outcross(
        genome_bits,
        bit_start=config.outcross_bit_start,
        bit_width=config.outcross_bit_width,
        ablate=config.outcross_ablate,
    ):
        return 0.0
    return float(config.outcross_runtime_atp)


def outcross_fee_debit(
    genome_bits: str, config: ClosedLoopHPLifeConfig
) -> tuple[float, str, str] | None:
    """Fee, codon label, and ledger reason. The motor writes the ATP row."""

    cost = outcross_runtime_cost(genome_bits, config)
    if cost <= 0.0:
        return None
    window = genome_bits[config.outcross_bit_start : config.outcross_bit_start + config.outcross_bit_width]
    codon = window or OUTCROSS_SELFING_BITS
    return cost, codon, "outcross_runtime_cost"


def copy_self_chamber_refusal(
    genome_bits: str, config: ClosedLoopHPLifeConfig, *, chamber_available: bool
) -> str | None:
    """Locus policy only. The motor decides how a refusal is recorded."""

    if resolve_copy_self_mode(genome_bits, config) == "chamber" and not chamber_available:
        return "outcross_chamber_required"
    return None


def resolve_copy_self_mode(genome_bits: str, config: ClosedLoopHPLifeConfig) -> str:
    """'default' when P5 is off. 'chamber' if the locus is on. Else 'asexual'."""

    if not config.outcross_enabled:
        return "default"
    if decode_outcross(
        genome_bits,
        bit_start=config.outcross_bit_start,
        bit_width=config.outcross_bit_width,
        ablate=config.outcross_ablate,
    ):
        return "chamber"
    return "asexual"


def outcross_entry_plan(
    organism: GenesisOrganism,
    config: ClosedLoopHPLifeConfig,
    *,
    remaining_after_parent_cost: float,
    projected_offspring_atp: float,
) -> tuple[float, str | None]:
    """Compare the mating fee with ATP the motor has already projected."""

    if resolve_copy_self_mode(organism.genome.to_compact(), config) != "chamber":
        return 0.0, None
    fee = outcross_runtime_cost(organism.genome.to_compact(), config)
    if fee <= 0.0:
        return 0.0, None
    if (
        projected_offspring_atp <= 0.0
        or remaining_after_parent_cost - projected_offspring_atp + 1e-12 < fee
    ):
        return fee, "outcross_runtime_cost_not_payable"
    return fee, None


def decode_recognition(
    genome_bits: str,
    *,
    bit_start: int = MATCH_BIT_START,
    bit_width: int = MATCH_BIT_WIDTH,
) -> str:
    """Silent recognition window. Empty when the tape is too short or not binary."""

    if bit_width <= 0 or bit_start < 0:
        raise ConfigurationError("recognition window is invalid")
    window = str(genome_bits)[bit_start : bit_start + bit_width]
    if len(window) < bit_width or any(ch not in "01" for ch in window):
        return ""
    return window


def coding_bits_for_execution(genome_bits: str, config: ClosedLoopHPLifeConfig) -> str:
    """Program the body runs. Mating and recognition windows stay off the brain."""

    bits = str(genome_bits)
    windows: list[tuple[int, int]] = []
    if config.outcross_enabled:
        windows.append((config.outcross_bit_start, config.outcross_bit_width))
        if not config.kappa_enabled:
            windows.append((config.kappa_bit_start, config.kappa_bit_width))
    if config.match_locus_enabled:
        windows.append((config.match_bit_start, config.match_bit_width))
    if not windows:
        return bits
    for start, width in sorted(windows, reverse=True):
        if start < 0 or width <= 0 or len(bits) < start + width:
            continue
        bits = bits[:start] + bits[start + width :]
    if not bits or len(bits) % 3 != 0:
        return str(genome_bits)
    return bits


def silence_outcross_locus(organism: GenesisOrganism, config: ClosedLoopHPLifeConfig) -> None:
    """Recompile actions from the coding prefix. Genome bits, including the locus, stay."""

    coding = coding_bits_for_execution(organism.genome.to_compact(), config)
    current = "".join(token.bits for token in organism.compiled_brain.tokens)
    if current == coding:
        return
    organism.compiled_brain = organism.ribosome.translate(coding).compiled_brain
    if organism._cursor >= len(organism.compiled_brain.tokens):
        organism._cursor = 0


def outcross_mates_compatible(
    parent_a_id: str, parent_b_id: str, config: ClosedLoopHPLifeConfig
) -> bool:
    if not config.outcross_same_role_only:
        return True
    role_a = role_of(parent_a_id, config.role_map())
    role_b = role_of(parent_b_id, config.role_map())
    if role_a is None or role_b is None:
        return False
    return role_a == role_b


def apply_closed_loop_hp_life(
    organisms: Sequence[GenesisOrganism],
    *,
    config: ClosedLoopHPLifeConfig,
    stream: RNGManager,
    mutation_config: object,
    tick: int,
) -> list[GenesisOrganism]:
    """Engine-mutate every role-tagged organism via mutate_genome + live stream.

    Must be invoked post-ATP-settle / pre-birth. Forks the generation stream;
    does not construct a parallel RNGManager(seed=...). Unmapped ids are skipped.
    """

    if not config.enabled:
        return list(organisms)
    assert_single_atp_owner(organisms)
    if not config.mutate_both_roles:
        return list(organisms)

    # Local import avoids circular import with population.py
    from codontrace.genesis.population import MutationConfig, mutate_genome

    if not isinstance(mutation_config, MutationConfig):
        raise ConfigurationError("closed_loop_hp_life requires MutationConfig")

    effective = mutation_config
    if config.plugin_bit_flip_rate is not None:
        effective = replace(
            mutation_config, bit_flip_rate=float(config.plugin_bit_flip_rate)
        )

    roles = config.role_map()
    locked = config.locked_roles()
    out: list[GenesisOrganism] = []
    for org in organisms:
        role = role_of(org.id, roles)
        if role is None:
            out.append(org)
            continue
        if role in locked:
            out.append(org)
            continue
        org_stream = stream.fork(f"clp1/{role}/{org.id}/{tick}")
        result = mutate_genome(org.genome, effective, rng=org_stream)
        org.genome = result.mutated_genome
        out.append(org)
    return out


def mating_codon_of(genome_bits: str, config: ClosedLoopHPLifeConfig) -> str:
    """Return the mating-locus codon (selfing 000 or outcross 001 window)."""

    start = config.outcross_bit_start
    width = config.outcross_bit_width
    window = str(genome_bits)[start : start + width]
    if len(window) < width:
        return OUTCROSS_SELFING_BITS
    return window


def lock_mating_locus_bits(
    genome_bits: str, *, parent_bits: str, config: ClosedLoopHPLifeConfig
) -> str:
    """Overwrite child mating codon with the declaring parent's codon."""

    if not config.mating_locus_lock or not config.outcross_enabled:
        return str(genome_bits)
    start = config.outcross_bit_start
    width = config.outcross_bit_width
    bits = str(genome_bits)
    parent = str(parent_bits)
    if len(bits) < start + width or len(parent) < start + width:
        return bits
    codon = parent[start : start + width]
    return bits[:start] + codon + bits[start + width :]


def apply_mating_locus_lock(
    child: GenesisOrganism,
    *,
    parent: GenesisOrganism,
    config: ClosedLoopHPLifeConfig,
) -> None:
    """Restore declaring parent's mating codon onto the child genome in place."""

    if not config.mating_locus_lock or not config.outcross_enabled:
        return
    parent_bits = parent.genome.to_compact()
    child_bits = child.genome.to_compact()
    locked = lock_mating_locus_bits(child_bits, parent_bits=parent_bits, config=config)
    if locked == child_bits:
        return
    from codontrace.genome import SemanticGenome

    child.genome = SemanticGenome.from_compact(locked, spec=child.genome.spec)
    silence_outcross_locus(child, config)


def apply_selfing_birth_endowment(
    child: GenesisOrganism,
    *,
    config: ClosedLoopHPLifeConfig,
    tick: int,
) -> None:
    """Top up selfing offspring ATP to the locked endowment (reproductive assurance)."""

    endowment = float(config.selfing_birth_atp_endowment)
    if endowment <= 0.0:
        return
    if resolve_copy_self_mode(child.genome.to_compact(), config) != "asexual":
        return
    current = float(child.atp_state.runtime_available)
    if current + 1e-12 >= endowment:
        return
    child.atp_state.credit_runtime(
        endowment - current,
        tick=tick,
        organism_id=child.id,
        codon="000",
        action="SELFING_BIRTH_ENDOWMENT",
        reason="reproductive_assurance_selfing_birth_atp",
    )


def mates_within_search_radius(
    position_a: tuple[int, int],
    position_b: tuple[int, int],
    *,
    radius: int | None,
) -> bool:
    """Manhattan neighborhood test; ``None`` radius means unlimited."""

    if radius is None:
        return True
    dist = abs(int(position_a[0]) - int(position_b[0])) + abs(
        int(position_a[1]) - int(position_b[1])
    )
    return dist <= int(radius)



__all__ = [
    "ROLE_PRIMARY",
    "ROLE_SECONDARY",
    "ROLE_TAG_PRIMARY",
    "ROLE_TAG_SECONDARY",
    "P1_SCOPE",
    "P2_SCOPE",
    "P3_SCOPE",
    "P4_SCOPE",
    "P5_SCOPE",
    "P6_SCOPE",
    "KAPPA_BIT_START",
    "KAPPA_BIT_WIDTH",
    "KAPPA_TRANSFER_CLAMP",
    "OUTCROSS_BIT_START",
    "OUTCROSS_BIT_WIDTH",
    "OUTCROSS_SELFING_BITS",
    "OUTCROSS_OUT_BITS",
    "MATCH_BIT_START",
    "MATCH_BIT_WIDTH",
    "ClosedLoopHPLifeConfig",
    "role_of",
    "assert_single_atp_owner",
    "inherit_roles_for_births",
    "with_inherited_birth_roles",
    "decode_kappa",
    "kappa_transfer_amount",
    "decode_outcross",
    "decode_recognition",
    "outcross_runtime_cost",
    "outcross_fee_debit",
    "copy_self_chamber_refusal",
    "resolve_copy_self_mode",
    "outcross_entry_plan",
    "coding_bits_for_execution",
    "silence_outcross_locus",
    "outcross_mates_compatible",
    "apply_closed_loop_hp_life",
    "mating_codon_of",
]
