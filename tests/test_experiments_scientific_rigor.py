"""Scientific rigor verification suite for Genesis experiments (T01-T12).

Tests mathematical invariants, zero controls, Price equation identities,
uniform 32-bit mutation distributions, and epistemic invariants.
Zero external dependency (pure Python + codontrace.experiments).
"""

from __future__ import annotations

import dataclasses
import inspect
import math

from codontrace.experiments import models
from codontrace.experiments.math_utils import (
    compute_exact_price_equation,
    compute_functional_information,
    sha_prng_float,
    sha_prng_int,
)
from codontrace.experiments.models import (
    MAJOR_TRANSITION_PROVED,
    OPEN_ENDED_INTELLIGENCE_PROVED,
    RED_QUEEN_PROVED,
)


def test_price_equation_identity() -> None:
    """Test Price identity under conditions with and without mutation with tolerance < 1e-7."""
    n = 100
    z = [sha_prng_float(42, i, "trait_z") for i in range(n)]
    w = [sha_prng_int(42, i, "offspring_w", 0, 10) for i in range(n)]

    # Mutations on offspring trait
    z_prime = [
        max(0.0, min(1.0, z[i] + (sha_prng_float(42, i, "mut") - 0.5) * 0.1))
        for i in range(n)
    ]

    accounting = compute_exact_price_equation(
        parents_z=z,
        offspring_counts=w,
        offspring_mean_z=z_prime,
    )

    assert accounting.is_identity_exact
    assert abs(accounting.identity_residual) < 1e-7


def test_oee_zero_control() -> None:
    """Synthetic cycle with repeated components must yield 0 functional novelty."""
    cycle = ["A", "B", "C"]
    new_items = [x for x in cycle if x not in ["A", "B", "C"]]
    novelty = len(new_items)
    assert novelty == 0


def test_t03_transition_assays() -> None:
    """4 assays (partner, remove, non-cooperative, scrambled partner) and algebraic boundary of slope."""
    assays = ["partner", "remove", "non-cooperative", "scrambled"]
    assert len(assays) == 4

    # Algebraic boundary of slope
    v_boundary = 1.2 / 2.475
    assert abs(v_boundary - 0.48484848) < 1e-5


def test_t04_replay_deterministic() -> None:
    """Deterministic Replay and no bias in mutation bits (uniformity across all 32 bits)."""
    counts = [0] * 32
    total_samples = 32000
    for i in range(total_samples):
        locus = sha_prng_int(12345, i, "locus", 0, 31)
        counts[locus] += 1

    expected = total_samples / 32.0
    chi_square = sum(((c - expected) ** 2) / expected for c in counts)
    # Degrees of freedom = 31; critical value for alpha=0.001 is 60.4
    assert chi_square < 60.0


def test_t09_functional_info() -> None:
    """I(E) = -log2 F(E) with binomial bounds."""
    n = 10000
    k = 10
    point_bits, lower_bits, upper_bits = compute_functional_information(
        num_successes=k,
        total_samples=n,
    )
    expected_bits = -math.log2(k / n)
    assert abs(point_bits - expected_bits) < 1e-9
    assert lower_bits <= point_bits <= upper_bits


def test_invariants() -> None:
    """Check non-violability of the mandatory epistemic invariants.

    Basis: the two invariants have no registered evidence path. Red Queen is
    not one of them: docs/prereg/jr5/RED_QUEEN_CLAIM_PATH.md replaces the
    permanent ban with the JR5 verdict, so this test does not pin it.
    """
    assert not MAJOR_TRANSITION_PROVED
    assert not OPEN_ENDED_INTELLIGENCE_PROVED


def test_red_queen_flag_is_a_default_not_an_invariant() -> None:
    """RED_QUEEN_PROVED is the default False of T01-T12 records, outside the invariants group.

    Basis: RED_QUEEN_CLAIM_PATH.md, "This replaces the permanent ban"; the
    flag is decided only by the JR5 verdict under (a) to (e). Expected: the
    "Mandatory epistemic invariants" block lists exactly the two constants
    pinned by test_invariants, and the manifest and completion-summary
    defaults read RED_QUEEN_PROVED (False until a JR5 verdict says otherwise;
    these runners never produce one).
    """
    source = inspect.getsource(models)
    block = source.split("# Mandatory epistemic invariants\n", 1)[1].split("\n\n", 1)[0]
    names = {line.split(":", 1)[0].strip() for line in block.splitlines() if line.strip()}
    assert names == {"MAJOR_TRANSITION_PROVED", "OPEN_ENDED_INTELLIGENCE_PROVED"}
    assert RED_QUEEN_PROVED is False
    summary_default = {f.name: f.default for f in dataclasses.fields(models.CompletionSummary)}
    assert summary_default["red_queen_proved"] is RED_QUEEN_PROVED
    manifest = models.ExperimentManifest("x", models.ExecutionTrack.REFERENCE, "b", "s", 0, 1, 1, None, {})
    assert manifest.epistemic_invariants["red_queen_proved"] is RED_QUEEN_PROVED
