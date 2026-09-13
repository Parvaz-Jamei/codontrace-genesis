"""ILW integrated causal chain runtime (ILW-2/ILW-3).

Wires genome -> toolchain -> VM phenotype -> action -> resource/world
consequence -> experienced event -> capsule+provenance -> transport/accept/apply
-> receiver policy/action change -> survival/reproduction -> mutation/lineage
-> next ecological state under one run_id / WorldSpec / scheduler / ledger.

ILW-3 adds final digest, S1 smoke scale helper, and initial resource snapshots
for replay / conservation assays. Claim ceiling stays ``runtime_observation``.
No outcome injection / oracle treatment / fitness shortcut outside VM/world.
Smoke must not emit ClaimGate ladder promotions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.ilw.adapter_honesty import (
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
)
from codontrace.genesis.ilw.dag import CLAIM_CEILING, load_integration_dag
from codontrace.genesis.ilw.dual_resource_world import DualResourceWorld
from codontrace.genesis.ilw.event_ledger import EventLedger
from codontrace.genesis.ilw.knockouts import KnockoutConfig
from codontrace.genesis.ilw.orphan import SubsystemRegistry
from codontrace.genesis.ilw.scheduler import IlwScheduler
from codontrace.genesis.ilw.seed_namespace import SeedNamespace
from codontrace.genesis.ilw.world_spec import WorldSpec
from codontrace.genesis.structural_mutation import (
    StructuralMutationConfig,
    build_genome_program,
    mutate_genome_program,
)

# Minimal action vocabulary controlled by genome / policy.
_ACTIONS = ("WAIT", "MOVE", "HARVEST_0", "HARVEST_1", "EMIT", "REPRODUCE")


class IlwChainError(ConfigurationError):
    """Raised when the ILW-2 causal chain cannot proceed honestly."""


@dataclass(slots=True)
class IlwOrganism:
    """Minimal organism for the ILW-2 vertical slice."""

    organism_id: str
    lineage_id: str
    generation: int
    x: int
    y: int
    energy: float
    genome_bits: str
    genome_digest: str
    parent_id: str | None = None
    policy_bias: dict[str, float] = field(default_factory=dict)
    last_experience: dict[str, JsonValue] | None = None
    adopted_capsules: list[str] = field(default_factory=list)
    alive: bool = True

    def state_digest(self) -> str:
        return canonical_digest(
            {
                "organism_id": self.organism_id,
                "lineage_id": self.lineage_id,
                "generation": self.generation,
                "x": self.x,
                "y": self.y,
                "energy": self.energy,
                "genome_digest": self.genome_digest,
                "policy_bias": dict(sorted(self.policy_bias.items())),
                "adopted_capsules": list(self.adopted_capsules),
                "alive": self.alive,
            },
            prefix="ilw_organism",
        )


@dataclass(slots=True)
class CapsuleRecord:
    capsule_id: str
    parent_capsule_id: str | None
    source_id: str
    lineage_id: str
    payload_digest: str
    provenance_digest: str
    event_pattern: tuple[str, ...]
    tick: int
    ttl: int = 4

    def active_at(self, tick: int) -> bool:
        return self.tick <= tick < self.tick + self.ttl


@dataclass(slots=True)
class IlwChainRuntime:
    """One-run integrated living-world chain executor (ILW-2)."""

    run_id: str
    world_spec: WorldSpec
    knockouts: KnockoutConfig = field(default_factory=KnockoutConfig.none)
    move_cost: float = 0.2
    harvest_gain_scale: float = 1.0
    emit_cost: float = 0.3
    reproduce_cost: float = 1.0
    metabolism: float = 0.1
    reproduce_energy: float = 2.2
    mutation_rate_proxy: float = 1.0  # always attempt mutate path when birth occurs
    _scheduler: IlwScheduler = field(init=False, repr=False)
    _ledger: EventLedger = field(init=False, repr=False)
    _world: DualResourceWorld = field(init=False, repr=False)
    _organisms: dict[str, IlwOrganism] = field(default_factory=dict, init=False, repr=False)
    _capsules: dict[str, CapsuleRecord] = field(default_factory=dict, init=False, repr=False)
    _capsule_genealogy: list[dict[str, JsonValue]] = field(
        default_factory=list, init=False, repr=False
    )
    _lineage_records: list[dict[str, JsonValue]] = field(
        default_factory=list, init=False, repr=False
    )
    _event_seq: int = field(default=0, init=False, repr=False)
    _birth_counter: int = field(default=0, init=False, repr=False)
    _registry: SubsystemRegistry = field(init=False, repr=False)
    _initial_resource_totals: dict[str, float] | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        rid = str(self.run_id).strip()
        if not rid:
            raise IlwChainError("run_id must be non-empty.")
        if self.world_spec.claim_ceiling != CLAIM_CEILING:
            raise IlwChainError("WorldSpec claim ceiling must remain runtime_observation.")
        assert_claim_ceiling_runtime_observation(self.world_spec.claim_ceiling)
        object.__setattr__(self, "run_id", rid)
        self._scheduler = IlwScheduler.for_run(rid, self.world_spec)
        self._ledger = EventLedger(run_id=rid, require_full_telemetry=False)
        self._world = DualResourceWorld.from_world_spec(self.world_spec)
        self._registry = SubsystemRegistry()
        self._registry.register_many(load_integration_dag().subsystems)
        if len(self.world_spec.resource_kinds) < 2:
            raise IlwChainError("ILW-2 requires dual resource kinds on WorldSpec.")

    @classmethod
    def s0(
        cls,
        *,
        run_id: str = "ilw2-s0",
        seed: int = 11,
        knockouts: KnockoutConfig | None = None,
    ) -> IlwChainRuntime:
        return cls(
            run_id=run_id,
            world_spec=WorldSpec.s0_unit(seed=seed),
            knockouts=knockouts or KnockoutConfig.none(),
        )

    @classmethod
    def s1(
        cls,
        *,
        run_id: str = "ilw3-s1",
        seed: int = 1,
        knockouts: KnockoutConfig | None = None,
    ) -> IlwChainRuntime:
        """S1 integrated-smoke scale runtime (16×16 / 32 tick)."""

        return cls(
            run_id=run_id,
            world_spec=WorldSpec.s1_smoke(seed=seed),
            knockouts=knockouts or KnockoutConfig.none(),
        )

    @property
    def scheduler(self) -> IlwScheduler:
        return self._scheduler

    @property
    def ledger(self) -> EventLedger:
        return self._ledger

    @property
    def world(self) -> DualResourceWorld:
        return self._world

    @property
    def seed_namespace(self) -> SeedNamespace:
        return self._scheduler.seed_namespace

    @property
    def organisms(self) -> tuple[IlwOrganism, ...]:
        return tuple(self._organisms.values())

    @property
    def alive_organisms(self) -> tuple[IlwOrganism, ...]:
        return tuple(org for org in self._organisms.values() if org.alive)

    @property
    def capsules(self) -> tuple[CapsuleRecord, ...]:
        return tuple(self._capsules.values())

    @property
    def lineage_records(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(self._lineage_records)

    @property
    def capsule_genealogy(self) -> tuple[dict[str, JsonValue], ...]:
        return tuple(self._capsule_genealogy)

    def bootstrap(self, population: int = 2) -> None:
        """Seed initial organisms under the shared seed namespace."""

        if population < 1:
            raise IlwChainError("population must be >= 1.")
        rng = self.seed_namespace.fork_rng("bootstrap")
        kinds = self.world_spec.resource_kinds
        for i in range(population):
            x = int(rng.randrange(0, self.world_spec.width))
            y = int(rng.randrange(0, self.world_spec.height))
            # 15-bit genome: exploration, harvest preference, move, emit, reproduce.
            bits = "".join("1" if rng.random() < 0.5 else "0" for _ in range(15))
            program = build_genome_program(bits, codon_width=3, lineage_tags=(f"founder-{i}",))
            oid = f"{self.run_id}:org:{i}"
            org = IlwOrganism(
                organism_id=oid,
                lineage_id=f"{self.run_id}:lin:{i}",
                generation=0,
                x=x,
                y=y,
                energy=3.2,
                genome_bits=program.bits,
                genome_digest=program.identity_digest,
                policy_bias={
                    "HARVEST_0": 0.1 if kinds[0] else 0.0,
                    "HARVEST_1": 0.1 if len(kinds) > 1 else 0.0,
                },
            )
            self._organisms[oid] = org
            self._lineage_records.append(
                {
                    "organism_id": oid,
                    "lineage_id": org.lineage_id,
                    "parent_id": None,
                    "generation": 0,
                    "genome_digest": org.genome_digest,
                    "tick": 0,
                }
            )
        # Snapshot resources after bootstrap, before organism actions mutate them.
        self._initial_resource_totals = dict(self._world.totals())

    def run(self, ticks: int | None = None) -> dict[str, JsonValue]:
        """Execute the integrated chain for ``ticks`` (default: WorldSpec horizon)."""

        if not self._organisms:
            self.bootstrap()
        elif self._initial_resource_totals is None:
            self._initial_resource_totals = dict(self._world.totals())
        horizon = self.world_spec.tick_horizon if ticks is None else int(ticks)
        if horizon < 0:
            raise IlwChainError("ticks must be non-negative.")
        while self._scheduler.tick < horizon:
            self.step()
        return self.summary()

    def step(self) -> int:
        """Advance one scheduler tick and run the causal chain for all organisms."""

        tick = self._scheduler.advance(run_id=self.run_id)
        # Stable organism order for determinism.
        actors = sorted(
            (org for org in self._organisms.values() if org.alive),
            key=lambda o: o.organism_id,
        )
        for org in actors:
            self._run_organism_chain(org, tick)
        # Ecological turnover after organism actions.
        eco_parent = self._last_event_id_for_edges(
            (
                "mutation_lineage_to_next_ecological_state",
                "lineage_inheritance",
                "survival_reproduction_to_mutation_lineage",
                "policy_to_survival_reproduction",
                "action_to_resource_world",
            )
        )
        self._edge_ecological_state(tick, parents=[eco_parent] if eco_parent else [])
        return tick

    def summary(self) -> dict[str, JsonValue]:
        births = sum(1 for rec in self._lineage_records if rec.get("parent_id"))
        deaths = sum(1 for org in self._organisms.values() if not org.alive)
        return {
            "run_id": self.run_id,
            "world_spec_digest": self.world_spec.digest(),
            "scale_label": self.world_spec.scale_label,
            "tick": self._scheduler.tick,
            "ledger_digest": self._ledger.digest(),
            "world_digest": self._world.digest(),
            "final_digest": self.final_digest(),
            "observed_edge_ids": sorted(self._ledger.observed_edge_ids),
            "event_count": len(self._ledger),
            "alive_count": len(self.alive_organisms),
            "organism_count": len(self._organisms),
            "capsule_count": len(self._capsules),
            "lineage_record_count": len(self._lineage_records),
            "birth_count": int(births),
            "death_count": int(deaths),
            "resource_totals": self._world.totals(),
            "claim_ceiling": CLAIM_CEILING,
            "claim_promotions": [],
            "ladder_promotion": None,
            "scientific_claim_emitted": False,
            "knockouts": self.knockouts.to_dict(),
        }

    def assert_required_edges_covered(self) -> None:
        self._registry.assert_ready_for_world_claim(self._ledger.observed_edge_ids)

    @property
    def initial_resource_totals(self) -> dict[str, float]:
        if self._initial_resource_totals is None:
            raise IlwChainError(
                "initial_resource_totals unavailable; call bootstrap() or run() first."
            )
        return dict(self._initial_resource_totals)

    def final_digest(self) -> str:
        """Bitwise-stable digest of world + ledger + organism/capsule state."""

        organisms = [
            {
                "organism_id": org.organism_id,
                "state_digest": org.state_digest(),
            }
            for org in sorted(self._organisms.values(), key=lambda o: o.organism_id)
        ]
        capsules = [
            {
                "capsule_id": cap.capsule_id,
                "payload_digest": cap.payload_digest,
                "provenance_digest": cap.provenance_digest,
                "parent_capsule_id": cap.parent_capsule_id,
                "source_id": cap.source_id,
                "tick": cap.tick,
            }
            for cap in sorted(self._capsules.values(), key=lambda c: c.capsule_id)
        ]
        return canonical_digest(
            {
                "run_id": self.run_id,
                "tick": self._scheduler.tick,
                "world_spec_digest": self.world_spec.digest(),
                "ledger_digest": self._ledger.digest(),
                "world_digest": self._world.digest(),
                "organisms": organisms,
                "capsules": capsules,
                "lineage_records": list(self._lineage_records),
                "capsule_genealogy": list(self._capsule_genealogy),
                "claim_ceiling": CLAIM_CEILING,
            },
            prefix="ilw_final",
        )

    # ------------------------------------------------------------------ chain
    def _run_organism_chain(self, org: IlwOrganism, tick: int) -> None:
        g2t = self._edge_genome_to_toolchain(org, tick)
        if g2t is None:
            return
        t2v = self._edge_toolchain_to_vm(org, tick, parents=[g2t])
        if t2v is None:
            return
        v2a = self._edge_vm_to_action(org, tick, parents=[t2v])
        if v2a is None:
            return
        action_payload = self._peek_event(v2a)
        action = str(action_payload.get("action", "WAIT"))
        a2r = self._edge_action_to_world(org, tick, action=action, parents=[v2a])
        if a2r is None:
            return
        r2e = self._edge_world_to_experience(org, tick, parents=[a2r])
        if r2e is None:
            return
        e2c = self._edge_experience_to_capsule(org, tick, parents=[r2e])
        transport_parents = [e2c] if e2c else [r2e]
        cta = self._edge_capsule_transport(org, tick, parents=transport_parents)
        policy_parents = [cta] if cta else transport_parents
        c2p = self._edge_capsule_to_policy(org, tick, parents=policy_parents)
        surv_parents = [c2p] if c2p else policy_parents
        p2s = self._edge_policy_to_survival(org, tick, parents=surv_parents)
        if p2s is None:
            return
        mut = self._edge_survival_to_mutation(org, tick, parents=[p2s])
        if mut is None:
            return
        self._edge_lineage_inheritance(org, tick, parents=[mut])

    def _edge_genome_to_toolchain(self, org: IlwOrganism, tick: int) -> str | None:
        edge_id = "genome_to_toolchain"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        toolchain: dict[str, JsonValue] = {}
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
        else:
            accepted = 1
            # Honest adapter: genome bits select codon/toolchain preferences.
            program = build_genome_program(
                org.genome_bits, codon_width=3, lineage_tags=(org.lineage_id,)
            )
            tokens = [
                org.genome_bits[i : i + 3]
                for i in range(0, len(org.genome_bits) - 2, 3)
            ]
            toolchain = {
                "codon_tokens": tokens,
                "viable": program.viable,
                "preferred_resource_index": self._bit_int(org.genome_bits[3:6]) % 2,
                "explore": self._bit_int(org.genome_bits[0:3]) / 7.0,
                "emit_threshold": self._bit_int(org.genome_bits[9:12]) / 7.0,
                "reproduce_threshold": 0.4 + self._bit_int(org.genome_bits[12:15]) / 14.0,
            }
            org.policy_bias.setdefault("toolchain_explore", float(toolchain["explore"]))
            applied = 1
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=[],
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            extra={"toolchain": toolchain},
        )

    def _edge_toolchain_to_vm(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "toolchain_to_vm_phenotype"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        phenotype: dict[str, JsonValue] = {}
        energy_delta = 0.0
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            # Sham cost: still pay a tiny compute cost so throughput matching stays honest.
            org.energy = max(0.0, org.energy - 0.01)
            energy_delta = -0.01
        else:
            accepted = 1
            explore = float(org.policy_bias.get("toolchain_explore", 0.5))
            scores = {action: 0.05 for action in _ACTIONS}
            scores["MOVE"] += explore
            scores["HARVEST_0"] += float(org.policy_bias.get("HARVEST_0", 0.0))
            scores["HARVEST_1"] += float(org.policy_bias.get("HARVEST_1", 0.0))
            # Genome harvest preference.
            pref = self._bit_int(org.genome_bits[3:6]) % 2
            scores["HARVEST_0" if pref == 0 else "HARVEST_1"] += 0.4
            scores["EMIT"] += float(org.policy_bias.get("EMIT", 0.0))
            if org.energy >= self.reproduce_energy:
                scores["REPRODUCE"] += 0.5
            # Compute cost for phenotype construction.
            org.energy = max(0.0, org.energy - 0.05)
            energy_delta = -0.05
            phenotype = {"action_scores": scores}
            applied = 1
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            energy_delta=energy_delta,
            extra={"phenotype": phenotype},
        )

    def _edge_vm_to_action(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "vm_phenotype_to_action"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        action = "WAIT"
        energy_delta = 0.0
        parent_payload = self._peek_event(parents[0]) if parents else {}
        scores_raw = parent_payload.get("phenotype", {})
        scores = {}
        if isinstance(scores_raw, Mapping):
            maybe = scores_raw.get("action_scores", {})
            if isinstance(maybe, Mapping):
                scores = {str(k): float(v) for k, v in maybe.items()}
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            org.energy = max(0.0, org.energy - 0.01)
            energy_delta = -0.01
        else:
            accepted = 1
            if not scores:
                scores = {"WAIT": 1.0}
            # Deterministic argmax with RNG tie-break from seed namespace.
            rng = self.seed_namespace.fork_rng("action", org.organism_id, f"t{tick}")
            best = max(scores.values())
            candidates = sorted(k for k, v in scores.items() if v == best)
            action = candidates[int(rng.randrange(0, len(candidates)))]
            applied = 1
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            energy_delta=energy_delta,
            extra={"action": action, "action_scores": scores},
        )

    def _edge_action_to_world(
        self,
        org: IlwOrganism,
        tick: int,
        *,
        action: str,
        parents: Sequence[str],
    ) -> str | None:
        edge_id = "action_to_resource_world"
        before = self._world.digest()
        before_org = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        energy_delta = 0.0
        resource_delta = 0.0
        fitness_proxy_delta = 0.0
        detail: dict[str, JsonValue] = {"action": action}
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
        else:
            accepted = 1
            if action == "MOVE":
                rng = self.seed_namespace.fork_rng("move", org.organism_id, f"t{tick}")
                dx, dy = ((1, 0), (-1, 0), (0, 1), (0, -1))[int(rng.randrange(0, 4))]
                nx = max(0, min(self.world_spec.width - 1, org.x + dx))
                ny = max(0, min(self.world_spec.height - 1, org.y + dy))
                org.x, org.y = nx, ny
                org.energy = max(0.0, org.energy - self.move_cost)
                energy_delta = -self.move_cost
                detail["position"] = [org.x, org.y]
                applied = 1
            elif action in {"HARVEST_0", "HARVEST_1"}:
                idx = 0 if action == "HARVEST_0" else 1
                kind = self.world_spec.resource_kinds[idx]
                taken = self._world.harvest(org.x, org.y, kind)
                gain = taken * self.harvest_gain_scale
                org.energy += gain
                energy_delta = gain
                resource_delta = -taken
                fitness_proxy_delta = gain
                detail.update({"kind": kind, "taken": taken, "position": [org.x, org.y]})
                org.last_experience = {
                    "kind": "harvest",
                    "resource_kind": kind,
                    "taken": taken,
                    "x": org.x,
                    "y": org.y,
                    "tick": tick,
                }
                applied = 1 if taken > 0 else 0
                if taken <= 0:
                    blocked = "no_resource_available"
            elif action == "EMIT":
                # Emission itself is applied on experience_to_capsule; pay cost here.
                org.energy = max(0.0, org.energy - self.emit_cost)
                energy_delta = -self.emit_cost
                detail["emit_intent"] = True
                applied = 1
            elif action == "REPRODUCE":
                detail["reproduce_intent"] = True
                applied = 1
            else:
                applied = 1
            # Metabolism always applies on an accepted world step.
            org.energy = max(0.0, org.energy - self.metabolism)
            energy_delta -= self.metabolism
        after = self._world.digest()
        _ = before_org
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            energy_delta=energy_delta,
            resource_delta=resource_delta,
            fitness_proxy_delta=fitness_proxy_delta,
            extra=detail,
        )

    def _edge_world_to_experience(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "resource_world_to_experienced_event"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        experience: dict[str, JsonValue] = {}
        energy_delta = 0.0
        resource_delta = 0.0
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
        else:
            accepted = 1
            parent = self._peek_event(parents[0]) if parents else {}
            experience = {
                "action": str(parent.get("action", "WAIT")),
                "taken": float(parent.get("taken", 0.0) or 0.0),
                "kind": str(parent.get("kind", "")),
                "position": list(parent.get("position", [org.x, org.y])),
                "world_digest": self._world.digest(),
            }
            if org.last_experience is not None:
                experience["last_experience"] = dict(org.last_experience)
            resource_delta = float(parent.get("resource_delta", 0.0) or 0.0)
            energy_delta = float(parent.get("energy_delta", 0.0) or 0.0)
            applied = 1
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            energy_delta=energy_delta,
            resource_delta=resource_delta,
            extra={"experience": experience, "source_id": org.organism_id},
            source_id=org.organism_id,
        )

    def _edge_experience_to_capsule(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "experience_to_capsule"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        capsule_id = ""
        payload_digest = ""
        provenance_digest = ""
        parent_capsule_id = ""
        parent_event = self._peek_event(parents[0]) if parents else {}
        experience = parent_event.get("experience", {})
        # Only form capsules from real harvest experience (not hand payloads).
        should_emit = (
            isinstance(experience, Mapping)
            and str(experience.get("action", "")) in {"HARVEST_0", "HARVEST_1", "EMIT"}
            and (
                float(experience.get("taken", 0.0) or 0.0) > 0.0
                or str(experience.get("action", "")) == "EMIT"
            )
        )
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            # Sham emit cost already paid on action path; do not fabricate capsule.
        elif not should_emit:
            blocked = "no_experience_for_capsule"
            accepted = 1
        else:
            accepted = 1
            pattern = (
                str(experience.get("action", "WAIT")),
                str(experience.get("kind", "unknown")),
                f"pos:{experience.get('position', [org.x, org.y])}",
            )
            payload_digest = canonical_digest(
                {"pattern": list(pattern), "taken": experience.get("taken", 0.0)},
                prefix="ilw_capsule_payload",
            )
            provenance_digest = canonical_digest(
                {
                    "source_id": org.organism_id,
                    "lineage_id": org.lineage_id,
                    "experience_event": parents[0] if parents else "",
                    "genome_digest": org.genome_digest,
                },
                prefix="ilw_capsule_provenance",
            )
            capsule_id = f"{self.run_id}:cap:{tick}:{org.organism_id}:{self._event_seq + 1}"
            # Capsule genealogy: link to most recent capsule from same lineage if any.
            prior = [
                c
                for c in self._capsules.values()
                if c.lineage_id == org.lineage_id and c.source_id == org.organism_id
            ]
            parent_capsule_id = prior[-1].capsule_id if prior else ""
            record = CapsuleRecord(
                capsule_id=capsule_id,
                parent_capsule_id=parent_capsule_id or None,
                source_id=org.organism_id,
                lineage_id=org.lineage_id,
                payload_digest=payload_digest,
                provenance_digest=provenance_digest,
                event_pattern=pattern,
                tick=tick,
            )
            self._capsules[capsule_id] = record
            self._capsule_genealogy.append(
                {
                    "capsule_id": capsule_id,
                    "capsule_parent_id": parent_capsule_id or None,
                    "source_id": org.organism_id,
                    "lineage_id": org.lineage_id,
                    "payload_digest": payload_digest,
                    "provenance_digest": provenance_digest,
                    "tick": tick,
                }
            )
            applied = 1
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            capsule_id=capsule_id,
            capsule_parent_id=parent_capsule_id,
            payload_digest=payload_digest,
            provenance_digest=provenance_digest,
        )

    def _edge_capsule_transport(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "capsule_transport_accept_apply"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        capsule_id = ""
        payload_digest = ""
        provenance_digest = ""
        parent_capsule_id = ""
        source_id = ""
        # Find a foreign active capsule to transport.
        candidates = [
            c
            for c in self._capsules.values()
            if c.active_at(tick) and c.source_id != org.organism_id
        ]
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
        elif not candidates:
            blocked = "no_capsule_to_transport"
            accepted = 0
        else:
            # Deterministic choice.
            candidates.sort(key=lambda c: c.capsule_id)
            chosen = candidates[0]
            attempted = 1
            accepted = 1  # transport+accept succeed; apply counted separately below
            # Apply means receiver stores capsule id for policy edge.
            capsule_id = chosen.capsule_id
            payload_digest = chosen.payload_digest
            provenance_digest = chosen.provenance_digest
            parent_capsule_id = chosen.parent_capsule_id or ""
            source_id = chosen.source_id
            if capsule_id not in org.adopted_capsules:
                org.adopted_capsules.append(capsule_id)
                applied = 1
            else:
                blocked = "already_adopted"
                applied = 0
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            capsule_id=capsule_id,
            capsule_parent_id=parent_capsule_id,
            payload_digest=payload_digest,
            provenance_digest=provenance_digest,
            source_id=source_id or org.organism_id,
        )

    def _edge_capsule_to_policy(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "capsule_to_policy"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        energy_delta = 0.0
        fitness_proxy_delta = 0.0
        capsule_id = ""
        payload_digest = ""
        provenance_digest = ""
        parent = self._peek_event(parents[0]) if parents else {}
        transported = str(parent.get("capsule_id", "") or "")
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
        elif not transported or int(parent.get("applied", 0) or 0) < 1:
            blocked = "no_applied_capsule"
            accepted = 1
        else:
            accepted = 1
            capsule = self._capsules.get(transported)
            if capsule is None:
                blocked = "missing_capsule"
            else:
                capsule_id = capsule.capsule_id
                payload_digest = capsule.payload_digest
                provenance_digest = capsule.provenance_digest
                # Change receiver policy from capsule content (honest, no oracle).
                pattern = capsule.event_pattern
                if len(pattern) >= 2 and pattern[1] in self.world_spec.resource_kinds:
                    kind = pattern[1]
                    idx = list(self.world_spec.resource_kinds).index(kind)
                    key = "HARVEST_0" if idx == 0 else "HARVEST_1"
                    org.policy_bias[key] = float(org.policy_bias.get(key, 0.0)) + 0.35
                    org.policy_bias["EMIT"] = float(org.policy_bias.get("EMIT", 0.0)) + 0.1
                    # Small learning ATP cost.
                    org.energy = max(0.0, org.energy - 0.05)
                    energy_delta = -0.05
                    fitness_proxy_delta = 0.0
                    applied = 1
                else:
                    blocked = "capsule_pattern_unusable"
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            energy_delta=energy_delta,
            fitness_proxy_delta=fitness_proxy_delta,
            capsule_id=capsule_id,
            payload_digest=payload_digest,
            provenance_digest=provenance_digest,
        )

    def _edge_policy_to_survival(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "policy_to_survival_reproduction"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        energy_delta = 0.0
        resource_delta = 0.0
        fitness_proxy_delta = 0.0
        birth_id = ""
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
        else:
            accepted = 1
            if org.energy <= 0:
                org.alive = False
                fitness_proxy_delta = -1.0
                applied = 1
                blocked = "death_by_energy"
            else:
                # Reproduction decision from energy + genome threshold (policy influenced).
                # Honor reproduce_intent from the action edge when present (same causal chain).
                intent = False
                for pid in parents:
                    payload = self._peek_event(pid)
                    # Walk one hop to action_to_resource_world if needed.
                    if payload.get("reproduce_intent"):
                        intent = True
                    if payload.get("action") == "REPRODUCE":
                        intent = True
                    for grand in payload.get("causal_parent_ids", []) or []:
                        gp = self._peek_event(str(grand))
                        if gp.get("reproduce_intent") or gp.get("action") == "REPRODUCE":
                            intent = True
                thresh_bits = self._bit_int(org.genome_bits[12:15]) / 7.0
                threshold = self.reproduce_energy * (0.75 + 0.35 * thresh_bits)
                # Policy bias can lower effective threshold slightly (learned).
                threshold -= 0.25 * float(org.policy_bias.get("HARVEST_0", 0.0))
                threshold -= 0.25 * float(org.policy_bias.get("HARVEST_1", 0.0))
                if intent:
                    threshold = min(threshold, self.reproduce_energy)
                can_birth = (
                    org.energy >= max(self.reproduce_cost + 0.4, threshold)
                    and len(self.alive_organisms) < self.world_spec.population_cap
                )
                if can_birth:
                    birth_id = self._spawn_child_placeholder(org, tick)
                    org.energy -= self.reproduce_cost
                    energy_delta = -self.reproduce_cost
                    fitness_proxy_delta = 1.0
                    applied = 1
                else:
                    blocked = "no_reproduction_this_tick"
                    applied = 1  # survival update applied (still alive)
        after = org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            energy_delta=energy_delta,
            resource_delta=resource_delta,
            fitness_proxy_delta=fitness_proxy_delta,
            extra={"birth_id": birth_id},
        )

    def _spawn_child_placeholder(self, parent: IlwOrganism, tick: int) -> str:
        """Allocate child id; mutation/lineage edge fills genome."""

        self._birth_counter += 1
        child_id = f"{self.run_id}:org:birth:{tick}:{self._birth_counter}"
        # Temporary genome = parent; mutation edge may replace.
        child = IlwOrganism(
            organism_id=child_id,
            lineage_id=parent.lineage_id,
            generation=parent.generation + 1,
            x=parent.x,
            y=parent.y,
            energy=1.0,
            genome_bits=parent.genome_bits,
            genome_digest=parent.genome_digest,
            parent_id=parent.organism_id,
            policy_bias={},  # inheritance edge may copy
            alive=True,
        )
        self._organisms[child_id] = child
        return child_id

    def _edge_survival_to_mutation(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "survival_reproduction_to_mutation_lineage"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        parent_event = self._peek_event(parents[0]) if parents else {}
        birth_id = str(parent_event.get("birth_id", "") or "")
        child = self._organisms.get(birth_id)
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            # Birth still happened; genome stays clonal (no mutation record).
            if child is not None:
                accepted = 1
        elif child is None:
            blocked = "no_birth"
            accepted = 1
        else:
            accepted = 1
            program = build_genome_program(
                child.genome_bits,
                codon_width=3,
                lineage_tags=(child.lineage_id, f"gen-{child.generation}"),
            )
            rng = self.seed_namespace.fork_rng("mutation", child.organism_id, f"t{tick}")
            cfg = StructuralMutationConfig(
                bit_flip_rate=0.5,
                codon_insert_rate=0.0,
                codon_delete_rate=0.0,
                codon_duplicate_rate=0.0,
                codon_invert_rate=0.0,
                codon_translocate_rate=0.0,
            )
            mutated, record = mutate_genome_program(program, config=cfg, rng=rng, kind="bit_flip")
            child.genome_bits = mutated.bits
            child.genome_digest = mutated.identity_digest
            self._lineage_records.append(
                {
                    "organism_id": child.organism_id,
                    "lineage_id": child.lineage_id,
                    "parent_id": org.organism_id,
                    "generation": child.generation,
                    "genome_digest": child.genome_digest,
                    "parent_genome_digest": org.genome_digest,
                    "mutation_digest": record.digest,
                    "tick": tick,
                }
            )
            applied = 1
        after = (child.state_digest() if child is not None else org.state_digest())
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            extra={
                "birth_id": birth_id,
                "child_genome_digest": child.genome_digest if child else "",
            },
        )

    def _edge_lineage_inheritance(
        self, org: IlwOrganism, tick: int, *, parents: Sequence[str]
    ) -> str | None:
        edge_id = "lineage_inheritance"
        before = org.state_digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        parent_event = self._peek_event(parents[0]) if parents else {}
        birth_id = str(parent_event.get("birth_id", "") or "")
        child = self._organisms.get(birth_id)
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            if child is not None:
                # Severed inheritance: child keeps empty policy / no parent bias copy.
                child.policy_bias = {}
                accepted = 1
        elif child is None:
            blocked = "no_child_to_inherit"
            accepted = 1
        else:
            accepted = 1
            # Inherit a fraction of parent policy (joinable with capsule genealogy).
            child.policy_bias = {
                key: 0.5 * float(val) for key, val in org.policy_bias.items()
            }
            applied = 1
        after = child.state_digest() if child is not None else org.state_digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=org,
            parents=parents,
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            extra={"birth_id": birth_id},
        )

    def _edge_ecological_state(self, tick: int, *, parents: Sequence[str]) -> str | None:
        edge_id = "mutation_lineage_to_next_ecological_state"
        before = self._world.digest()
        attempted = 1
        accepted = 1
        applied = 0
        blocked: str | None = None
        resource_delta = 0.0
        fitness_proxy_delta = 0.0
        alive = len(self.alive_organisms)
        # Ecological state summary: density + resource totals after births/deaths.
        eco = {
            "alive": alive,
            "population_cap": self.world_spec.population_cap,
            "resource_totals": self._world.totals(),
            "lineage_count": len({o.lineage_id for o in self.alive_organisms}),
        }
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            accepted = 0
        else:
            applied = 1
            fitness_proxy_delta = float(alive)
        after_eco = canonical_digest(eco, prefix="ilw_eco_state")
        event_id = self._emit(
            edge_id,
            tick=tick,
            org=None,
            parents=list(parents),
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after_eco,
            resource_delta=resource_delta,
            fitness_proxy_delta=fitness_proxy_delta,
            extra={"ecological_state": eco},
            actor_id="ecology",
            lineage_id="ecology",
            genome_digest="",
        )
        # Feedback edge.
        self._edge_ecological_feedback(tick, parents=[event_id] if event_id else [])
        return event_id

    def _edge_ecological_feedback(self, tick: int, *, parents: Sequence[str]) -> str | None:
        edge_id = "ecological_feedback"
        before = self._world.digest()
        attempted = 1
        accepted = 0
        applied = 0
        blocked: str | None = None
        resource_delta = 0.0
        deltas: dict[str, float] = {}
        if self.knockouts.cuts_edge(edge_id):
            blocked = self.knockouts.blocked_reason(edge_id)
            # Sham: skip renew but keep attempted telemetry.
        else:
            accepted = 1
            alive = len(self.alive_organisms)
            # Density pressure: more alive -> slower renewal.
            pressure = max(0.25, 1.0 - (alive / max(1, self.world_spec.population_cap)))
            deltas = self._world.renew(pressure=pressure)
            resource_delta = float(sum(deltas.values()))
            applied = 1
        after = self._world.digest()
        return self._emit(
            edge_id,
            tick=tick,
            org=None,
            parents=list(parents),
            attempted=attempted,
            accepted=accepted,
            applied=applied,
            blocked_reason=blocked,
            before=before,
            after=after,
            resource_delta=resource_delta,
            extra={"renewal_deltas": deltas},
            actor_id="ecology",
            lineage_id="ecology",
            genome_digest="",
        )

    # ---------------------------------------------------------------- telemetry
    def _emit(
        self,
        edge_id: str,
        *,
        tick: int,
        org: IlwOrganism | None,
        parents: Sequence[str],
        attempted: int,
        accepted: int,
        applied: int,
        blocked_reason: str | None,
        before: str,
        after: str,
        energy_delta: float = 0.0,
        resource_delta: float = 0.0,
        fitness_proxy_delta: float = 0.0,
        capsule_id: str = "",
        capsule_parent_id: str = "",
        payload_digest: str = "",
        provenance_digest: str = "",
        source_id: str = "",
        actor_id: str | None = None,
        lineage_id: str | None = None,
        genome_digest: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> str:
        self._event_seq += 1
        event_id = f"{self.run_id}:evt:{self._event_seq}"
        actor = actor_id if actor_id is not None else (org.organism_id if org else "world")
        lin = lineage_id if lineage_id is not None else (org.lineage_id if org else "")
        gdig = (
            genome_digest
            if genome_digest is not None
            else (org.genome_digest if org else "")
        )
        generation = int(org.generation) if org is not None else 0
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "seed": self.world_spec.seed,
            "tick": tick,
            "generation": generation,
            "world_spec_digest": self.world_spec.digest(),
            "event_id": event_id,
            "causal_parent_ids": list(parents),
            "edge_id": edge_id,
            "actor_id": actor,
            "lineage_id": lin,
            "genome_digest": gdig,
            "source_id": source_id,
            "capsule_id": capsule_id,
            "capsule_parent_id": capsule_parent_id,
            "payload_digest": payload_digest,
            "provenance_digest": provenance_digest,
            "attempted": int(attempted),
            "accepted": int(accepted),
            "applied": int(applied),
            "blocked_reason": blocked_reason or "",
            "state_before_digest": before,
            "state_after_digest": after,
            "energy_delta": float(energy_delta),
            "resource_delta": float(resource_delta),
            "fitness_proxy_delta": float(fitness_proxy_delta),
        }
        if extra:
            for key, value in extra.items():
                if key in payload:
                    continue
                payload[key] = value
        assert_no_fixture_outcome_injection(payload)
        self._ledger.append(payload)
        return event_id

    def _peek_event(self, event_id: str) -> Mapping[str, JsonValue]:
        return self._ledger.get(event_id).payload

    def _last_event_id_for_edges(self, edge_ids: Sequence[str]) -> str | None:
        wanted = set(edge_ids)
        for event in reversed(self._ledger.events):
            if event.edge_id in wanted:
                return event.event_id
        return None

    @staticmethod
    def _bit_int(bits: str) -> int:
        if not bits:
            return 0
        return int(bits, 2)
