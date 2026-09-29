"""API smoke test for the causal-tape experiment harness.

Verifies the two properties the experiment depends on:
  1. RNGManager streams are reproducible and restorable (exact counterfactuals).
  2. The codon genome + Mutation + WhiteBoxAgent run is bit-deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_SRC = Path(__file__).resolve().parents[1] / "codontrace-genesis" / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from codontrace.agent import WhiteBoxAgent  # noqa: E402
from codontrace.codon import CodonTable  # noqa: E402
from codontrace.energy import ATPAccount  # noqa: E402
from codontrace.genome import SemanticGenome  # noqa: E402
from codontrace.mutation import Mutation  # noqa: E402
from codontrace.rng import RNGManager  # noqa: E402
from codontrace.world import World2D  # noqa: E402

TABLE = CodonTable.default_minimal()
WORLD_ASCII = """
.......
.A.....
...*...
.......
"""


def draws(seed: int, namespace: str, n: int) -> list[int]:
    stream = RNGManager(seed=seed).fork(namespace)
    return [stream.randrange(10_000) for _ in range(n)]


def main() -> int:
    ok = True

    # 1. Determinism of RNG streams.
    a = draws(7, "lineage-0", 8)
    b = draws(7, "lineage-0", 8)
    c = draws(7, "lineage-1", 8)
    print("rng.same_seed_same_stream:", a == b, flush=True)
    print("rng.different_namespace_differs:", a != c, flush=True)
    ok &= a == b and a != c

    # 2. Snapshot / restore round trip.
    stream = RNGManager(seed=11).fork("lineage-0")
    [stream.randrange(100) for _ in range(5)]
    snap = stream.snapshot(include_state=True)
    digest_before = stream.state_digest()
    tail = [stream.randrange(100) for _ in range(5)]
    restored = RNGManager.restore(snap)
    digest_after = restored.state_digest()
    tail2 = [restored.randrange(100) for _ in range(5)]
    print("rng.snapshot_roundtrip:", digest_before == digest_after and tail == tail2, flush=True)
    ok &= digest_before == digest_after and tail == tail2

    # 3. Genome + mutation determinism.
    founder = SemanticGenome.from_codons(["101", "011", "110"])
    print("genome.digest:", founder.digest()[:16], flush=True)
    m1 = Mutation.point(seed=3)
    g1 = m1.apply(founder, parent_id="p", generation=1, codon_table=TABLE)
    m2 = Mutation.point(seed=3)
    g2 = m2.apply(founder, parent_id="p", generation=1, codon_table=TABLE)
    print("mutation.deterministic:", g1.digest() == g2.digest(), founder.to_compact(), "->", g1.to_compact(), flush=True)
    ok &= g1.digest() == g2.digest()

    # 4. Agent run determinism + trace digest.
    def agent_digest(genome: SemanticGenome) -> tuple[str, int]:
        world = World2D.from_ascii(WORLD_ASCII)
        agent = WhiteBoxAgent(
            id="a",
            genome=genome,
            codon_table=TABLE,
            atp_account=ATPAccount(initial_atp=20.0),
            position=(1, 1),
        )
        trace = agent.run(world, steps=6)
        return trace.digest(), len(trace)

    d1, n1 = agent_digest(g1)
    d2, n2 = agent_digest(g1)
    d3, n3 = agent_digest(founder)
    print(f"agent.trace_digest_stable: {d1 == d2} (len={n1})", flush=True)
    print(f"agent.mutant_differs_from_founder: {d1 != d3}", flush=True)
    ok &= d1 == d2 and d1 != d3

    print("SMOKE_OK" if ok else "SMOKE_FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
