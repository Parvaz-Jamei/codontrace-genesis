"""Phase 10 — genome-aware dual digests on Zaman freeze/replay/reciprocal arms.

Layers host + parasite ``SemanticGenome.digest()`` trajectories onto the same
three-arm contrast as Phase 7. Repertoire richness fields remain for continuity;
complexity emergence and Red Queen stay unproved. No infection physics in
``engine.py``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_zaman import (
    ZAMAN_ARMS,
    RepertoireSummary,
    run_zaman_three_arm_campaign,
)
from codontrace.genesis.structural_mutation import GenomeProgram
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_genome_zaman_campaign_v1"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_DEFAULT_LENGTH = 8


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    out: list[int] = []
    for item in seeds:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ConfigurationError("seeds must be integers.")
        out.append(int(item))
    return tuple(out)


def _require_arms(arms: Sequence[str] | None) -> tuple[str, ...]:
    ordered = (
        "freeze_parasites",
        "replay_parasite_schedule",
        "reciprocal_coevolution",
    )
    if arms is None:
        return ordered
    if not arms:
        raise ConfigurationError("arms must be non-empty when provided.")
    cleaned: list[str] = []
    for raw in arms:
        name = str(raw).strip()
        if name not in ZAMAN_ARMS:
            raise ConfigurationError(f"unknown Zaman arm {raw!r}.")
        if name not in cleaned:
            cleaned.append(name)
    return tuple(cleaned)


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _genome_for_seed(seed: int, role: str, length: int = _DEFAULT_LENGTH) -> SemanticGenome:
    """Deterministic SemanticGenome from seed+role (binary3 default)."""

    return SemanticGenome.random(length=length, seed=int(seed) * 1_000_003 + len(role) * 17 + sum(ord(c) for c in role) % 97)


def _flip_codons(genome: SemanticGenome, seed: int, step: int, flips: int) -> SemanticGenome:
    """Flip up to ``flips`` codon symbols deterministically (content mutation)."""

    codons = list(genome.to_codons())
    if not codons or flips <= 0:
        return genome
    digest = _seed_bytes(seed, f"flip_{step}")
    alphabet = tuple(genome.spec.alphabet)
    width = genome.spec.codon_width
    n = min(flips, len(codons))
    for i in range(n):
        idx = digest[i % len(digest)] % len(codons)
        symbols = list(codons[idx])
        pos = digest[(i + 1) % len(digest)] % width
        current = symbols[pos]
        # Pick a different alphabet symbol when possible.
        choices = [s for s in alphabet if s != current] or list(alphabet)
        symbols[pos] = choices[digest[(i + 2) % len(digest)] % len(choices)]
        codons[idx] = "".join(symbols)
    return SemanticGenome.from_codons(codons, spec=genome.spec)


def _program_identity(genome: SemanticGenome) -> str:
    """Secondary GenomeProgram identity digest (never primary claim surface)."""

    program = GenomeProgram(
        bits=genome.to_compact(),
        codon_width=genome.spec.codon_width,
        macro_registry_digest=None,
        lineage_tags=(),
        structural_mutation_digest=None,
        digest="",
    )
    return str(program.identity_digest)


@dataclass(frozen=True, slots=True)
class DualGenomeSummary:
    """Host + parasite genome digests with trajectories; complexity unproved."""

    host_genome_digest: str
    parasite_genome_digest: str
    host_genome_length: int
    parasite_genome_length: int
    host_digest_trajectory: tuple[str, ...]
    parasite_digest_trajectory: tuple[str, ...]
    parasite_schedule_digest: str
    host_program_identity: str
    parasite_program_identity: str
    parasite_genome_frozen: bool
    parasite_schedule_predetermined: bool
    reciprocal_genome_update: bool
    complexity_emergence_proved: bool
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "host_genome_digest": self.host_genome_digest,
            "parasite_genome_digest": self.parasite_genome_digest,
            "host_genome_length": self.host_genome_length,
            "parasite_genome_length": self.parasite_genome_length,
            "host_digest_trajectory": list(self.host_digest_trajectory),
            "parasite_digest_trajectory": list(self.parasite_digest_trajectory),
            "parasite_schedule_digest": self.parasite_schedule_digest,
            "host_program_identity": self.host_program_identity,
            "parasite_program_identity": self.parasite_program_identity,
            "parasite_genome_frozen": self.parasite_genome_frozen,
            "parasite_schedule_predetermined": self.parasite_schedule_predetermined,
            "reciprocal_genome_update": self.reciprocal_genome_update,
            "complexity_emergence_proved": self.complexity_emergence_proved,
            "red_queen_proved": self.red_queen_proved,
            "primary_digest_surface": "semantic_genome",
            "genome_program_identity_is_secondary": True,
        }
        body["digest"] = _digest_body(body)
        return body


@dataclass(frozen=True, slots=True)
class GenomeZamanSeedOutcome:
    seed: int
    arm: str
    genomes: DualGenomeSummary
    repertoire: RepertoireSummary
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "seed": self.seed,
            "arm": self.arm,
            "genomes": self.genomes.to_dict(),
            "repertoire": self.repertoire.to_dict(),
            "notes": list(self.notes),
        }
        body["digest"] = _digest_body({k: body[k] for k in body if k != "digest"})
        return body


@dataclass(frozen=True, slots=True)
class GenomeZamanArmResult:
    arm: str
    seed_outcomes: tuple[GenomeZamanSeedOutcome, ...]
    mean_host_genome_length: float
    distinct_parasite_final_digests: int

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.seed_outcomes]
        body: dict[str, object] = {
            "arm": self.arm,
            "seed_count": len(self.seed_outcomes),
            "mean_host_genome_length": self.mean_host_genome_length,
            "distinct_parasite_final_digests": self.distinct_parasite_final_digests,
            "seed_outcomes": outcomes,
            "seed_digests": [str(item["digest"]) for item in outcomes],
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
        }
        body["digest"] = _digest_body({k: body[k] for k in body if k != "digest"})
        return body


@dataclass(frozen=True, slots=True)
class GenomeZamanCampaignResult:
    """Three-arm genome-aware Zaman contrast; complexity / RQ unproved."""

    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    steps: int
    genome_length: int
    arm_results: tuple[GenomeZamanArmResult, ...]
    claim_ceiling: str
    complexity_emergence_proved: bool
    red_queen_proved: bool
    arms_are_distinct: bool
    repertoire_campaign_digest: str

    def to_dict(self) -> dict[str, object]:
        arm_dicts = [item.to_dict() for item in self.arm_results]
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "steps": self.steps,
            "genome_length": self.genome_length,
            "arm_results": arm_dicts,
            "arm_digests": {str(item["arm"]): str(item["digest"]) for item in arm_dicts},
            "claim_ceiling": self.claim_ceiling,
            "complexity_emergence_proved": self.complexity_emergence_proved,
            "red_queen_proved": self.red_queen_proved,
            "arms_are_distinct": self.arms_are_distinct,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "zaman_scope": "digital_genome_analogue_only",
            "repertoire_campaign_digest": self.repertoire_campaign_digest,
            "zaman_citation": "doi:10.1371/journal.pbio.1002023",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _schedule_digest(trajectory: Sequence[str]) -> str:
    return _digest_body({"parasite_digest_trajectory": list(trajectory)})


def _run_freeze_genomes(
    *,
    seed: int,
    steps: int,
    genome_length: int,
    repertoire: RepertoireSummary,
) -> GenomeZamanSeedOutcome:
    host = _genome_for_seed(seed, "host_freeze", genome_length)
    parasite = _genome_for_seed(seed, "parasite_freeze", genome_length)
    frozen_digest = parasite.digest()
    host_traj = [host.digest()]
    parasite_traj = [frozen_digest]
    notes = ["parasite_genome_frozen_at_t0"]
    for step in range(1, steps + 1):
        host = _flip_codons(host, seed, step, flips=2)
        host_traj.append(host.digest())
        parasite_traj.append(frozen_digest)  # frozen
        notes.append(f"freeze_step_{step}_host_mutated")
    genomes = DualGenomeSummary(
        host_genome_digest=host.digest(),
        parasite_genome_digest=frozen_digest,
        host_genome_length=len(host),
        parasite_genome_length=len(parasite),
        host_digest_trajectory=tuple(host_traj),
        parasite_digest_trajectory=tuple(parasite_traj),
        parasite_schedule_digest=_schedule_digest(parasite_traj),
        host_program_identity=_program_identity(host),
        parasite_program_identity=_program_identity(parasite),
        parasite_genome_frozen=True,
        parasite_schedule_predetermined=False,
        reciprocal_genome_update=False,
        complexity_emergence_proved=False,
        red_queen_proved=False,
    )
    return GenomeZamanSeedOutcome(
        seed=seed,
        arm="freeze_parasites",
        genomes=genomes,
        repertoire=repertoire,
        notes=tuple(notes),
    )


def _run_replay_genomes(
    *,
    seed: int,
    steps: int,
    genome_length: int,
    repertoire: RepertoireSummary,
) -> GenomeZamanSeedOutcome:
    host = _genome_for_seed(seed, "host_replay", genome_length)
    # Precompute parasite schedule (fixed history); host mutates without reciprocal.
    parasite = _genome_for_seed(seed, "parasite_replay", genome_length)
    schedule: list[SemanticGenome] = [parasite]
    for step in range(1, steps + 1):
        # Predetermined flips using a salt independent of host state.
        parasite = _flip_codons(parasite, seed, step + 1000, flips=1)
        schedule.append(parasite)
    host_traj = [host.digest()]
    parasite_traj = [schedule[0].digest()]
    notes = ["parasite_genome_schedule_predetermined", f"schedule_len_{len(schedule)}"]
    for step in range(1, steps + 1):
        host = _flip_codons(host, seed, step, flips=1)  # weaker than freeze pressure
        host_traj.append(host.digest())
        parasite_traj.append(schedule[step].digest())
        notes.append(f"replay_step_{step}")
    final_parasite = schedule[-1]
    genomes = DualGenomeSummary(
        host_genome_digest=host.digest(),
        parasite_genome_digest=final_parasite.digest(),
        host_genome_length=len(host),
        parasite_genome_length=len(final_parasite),
        host_digest_trajectory=tuple(host_traj),
        parasite_digest_trajectory=tuple(parasite_traj),
        parasite_schedule_digest=_schedule_digest(parasite_traj),
        host_program_identity=_program_identity(host),
        parasite_program_identity=_program_identity(final_parasite),
        parasite_genome_frozen=False,
        parasite_schedule_predetermined=True,
        reciprocal_genome_update=False,
        complexity_emergence_proved=False,
        red_queen_proved=False,
    )
    return GenomeZamanSeedOutcome(
        seed=seed,
        arm="replay_parasite_schedule",
        genomes=genomes,
        repertoire=repertoire,
        notes=tuple(notes),
    )


def _run_reciprocal_genomes(
    *,
    seed: int,
    steps: int,
    genome_length: int,
    repertoire: RepertoireSummary,
) -> GenomeZamanSeedOutcome:
    host = _genome_for_seed(seed, "host_recip", genome_length)
    parasite = _genome_for_seed(seed, "parasite_recip", genome_length)
    host_traj = [host.digest()]
    parasite_traj = [parasite.digest()]
    notes = ["reciprocal_host_and_parasite_genome_update"]
    for step in range(1, steps + 1):
        host = _flip_codons(host, seed, step, flips=2)
        # Parasite co-adapts using host digest salt so trajectory depends on host.
        parasite = _flip_codons(
            parasite,
            seed,
            step + (int(host.digest()[:8], 16) % 97),
            flips=2,
        )
        host_traj.append(host.digest())
        parasite_traj.append(parasite.digest())
        notes.append(f"recip_step_{step}")
    genomes = DualGenomeSummary(
        host_genome_digest=host.digest(),
        parasite_genome_digest=parasite.digest(),
        host_genome_length=len(host),
        parasite_genome_length=len(parasite),
        host_digest_trajectory=tuple(host_traj),
        parasite_digest_trajectory=tuple(parasite_traj),
        parasite_schedule_digest=_schedule_digest(parasite_traj),
        host_program_identity=_program_identity(host),
        parasite_program_identity=_program_identity(parasite),
        parasite_genome_frozen=False,
        parasite_schedule_predetermined=False,
        reciprocal_genome_update=True,
        complexity_emergence_proved=False,
        red_queen_proved=False,
    )
    return GenomeZamanSeedOutcome(
        seed=seed,
        arm="reciprocal_coevolution",
        genomes=genomes,
        repertoire=repertoire,
        notes=tuple(notes),
    )


_ARM_RUNNERS = {
    "freeze_parasites": _run_freeze_genomes,
    "replay_parasite_schedule": _run_replay_genomes,
    "reciprocal_coevolution": _run_reciprocal_genomes,
}


def run_genome_zaman_campaign(
    *,
    seeds: Sequence[int],
    steps: int = 3,
    genome_length: int = _DEFAULT_LENGTH,
    arms: Sequence[str] | None = None,
    request_claim_ceiling: str = "runtime_observation",
) -> GenomeZamanCampaignResult:
    """Run freeze ≠ replay ≠ reciprocal with dual-genome digests + repertoire.

    Never sets ``complexity_emergence_proved`` or ``red_queen_proved``.
    ``candidate_evidence`` requires pairwise-distinct arm digests.
    """

    seed_tuple = _require_seeds(seeds)
    arm_tuple = _require_arms(arms)
    if steps < 1:
        raise ConfigurationError("steps must be >= 1.")
    if genome_length < 2:
        raise ConfigurationError("genome_length must be >= 2.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    # Layer repertoire continuity from Phase 7 Zaman campaign (same seeds/steps/arms).
    repertoire_campaign = run_zaman_three_arm_campaign(
        seeds=seed_tuple,
        steps=steps,
        arms=arm_tuple,
        request_claim_ceiling="runtime_observation",
    )
    repertoire_by_arm_seed: dict[tuple[str, int], RepertoireSummary] = {}
    for arm_result in repertoire_campaign.arm_results:
        for outcome in arm_result.seed_outcomes:
            repertoire_by_arm_seed[(arm_result.arm, outcome.seed)] = outcome.repertoire
    repertoire_digest = str(repertoire_campaign.to_dict()["campaign_digest"])

    arm_results: list[GenomeZamanArmResult] = []
    for arm in arm_tuple:
        runner = _ARM_RUNNERS[arm]
        seed_outcomes: list[GenomeZamanSeedOutcome] = []
        for seed in seed_tuple:
            seed_outcomes.append(
                runner(
                    seed=seed,
                    steps=steps,
                    genome_length=genome_length,
                    repertoire=repertoire_by_arm_seed[(arm, seed)],
                )
            )
        lengths = [float(item.genomes.host_genome_length) for item in seed_outcomes]
        parasite_finals = {item.genomes.parasite_genome_digest for item in seed_outcomes}
        arm_results.append(
            GenomeZamanArmResult(
                arm=arm,
                seed_outcomes=tuple(seed_outcomes),
                mean_host_genome_length=sum(lengths) / len(lengths),
                distinct_parasite_final_digests=len(parasite_finals),
            )
        )

    digests = [item.to_dict()["digest"] for item in arm_results]
    arms_distinct = len(set(digests)) == len(digests) and len(digests) >= 2
    if ceiling == "candidate_evidence" and not arms_distinct:
        raise ConfigurationError(
            "candidate_evidence refused: Zaman genome arms must produce distinct digests "
            "(need >=2 pairwise-distinct arms)."
        )

    return GenomeZamanCampaignResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=arm_tuple,
        steps=steps,
        genome_length=genome_length,
        arm_results=tuple(arm_results),
        claim_ceiling=ceiling if arms_distinct or ceiling == "runtime_observation" else "runtime_observation",
        complexity_emergence_proved=False,
        red_queen_proved=False,
        arms_are_distinct=arms_distinct,
        repertoire_campaign_digest=repertoire_digest,
    )


__all__ = [
    "SCHEMA",
    "DualGenomeSummary",
    "GenomeZamanArmResult",
    "GenomeZamanCampaignResult",
    "GenomeZamanSeedOutcome",
    "run_genome_zaman_campaign",
]
