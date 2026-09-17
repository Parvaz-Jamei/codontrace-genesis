"""Small open-ended discovery campaign with mandatory three-negative audits.

Wave د: 3–5 proposals, all three HE01 discovery negatives, honest accept/reject
rates (100% reject is valid data). No AGI / collective-intelligence claims.
Pins A–E unchanged — this campaign does not touch life_loop_world knobs.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.discovery_runner import run_discovery_pipeline
from codontrace.genesis.discovery_witness import (
    CLAIM_CEILING_RUNTIME,
    CandidateSpec,
    DiscoveryAuditReport,
)
from codontrace.genesis.novelty_proposer import (
    ArchiveSummary,
    ExternalModelStubProposer,
    NoveltyProposer,
    RandomProposer,
    empty_archive_summary,
)

ScaleName = Literal["S1", "S2", "research"]
CAMPAIGN_ID = "open_ended_discovery_campaign_v1"
CLAIM_CEILING = CLAIM_CEILING_RUNTIME


@dataclass(frozen=True, slots=True)
class DiscoveryCampaignReport:
    """Digest-bearing campaign summary; rates may be 100% reject."""

    campaign_id: str
    scale: str
    proposal_count: int
    accept_count: int
    reject_count: int
    accept_rate: float
    reject_rate: float
    claim_ceiling: str
    beat_all_negatives_count: int
    reports: tuple[DiscoveryAuditReport, ...]
    protocol_digest: str
    archive_digest: str

    def __post_init__(self) -> None:
        if self.proposal_count != len(self.reports):
            raise ConfigurationError("proposal_count must match reports length.")
        if self.accept_count + self.reject_count != self.proposal_count:
            raise ConfigurationError("accept_count + reject_count must equal proposal_count.")
        if self.claim_ceiling != CLAIM_CEILING_RUNTIME and self.beat_all_negatives_count == 0:
            raise ConfigurationError(
                "Campaign ceiling above runtime_observation requires at least one "
                "proposal that beat all three negatives."
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "campaign_id": self.campaign_id,
            "scale": self.scale,
            "proposal_count": self.proposal_count,
            "accept_count": self.accept_count,
            "reject_count": self.reject_count,
            "accept_rate": self.accept_rate,
            "reject_rate": self.reject_rate,
            "claim_ceiling": self.claim_ceiling,
            "beat_all_negatives_count": self.beat_all_negatives_count,
            "reports": [report.to_dict() for report in self.reports],
            "protocol_digest": self.protocol_digest,
            "archive_digest": self.archive_digest,
            "honesty": (
                "100% reject is valid data; do not fabricate passes. "
                "Ceiling stays runtime_observation unless proposals beat all three negatives."
            ),
            "literature": [
                "Kumar et al. ASAL arXiv:2412.17799 / Artificial Life 2025",
                "Flageat, Janmohamed, Lim & Cully IEEE TEVC 30(1):286-295 (2026) arXiv:2409.13315",
                "MAP-Elites Mouret & Clune 2015; QD Chatzilygeroudis et al. 2021; OMNI-EPIC 2024",
                "HE01 lesson: three discovery negatives required",
            ],
            "forbidden_claims": [
                "agi",
                "collective_intelligence",
                "open_ended_intelligence",
                "tokyo_type1_passed",
                "avida_replacement",
            ],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def default_campaign_proposers(*, seed: int = 7) -> tuple[NoveltyProposer, ...]:
    """Mix of random + stub proposers (no paid API)."""

    return (
        RandomProposer(seed=seed),
        RandomProposer(seed=seed + 1),
        ExternalModelStubProposer(seed=seed + 10),
        ExternalModelStubProposer(seed=seed + 11),
        RandomProposer(seed=seed + 2),
    )


def run_discovery_campaign(
    *,
    scale: ScaleName = "S1",
    proposers: Sequence[NoveltyProposer] | None = None,
    archive_summary: ArchiveSummary | None = None,
    max_proposals: int = 5,
    hand_crafted: Sequence[CandidateSpec] = (),
) -> DiscoveryCampaignReport:
    """Run 3–5 proposals through the mandatory three-negative audit pipeline."""

    if max_proposals < 3 or max_proposals > 5:
        raise ConfigurationError("discovery campaign requires 3–5 proposals.")
    archive = archive_summary or empty_archive_summary(
        digest="campaign_archive_empty_v1"
    )
    # Seed a tiny synthetic archive so shuffled-archive control is non-trivial.
    if not archive.elite_genomes:
        archive = ArchiveSummary(
            archive_digest=archive.archive_digest,
            filled_bins=max(archive.filled_bins, 2),
            coverage=max(archive.coverage, 0.1),
            best_fitness=archive.best_fitness if archive.best_fitness is not None else 0.3,
            mean_fitness=archive.mean_fitness if archive.mean_fitness is not None else 0.2,
            descriptor_names=archive.descriptor_names
            or ("unique_positions", "energy_efficiency"),
            elite_genomes=("ELITE_A", "ELITE_B", "ELITE_C"),
            metadata=dict(archive.metadata),
        )

    candidates: list[CandidateSpec] = list(hand_crafted)
    active_proposers = tuple(proposers) if proposers is not None else default_campaign_proposers()
    for proposer in active_proposers:
        if len(candidates) >= max_proposals:
            break
        candidates.append(proposer.propose(archive))
    if len(candidates) < 3:
        raise ConfigurationError("discovery campaign produced fewer than 3 candidates.")
    candidates = candidates[:max_proposals]

    reports = tuple(
        run_discovery_pipeline(candidate, scale=scale, archive_summary=archive)
        for candidate in candidates
    )
    accept_count = sum(1 for report in reports if report.accepted)
    reject_count = len(reports) - accept_count
    beat_count = sum(1 for report in reports if report.beat_all_negatives)
    # Campaign-level ceiling stays observational unless at least one proposal
    # cleared all three negatives (still not publication-grade).
    claim_ceiling = CLAIM_CEILING_RUNTIME
    protocol_digest = canonical_digest(
        {
            "campaign_id": CAMPAIGN_ID,
            "scale": scale,
            "max_proposals": max_proposals,
            "negatives": [
                "proposer_random",
                "proposer_shuffled_archive",
                "archive_no_op",
            ],
        }
    )
    return DiscoveryCampaignReport(
        campaign_id=CAMPAIGN_ID,
        scale=scale,
        proposal_count=len(reports),
        accept_count=accept_count,
        reject_count=reject_count,
        accept_rate=round(accept_count / len(reports), 10),
        reject_rate=round(reject_count / len(reports), 10),
        claim_ceiling=claim_ceiling,
        beat_all_negatives_count=beat_count,
        reports=reports,
        protocol_digest=protocol_digest,
        archive_digest=archive.archive_digest,
    )


def write_discovery_campaign_report(
    report: DiscoveryCampaignReport,
    *,
    json_path: Path,
    markdown_path: Path | None = None,
) -> tuple[Path, Path | None]:
    """Write JSON (+ optional markdown) campaign artifacts."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    payload["report_digest"] = report.digest()
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = markdown_path
    if md_path is not None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Open-ended discovery ClaimGate campaign report",
            "",
            f"- campaign_id: `{report.campaign_id}`",
            f"- scale: `{report.scale}`",
            f"- proposals: **{report.proposal_count}**",
            f"- accept_count: **{report.accept_count}** ({report.accept_rate:.0%})",
            f"- reject_count: **{report.reject_count}** ({report.reject_rate:.0%})",
            f"- beat_all_negatives_count: **{report.beat_all_negatives_count}**",
            f"- claim_ceiling: **`{report.claim_ceiling}`**",
            f"- report_digest: `{report.digest()}`",
            "",
            "## Honesty",
            "",
            "100% reject is valid data — do not fabricate passes. Ceiling stays",
            "`runtime_observation` unless a proposal is meaningfully better than",
            "all three negatives (`proposer_random`, `proposer_shuffled_archive`,",
            "`archive_no_op`). No AGI / collective-intelligence claims.",
            "",
            "## Literature",
            "",
            "- ASAL: Kumar et al., arXiv:2412.17799 / Artificial Life 2025",
            "- Flageat, Janmohamed, Lim & Cully, IEEE TEVC 30(1):286–295 (2026), arXiv:2409.13315",
            "- MAP-Elites (Mouret & Clune 2015); QD Chatzilygeroudis et al. 2021; OMNI-EPIC 2024",
            "- HE01 lesson: weak negatives insufficient — need three discovery negatives",
            "",
            "## Per-proposal",
            "",
        ]
        for item in report.reports:
            lines.append(
                f"- `{item.candidate_id}` accepted={item.accepted} "
                f"ceiling={item.claim_ceiling} score={item.novelty_score} "
                f"reasons={list(item.reasons)}"
            )
        lines.append("")
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


__all__ = [
    "CAMPAIGN_ID",
    "CLAIM_CEILING",
    "DiscoveryCampaignReport",
    "default_campaign_proposers",
    "run_discovery_campaign",
    "write_discovery_campaign_report",
]
