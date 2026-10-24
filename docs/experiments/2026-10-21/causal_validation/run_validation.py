"""Regenerate result.json: identified effect vs engine reruns, and the replay decomposition.

    python docs/experiments/2026-10-21/causal_validation/run_validation.py

Every random draw comes from fixed seeds, so two runs give byte-identical
files except for ``commit`` (the HEAD the run started from).
tests/causal_inference/test_causal_validation_result.py reruns ``build`` and
compares it with the committed file.
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import codontrace
from codontrace.causal_inference.contingency import decompose, engine_contingency_table
from codontrace.causal_inference.engine_study import EngineBitStudy


HERE = Path(__file__).resolve().parent


def build(commit: str | None = None) -> dict[str, object]:
    """Compute the result document. ``commit`` defaults to ``git rev-parse HEAD``."""

    here = HERE
    if commit is None:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=here).stdout.strip()
    study = EngineBitStudy(seeds=tuple(range(8)), truth_seeds=tuple(range(1000, 1008)))
    out: dict[str, object] = {
        "codontrace_version": codontrace.__version__,
        "python": platform.python_version(),
        "commit": commit,
        "design": {
            "preset": "GenesisRuntimeProfile.life_loop_world",
            "ticks": study.ticks,
            "populations": list(study.populations),
            "focal_bit": study.focal_bit,
            "background_bit": study.background_bit,
            "seeds": list(study.seeds),
            "truth_seeds": list(study.truth_seeds),
            "assignment_p_focal_1": {f"env={k[0]},bg={k[1]}": v for k, v in study.assignment.items()},
        },
        "validation": {str(s): study.validate(n_units=400, seed=s, n_bootstrap=400).to_dict() for s in (0, 1, 2)},
        "hidden_environment_not_identifiable": study.hidden_environment_is_not_identifiable(),
        "replay_decomposition": {},
    }
    for env in (0, 1):
        tab = engine_contingency_table(study, env=env)
        out["replay_decomposition"][f"env={env}"] = {  # type: ignore[index]
            "table": {h: {str(t): v for t, v in row.items()} for h, row in tab.items()},
            "decomposition": decompose(tab, n_permutations=1999).to_dict(),
        }
    return out


def render(out: dict[str, object]) -> str:
    return json.dumps(out, indent=2, sort_keys=True) + "\n"


def main() -> None:
    (HERE / "result.json").write_text(render(build()), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
