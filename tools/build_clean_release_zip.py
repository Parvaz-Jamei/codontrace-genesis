#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import zipfile, sys
BAD = ("__pycache__", ".pytest_cache", ".phase3_", ".ipynb_checkpoints")
BAD_SUFFIX = {".pyc", ".pyo"}

def build(root: str | Path, out: str | Path) -> Path:
    base=Path(root).resolve(); outp=Path(out).resolve()
    if outp.exists(): outp.unlink()
    with zipfile.ZipFile(outp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(base.rglob("*")):
            if not p.is_file(): continue
            rel=p.relative_to(base).as_posix()
            if any(tok in rel for tok in BAD) or p.suffix in BAD_SUFFIX or rel.endswith(".DS_Store"):
                continue
            z.write(p, rel)
    return outp

def main(argv=None):
    argv=argv or sys.argv[1:]
    if len(argv)!=2:
        print("usage: build_clean_release_zip.py <root> <out>", file=sys.stderr); return 2
    print(build(argv[0], argv[1])); return 0
if __name__ == "__main__": raise SystemExit(main())
