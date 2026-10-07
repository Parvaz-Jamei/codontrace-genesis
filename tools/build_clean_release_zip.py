#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

BAD_DIR_NAMES = {
    ".git",
    "node_modules",
    "output",
    "simulation_runs",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    ".ipynb_checkpoints",
    ".phase3_",
}
BAD_DIR_FRAGMENTS = ("__pycache__", ".pytest_cache", ".phase3_", ".ipynb_checkpoints")
BAD_SUFFIX = {".pyc", ".pyo"}


def build(root: str | Path, out: str | Path) -> Path:
    base = Path(root).resolve()
    outp = Path(out).resolve()
    if outp.exists():
        outp.unlink()
    outp.parent.mkdir(parents=True, exist_ok=True)

    files_to_pack: list[tuple[Path, str]] = []

    for dirpath, dirnames, filenames in os.walk(base):
        current_dir = Path(dirpath)
        # Prune unwanted directories in-place so os.walk does not descend into them
        dirnames[:] = [
            d for d in sorted(dirnames)
            if d not in BAD_DIR_NAMES
            and not any(frag in d for frag in BAD_DIR_FRAGMENTS)
            and not (current_dir / d).is_symlink()
        ]

        for fname in sorted(filenames):
            p = current_dir / fname
            if p.suffix in BAD_SUFFIX or fname == ".DS_Store" or fname.endswith("~"):
                continue
            if ".tmp." in fname:
                continue

            # Ensure file does not resolve to the output archive itself
            try:
                p_resolved = p.resolve(strict=True)
                if p_resolved == outp:
                    continue
                # Also verify containment (do not follow symlinks outside base)
                if not p_resolved.is_relative_to(base):
                    continue
            except (OSError, RuntimeError, ValueError):
                continue

            try:
                rel = p.relative_to(base).as_posix()
            except ValueError:
                continue

            if any(frag in rel for frag in BAD_DIR_FRAGMENTS):
                continue

            files_to_pack.append((p, rel))

    # Sort deterministically
    files_to_pack.sort(key=lambda item: item[1])

    with zipfile.ZipFile(outp, "w", zipfile.ZIP_DEFLATED) as z:
        for p, rel in files_to_pack:
            z.write(p, rel)

    return outp


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print("usage: build_clean_release_zip.py <root> <out>", file=sys.stderr)
        return 2
    print(build(argv[0], argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
