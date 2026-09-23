"""Phase 13 (optional earn-in) — declared task–gene map digests.

Bridges repertoire task labels to codon windows as a *declared* phenotype link.
Never claims gene identity, CRISPR identity, or wet locus proof. Same
``host_parasite`` profile; no engine infection physics.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_task_gene_map_v1"
_ALLOWED_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})
_TASKS = ("nand", "and", "or", "nor", "xor", "equ")


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _seed_bytes(seed: int, salt: str) -> bytes:
    return hashlib.sha256(f"{int(seed)}|{salt}".encode()).digest()


@dataclass(frozen=True, slots=True)
class TaskGeneWindow:
    task_label: str
    codon_start: int
    codon_end: int  # exclusive
    window_digest: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "task_label": self.task_label,
            "codon_start": self.codon_start,
            "codon_end": self.codon_end,
            "window_digest": self.window_digest,
            "gene_identity_proved": False,
        }
        body["digest"] = _digest_body(body)
        return body


@dataclass(frozen=True, slots=True)
class TaskGeneMapResult:
    schema: str
    seed: int
    host_genome_digest: str
    windows: tuple[TaskGeneWindow, ...]
    map_digest: str
    claim_ceiling: str
    gene_identity_proved: bool
    red_queen_proved: bool

    def to_dict(self) -> dict[str, object]:
        windows = [item.to_dict() for item in self.windows]
        body: dict[str, object] = {
            "schema": self.schema,
            "seed": self.seed,
            "host_genome_digest": self.host_genome_digest,
            "windows": windows,
            "map_digest": self.map_digest,
            "claim_ceiling": self.claim_ceiling,
            "gene_identity_proved": self.gene_identity_proved,
            "red_queen_proved": self.red_queen_proved,
            "raises_claim_ladder": False,
            "crispr_identity_proved": False,
            "major_transition_proved": False,
            "scope": "declared_digital_phenotype_link_only",
        }
        body["digest"] = _digest_body(
            {k: body[k] for k in body if k != "digest"}
        )
        return body


def build_task_gene_map(
    *,
    seed: int,
    genome_length: int = 12,
    window_width: int = 2,
    request_claim_ceiling: str = "runtime_observation",
) -> TaskGeneMapResult:
    """Declare codon-window → task-label map digests (digital only)."""

    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ConfigurationError("seed must be an integer.")
    if genome_length < 4:
        raise ConfigurationError("genome_length must be >= 4.")
    if window_width < 1 or window_width > genome_length:
        raise ConfigurationError("window_width out of range.")
    ceiling = str(request_claim_ceiling).strip().lower()
    if ceiling not in _ALLOWED_CEILINGS:
        raise ConfigurationError(
            "request_claim_ceiling must be runtime_observation or candidate_evidence."
        )

    genome = SemanticGenome.random(length=genome_length, seed=int(seed) * 1009 + 17)
    codons = genome.to_codons()
    digest = _seed_bytes(seed, "task_gene_map")
    windows: list[TaskGeneWindow] = []
    # Non-overlapping declared windows where possible.
    max_windows = min(len(_TASKS), genome_length // window_width)
    if max_windows < 1:
        raise ConfigurationError("task–gene map would produce zero windows.")
    for i in range(max_windows):
        start = i * window_width
        end = start + window_width
        segment = codons[start:end]
        task = _TASKS[digest[i % len(digest)] % len(_TASKS)]
        # Avoid duplicate task labels when possible.
        used = {w.task_label for w in windows}
        if task in used:
            for candidate in _TASKS:
                if candidate not in used:
                    task = candidate
                    break
        windows.append(
            TaskGeneWindow(
                task_label=task,
                codon_start=start,
                codon_end=end,
                window_digest=_digest_body({"segment": list(segment), "task": task}),
            )
        )

    map_digest = _digest_body(
        {
            "host_genome_digest": genome.digest(),
            "windows": [w.to_dict() for w in windows],
        }
    )
    return TaskGeneMapResult(
        schema=SCHEMA,
        seed=int(seed),
        host_genome_digest=genome.digest(),
        windows=tuple(windows),
        map_digest=map_digest,
        claim_ceiling=ceiling,
        gene_identity_proved=False,
        red_queen_proved=False,
    )


__all__ = [
    "SCHEMA",
    "TaskGeneMapResult",
    "TaskGeneWindow",
    "build_task_gene_map",
]
