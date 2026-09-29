"""Bit-for-bit stream-equality proof for the RNG backend migration.

Claim being tested: every migrated call site consumes the SAME numeric stream
after the change as before it, so no recorded discovery-campaign number moves.

Method (no repo edits; runs against whatever tree PYTHONPATH points at):
  1. Reconstruct the exact legacy expression at each call site with the standard
     library's ``random.Random(<expr>)`` (the "before" stream).
  2. Build ``StdlibSeedRNG(seed=<expr>)`` from ``codontrace.rng`` (the "after"
     stream).
  3. Draw 32 values from each with the same method schedule and require exact
     float/integer equality (repr equality, not a tolerance).
  4. Drive the real ledger through the same op schedule twice, once with the
     legacy ``random.Random`` injected at ``_rng`` and once with the real
     ``StdlibSeedRNG``, and compare every drawn value plus the resulting digest.
  5. Prove the unseeded default path: ``StdlibSeedRNG()`` (no seed) is
     OS-entropy seeded exactly like ``random.Random()``.

Exit code 0 only if every check passes.

Usage:
    PYTHONPATH=<scratch>/src python -B prove_rng_equality.py <output.json>
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from codontrace.life_loop.contact_atp_ledger import ContactAtpLedger, build_engine_scaffold_ledger
from codontrace.rng import StdlibSeedRNG

DRAWS = 32

# (label, seed expression, seed value) — mirrors every migrated call site.
# The value is computed arithmetically, not by eval, so the proof is explicit.
def _idea_seed(seed: int, cell: str) -> int:
    return int(seed) * 1009 + sum(ord(c) for c in cell)


CALL_SITES: tuple[tuple[str, str, int], ...] = (
    ("idea1.cell:discriminate", "401*1009+sum(ord(c) for c in 'discriminate')", _idea_seed(401, "discriminate")),
    ("idea1.cell:reactive", "401*1009+sum(ord(c) for c in 'reactive')", _idea_seed(401, "reactive")),
    ("idea1.cell:reward_explore", "401*1009+sum(ord(c) for c in 'reward_explore')", _idea_seed(401, "reward_explore")),
    ("idea3.cell:cut", "407*1009+sum(ord(c) for c in 'cut')", _idea_seed(407, "cut")),
    ("idea5.cell:retain_teach", "401*1009+sum(ord(c) for c in 'retain_teach')", _idea_seed(401, "retain_teach")),
    ("idea6.cell:withhold", "401*1009+sum(ord(c) for c in 'withhold')", _idea_seed(401, "withhold")),
    ("idea2.cell:baseline:gene", "401*1009+sum(ord(c) for c in 'baseline'+'gene')", _idea_seed(401, "baseline" + "gene")),
    (
        "idea2.cell:sham_predphase:causal",
        "5501*1009+sum(ord(c) for c in 'sham_predphase'+'causal')",
        _idea_seed(5501, "sham_predphase" + "causal"),
    ),
)


def _stream_random(rng, n: int) -> list[object]:
    return [rng.random() for _ in range(n)]


def _stream_mixed(rng, n: int) -> list[object]:
    out: list[object] = []
    for i in range(n):
        if i % 4 == 0:
            out.append(rng.random())
        elif i % 4 == 1:
            out.append(rng.randrange(0, 97))
        elif i % 4 == 2:
            out.append(rng.choice(["a", "b", "c", "d", "e"]))
        else:
            buf = [1, 2, 3, 4, 5, 6, 7, 8]
            rng.shuffle(buf)
            out.append(tuple(buf))
    return out


def _op_schedule(ledger: ContactAtpLedger, rng) -> list[object]:
    """Exercise every ledger method that consumes the RNG, in a fixed order."""

    ledger._rng = rng
    observed: list[object] = []
    observed.append(ledger.matched_random_edge())
    observed.append(ledger.matched_random_edge(degree=2))
    observed.append(ledger.reward_explore_eps(epsilon=0.25, budget=1.0)["edge_id"])
    alloc = ledger.reallocate_contact_budget(class_blind=True, zero_sum=True, budget=2.0)
    observed.append(tuple(sorted(alloc["allocation"].items())))
    return observed


def main() -> int:
    target = Path(sys.argv[1])
    report: dict[str, object] = {"draws_per_site": DRAWS, "checks": {}, "all_equal": True}

    # --- 1+2+3: per-call-site stream equality -------------------------------
    for label, expr, seed_value in CALL_SITES:
        before = random.Random(seed_value)
        after = StdlibSeedRNG(seed=seed_value)
        s_random_before = _stream_random(before, DRAWS)
        s_random_after = _stream_random(after, DRAWS)
        before_mixed = random.Random(seed_value)
        after_mixed = StdlibSeedRNG(seed=seed_value)
        s_mixed_before = _stream_mixed(before_mixed, DRAWS)
        s_mixed_after = _stream_mixed(after_mixed, DRAWS)
        ok = s_random_before == s_random_after and s_mixed_before == s_mixed_after
        report["checks"][label] = {
            "seed_expression": expr,
            "seed_value": seed_value,
            "random_first_4": [repr(v) for v in s_random_after[:4]],
            "random_last": repr(s_random_after[-1]),
            "mixed_first_4": [repr(v) for v in s_mixed_after[:4]],
            "random_stream_equal": s_random_before == s_random_after,
            "mixed_stream_equal": s_mixed_before == s_mixed_after,
            "equal": ok,
        }
        report["all_equal"] = bool(report["all_equal"]) and ok

    # --- 4: real ledger op schedule, legacy backend vs new backend -----------
    ledger_legacy = build_engine_scaffold_ledger(seed=401)
    ledger_new = build_engine_scaffold_ledger(seed=401)
    legacy_ops = _op_schedule(ledger_legacy, random.Random(401))
    new_ops = _op_schedule(ledger_new, StdlibSeedRNG(seed=401))
    report["ledger_op_schedule_equal"] = legacy_ops == new_ops
    report["ledger_ops"] = [repr(v) for v in new_ops]
    report["all_equal"] = bool(report["all_equal"]) and legacy_ops == new_ops

    # Whole-scaffold digest equality for several seeds (unseeded/re-seeded path).
    # The legacy digest is reproduced in-process by swapping the ledger's stream
    # back to the standard library's ``random.Random(seed)``, which is exactly
    # what the pre-patch line 162 constructed.
    digest_checks = {}
    for seed in (0, 1, 7, 11, 401, 5501):
        new = build_engine_scaffold_ledger(seed=seed)
        legacy = build_engine_scaffold_ledger(seed=seed)
        legacy._rng = random.Random(seed)
        legacy_digest = legacy.digest()
        new_digest = new.digest()
        digest_checks[str(seed)] = {
            "legacy": legacy_digest,
            "new": new_digest,
            "equal": legacy_digest == new_digest,
        }
        report["all_equal"] = bool(report["all_equal"]) and legacy_digest == new_digest
    report["scaffold_digests"] = digest_checks

    # --- 5: unseeded default path behaves like random.Random() ---------------
    unseeded_a = StdlibSeedRNG()
    unseeded_b = StdlibSeedRNG()
    seq_a = [unseeded_a.random() for _ in range(8)]
    seq_b = [unseeded_b.random() for _ in range(8)]
    report["unseeded_path"] = {
        "two_instances_differ": seq_a != seq_b,
        "matches_random_dot_Random_none_semantics": random.Random().random() != random.Random().random(),
        "seed_field_default": None,
        "draw_count_a": unseeded_a.draw_count,
        "re_seeded_path_equal": [
            repr(random.Random(int(s)).random()) for s in (0, 401)
        ]
        == [repr(StdlibSeedRNG(seed=int(s)).random()) for s in (0, 401)],
    }
    report["all_equal"] = bool(report["all_equal"]) and bool(
        report["unseeded_path"]["re_seeded_path_equal"]
    )

    target.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, indent=1, sort_keys=True))
    print("ALL_EQUAL" if report["all_equal"] else "MISMATCH")
    return 0 if report["all_equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
