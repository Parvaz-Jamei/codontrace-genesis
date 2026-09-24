"""De-toy D4: Aevol-inspired abstract metabolic phenotype on the HP port.

SemanticGenome → deterministic abstract triangle contributions → phenotype
bins on [0, 1] → metabolic_error vs a digital target. Inspiration from aevol.fr
G→P; **not** Aevol identity, not wet bacterial metabolism, not engine physics.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genome import SemanticGenome

SCHEMA = "host_parasite_abstract_phenotype_v1"
DOMAIN_PROFILE = "host_parasite"
DEFAULT_N_BINS = 16
DEFAULT_TARGET_SEED = 20260924


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _codon_triangle(codon: str, index: int) -> tuple[float, float, float]:
    """Map one codon to (m, w, h) in abstract trait space — digital only."""

    digest = hashlib.sha256(f"{index}|{codon}".encode()).digest()
    m = digest[0] / 255.0
    w = 0.02 + 0.10 * (digest[1] / 255.0)
    # signed height in [-1, 1] then used as magnitude contribution
    h = (digest[2] / 255.0) * 2.0 - 1.0
    return float(m), float(w), float(h)


def _triangle_value(x: float, m: float, w: float, h: float) -> float:
    if w <= 0.0:
        return 0.0
    dist = abs(x - m)
    if dist >= w:
        return 0.0
    return float(h) * (1.0 - dist / w)


def default_target_phenotype(
    *,
    n_bins: int = DEFAULT_N_BINS,
    seed: int = DEFAULT_TARGET_SEED,
) -> tuple[float, ...]:
    """Deterministic abstract target curve on [0, 1] bins."""

    if n_bins < 4:
        raise ConfigurationError("n_bins must be >= 4")
    digest = hashlib.sha256(f"target|{seed}|{n_bins}".encode()).digest()
    vals: list[float] = []
    for i in range(n_bins):
        # smooth-ish target: mid bump
        x = (i + 0.5) / n_bins
        base = math.exp(-((x - 0.45) ** 2) / (2 * 0.04))
        noise = 0.05 * (digest[i % len(digest)] / 255.0)
        vals.append(round(max(0.0, min(1.0, base + noise)), 10))
    return tuple(vals)


def decode_abstract_phenotype(
    genome: SemanticGenome,
    *,
    n_bins: int = DEFAULT_N_BINS,
    target: Sequence[float] | None = None,
) -> dict[str, object]:
    """Decode genome to abstract phenotype + metabolic_error vs target."""

    if n_bins < 4:
        raise ConfigurationError("n_bins must be >= 4")
    tgt = tuple(float(x) for x in (target if target is not None else default_target_phenotype(n_bins=n_bins)))
    if len(tgt) != n_bins:
        raise ConfigurationError("target length must equal n_bins")

    triangles = [_codon_triangle(c, i) for i, c in enumerate(genome.to_codons())]
    phenotype: list[float] = []
    for i in range(n_bins):
        x = (i + 0.5) / n_bins
        acc = 0.0
        for m, w, h in triangles:
            acc += _triangle_value(x, m, w, h)
        # squash to [0, 1] for digital phenotype channel
        phenotype.append(round(max(0.0, min(1.0, (acc + 1.0) / 2.0)), 10))

    error = round(sum(abs(p - t) for p, t in zip(phenotype, tgt, strict=True)) / n_bins, 10)
    body = {
        "schema": SCHEMA,
        "domain_profile": DOMAIN_PROFILE,
        "n_bins": n_bins,
        "n_triangles": len(triangles),
        "phenotype": phenotype,
        "target": list(tgt),
        "metabolic_error": error,
        "genome_digest": genome.digest(),
        "aevol_identity": False,
        "wet_metabolism_claim": False,
        "honesty": (
            "Abstract digital phenotype channel inspired by Aevol triangle G→P; "
            "not Aevol identity; not wet bacterial metabolism."
        ),
    }
    body["phenotype_digest"] = _digest_body(body)
    return body


def metabolic_error_for_genome(
    genome: SemanticGenome,
    *,
    n_bins: int = DEFAULT_N_BINS,
    target: Sequence[float] | None = None,
) -> float:
    return float(decode_abstract_phenotype(genome, n_bins=n_bins, target=target)["metabolic_error"])


__all__ = [
    "SCHEMA",
    "DOMAIN_PROFILE",
    "decode_abstract_phenotype",
    "default_target_phenotype",
    "metabolic_error_for_genome",
]
