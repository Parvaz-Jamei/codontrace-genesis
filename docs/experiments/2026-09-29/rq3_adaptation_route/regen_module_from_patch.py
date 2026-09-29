"""Regenerate test-runs/rq3/antagonist_population.py from PROPOSED_CHANGE_3.patch.

Run after editing the module or the patch, and before running build_patch.py, so the two
stay in sync: the module is the source, the patch carries it.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCH = HERE / "PROPOSED_CHANGE.patch"
MODULE = HERE / "antagonist_population.py"
MARKER = "diff --git a/src/codontrace/genesis/measurements/antagonist_population.py"


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")
    if MARKER not in text:
        # No patch yet: the module stands alone.
        print("patch has no module section yet; module left as is")
        return 0
    segment = text[text.index(MARKER) :]
    body = [
        line[1:]
        for line in segment.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    while body and body[-1].strip() == "":
        body.pop()
    MODULE.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"regenerated {MODULE} ({len(body)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
