"""Deterministic per-run seed namespacing for ILW (ILW-1).

Streams are bound to ``run_id`` so identical base seeds across different runs
cannot leak RNG state into each other.
"""

from __future__ import annotations

from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.rng import RNGManager


class SeedNamespaceError(ConfigurationError):
    """Raised when an ILW seed namespace is misconfigured."""


@dataclass(frozen=True, slots=True)
class SeedNamespace:
    """Run-scoped deterministic RNG namespace factory.

    Path form: ``ilw/<run_id>/<component[/...]>``. Two namespaces with the same
    base ``seed`` but different ``run_id`` values always produce distinct paths
    and distinct forked RNG streams.
    """

    run_id: str
    seed: int
    root: str = "ilw"

    def __post_init__(self) -> None:
        rid = str(self.run_id).strip()
        if not rid:
            raise SeedNamespaceError("SeedNamespace.run_id must be non-empty.")
        if "/" in rid or "\\" in rid:
            raise SeedNamespaceError("SeedNamespace.run_id must not contain path separators.")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise SeedNamespaceError("SeedNamespace.seed must be an integer (bool rejected).")
        root = str(self.root).strip()
        if not root:
            raise SeedNamespaceError("SeedNamespace.root must be non-empty.")
        object.__setattr__(self, "run_id", rid)
        object.__setattr__(self, "root", root)

    def path(self, *parts: str) -> str:
        segments = [self.root, self.run_id]
        for part in parts:
            text = str(part).strip()
            if not text:
                raise SeedNamespaceError("Seed namespace path segments must be non-empty.")
            if "/" in text or "\\" in text:
                raise SeedNamespaceError(
                    f"Seed namespace segment {text!r} must not contain path separators."
                )
            segments.append(text)
        return "/".join(segments)

    def fork_rng(self, *parts: str) -> RNGManager:
        """Return an RNGManager whose namespace is bound to this run_id."""

        return RNGManager(seed=self.seed, namespace=self.path(*parts))

    def child(self, *parts: str) -> SeedNamespace:
        """Return a logical child descriptor (same run_id/seed; path via ``path``)."""

        # Child is the same binding; callers use path()/fork_rng() for components.
        _ = self.path(*parts)
        return self

    def digest(self) -> str:
        return canonical_digest(
            {"run_id": self.run_id, "seed": self.seed, "root": self.root},
            prefix="ilw_seed_namespace",
        )

    def assert_no_cross_run_leakage(self, other: SeedNamespace) -> None:
        """Fail if two different runs would share the same namespace root path."""

        if self.run_id == other.run_id:
            return
        if self.path() == other.path():
            raise SeedNamespaceError(
                "Cross-run seed namespace leakage detected: identical paths "
                f"for run_id {self.run_id!r} and {other.run_id!r}."
            )
        # Same base seed is allowed; paths must still differ.
        if self.path("scheduler") == other.path("scheduler"):
            raise SeedNamespaceError("Cross-run scheduler namespace collision.")
