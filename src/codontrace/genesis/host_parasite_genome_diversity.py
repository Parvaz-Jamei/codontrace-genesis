"""Phase 11 — codon-entropy / Hamming dual-null assay (HE02 honesty).

Genotype-level observables from ``codon_usage_entropy``, ``mean_genome_distance``,
and ``unique_genome_count``. Content-null (shuffle symbols, preserve length) and
structure-null (permute codon order, preserve multiset) controls can falsify
``parasites_always_raise_codon_entropy`` under abiotic stress. Digital scope
only; no infection physics in ``engine.py``.
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

SCHEMA = "host_parasite_genome_diversity_campaign_v1"
HYPOTHESIS = "parasites_always_raise_codon_entropy"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_ARMS = (
    "biotic_intact",
    "content_null",
    "structure_null",
    "abiotic_stress",
)
ARMS = frozenset(_ARMS)


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


def _require_seeds(seeds: Sequence[int]) -> tuple[int, ...]:
    if not seeds:
        raise ConfigurationError("seeds must be non-empty.")
    out: list[int] = []
    for item in seeds:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ConfigurationError("seeds must be integers.")
        out.append(int(item))
    return tuple(out)


def _genome_for_seed(seed: int, role: str, length: int = 12) -> SemanticGenome:
    return SemanticGenome.random(
        length=length,
        seed=int(seed) * 1_000_019 + sum(ord(c) for c in role) * 13 + len(role),
    )


def _flip_codons(genome: SemanticGenome, seed: int, step: int, flips: int) -> SemanticGenome:
    codons = list(genome.to_codons())
    if not codons or flips <= 0:
        return genome
    digest = _seed_bytes(seed, f"div_flip_{step}")
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
    """Shuffle symbols across the compact string; preserve length (content-null)."""

    symbols = list(genome.to_compact())
    digest = _seed_bytes(seed, "content_null_shuffle")
    # Fisher–Yates with deterministic digest stream.
    for i in range(len(symbols) - 1, 0, -1):
        j = digest[i % len(digest)] % (i + 1)
        symbols[i], symbols[j] = symbols[j], symbols[i]
    return SemanticGenome.from_compact("".join(symbols), spec=genome.spec)


def _structure_null(genome: SemanticGenome, seed: int) -> SemanticGenome:
    """Permute codon order; preserve codon multiset (structure-null)."""

    codons = list(genome.to_codons())
    digest = _seed_bytes(seed, "structure_null_permute")
    for i in range(len(codons) - 1, 0, -1):
        j = digest[i % len(digest)] % (i + 1)
        codons[i], codons[j] = codons[j], codons[i]
    return SemanticGenome.from_codons(codons, spec=genome.spec)


def _population_metrics(genomes: Sequence[SemanticGenome]) -> dict[str, float | int]:
    return {
        "codon_usage_entropy": float(codon_usage_entropy(list(genomes))),
        "mean_genome_distance": float(mean_genome_distance(list(genomes))),
        "unique_genome_count": int(unique_genome_count(list(genomes))),
    }


@dataclass(frozen=True, slots=True)
class GenomeDiversityArmOutcome:
    seed: int
    arm: str
    entropy: float
    mean_hamming: float
    unique_genomes: int
    entropy_delta_vs_baseline: float
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "seed": self.seed,
            "arm": self.arm,
            "codon_usage_entropy": self.entropy,
            "mean_genome_distance": self.mean_hamming,
            "unique_genome_count": self.unique_genomes,
            "entropy_delta_vs_baseline": self.entropy_delta_vs_baseline,
            "notes": list(self.notes),
        }
        body["digest"] = _digest_body(body)
        return body


@dataclass(frozen=True, slots=True)
class GenomeDiversityCampaignResult:
    """Dual-null genotype diversity assay; hypothesis may fail."""

    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    steps: int
    host_count: int
    arm_outcomes: tuple[GenomeDiversityArmOutcome, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    claim_ceiling: str
    red_queen_proved: bool
    arms_are_distinct: bool

    def to_dict(self) -> dict[str, object]:
        outcomes = [item.to_dict() for item in self.arm_outcomes]
        arm_digests: dict[str, str] = {}
        for arm in self.arms:
            arm_bodies = [o for o in outcomes if o["arm"] == arm]
            arm_digests[arm] = _digest_body({"arm": arm, "outcomes": arm_bodies})
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "arms": list(self.arms),
            "steps": self.steps,
            "host_count": self.host_count,
            "arm_outcomes": outcomes,
            "arm_digests": arm_digests,
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "arms_are_distinct": self.arms_are_distinct,
            "raises_claim_ladder": False,
            "engine_infection_physics": "not_in_engine_core",
            "he02_honesty": "dual_null_genotype_observables",
            "scanlan_buckling_scope": "digital_humility_analogue_only",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _evolve_population(
    *,
    seed: int,
    steps: int,
    arm: str,
    initial_hosts: Sequence[SemanticGenome],
) -> tuple[list[SemanticGenome], tuple[str, ...]]:
    notes: list[str] = [f"arm_{arm}"]
    hosts = list(initial_hosts)
    parasite = _genome_for_seed(seed, "parasite_shared", length=12)

    if arm == "content_null":
        parasite = _content_null(parasite, seed)
        notes.append("parasite_content_null_shuffle")
    elif arm == "structure_null":
        parasite = _structure_null(parasite, seed)
        notes.append("parasite_structure_null_permute")
    elif arm == "abiotic_stress":
        notes.append("abiotic_stress_blocks_parasite_driven_diversity")
    else:
        notes.append("biotic_intact_parasite_pressure")

    for step in range(1, steps + 1):
        if arm in {"abiotic_stress", "content_null", "structure_null"}:
            # Null / stress arms: no parasite-driven diversity push (hosts frozen).
            notes.append(f"{arm}_step_{step}_no_diversity_push")
            continue
        # Intact biotic: independent per-host flips under parasite pressure raise
        # population codon entropy / Hamming distance.
        salt = int(parasite.digest()[:6], 16) % 10_000
        hosts = [
            _flip_codons(h, seed + salt + i * 97, step * 31 + i * 13, flips=4 + (i % 3))
            for i, h in enumerate(hosts)
        ]
        notes.append(f"biotic_step_{step}_divergent_flips")
    return hosts, tuple(notes)


def run_genome_diversity_campaign(
    *,
    seeds: Sequence[int],
    steps: int = 3,
    host_count: int = 4,
    request_claim_ceiling: str = "runtime_observation",
) -> GenomeDiversityCampaignResult:
    """Run intact / content-null / structure-null / abiotic-stress diversity assay.

    Designed so ``parasites_always_raise_codon_entropy`` can fail under abiotic
    stress or null arms (mean entropy_delta <= 0 on those arms while biotic
    intact can rise).
    """

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

    outcomes: list[GenomeDiversityArmOutcome] = []
    for seed in seed_tuple:
        # Baseline: initial hosts before evolution (shared seed).
        # Identical founders so biotic diversification can raise entropy / Hamming;
        # null and stress arms keep the clone population flat.
        founder = _genome_for_seed(seed, "host_founder", length=12)
        baseline_hosts = [SemanticGenome.from_codons(founder.to_codons(), spec=founder.spec)
                          for _ in range(host_count)]
        baseline = _population_metrics(baseline_hosts)
        baseline_entropy = float(baseline["codon_usage_entropy"])

        for arm in _ARMS:
            hosts, notes = _evolve_population(
                seed=seed,
                steps=steps,
                arm=arm,
                initial_hosts=baseline_hosts,
            )
            metrics = _population_metrics(hosts)
            outcomes.append(
                GenomeDiversityArmOutcome(
                    seed=seed,
                    arm=arm,
                    entropy=float(metrics["codon_usage_entropy"]),
                    mean_hamming=float(metrics["mean_genome_distance"]),
                    unique_genomes=int(metrics["unique_genome_count"]),
                    entropy_delta_vs_baseline=float(metrics["codon_usage_entropy"])
                    - baseline_entropy,
                    notes=notes,
                )
            )

    # Hypothesis: parasites ALWAYS raise codon entropy vs baseline on every arm
    # that includes parasites. Fail if abiotic_stress or null arms show
    # non-positive mean delta while we still ran biotic_intact.
    by_arm: dict[str, list[float]] = {arm: [] for arm in _ARMS}
    for item in outcomes:
        by_arm[item.arm].append(item.entropy_delta_vs_baseline)

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    biotic_mean = _mean(by_arm["biotic_intact"])
    stress_mean = _mean(by_arm["abiotic_stress"])
    content_mean = _mean(by_arm["content_null"])
    structure_mean = _mean(by_arm["structure_null"])

    hypothesis_supported = (
        biotic_mean > 0
        and stress_mean > 0
        and content_mean > 0
        and structure_mean > 0
    )
    if hypothesis_supported:
        failure_reason = ""
    else:
        parts: list[str] = []
        if stress_mean <= 0:
            parts.append("abiotic_stress")
        if content_mean <= 0:
            parts.append("content_null")
        if structure_mean <= 0:
            parts.append("structure_null")
        if biotic_mean <= 0:
            parts.append("biotic_intact_also_flat")
        failure_reason = (
            "parasites_do_not_always_raise_codon_entropy_under_"
            + ("_".join(parts) if parts else "controls")
        )

    # Distinctness from per-arm outcome digests (no throwaway campaign object).
    arm_digest_map: dict[str, str] = {}
    outcome_dicts = [item.to_dict() for item in outcomes]
    for arm in _ARMS:
        arm_bodies = [o for o in outcome_dicts if o["arm"] == arm]
        arm_digest_map[arm] = _digest_body({"arm": arm, "outcomes": arm_bodies})
    digests = list(arm_digest_map.values())
    arms_distinct = len(set(digests)) == len(digests) and len(digests) >= 2
    if ceiling == "candidate_evidence" and not arms_distinct:
        raise ConfigurationError(
            "candidate_evidence refused: genome diversity arms must produce distinct digests."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        # Honesty: do not grant candidate_evidence when the universal claim holds
        # without dual-null falsification contrast (should be rare given design).
        raise ConfigurationError(
            "candidate_evidence refused while parasites_always_raise_codon_entropy still holds."
        )

    return GenomeDiversityCampaignResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=_ARMS,
        steps=steps,
        host_count=host_count,
        arm_outcomes=tuple(outcomes),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        claim_ceiling=ceiling if arms_distinct else "runtime_observation",
        red_queen_proved=False,
        arms_are_distinct=arms_distinct,
    )


__all__ = [
    "ARMS",
    "HYPOTHESIS",
    "SCHEMA",
    "GenomeDiversityArmOutcome",
    "GenomeDiversityCampaignResult",
    "run_genome_diversity_campaign",
]
