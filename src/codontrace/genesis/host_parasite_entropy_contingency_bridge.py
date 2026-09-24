"""Phase 26 — Phase 11×21 entropy × contingency bridge (Wave 6 earn-in).

Seed-stratified digest that pairs Phase 11 codon-entropy dual-null with Phase 21
multi-seed contingency without new biology claims. complexity_emergence_proved
stays False; red_queen_proved stays False. ClaimGate-honest join only.

Companion-seed honesty: Phase 21 requires ≥3 seeds, so for each outer
stratification seed S this module runs contingency on (S, S+1000, S+2000) and
entropy on (S,). The outer seed is a stratification key — not a claim that both
campaigns share one identical single-seed object. See
docs/claimgate/host_parasite_port_20260924/evidence/phase26_entropy_contingency_bridge.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_contingency import (
    SCHEMA as PHASE21_SCHEMA,
)
from codontrace.genesis.host_parasite_contingency import (
    run_multi_seed_contingency_campaign,
)
from codontrace.genesis.host_parasite_genome_diversity import (
    SCHEMA as PHASE11_SCHEMA,
)
from codontrace.genesis.host_parasite_genome_diversity import (
    run_genome_diversity_campaign,
)

SCHEMA = "host_parasite_entropy_contingency_bridge_v1"
HYPOTHESIS = "parasites_always_raise_entropy_and_complexity_jointly_across_seeds"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


@dataclass(frozen=True, slots=True)
class EntropyContingencySeedOutcome:
    seed: int
    entropy_hypothesis_supported: bool
    contingency_hypothesis_supported: bool
    entropy_campaign_digest: str
    contingency_campaign_digest: str
    joint_rise: bool
    seed_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "entropy_hypothesis_supported": self.entropy_hypothesis_supported,
            "contingency_hypothesis_supported": self.contingency_hypothesis_supported,
            "entropy_campaign_digest": self.entropy_campaign_digest,
            "contingency_campaign_digest": self.contingency_campaign_digest,
            "joint_rise": self.joint_rise,
            "seed_digest": self.seed_digest,
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
        }


@dataclass(frozen=True, slots=True)
class EntropyContingencyBridgeResult:
    schema: str
    seeds: tuple[int, ...]
    seed_outcomes: tuple[EntropyContingencySeedOutcome, ...]
    hypothesis: str
    hypothesis_supported: bool
    failure_reason: str
    seed_digests_are_distinct: bool
    claim_ceiling: str
    complexity_emergence_proved: bool
    red_queen_proved: bool
    phase11_schema: str
    phase21_schema: str
    campaign_digest: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "seed_outcomes": [o.to_dict() for o in self.seed_outcomes],
            "seed_digests": {str(o.seed): o.seed_digest for o in self.seed_outcomes},
            "hypothesis": self.hypothesis,
            "hypothesis_supported": self.hypothesis_supported,
            "failure_reason": self.failure_reason,
            "seed_digests_are_distinct": self.seed_digests_are_distinct,
            "claim_ceiling": self.claim_ceiling,
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "phase11_schema": self.phase11_schema,
            "phase21_schema": self.phase21_schema,
            "wave": 6,
            "phase": 26,
            "note": (
                "Pairs Phase 11 entropy dual-null with Phase 21 contingency per "
                "seed. Joint universal-rise claim is refused; not Red Queen proof."
            ),
            "domain_profile": "host_parasite",
        }
        body["campaign_digest"] = self.campaign_digest or _digest_body(
            {
                k: body[k]
                for k in body
                if k not in {"campaign_digest", "digest"}
            }
        )
        body["digest"] = body["campaign_digest"]
        return body


def run_entropy_contingency_bridge(
    *,
    seeds: Sequence[int],
    steps: int = 2,
    request_claim_ceiling: str = "runtime_observation",
) -> EntropyContingencyBridgeResult:
    """Join Phase 11 entropy dual-null with Phase 21 contingency per seed."""

    if len(seeds) < 3:
        raise ConfigurationError("entropy×contingency bridge requires at least 3 seeds.")
    seed_tuple = tuple(int(s) for s in seeds)
    if len(set(seed_tuple)) != len(seed_tuple):
        raise ConfigurationError("seeds must be unique.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    outcomes: list[EntropyContingencySeedOutcome] = []
    for seed in seed_tuple:
        entropy = run_genome_diversity_campaign(
            seeds=(seed,),
            steps=steps,
            request_claim_ceiling=ceiling,
        )
        contingency = run_multi_seed_contingency_campaign(
            seeds=(seed, seed + 1000, seed + 2000),
            request_claim_ceiling=ceiling,
        )
        # Per-seed joint rise would require BOTH universal claims to hold.
        # Both campaigns are designed to falsify their universal claims, so
        # joint_rise stays False — S1 humility preserved.
        entropy_supported = bool(entropy.hypothesis_supported)
        contingency_supported = bool(contingency.hypothesis_supported)
        joint = entropy_supported and contingency_supported
        e_digest = str(entropy.to_dict()["campaign_digest"])
        c_digest = str(contingency.to_dict()["campaign_digest"])
        seed_digest = _digest_body(
            {
                "seed": seed,
                "entropy_campaign_digest": e_digest,
                "contingency_campaign_digest": c_digest,
                "entropy_hypothesis_supported": entropy_supported,
                "contingency_hypothesis_supported": contingency_supported,
                "joint_rise": joint,
            }
        )
        outcomes.append(
            EntropyContingencySeedOutcome(
                seed=seed,
                entropy_hypothesis_supported=entropy_supported,
                contingency_hypothesis_supported=contingency_supported,
                entropy_campaign_digest=e_digest,
                contingency_campaign_digest=c_digest,
                joint_rise=joint,
                seed_digest=seed_digest,
            )
        )

    always_joint = all(o.joint_rise for o in outcomes)
    hypothesis_supported = always_joint
    failure_reason = (
        ""
        if always_joint
        else "parasites_do_not_jointly_raise_entropy_and_complexity_across_seeds"
    )
    digests = [o.seed_digest for o in outcomes]
    distinct = len(set(digests)) == len(digests)
    if ceiling == "candidate_evidence" and not distinct:
        raise ConfigurationError(
            "candidate_evidence refused: bridge seed digests must be pairwise distinct."
        )
    if ceiling == "candidate_evidence" and hypothesis_supported:
        raise ConfigurationError(
            "candidate_evidence refused while joint universal-rise claim still holds."
        )

    preview = {
        "schema": SCHEMA,
        "seeds": list(seed_tuple),
        "seed_digests": {str(o.seed): o.seed_digest for o in outcomes},
        "hypothesis": HYPOTHESIS,
        "hypothesis_supported": hypothesis_supported,
        "failure_reason": failure_reason,
        "seed_digests_are_distinct": distinct,
        "claim_ceiling": ceiling if distinct or ceiling == "runtime_observation" else "runtime_observation",
        "complexity_emergence_proved": False,
        "red_queen_proved": False,
        "raises_claim_ladder": False,
        "phase11_schema": PHASE11_SCHEMA,
        "phase21_schema": PHASE21_SCHEMA,
        "wave": 6,
        "phase": 26,
        "domain_profile": "host_parasite",
    }
    return EntropyContingencyBridgeResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        seed_outcomes=tuple(outcomes),
        hypothesis=HYPOTHESIS,
        hypothesis_supported=hypothesis_supported,
        failure_reason=failure_reason,
        seed_digests_are_distinct=distinct,
        claim_ceiling=str(preview["claim_ceiling"]),
        complexity_emergence_proved=False,
        red_queen_proved=False,
        phase11_schema=PHASE11_SCHEMA,
        phase21_schema=PHASE21_SCHEMA,
        campaign_digest=_digest_body(preview),
    )


__all__ = [
    "HYPOTHESIS",
    "SCHEMA",
    "EntropyContingencyBridgeResult",
    "EntropyContingencySeedOutcome",
    "run_entropy_contingency_bridge",
]
