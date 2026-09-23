"""Phase 23 — Scanlan mutator / abiotic-constraint dual-null (earn-in).

Genome-layer mutation-rate factor crossed with coevolution vs abiotic arms.
Designed so ``elevated_mutation_under_coevolution_always_improves_abiotic`` can
fail (Scanlan et al. 2015 honesty map: coevolution can constrain
abiotic-beneficial acquisition). ``gene_identity_proved`` stays False; no wet
mutator-gene identity or CRISPR claim.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genome import SemanticGenome
from codontrace.metrics.diversity import (
    codon_usage_entropy,
    mean_genome_distance,
    unique_genome_count,
)

SCHEMA = "host_parasite_scanlan_mutator_dual_null_v1"
ARMS = (
    "coevolution_elevated_mutation",
    "coevolution_baseline_mutation",
    "abiotic_elevated_mutation",
    "content_null_elevated_mutation",
)
HYPOTHESIS = "elevated_mutation_under_coevolution_always_improves_abiotic"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    out: list[int] = []
    seen: set[int] = set()
    for index, seed in enumerate(seeds):
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ConfigurationError(f"seeds[{index}] must be a non-negative int.")
        if seed in seen:
            raise ConfigurationError(f"duplicate seed {seed}.")
        seen.add(seed)
        out.append(seed)
    return tuple(out)


def _genome_for_seed(seed: int, role: str, length: int = 12) -> SemanticGenome:
    return SemanticGenome.random(
        length=length,
        seed=int(seed) * 1_000_019 + sum(ord(c) for c in role) * 13 + len(role),
    )


def _flip_codons(
    genome: SemanticGenome, seed: int, step: int, flips: int
) -> SemanticGenome:
    codons = list(genome.to_codons())
    if not codons or flips <= 0:
        return genome
    digest = _seed_bytes(seed, f"mut_flip_{step}")
    alphabet = tuple(genome.spec.alphabet)
    width = genome.spec.codon_width
    for i in range(min(flips, len(codons))):
        idx = digest[i % len(digest)] % len(codons)
        symbols = list(codons[idx])
        pos = digest[(i + 3) % len(digest)] % width
        current = symbols[pos]
        choices = [s for s in alphabet if s != current] or list(alphabet)
        symbols[pos] = choices[digest[(i + 5) % len(digest)] % len(choices)]
        codons[idx] = "".join(symbols)
    return SemanticGenome.from_codons(codons, spec=genome.spec)


def _content_null(genome: SemanticGenome, seed: int) -> SemanticGenome:
    symbols = list(genome.to_compact())
    digest = _seed_bytes(seed, "mut_content_null")
    for i in range(len(symbols) - 1, 0, -1):
        j = digest[i % len(digest)] % (i + 1)
        symbols[i], symbols[j] = symbols[j], symbols[i]
    return SemanticGenome.from_compact("".join(symbols), spec=genome.spec)


def _bias_toward_target(
    genome: SemanticGenome, target: SemanticGenome, seed: int, step: int, flips: int
) -> SemanticGenome:
    symbols = list(genome.to_compact())
    target_symbols = list(target.to_compact())
    if not symbols or flips <= 0:
        return genome
    digest = _seed_bytes(seed, f"mut_bias_{step}")
    for i in range(min(flips, len(symbols))):
        pos = digest[i % len(digest)] % len(symbols)
        symbols[pos] = target_symbols[pos % len(target_symbols)]
    return SemanticGenome.from_compact("".join(symbols), spec=genome.spec)


def _abiotic_fitness(genomes: Sequence[SemanticGenome], target: SemanticGenome) -> float:
    if not genomes:
        return 0.0
    target_c = target.to_compact()
    scores: list[float] = []
    for g in genomes:
        a = g.to_compact()
        n = min(len(a), len(target_c))
        if n == 0:
            scores.append(0.0)
            continue
        matches = sum(1 for i in range(n) if a[i] == target_c[i])
        scores.append(matches / n)
    return round(sum(scores) / len(scores), 10)


def _population_metrics(genomes: Sequence[SemanticGenome]) -> dict[str, float | int]:
    return {
        "codon_usage_entropy": float(codon_usage_entropy(list(genomes))),
        "mean_genome_distance": float(mean_genome_distance(list(genomes))),
        "unique_genome_count": int(unique_genome_count(list(genomes))),
    }


@dataclass(frozen=True, slots=True)
class MutatorArmOutcome:
    seed: int
    arm: str
    mutation_factor: float
    abiotic_fitness: float
    entropy: float
    mean_hamming: float
    arm_digest: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "mutation_factor": self.mutation_factor,
            "abiotic_fitness": self.abiotic_fitness,
            "codon_usage_entropy": self.entropy,
            "mean_genome_distance": self.mean_hamming,
            "arm_digest": self.arm_digest,
            "notes": list(self.notes),
            "gene_identity_proved": False,
            "crispr_identity_proved": False,
        }


@dataclass(frozen=True, slots=True)
class MutatorCampaignResult:
    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    arm_outcomes: tuple[MutatorArmOutcome, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    arms_are_distinct: bool
    claim_ceiling: str
    gene_identity_proved: bool
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.arm_outcomes]
        arm_digests = {
            arm: _digest_body(
                {"arm": arm, "outcomes": [o for o in outcomes if o["arm"] == arm]}
            )
            for arm in self.arms
        }
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "arm_outcomes": outcomes,
            "arm_digests": arm_digests,
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "arms_are_distinct": self.arms_are_distinct,
            "claim_ceiling": self.claim_ceiling,
            "gene_identity_proved": False,
            "crispr_identity_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "wet_mutator_gene_identity": False,
            "literature_map": "scanlan_et_al_2015_honesty_analogue",
            "domain_profile": "host_parasite",
            "note": (
                "Scanlan-style mutator/abiotic-constraint dual-null at genome layer; "
                "gene identity and CRISPR stay unproved."
            ),
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _evolve_arm(
    *,
    seed: int,
    arm: str,
    host_count: int,
    steps: int,
) -> tuple[list[SemanticGenome], float, float, tuple[str, ...]]:
    founder = _genome_for_seed(seed, "host_founder", length=12)
    hosts = [
        SemanticGenome.from_codons(founder.to_codons(), spec=founder.spec)
        for _ in range(host_count)
    ]
    abiotic_target = _genome_for_seed(seed, "abiotic_target", length=12)
    notes: list[str] = [f"arm_{arm}"]

    if arm == "coevolution_elevated_mutation":
        mutation_factor = 4.0
        for step in range(1, steps + 1):
            hosts = [
                _flip_codons(
                    h, seed + 11 * i, step * 17 + i, flips=int(mutation_factor) + (i % 2)
                )
                for i, h in enumerate(hosts)
            ]
        notes.append("coevolution_constrains_abiotic_beneficial_acquisition")
    elif arm == "coevolution_baseline_mutation":
        mutation_factor = 1.0
        for step in range(1, steps + 1):
            hosts = [
                _flip_codons(h, seed + 3 * i, step * 7 + i, flips=1)
                for i, h in enumerate(hosts)
            ]
        notes.append("coevolution_baseline_mutation")
    elif arm == "abiotic_elevated_mutation":
        mutation_factor = 4.0
        for step in range(1, steps + 1):
            hosts = [
                _bias_toward_target(
                    h, abiotic_target, seed + 5 * i, step, flips=int(mutation_factor)
                )
                for i, h in enumerate(hosts)
            ]
        notes.append("abiotic_elevated_mutation_improves_target_match")
    else:
        mutation_factor = 4.0
        hosts = [_content_null(h, seed + i) for i, h in enumerate(hosts)]
        notes.append("content_null_elevated_mutation")

    fitness = _abiotic_fitness(hosts, abiotic_target)
    return hosts, mutation_factor, fitness, tuple(notes)


def run_scanlan_mutator_campaign(
    *,
    seeds: Sequence[int],
    steps: int = 3,
    host_count: int = 4,
    request_claim_ceiling: str = "runtime_observation",
) -> MutatorCampaignResult:
    """Run Scanlan-style mutator × coevolution/abiotic dual-null campaign."""

    seed_tuple = _require_seeds(seeds)
    if steps < 1:
        raise ConfigurationError("steps must be >= 1.")
    if host_count < 2:
        raise ConfigurationError("host_count must be >= 2.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    outcomes: list[MutatorArmOutcome] = []
    for seed in seed_tuple:
        for arm in ARMS:
            hosts, mutation_factor, fitness, notes = _evolve_arm(
                seed=seed, arm=arm, host_count=host_count, steps=steps
            )
            metrics = _population_metrics(hosts)
            arm_digest = _digest_body(
                {
                    "seed": seed,
                    "arm": arm,
                    "mutation_factor": mutation_factor,
                    "abiotic_fitness": fitness,
                    "entropy": float(metrics["codon_usage_entropy"]),
                    "mean_hamming": float(metrics["mean_genome_distance"]),
                }
            )
            outcomes.append(
                MutatorArmOutcome(
                    seed=seed,
                    arm=arm,
                    mutation_factor=mutation_factor,
                    abiotic_fitness=fitness,
                    entropy=float(metrics["codon_usage_entropy"]),
                    mean_hamming=float(metrics["mean_genome_distance"]),
                    arm_digest=arm_digest,
                    notes=notes,
                )
            )

    by_arm: dict[str, list[float]] = {arm: [] for arm in ARMS}
    for item in outcomes:
        by_arm[item.arm].append(item.abiotic_fitness)

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    coevo_elev = _mean(by_arm["coevolution_elevated_mutation"])
    abiotic_elev = _mean(by_arm["abiotic_elevated_mutation"])
    hypothesis_supported = coevo_elev >= abiotic_elev and coevo_elev > 0
    if not hypothesis_supported:
        failure_reason = (
            "elevated_mutation_under_coevolution_does_not_always_improve_abiotic_"
            "scanlan_constraint"
        )
    else:
        failure_reason = ""

    digests = [o.arm_digest for o in outcomes]
    arm_level = {
        arm: _digest_body(
            {"arm": arm, "outcomes": [o.to_dict() for o in outcomes if o.arm == arm]}
        )
        for arm in ARMS
    }
    distinct = len(set(arm_level.values())) == len(ARMS) and len(set(digests)) == len(digests)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: mutator arms must produce distinct digests."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        raise ConfigurationError(
            "candidate_evidence refused while elevated_mutation_under_coevolution "
            "always improves abiotic still holds."
        )

    return MutatorCampaignResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=ARMS,
        arm_outcomes=tuple(outcomes),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        arms_are_distinct=distinct,
        claim_ceiling=(
            ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation"
        ),
        gene_identity_proved=False,
        red_queen_proved=False,
    )


__all__ = [
    "ARMS",
    "HYPOTHESIS",
    "SCHEMA",
    "MutatorArmOutcome",
    "MutatorCampaignResult",
    "run_scanlan_mutator_campaign",
]
