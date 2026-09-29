"""Independent bit-for-bit proof that 40138c9 preserves the legacy RNG stream.

Loads the PRE-COMMIT `contact_atp_ledger` module extracted from
`git show 40138c9^:...` directly from disk (not from the author's harness) and
compares it against the live patched module:

  * >= 512 draws per call site, several seeds, mixed methods;
  * the unseeded `random.Random()` / `StdlibSeedRNG(seed=None)` paths;
  * the re-seeded path (`ledger._rng = ...(seed=S)`) used by __post_init__;
  * ledger ops that consume the stream (shuffle / choice / random).

Run with:
    set PYTHONPATH=<repo>\\src
    set PYTHONUTF8=1
    python test-runs/verify/check_rng_equality.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import subprocess
import sys
from pathlib import Path

GIT = r"E:\MinGit\cmd\git.exe"
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
OUT = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\test-runs\verify")
PRE = "40138c9^"

failures: list[str] = []


def note(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}{(' :: ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def extract_old_module() -> Path:
    rel = "src/codontrace/life_loop/contact_atp_ledger.py"
    raw = subprocess.run(
        [GIT, "show", f"{PRE}:{rel}"], capture_output=True, cwd=REPO
    ).stdout
    assert raw, "could not extract pre-commit ledger"
    target = OUT / "_old_contact_atp_ledger.py"
    target.write_bytes(raw)
    return target


def load_old_module(path: Path):
    spec = importlib.util.spec_from_file_location("old_contact_atp_ledger", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["old_contact_atp_ledger"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def trace_rng(rng, draws: int) -> dict[str, object]:
    """Fixed, mixed-method draw schedule; returns the raw values."""

    floats = [rng.random() for _ in range(draws)]
    ints = [rng.randrange(0, 10_000) for _ in range(draws)]
    ints_one_arg = [rng.randrange(97) for _ in range(draws)]
    picks = [rng.choice(list(range(37))) for _ in range(draws)]
    bag = list(range(64))
    for i in range(draws):
        rng.shuffle(bag)
    shuffled = list(bag)
    sampled = [rng.sample(list(range(50)), 7) for _ in range(draws)]
    return {
        "floats": floats,
        "randrange_2arg": ints,
        "randrange_1arg": ints_one_arg,
        "choices": picks,
        "shuffled_final": shuffled,
        "samples": sampled,
    }


def compare_traces(label: str, old_rng, new_rng, draws: int) -> None:
    a = trace_rng(old_rng, draws)
    b = trace_rng(new_rng, draws)
    same = a == b
    digest_a = hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()
    digest_b = hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()
    note(same, label, f"draws/call={draws} sha256(old)={digest_a[:16]} sha256(new)={digest_b[:16]}")
    if not same:
        for key in a:
            if a[key] != b[key]:
                print(f"      first differing field: {key}")


def rng_battery() -> None:
    draws = 512
    for seed in (0, 1, 7, 11, 401, 5501, 2**31 - 1):
        old_rng = random.Random(seed)
        from codontrace.rng import StdlibSeedRNG

        compare_traces(f"stdlib seed={seed}", old_rng, StdlibSeedRNG(seed=seed), draws)

    # seeded path used by ContactAtpLedger.__post_init__ (int(rng_seed))
    for rng_seed in (0, 3, 401):
        old_rng = random.Random(int(rng_seed))
        from codontrace.rng import StdlibSeedRNG

        compare_traces(
            f"ledger __post_init__ int(rng_seed={rng_seed})",
            old_rng,
            StdlibSeedRNG(seed=int(rng_seed)),
            draws,
        )

    # unseeded path: random.Random(None) vs StdlibSeedRNG(seed=None) after a forced state
    old_rng = random.Random(None)
    from codontrace.rng import StdlibSeedRNG

    new_rng = StdlibSeedRNG(seed=None)
    note(True, "unseeded construction does not raise",
         f"old={type(old_rng).__name__} new={type(new_rng).__name__}")
    old_rng.seed(20260929)
    new_rng.setstate(old_rng.getstate())
    compare_traces("unseeded-then-state-forced", old_rng, new_rng, 64)


def ledger_op_battery(old_module, new_module) -> None:
    """Drive real ledger ops that consume the stream, on both modules."""

    from codontrace.rng import StdlibSeedRNG

    for seed in (0, 7, 401):
        old_ledger = old_module.build_engine_scaffold_ledger(seed=seed)
        new_ledger = new_module.build_engine_scaffold_ledger(seed=seed)
        note(
            old_ledger.snapshot() == new_ledger.snapshot(),
            f"scaffold snapshot seed={seed}",
            f"digest {old_ledger.digest()[:16]} vs {new_ledger.digest()[:16]}",
        )
        note(
            old_ledger.digest() == new_ledger.digest(),
            f"scaffold digest seed={seed}",
        )

        schedule = [
            ("scramble_contacts", {"degree_preserving": True}),
            ("reallocate_contact_budget", {"budget": 10.0, "class_blind": True, "zero_sum": True}),
            ("matched_random_edge", {}),
            ("reward_explore_eps", {"epsilon": 0.5, "budget": 2.0}),
            ("sham_cue_predphase", {}),
            ("scramble_contacts", {"degree_preserving": False}),
            ("update_reactive_ledger", {"predicted": 0.4, "realised": 0.6}),
        ]
        for op_name, kwargs in schedule:
            try:
                a = getattr(old_ledger, op_name)(**kwargs)
            except Exception as exc:  # noqa: BLE001
                a = f"{type(exc).__name__}: {exc}"
            try:
                b = getattr(new_ledger, op_name)(**kwargs)
            except Exception as exc:  # noqa: BLE001
                b = f"{type(exc).__name__}: {exc}"
            note(a == b, f"ledger op {op_name} seed={seed}")

        note(
            old_ledger.snapshot() == new_ledger.snapshot(),
            f"snapshot after op schedule seed={seed}",
        )

        # deep stream check: re-seed both to the same value and drain 512 mixed draws
        # through the *ledger* object's own rng attribute
        old_ledger._rng = random.Random(99)
        new_ledger._rng = StdlibSeedRNG(seed=99)
        old_trace = [old_ledger._rng.random() for _ in range(512)]
        new_trace = [new_ledger._rng.random() for _ in range(512)]
        note(old_trace == new_trace, f"ledger rng re-seed drain seed={seed} (512 draws)")

    # every scaffold builder, both modules
    builders = [
        name
        for name in dir(new_module)
        if name.startswith("build_") and name.endswith("ledger")
    ]
    for name in sorted(builders):
        for seed in (0, 7):
            old_value = getattr(old_module, name)(seed=seed)
            new_value = getattr(new_module, name)(seed=seed)
            note(
                old_value.digest() == new_value.digest(),
                f"{name}(seed={seed}) digest",
                f"{old_value.digest()[:16]}",
            )


def main() -> int:
    old_path = extract_old_module()
    print(f"extracted pre-commit module -> {old_path}")
    print(f"pre-commit source sha256 = {hashlib.sha256(old_path.read_bytes()).hexdigest()}")
    old_module = load_old_module(old_path)
    import codontrace.life_loop.contact_atp_ledger as new_module

    rng_battery()
    ledger_op_battery(old_module, new_module)

    print("\n=== RNG EQUALITY SUMMARY ===")
    print("failures:", failures if failures else "none")
    (OUT / "check_rng_equality.txt").write_text(
        "\n".join([f"failures={failures or 'none'}"]), encoding="utf-8"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
