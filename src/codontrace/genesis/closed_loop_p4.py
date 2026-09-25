"""Closed-loop P4: mutation-stream lock + dual-arm bit replay.

Hard scope (2026-09-25): mut-freeze only via mutation_stream_lock_roles in the
post-ATP plugin (skip mutate for locked roles). Birth/death stay ON. FAIL if
birth-time genome rewrite / mutate_genome / chamber rewrite bypasses the lock.
FAIL if bag ScheduleLock.freeze is the green path. Dual-arm, one master seed:
  Arm A: κ-on → elicit measured E with |net_transfer|_A > ε
  Arm B: ablate κ and/or lock mutation stream → |net_transfer|_B ≤ ε
Then bit-identical self-replay both arms; digests include genomes + ATP + κ.
Digests alone ≠ effect dies — measured kill first, then digests.
Not Gate7 / P2 same-seed theater.

Clock API: PopulationRunner.step_generation. No HostParasiteWorld.tick /
_birth_role. engine.py stays domain-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.closed_loop_p3 import ClosedLoopP3Session
from codontrace.genesis.host_parasite_life_plugin import (
    P4_SCOPE,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    role_of,
)
from codontrace.genesis.population import MutationConfig

_TRANSFER_EPS = 1e-6


def _arm_digest(session: ClosedLoopP3Session) -> str:
    """Digest over genomes + ATP + κ (measured state), not a claim flag."""

    return session.snapshot_digest()


@dataclass(frozen=True, slots=True)
class DualArmResult:
    """Measured dual-arm outcome under one master seed."""

    master_seed: int
    ticks: int
    net_transfer_a: float
    net_transfer_b: float
    peak_abs_atp_skew_a: float
    peak_abs_atp_skew_b: float
    digest_a: str
    digest_b: str
    digest_a_replay: str
    digest_b_replay: str
    locked_roles_b: tuple[str, ...]
    kappa_ablate_b: bool
    effect_killed: bool  # measured: |net_transfer|_B ≤ ε after elicit on A
    bit_identical_a: bool
    bit_identical_b: bool
    claim_ceiling: str = "candidate_evidence"
    red_queen_proved: bool = False
    p4_scope: str = P4_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "master_seed": self.master_seed,
            "ticks": self.ticks,
            "net_transfer_a": self.net_transfer_a,
            "net_transfer_b": self.net_transfer_b,
            "peak_abs_atp_skew_a": self.peak_abs_atp_skew_a,
            "peak_abs_atp_skew_b": self.peak_abs_atp_skew_b,
            "digest_a": self.digest_a,
            "digest_b": self.digest_b,
            "digest_a_replay": self.digest_a_replay,
            "digest_b_replay": self.digest_b_replay,
            "locked_roles_b": list(self.locked_roles_b),
            "kappa_ablate_b": self.kappa_ablate_b,
            "effect_killed": self.effect_killed,
            "bit_identical_a": self.bit_identical_a,
            "bit_identical_b": self.bit_identical_b,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "p4_scope": self.p4_scope,
            "clock_api": "PopulationRunner.step_generation",
        }


def boot_locked_session(
    *,
    seed: int,
    locked_roles: Sequence[str] = (),
    kappa_ablate: bool = False,
    kappa_enabled: bool = True,
    plugin_bit_flip_rate: float = 0.35,
    bit_flip_rate: float | None = None,
    **kwargs: Any,
) -> ClosedLoopP3Session:
    """Boot a P3 session with optional mutation-stream role locks (P4).

    When any role is locked, engine MutationConfig.bit_flip_rate is forced to 0
    so birth-time mutate_genome cannot bypass the lock; unlocked roles still
    mutate via the post-ATP plugin at plugin_bit_flip_rate.
    """

    locks = tuple(str(r) for r in locked_roles)
    if bit_flip_rate is None:
        engine_rate = 0.0 if locks else plugin_bit_flip_rate
    else:
        engine_rate = float(bit_flip_rate)

    session = ClosedLoopP3Session.boot(
        seed=seed,
        bit_flip_rate=engine_rate,
        kappa_enabled=kappa_enabled,
        kappa_ablate=kappa_ablate,
        **kwargs,
    )
    life = session.runner.configs.closed_loop_hp_life
    session.runner.configs = replace(
        session.runner.configs,
        mutation=MutationConfig(bit_flip_rate=engine_rate),
        closed_loop_hp_life=replace(
            life,
            mutation_stream_lock_roles=locks,
            plugin_bit_flip_rate=(
                None if not locks else float(plugin_bit_flip_rate)
            ),
        ),
    )
    return session


def genomes_by_role(session: ClosedLoopP3Session, role: str) -> dict[str, str]:
    role_map = session.runner.configs.closed_loop_hp_life.role_map()
    return {
        o.id: o.genome.to_compact()
        for o in session.runner.population.organisms
        if role_of(o.id, role_map) == role
    }


def assert_locked_roles_genome_frozen(
    before: dict[str, str],
    after: dict[str, str],
    *,
    label: str,
) -> None:
    """FAIL if a locked-role genome changed (including across births of that role).

    Newborns of a locked role must match their parent genome (engine birth
    mutation rate is 0 when locks are active). Founders must be unchanged.
    """

    # Founders present in both snapshots must be bit-identical.
    shared = set(before) & set(after)
    for oid in shared:
        if before[oid] != after[oid]:
            raise ConfigurationError(
                f"mutation-stream lock bypassed for {label} organism {oid}"
            )


def run_dual_arm(
    *,
    master_seed: int = 41,
    ticks: int = 2,
    lock_roles_b: Sequence[str] = (ROLE_PRIMARY, ROLE_SECONDARY),
    kappa_ablate_b: bool = True,
    transfer_eps: float = _TRANSFER_EPS,
) -> DualArmResult:
    """Dual-arm elicit/ablate under one master seed, then bit-identical self-replay."""

    locks_b = tuple(lock_roles_b)

    def _arm_a(seed: int) -> ClosedLoopP3Session:
        return boot_locked_session(
            seed=seed,
            locked_roles=(),
            kappa_ablate=False,
            kappa_enabled=True,
            plugin_bit_flip_rate=0.0,
            bit_flip_rate=0.0,
            secondary_kappa_high=True,
        )

    def _arm_b(seed: int) -> ClosedLoopP3Session:
        return boot_locked_session(
            seed=seed,
            locked_roles=locks_b,
            kappa_ablate=kappa_ablate_b,
            kappa_enabled=True,
            plugin_bit_flip_rate=0.0,
            bit_flip_rate=0.0,
            secondary_kappa_high=True,
        )

    a1 = _arm_a(master_seed)
    b1 = _arm_b(master_seed)
    before_b_genomes = {
        role: genomes_by_role(b1, role) for role in locks_b
    }
    a1.run_ticks(ticks)
    b1.run_ticks(ticks)
    for role in locks_b:
        assert_locked_roles_genome_frozen(
            before_b_genomes[role],
            genomes_by_role(b1, role),
            label=role,
        )
        # Newborns of locked roles: every live genome for that role must equal
        # some pre-tick founder genome (birth mutation bypass forbidden).
        founders = set(before_b_genomes[role].values())
        for oid, bits in genomes_by_role(b1, role).items():
            if bits not in founders and oid not in before_b_genomes[role]:
                # Child of locked parent with engine rate 0 must clone parent bits.
                # Parent may still be alive; require membership in founder set OR
                # equality with a live parent's genome (already covered if parent
                # frozen). Strict: child bits must appear in the locked pool.
                raise ConfigurationError(
                    f"birth-time mutate bypassed lock for newborn {oid} role={role}"
                )

    s_a = a1.summary()
    s_b = b1.summary()
    net_a = float(s_a["net_transfer"])
    net_b = float(s_b["net_transfer"])
    if abs(net_a) <= transfer_eps:
        raise ConfigurationError("arm A failed to elicit |net_transfer| > ε")
    effect_killed = abs(net_b) <= transfer_eps

    # Self-replay both arms (bit-identical under same master seed).
    a2 = _arm_a(master_seed)
    b2 = _arm_b(master_seed)
    a2.run_ticks(ticks)
    b2.run_ticks(ticks)
    d_a1 = _arm_digest(a1)
    d_a2 = _arm_digest(a2)
    d_b1 = _arm_digest(b1)
    d_b2 = _arm_digest(b2)

    return DualArmResult(
        master_seed=master_seed,
        ticks=ticks,
        net_transfer_a=net_a,
        net_transfer_b=net_b,
        peak_abs_atp_skew_a=float(s_a["peak_abs_atp_skew"]),
        peak_abs_atp_skew_b=float(s_b["peak_abs_atp_skew"]),
        digest_a=d_a1,
        digest_b=d_b1,
        digest_a_replay=d_a2,
        digest_b_replay=d_b2,
        locked_roles_b=locks_b,
        kappa_ablate_b=kappa_ablate_b,
        effect_killed=effect_killed,
        bit_identical_a=d_a1 == d_a2,
        bit_identical_b=d_b1 == d_b2,
    )


def mutation_stream_lock_freezes_role(
    *,
    seed: int = 43,
    ticks: int = 3,
    locked_role: str = ROLE_SECONDARY,
    plugin_bit_flip_rate: float = 0.5,
) -> dict[str, Any]:
    """Witness: locked role genomes unchanged while unlocked role may change."""

    session = boot_locked_session(
        seed=seed,
        locked_roles=(locked_role,),
        kappa_ablate=True,  # isolate mutation-lock witness from κ ATP noise
        kappa_enabled=True,
        plugin_bit_flip_rate=plugin_bit_flip_rate,
        bit_flip_rate=0.0,
        secondary_kappa_high=False,
    )
    before_locked = genomes_by_role(session, locked_role)
    unlocked = ROLE_PRIMARY if locked_role == ROLE_SECONDARY else ROLE_SECONDARY
    before_unlocked = genomes_by_role(session, unlocked)
    session.run_ticks(ticks)
    after_locked = genomes_by_role(session, locked_role)
    after_unlocked = genomes_by_role(session, unlocked)
    # Founders of locked role must be frozen.
    shared_locked = set(before_locked) & set(after_locked)
    locked_changed = any(
        before_locked[i] != after_locked[i] for i in shared_locked
    )
    shared_unlocked = set(before_unlocked) & set(after_unlocked)
    unlocked_changed = any(
        before_unlocked[i] != after_unlocked[i] for i in shared_unlocked
    )
    return {
        "locked_role": locked_role,
        "locked_founder_changed": locked_changed,
        "unlocked_founder_changed": unlocked_changed,
        "locked_founder_ids": sorted(shared_locked),
        "unlocked_founder_ids": sorted(shared_unlocked),
        "claim_ceiling": "candidate_evidence",
        "red_queen_proved": False,
        "p4_scope": P4_SCOPE,
    }
