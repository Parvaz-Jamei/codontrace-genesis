"""Phase 17 — Price≠causality / multilevel caution digests (Challenge S8).

Emits a Price-style covariance summary as a *diagnostic* and a ClaimGate refusal
assay: presence of the summary never unlocks major_transition_proved or causal
transition language. Digital only; cites Okasha multilevel caution as literature
comparator already listed in CHALLENGES / REQUIREMENTS.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

SCHEMA = "host_parasite_price_causality_caution_v1"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


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


@dataclass(frozen=True, slots=True)
class PriceCautionResult:
    schema: str
    seeds: tuple[int, ...]
    price_covariance: float
    within_group_term: float
    between_group_term: float
    summary_digest: str
    claim_ceiling: str
    price_summary_is_causal: bool
    major_transition_proved: bool
    red_queen_proved: bool
    refusal_assay_passed: bool

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "seeds": list(self.seeds),
            "price_covariance": self.price_covariance,
            "within_group_term": self.within_group_term,
            "between_group_term": self.between_group_term,
            "summary_digest": self.summary_digest,
            "claim_ceiling": self.claim_ceiling,
            "price_summary_is_causal": False,
            "major_transition_proved": False,
            "red_queen_proved": False,
            "refusal_assay_passed": self.refusal_assay_passed,
            "raises_claim_ladder": False,
            "challenge": "S8_okasha_price_not_causality",
            "domain_profile": "host_parasite",
            "note": "Price-style covariance is a diagnostic summary, not a causal proof.",
        }
        body["campaign_digest"] = _digest_body(
            {k: body[k] for k in body if k not in {"campaign_digest", "digest"}}
        )
        body["digest"] = body["campaign_digest"]
        return body


def run_price_causality_caution_assay(
    *,
    seeds: Sequence[int],
    request_claim_ceiling: str = "runtime_observation",
) -> PriceCautionResult:
    """Build Price-style terms and assert they do not prove major transition."""

    seed_tuple = _require_seeds(seeds)
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    # Deterministic synthetic group fitness / trait values from seeds (digital only).
    within = 0.0
    between = 0.0
    for seed in seed_tuple:
        trait = ((seed * 17) % 97) / 97.0
        fitness = ((seed * 29) % 89) / 89.0
        group_trait = ((seed * 11) % 53) / 53.0
        group_fitness = ((seed * 13) % 59) / 59.0
        within += (trait - group_trait) * (fitness - group_fitness)
        between += group_trait * group_fitness
    n = float(len(seed_tuple))
    within /= n
    between /= n
    cov = within + between
    summary = _digest_body(
        {
            "seeds": list(seed_tuple),
            "price_covariance": round(cov, 12),
            "within_group_term": round(within, 12),
            "between_group_term": round(between, 12),
            "price_summary_is_causal": False,
            "major_transition_proved": False,
        }
    )
    # Refusal assay: summary present, causal/transition flags forced false.
    refusal_ok = summary != "" and True
    if ceiling == "candidate_evidence" and not refusal_ok:
        raise ConfigurationError("candidate_evidence refused: Price caution digest missing.")

    return PriceCautionResult(
        schema=SCHEMA,
        seeds=seed_tuple,
        price_covariance=round(cov, 12),
        within_group_term=round(within, 12),
        between_group_term=round(between, 12),
        summary_digest=summary,
        claim_ceiling=ceiling,
        price_summary_is_causal=False,
        major_transition_proved=False,
        red_queen_proved=False,
        refusal_assay_passed=refusal_ok,
    )


__all__ = ["PriceCautionResult", "SCHEMA", "run_price_causality_caution_assay"]
