"""Closed-loop P3: scalar genetic harm/help (κ) via EnergyCoupling on atp_state.

Hard scope (2026-09-25): κ ∈ [-1,+1] from a mutable genome locus with fixed
bit-window decode (both roles). Magnitude f(κ_primary, κ_secondary)=product. Transfer only through life-loop EnergyCoupling
mirrored onto organism.atp_state — never HostParasiteEnv.steal_fraction or
profile coupling_amount. Clamp 0.8 is post-f(κ), never a gene default.
Ablate κ→0 ⇒ |net_transfer|→0 and ATP skew dies. Not Morran. Not red-queen
proved. Not P4 dual-arm.

Clock API: PopulationRunner.step_generation. No HostParasiteWorld.tick /
_birth_role. engine.py stays domain-free.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_life_plugin import (
    KAPPA_BIT_START,
    KAPPA_BIT_WIDTH,
    KAPPA_TRANSFER_CLAMP,
    P3_SCOPE,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    assert_single_atp_owner,
    decode_kappa,
    kappa_transfer_amount,
    role_of,
    with_inherited_birth_roles,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    GenerationResult,
    MetabolicConfig,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
)
from codontrace.genesis.population_runner import PopulationRunner
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME
from codontrace.life_loop.attachment import AttachmentSlot
from codontrace.life_loop.energy_coupling import EnergyCoupling
from codontrace.world import World2D

# Opaque ids — role comes from role_by_id map, never from parsing these strings.
_PRIMARY_IDS = ("org_a0", "org_a1")
_SECONDARY_IDS = ("org_b0", "org_b1")

# Functional program (9 bits) + fixed kappa locus (6 bits).
_KAPPA_HIGH = "111111"  # → κ = +1.0
_KAPPA_MID = "100000"  # → κ ≈ 0

_FOUNDER_PRIMARY = (
    LIFE_LOOP_EATER_GENOME + _KAPPA_HIGH,
    "111101000" + _KAPPA_HIGH,
)
_FOUNDER_SECONDARY_HIGH = (
    LIFE_LOOP_EATER_GENOME + _KAPPA_HIGH,
    "101000111" + _KAPPA_HIGH,
)

_PARTITION_EPS = 1e-9
_TRANSFER_EPS = 1e-9


def _genome_digest(organism: GenesisOrganism) -> str:
    return canonical_digest(
        {"id": organism.id, "g": organism.genome.to_compact()}, prefix="clp3g"
    )


def _atp_of(organism: GenesisOrganism) -> float:
    return float(organism.atp_state.runtime.current_atp)


def _kappa_of(
    organism: GenesisOrganism,
    *,
    ablate: bool,
    bit_start: int,
    bit_width: int,
) -> float:
    return decode_kappa(
        organism.genome.to_compact(),
        bit_start=bit_start,
        bit_width=bit_width,
        ablate=ablate,
    )


@dataclass
class ClosedLoopP3Session:
    """κ EnergyCoupling under step_generation; no HP world demography."""

    seed: int
    runner: PopulationRunner
    roles: dict[str, str] = field(default_factory=dict)
    tick_index: int = 0
    history_digests: list[str] = field(default_factory=list)
    hp_world_tick_calls: int = 0
    total_births: int = 0
    birth_Iy: list[float] = field(default_factory=list)
    partition_ok_flags: list[bool] = field(default_factory=list)
    births_by_role: dict[str, int] = field(
        default_factory=lambda: {ROLE_PRIMARY: 0, ROLE_SECONDARY: 0}
    )
    parent_atp_cost: float = 1.0
    offspring_atp_fraction: float = 0.25
    kappa_enabled: bool = True
    kappa_ablate: bool = False
    kappa_ablate_primary: bool = False
    kappa_ablate_secondary: bool = False
    kappa_bit_start: int = KAPPA_BIT_START
    kappa_bit_width: int = KAPPA_BIT_WIDTH
    net_transfer: float = 0.0  # secondary gains from primary → positive
    transfer_events: int = 0
    transfer_conserved_flags: list[bool] = field(default_factory=list)
    atp_mirror_ok_flags: list[bool] = field(default_factory=list)
    attachment_pairs: int = 0
    peak_abs_atp_skew: float = 0.0

    @classmethod
    def boot(
        cls,
        *,
        seed: int = 7,
        n_primary: int = 2,
        n_secondary: int = 2,
        initial_atp: float = 24.0,
        world_size: int = 8,
        basal_atp_cost: float = 0.5,
        bit_flip_rate: float = 0.0,
        parent_atp_cost: float = 1.0,
        offspring_atp_fraction: float = 0.25,
        min_runtime_atp: float = 4.0,
        max_population: int = 64,
        ticks_per_generation: int = 3,
        place_food: bool = True,
        kappa_enabled: bool = True,
        kappa_ablate: bool = False,
        kappa_ablate_primary: bool = False,
        kappa_ablate_secondary: bool = False,
        kappa_bit_start: int = KAPPA_BIT_START,
        kappa_bit_width: int = KAPPA_BIT_WIDTH,
        secondary_kappa_high: bool = True,
    ) -> ClosedLoopP3Session:
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        for i in range(n_primary):
            oid = _PRIMARY_IDS[i] if i < len(_PRIMARY_IDS) else f"org_a{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _FOUNDER_PRIMARY[i % len(_FOUNDER_PRIMARY)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 0),
                )
            )
            roles[oid] = ROLE_PRIMARY
        sec_pool = (
            _FOUNDER_SECONDARY_HIGH
            if secondary_kappa_high
            else (
                LIFE_LOOP_EATER_GENOME + _KAPPA_MID,
                "101000111" + _KAPPA_MID,
            )
        )
        for i in range(n_secondary):
            oid = _SECONDARY_IDS[i] if i < len(_SECONDARY_IDS) else f"org_b{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    sec_pool[i % len(sec_pool)],
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 1),
                )
            )
            roles[oid] = ROLE_SECONDARY

        assert_single_atp_owner(organisms)

        configs = PopulationConfigs(
            reproduction=ReproductionConfig(
                enabled=True,
                min_runtime_atp=min_runtime_atp,
                parent_atp_cost=parent_atp_cost,
                offspring_atp_fraction=offspring_atp_fraction,
                max_population=max_population,
            ),
            mutation=MutationConfig(bit_flip_rate=bit_flip_rate),
            metabolism=MetabolicConfig(
                enabled=True,
                basal_runtime_atp_cost=basal_atp_cost,
            ),
            ticks_per_generation=ticks_per_generation,
            closed_loop_hp_life=ClosedLoopHPLifeConfig(
                enabled=True,
                mutate_both_roles=True,
                role_by_id=tuple(sorted(roles.items())),
                kappa_enabled=kappa_enabled,
                kappa_ablate=kappa_ablate,
                kappa_bit_start=kappa_bit_start,
                kappa_bit_width=kappa_bit_width,
            ),
        )
        population = PopulationState(
            generation=0,
            tick=0,
            organisms=tuple(organisms),
            lineage=(),
            fitness=(),
        )
        world = World2D(width=world_size, height=world_size)
        if place_food:
            for x in range(min(4, world_size)):
                for y in range(min(2, world_size)):
                    world.place_resource((x, y), 4.0)
        runner = PopulationRunner(
            population=population,
            world=world,
            configs=configs,
        )
        return cls(
            seed=seed,
            runner=runner,
            roles=roles,
            parent_atp_cost=parent_atp_cost,
            offspring_atp_fraction=offspring_atp_fraction,
            kappa_enabled=kappa_enabled,
            kappa_ablate=kappa_ablate,
            kappa_ablate_primary=kappa_ablate_primary,
            kappa_ablate_secondary=kappa_ablate_secondary,
            kappa_bit_start=kappa_bit_start,
            kappa_bit_width=kappa_bit_width,
        )

    def _record_births(self, result: GenerationResult) -> None:
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        new_births: list[tuple[str, str]] = []
        for record in result.organism_records:
            rr = record.reproduction_result
            if rr is None or not rr.succeeded or rr.child is None:
                continue
            if rr.birth_event is None or rr.reproduction_gate_result is None:
                continue
            child = rr.child
            be = rr.birth_event
            gate = rr.reproduction_gate_result
            parent_before = float(gate.parent_runtime_atp_before_copy_self)
            cost = float(be.birth_cost_runtime_atp)
            iy = float(be.child_initial_runtime_atp or 0.0)
            child_runtime = float(child.atp_state.runtime_available)
            child_learning = float(child.atp_state.learning_available)
            expected_iy = round(
                (parent_before - cost) * self.offspring_atp_fraction, 10
            )
            # Measured birth Iy consistency only (no invented parent_after algebra).
            conserved = (
                iy > 0.0
                and abs(iy - expected_iy) <= _PARTITION_EPS
                and abs(child_runtime - iy) <= _PARTITION_EPS
                and abs(child_learning) <= _PARTITION_EPS
            )
            self.partition_ok_flags.append(conserved)
            self.birth_Iy.append(iy)
            self.total_births += 1
            parent_id = rr.parent_before_id
            parent_role = role_of(parent_id, role_map) or self.roles.get(parent_id)
            if parent_role in {ROLE_PRIMARY, ROLE_SECONDARY}:
                self.births_by_role[parent_role] = (
                    self.births_by_role.get(parent_role, 0) + 1
                )
            new_births.append((parent_id, child.id))

        if new_births:
            life = with_inherited_birth_roles(
                self.runner.configs.closed_loop_hp_life, new_births
            )
            self.runner.configs = replace(
                self.runner.configs, closed_loop_hp_life=life
            )
            role_map = life.role_map()

        self.roles = {
            org.id: (role_of(org.id, role_map) or self.roles.get(org.id, "unknown"))
            for org in self.runner.population.organisms
        }
        for rec in self.runner.population.lineage:
            if rec.parent_id and rec.organism_id not in self.roles:
                prow = role_of(rec.parent_id, role_map) or self.roles.get(rec.parent_id)
                if prow:
                    self.roles[rec.organism_id] = prow

    def _apply_kappa_couplings(self) -> None:
        if not self.kappa_enabled:
            return
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        primaries = sorted(
            [
                o
                for o in self.runner.population.organisms
                if role_of(o.id, role_map) == ROLE_PRIMARY
            ],
            key=lambda o: o.id,
        )
        secondaries = sorted(
            [
                o
                for o in self.runner.population.organisms
                if role_of(o.id, role_map) == ROLE_SECONDARY
            ],
            key=lambda o: o.id,
        )
        n = min(len(primaries), len(secondaries))
        self.attachment_pairs = n
        for i in range(n):
            primary = primaries[i]
            secondary = secondaries[i]
            slot = AttachmentSlot(
                slot_id=f"seat_{primary.id}",
                owner_id=primary.id,
                capacity=1,
            )
            slot, _ev = slot.attach(secondary.id)
            if not slot.linked(primary.id, secondary.id):
                continue
            # f(κ_primary, κ_secondary) = product; ablating either locus kills E.
            ablate_p = self.kappa_ablate or self.kappa_ablate_primary
            ablate_s = self.kappa_ablate or self.kappa_ablate_secondary
            kappa_p = _kappa_of(
                primary,
                ablate=ablate_p,
                bit_start=self.kappa_bit_start,
                bit_width=self.kappa_bit_width,
            )
            kappa_s = _kappa_of(
                secondary,
                ablate=ablate_s,
                bit_start=self.kappa_bit_start,
                bit_width=self.kappa_bit_width,
            )
            kappa = kappa_p * kappa_s
            if abs(kappa) <= _TRANSFER_EPS:
                continue
            if kappa > 0.0:
                donor, recv = primary, secondary
                sign = 1.0
            else:
                donor, recv = secondary, primary
                sign = -1.0
            available = float(donor.atp_state.runtime_available)
            amount = kappa_transfer_amount(kappa, available)
            if amount <= _TRANSFER_EPS:
                continue
            # Post-f(κ) clamp: never exceed 0.8 × donor (clamp is not a gene).
            if amount > KAPPA_TRANSFER_CLAMP * available + 1e-12:
                raise ConfigurationError("kappa transfer exceeded post-f clamp")
            coupling = EnergyCoupling(
                coupling_id=f"clp3_{donor.id}_{recv.id}_{self.tick_index}_{i}",
                source_id=donor.id,
                target_id=recv.id,
                amount=amount,
                loss_fraction=0.0,
                label="kappa_xfer",
            )
            balances = {
                donor.id: float(donor.atp_state.runtime_available),
                recv.id: float(recv.atp_state.runtime_available),
            }
            donor_before = balances[donor.id]
            recv_before = balances[recv.id]
            new_bal, _event, _entries, conserved = coupling.apply(
                balances,
                tick=self.tick_index,
                require_attached=True,
                attached=True,
                allow_partial=True,
            )
            paid = balances[donor.id] - new_bal[donor.id]
            gained = new_bal[recv.id] - balances[recv.id]
            debit_ok = True
            credit_ok = True
            if paid > 0.0:
                debit_tok = donor.atp_state.debit_runtime(
                    paid,
                    tick=self.tick_index,
                    organism_id=donor.id,
                    codon="000",
                    action="energy_coupling",
                    reason="kappa_xfer",
                )
                debit_ok = debit_tok is not None
            if gained > 0.0:
                recv.atp_state.credit_runtime(
                    gained,
                    tick=self.tick_index,
                    organism_id=recv.id,
                    codon="000",
                    action="energy_coupling",
                    reason="kappa_xfer",
                )
            donor_after = float(donor.atp_state.runtime_available)
            recv_after = float(recv.atp_state.runtime_available)
            mirror_ok = (
                debit_ok
                and credit_ok
                and abs((donor_before - donor_after) - paid) <= _TRANSFER_EPS
                and abs((recv_after - recv_before) - gained) <= _TRANSFER_EPS
            )
            self.net_transfer += sign * gained
            self.transfer_events += 1
            # Dict conserved alone is mint-blind; require atp_state delta match.
            self.transfer_conserved_flags.append(bool(conserved) and mirror_ok)
            self.atp_mirror_ok_flags.append(mirror_ok)

    def run_ticks(self, ticks: int) -> dict[str, Any]:
        if ticks < 0:
            raise ConfigurationError("ticks must be non-negative")
        for i in range(ticks):
            result = self.runner.step_generation(seed=self.seed + self.tick_index + i)
            self.tick_index += 1
            self._record_births(result)
            self._apply_kappa_couplings()
            skew_now = abs(self.atp_skew())
            if skew_now > self.peak_abs_atp_skew:
                self.peak_abs_atp_skew = skew_now
            assert_single_atp_owner(self.runner.population.organisms)
            self.history_digests.append(self.snapshot_digest())
        return self.summary()

    def mean_kappa(self, role: str) -> float:
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        vals = [
            _kappa_of(
                o,
                ablate=self.kappa_ablate,
                bit_start=self.kappa_bit_start,
                bit_width=self.kappa_bit_width,
            )
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == role
        ]
        if not vals:
            return 0.0
        return sum(vals) / len(vals)

    def atp_skew(self) -> float:
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        primary = [
            _atp_of(o)
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_PRIMARY
        ]
        secondary = [
            _atp_of(o)
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_SECONDARY
        ]
        if not primary or not secondary:
            return 0.0
        return (sum(secondary) / len(secondary)) - (sum(primary) / len(primary))

    def snapshot_digest(self) -> str:
        orgs = sorted(self.runner.population.organisms, key=lambda o: o.id)
        payload = {
            "tick": self.tick_index,
            "generation": self.runner.population.generation,
            "ids": [o.id for o in orgs],
            "genomes": [_genome_digest(o) for o in orgs],
            "atp": [_atp_of(o) for o in orgs],
            "kappa": [
                _kappa_of(
                    o,
                    ablate=self.kappa_ablate,
                    bit_start=self.kappa_bit_start,
                    bit_width=self.kappa_bit_width,
                )
                for o in orgs
            ],
            "roles": {o.id: self.roles.get(o.id) for o in orgs},
            "net_transfer": self.net_transfer,
            "births": self.total_births,
        }
        return canonical_digest(payload, prefix="clp3snap")

    def summary(self) -> dict[str, Any]:
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        primary = [
            o
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_PRIMARY
        ]
        secondary = [
            o
            for o in self.runner.population.organisms
            if role_of(o.id, role_map) == ROLE_SECONDARY
        ]
        n_ok = sum(1 for f in self.partition_ok_flags if f)
        n_checks = len(self.partition_ok_flags)
        n_xfer_ok = sum(1 for f in self.transfer_conserved_flags if f)
        n_xfer = len(self.transfer_conserved_flags)
        return {
            "tick_index": self.tick_index,
            "population_tick": self.runner.population.tick,
            "population_generation": self.runner.population.generation,
            "n_primary": len(primary),
            "n_secondary": len(secondary),
            "organism_ids": [o.id for o in self.runner.population.organisms],
            "snapshot_digest": self.snapshot_digest(),
            "claim_ceiling": "candidate_evidence",
            "red_queen_proved": False,
            "p3_scope": P3_SCOPE,
            "clock_api": "PopulationRunner.step_generation",
            "hp_world_tick_calls": self.hp_world_tick_calls,
            "kappa_enabled": self.kappa_enabled,
            "kappa_ablate": self.kappa_ablate,
            "kappa_transfer_clamp": KAPPA_TRANSFER_CLAMP,
            "mean_kappa_primary": self.mean_kappa(ROLE_PRIMARY),
            "mean_kappa_secondary": self.mean_kappa(ROLE_SECONDARY),
            "net_transfer": self.net_transfer,
            "transfer_events": self.transfer_events,
            "transfer_conserved_count": n_xfer_ok,
            "transfer_conserved_checks": n_xfer,
            "transfer_conserved": bool(n_xfer > 0 and n_xfer_ok == n_xfer),
            "atp_skew": self.atp_skew(),
            "peak_abs_atp_skew": self.peak_abs_atp_skew,
            "attachment_pairs": self.attachment_pairs,
            "atp_mirror_ok_count": sum(1 for f in self.atp_mirror_ok_flags if f),
            "atp_mirror_ok_checks": len(self.atp_mirror_ok_flags),
            "atp_mirror_ok": bool(
                self.atp_mirror_ok_flags
                and all(self.atp_mirror_ok_flags)
            ),
            "kappa_ablate_primary": self.kappa_ablate_primary,
            "kappa_ablate_secondary": self.kappa_ablate_secondary,
            "kappa_interaction": "product",
            "births": self.total_births,
            "partition_conserved_count": n_ok,
            "partition_conserved_checks": n_checks,
            "partition_conserved": bool(n_checks > 0 and n_ok == n_checks),
        }


def ablate_delta(*, seed: int, ticks: int) -> dict[str, float]:
    """Run κ-on vs κ-ablate under one master seed; return measured deltas."""

    on = ClosedLoopP3Session.boot(seed=seed, kappa_enabled=True, kappa_ablate=False)
    off = ClosedLoopP3Session.boot(seed=seed, kappa_enabled=True, kappa_ablate=True)
    on.run_ticks(ticks)
    off.run_ticks(ticks)
    s_on = on.summary()
    s_off = off.summary()
    return {
        "net_transfer_on": float(s_on["net_transfer"]),
        "net_transfer_off": float(s_off["net_transfer"]),
        "atp_skew_on": float(s_on["atp_skew"]),
        "atp_skew_off": float(s_off["atp_skew"]),
        "peak_abs_atp_skew_on": float(s_on["peak_abs_atp_skew"]),
        "peak_abs_atp_skew_off": float(s_off["peak_abs_atp_skew"]),
        "ablation_delta_transfer": abs(float(s_on["net_transfer"]))
        - abs(float(s_off["net_transfer"])),
        "ablation_delta_skew": float(s_on["peak_abs_atp_skew"])
        - float(s_off["peak_abs_atp_skew"]),
    }


def replay_bit_identical(*, seed: int, ticks: int) -> tuple[str, str]:
    """Same-seed session match (Gate7-shaped). NOT P4 dual-arm."""

    a = ClosedLoopP3Session.boot(seed=seed)
    b = ClosedLoopP3Session.boot(seed=seed)
    a.run_ticks(ticks)
    b.run_ticks(ticks)
    return a.snapshot_digest(), b.snapshot_digest()
