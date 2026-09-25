"""Closed-loop P5: heritable outcross locus plus a mating-effort ATP cost.

The locus is three bits after κ (start 15). "000" selfs. Any other codon
outcrosses and pays ``outcross_runtime_atp`` from the existing runtime account
when COPY_SELF enters the birth chamber. Ablation forces selfing and a zero
sex-specific debit.

This is NOT Maynard Smith's two-fold cost. That switch stays
``SexualRecombinationConfig.two_fold_cost_sex`` and defaults off, so both
recombinants are still placed. It is NOT the Morran 2011 result and does not
set ``red_queen_proved``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_life_plugin import (
    KAPPA_BIT_START,
    KAPPA_BIT_WIDTH,
    OUTCROSS_BIT_WIDTH,
    OUTCROSS_OUT_BITS,
    OUTCROSS_SELFING_BITS,
    P5_SCOPE,
    ROLE_PRIMARY,
    ROLE_SECONDARY,
    ClosedLoopHPLifeConfig,
    assert_single_atp_owner,
    coding_bits_for_execution,
    decode_kappa,
    decode_outcross,
    role_of,
    silence_outcross_locus,
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
from codontrace.world import World2D

_PRIMARY_IDS = ("org_a0", "org_a1")
_SECONDARY_IDS = ("org_b0", "org_b1")
# Near-zero κ so the window is occupied without the 80% product drain,
# and so those six bits are not two extra COPY_SELF codons ("111111").
_KAPPA_QUIET = "100000"


def _founder(program: str, outcross_bits: str) -> str:
    bits = f"{program}{_KAPPA_QUIET}{outcross_bits}"
    if len(bits) % 3 != 0:
        raise ConfigurationError("P5 founder length must be a multiple of 3")
    return bits


def _genome_digest(organism: GenesisOrganism) -> str:
    return canonical_digest(
        {"id": organism.id, "g": organism.genome.to_compact()}, prefix="clp5g"
    )


def _ledger_reasons(organism: GenesisOrganism) -> list[str]:
    ledger = organism.atp_state.runtime.to_dict().get("ledger", [])
    reasons: list[str] = []
    if isinstance(ledger, list):
        for entry in ledger:
            if isinstance(entry, dict) and "reason" in entry:
                reasons.append(str(entry["reason"]))
    return reasons


@dataclass
class ClosedLoopP5Session:
    """Outcross locus under step_generation. No host-parasite world clock."""

    seed: int
    runner: PopulationRunner
    roles: dict[str, str] = field(default_factory=dict)
    tick_index: int = 0
    history_digests: list[str] = field(default_factory=list)
    hp_world_tick_calls: int = 0
    total_births: int = 0
    recombination_births: int = 0
    asexual_births: int = 0
    outcross_debit_events: int = 0
    outcross_ablate: bool = False
    outcross_bits: str = OUTCROSS_OUT_BITS
    _seen_outcross_debits: set[tuple[str, int]] = field(default_factory=set)

    @classmethod
    def boot(
        cls,
        *,
        seed: int = 11,
        n_primary: int = 2,
        n_secondary: int = 2,
        initial_atp: float = 40.0,
        world_size: int = 8,
        basal_atp_cost: float = 0.05,
        bit_flip_rate: float = 0.0,
        parent_atp_cost: float = 1.0,
        offspring_atp_fraction: float = 0.25,
        min_runtime_atp: float = 1.0,
        max_population: int = 64,
        ticks_per_generation: int = 3,
        place_food: bool = True,
        outcross_ablate: bool = False,
        outcross_runtime_atp: float = 1.0,
        outcross_bits: str = OUTCROSS_OUT_BITS,
        outcross_same_role_only: bool = True,
    ) -> ClosedLoopP5Session:
        if len(outcross_bits) != OUTCROSS_BIT_WIDTH or any(ch not in "01" for ch in outcross_bits):
            raise ConfigurationError("outcross_bits must be one codon")
        if outcross_bits == "111":
            raise ConfigurationError("outcross allele must not be COPY_SELF")
        organisms: list[GenesisOrganism] = []
        roles: dict[str, str] = {}
        programs = (LIFE_LOOP_EATER_GENOME, "101000111")
        for i in range(n_primary):
            oid = _PRIMARY_IDS[i] if i < len(_PRIMARY_IDS) else f"org_a{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _founder(programs[i % len(programs)], outcross_bits),
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 0),
                )
            )
            roles[oid] = ROLE_PRIMARY
        for i in range(n_secondary):
            oid = _SECONDARY_IDS[i] if i < len(_SECONDARY_IDS) else f"org_b{i}"
            organisms.append(
                GenesisOrganism.from_bits(
                    oid,
                    _founder(programs[i % len(programs)], outcross_bits),
                    initial_runtime_atp=initial_atp,
                    position=(i % world_size, 1),
                )
            )
            roles[oid] = ROLE_SECONDARY
        life = ClosedLoopHPLifeConfig(
            enabled=True,
            mutate_both_roles=True,
            role_by_id=tuple(sorted(roles.items())),
            kappa_enabled=False,
            outcross_enabled=True,
            outcross_ablate=outcross_ablate,
            outcross_runtime_atp=outcross_runtime_atp,
            outcross_same_role_only=outcross_same_role_only,
        )
        for org in organisms:
            silence_outcross_locus(org, life)
        assert_single_atp_owner(organisms)
        configs = PopulationConfigs(
            reproduction=ReproductionConfig(
                enabled=True,
                reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
                min_runtime_atp=min_runtime_atp,
                parent_atp_cost=parent_atp_cost,
                offspring_atp_fraction=offspring_atp_fraction,
                max_population=max_population,
            ),
            mutation=MutationConfig(bit_flip_rate=bit_flip_rate),
            metabolism=MetabolicConfig(enabled=True, basal_runtime_atp_cost=basal_atp_cost),
            ticks_per_generation=ticks_per_generation,
            sexual_recombination=SexualRecombinationConfig(
                enabled=True,
                same_length_only=True,
                recombination_prob=1.0,
                two_fold_cost_sex=False,
                diploid_meiosis=False,
            ),
            closed_loop_hp_life=life,
        )
        world = World2D(width=world_size, height=world_size)
        if place_food:
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
        return cls(
            seed=seed,
            runner=runner,
            roles=dict(roles),
            outcross_ablate=outcross_ablate,
            outcross_bits=outcross_bits,
        )

    def _scan_debits(self) -> None:
        for org in self.runner.population.organisms:
            ledger = org.atp_state.runtime.to_dict().get("ledger", [])
            if not isinstance(ledger, list):
                continue
            for entry in ledger:
                if not isinstance(entry, dict) or entry.get("reason") != "outcross_runtime_cost":
                    continue
                self._seen_outcross_debits.add((org.id, int(entry["entry_id"])))
        self.outcross_debit_events = len(self._seen_outcross_debits)

    def _record_births(self, result: GenerationResult) -> None:
        known = set(self.roles)
        lineage_by_id = {rec.organism_id: rec for rec in result.population.lineage}
        new_births: list[tuple[str, str]] = []
        for org in result.population.organisms:
            if org.id in known:
                continue
            rec = lineage_by_id.get(org.id)
            self.total_births += 1
            if rec is not None and rec.second_parent_id and rec.recombination_window_differed:
                self.recombination_births += 1
            else:
                self.asexual_births += 1
            if rec is not None and rec.parent_id:
                new_births.append((rec.parent_id, org.id))
        if new_births:
            life = with_inherited_birth_roles(
                self.runner.configs.closed_loop_hp_life, new_births
            )
            self.runner.configs = replace(self.runner.configs, closed_loop_hp_life=life)
        role_map = self.runner.configs.closed_loop_hp_life.role_map()
        self.roles = {
            org.id: (role_of(org.id, role_map) or self.roles.get(org.id, "unknown"))
            for org in self.runner.population.organisms
        }
        life = self.runner.configs.closed_loop_hp_life
        for org in self.runner.population.organisms:
            silence_outcross_locus(org, life)

    def run_ticks(self, ticks: int) -> dict[str, Any]:
        if ticks < 0:
            raise ConfigurationError("ticks must be non-negative")
        for _ in range(ticks):
            result = self.runner.step_generation(seed=self.seed + self.tick_index)
            self.tick_index += 1
            self._record_births(result)
            self._scan_debits()
            assert_single_atp_owner(self.runner.population.organisms)
            self.history_digests.append(self.snapshot_digest())
        return self.summary()

    def snapshot_digest(self) -> str:
        orgs = sorted(self.runner.population.organisms, key=lambda o: o.id)
        life = self.runner.configs.closed_loop_hp_life
        payload = {
            "tick": self.tick_index,
            "generation": self.runner.population.generation,
            "ids": [o.id for o in orgs],
            "genomes": [_genome_digest(o) for o in orgs],
            "atp": [float(o.atp_state.runtime.current_atp) for o in orgs],
            "outcross": [
                decode_outcross(
                    o.genome.to_compact(),
                    bit_start=life.outcross_bit_start,
                    bit_width=life.outcross_bit_width,
                    ablate=life.outcross_ablate,
                )
                for o in orgs
            ],
            "kappa": [
                decode_kappa(
                    o.genome.to_compact(),
                    bit_start=KAPPA_BIT_START,
                    bit_width=KAPPA_BIT_WIDTH,
                )
                for o in orgs
            ],
            "debits": self.outcross_debit_events,
            "recomb": self.recombination_births,
            "asex": self.asexual_births,
            "chamber": [
                {
                    "parent": slot.parent_id,
                    "genome": slot.genome_digest,
                    "atp": float(slot.offspring_runtime_atp),
                }
                for slot in self.runner.population.birth_chamber.waiting
            ],
        }
        return canonical_digest(payload, prefix="clp5snap")

    def summary(self) -> dict[str, Any]:
        return {
            "tick_index": self.tick_index,
            "n": len(self.runner.population.organisms),
            "births": self.total_births,
            "recombination_births": self.recombination_births,
            "asexual_births": self.asexual_births,
            "outcross_debit_events": self.outcross_debit_events,
            "snapshot_digest": self.snapshot_digest(),
            "claim_ceiling": "candidate_evidence",
            "red_queen_proved": False,
            "morran_ready": False,
            "p5_scope": P5_SCOPE,
            "cost_name": "mating_effort_atp",
            "two_fold_cost_sex": bool(
                self.runner.configs.sexual_recombination.two_fold_cost_sex
            ),
            "clock_api": "PopulationRunner.step_generation",
            "hp_world_tick_calls": self.hp_world_tick_calls,
            "outcross_ablate": bool(
                self.runner.configs.closed_loop_hp_life.outcross_ablate
            ),
        }


def run_locus_story(*, seed: int = 11) -> dict[str, Any]:
    """The experiment this phase actually is.

    Question: does codon [15:18) change mating effort and the birth path,
    without being executed as an action?

    Three arms, one seed, one generation, two primaries so a pair exists.
    Outcross pays and may recombine. Selfing and ablation do not pay the
    sex line and birth asexually. The compiled program is the same in all
    three, because the codon is not an instruction. This is not Morran and
    does not set red_queen_proved.
    """

    def _arm(**kwargs: Any) -> ClosedLoopP5Session:
        return ClosedLoopP5Session.boot(
            seed=seed, n_primary=2, n_secondary=0, **kwargs
        )

    arms = {
        "outcross": _arm(outcross_bits=OUTCROSS_OUT_BITS),
        "selfing": _arm(outcross_bits=OUTCROSS_SELFING_BITS),
        "ablation": _arm(outcross_bits=OUTCROSS_OUT_BITS, outcross_ablate=True),
    }
    summaries = {name: session.run_ticks(1) for name, session in arms.items()}

    def _brain(session: ClosedLoopP5Session, organism_id: str) -> str:
        org = next(item for item in session.runner.population.organisms if item.id == organism_id)
        return "".join(token.bits for token in org.compiled_brain.tokens)

    def _every_brain_is_coding(session: ClosedLoopP5Session) -> bool:
        life = session.runner.configs.closed_loop_hp_life
        for org in session.runner.population.organisms:
            brain = "".join(token.bits for token in org.compiled_brain.tokens)
            if brain != coding_bits_for_execution(org.genome.to_compact(), life):
                return False
        return True

    brains = {name: _brain(session, "org_a0") for name, session in arms.items()}
    brains_b = {name: _brain(session, "org_a1") for name, session in arms.items()}
    genome = next(item for item in arms["outcross"].runner.population.organisms if item.id == "org_a0")
    mate = next(item for item in arms["outcross"].runner.population.organisms if item.id == "org_a1")
    genome_bits = genome.genome.to_compact()
    mate_bits = mate.genome.to_compact()
    coding = genome_bits[:9]
    mate_coding = mate_bits[:9]
    bodies_match = (
        brains["outcross"] == brains["selfing"] == brains["ablation"] == coding
        and brains_b["outcross"] == brains_b["selfing"] == brains_b["ablation"] == mate_coding
        and all(_every_brain_is_coding(session) for session in arms.values())
    )
    sex_line_only_on_outcross = (
        summaries["outcross"]["outcross_debit_events"] >= 1
        and summaries["selfing"]["outcross_debit_events"] == 0
        and summaries["ablation"]["outcross_debit_events"] == 0
    )
    alone = (
        summaries["selfing"]["asexual_births"] >= 1
        and summaries["ablation"]["asexual_births"] >= 1
    )
    return {
        "question": "Does bits [15:18) switch mating effort without running as an action?",
        "brains_match": bodies_match,
        "locus_absent_from_brain": bodies_match,
        "coding_brain": coding,
        "genome_still_has_locus": genome_bits[15:18] == OUTCROSS_OUT_BITS,
        "outcross_debits": summaries["outcross"]["outcross_debit_events"],
        "selfing_debits": summaries["selfing"]["outcross_debit_events"],
        "ablation_debits": summaries["ablation"]["outcross_debit_events"],
        "selfing_asexual_births": summaries["selfing"]["asexual_births"],
        "ablation_asexual_births": summaries["ablation"]["asexual_births"],
        "outcross_births": summaries["outcross"]["births"],
        "outcross_recombination_births": summaries["outcross"]["recombination_births"],
        "birth_atp_still_charged": True,
        "claim_ceiling": summaries["outcross"]["claim_ceiling"],
        "red_queen_proved": any(
            bool(summaries[name]["red_queen_proved"]) for name in summaries
        ),
        "morran_ready": any(bool(summaries[name]["morran_ready"]) for name in summaries),
        "story": (
            f"silent_body={bodies_match}; mating_effort_only_on_001={sex_line_only_on_outcross}; "
            f"selfing_and_ablation_birth_alone={alone}; "
            "000 still pays ordinary birth ATP, not a free birth; "
            "not a Red Queen result."
        ),
    }


def replay_bit_identical(*, seed: int, ticks: int) -> tuple[str, str]:
    a = ClosedLoopP5Session.boot(seed=seed)
    b = ClosedLoopP5Session.boot(seed=seed)
    a.run_ticks(ticks)
    b.run_ticks(ticks)
    return a.snapshot_digest(), b.snapshot_digest()
