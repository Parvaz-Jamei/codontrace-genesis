"""Cross-platform script and gate tests discovery for the preview console.

Standard library only. Does not import the evolution engine.
"""

from __future__ import annotations

import ast
import os
import time
from pathlib import Path
from typing import Any


def script_directories() -> list[Path]:
    """Find directories containing custom tests and research scripts."""
    dirs: list[Path] = []
    custom_env = os.environ.get("CODONTRACE_SCRIPTS_DIR", "").strip()
    if custom_env:
        dirs.append(Path(custom_env).expanduser())

    dirs.append(Path("custom_tests").resolve())
    dirs.append(Path("scripts").resolve())
    dirs.append(Path.home() / "custom_tests")

    repo_dir = Path(__file__).resolve().parents[3]
    dirs.append(repo_dir / "custom_tests")
    dirs.append(repo_dir / "scripts")

    seen = set()
    valid = []
    for d in dirs:
        resolved = d.resolve()
        if resolved.is_dir() and resolved not in seen:
            seen.add(resolved)
            valid.append(resolved)
    return valid


def list_scripts() -> list[dict[str, Any]]:
    """Enumerate discovered python test and research scripts."""
    results = []
    seen_names = set()

    for s_dir in script_directories():
        try:
            for item in sorted(s_dir.iterdir()):
                if item.is_file() and item.suffix == ".py" and item.name not in seen_names:
                    seen_names.add(item.name)
                    doc = ""
                    try:
                        content = item.read_text(encoding="utf-8", errors="replace")[:1000]
                        tree = ast.parse(content)
                        doc = ast.get_docstring(tree) or ""
                    except Exception:
                        pass

                    stat = item.stat()
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                        "docstring": doc.strip().split("\n")[0] if doc else "",
                    })
        except OSError:
            continue

    return results


def read_script(name: str) -> str | None:
    """Read contents of a script safely."""
    clean_name = Path(name).name
    if not clean_name.endswith(".py") or ".." in clean_name:
        return None

    for s_dir in script_directories():
        candidate = s_dir / clean_name
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None
    return None


def list_gates(repo_root: Path | None = None) -> list[dict[str, Any]]:
    """List the 29 gate test files and their metadata."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]

    gates_dir = repo_root / "tests" / "genesis_gates"
    if not gates_dir.is_dir():
        return []

    gates = []
    for item in sorted(gates_dir.glob("test_*.py")):
        doc = ""
        try:
            content = item.read_text(encoding="utf-8", errors="replace")[:1500]
            tree = ast.parse(content)
            doc = ast.get_docstring(tree) or ""
        except Exception:
            pass

        gates.append({
            "file": item.name,
            "path": str(item),
            "description": doc.strip().split("\n")[0] if doc else item.stem.replace("test_", "").replace("_", " ").title(),
        })

    return gates


def save_script(name: str, content: str) -> dict[str, Any]:
    """Save an uploaded script to the custom_tests directory."""
    clean = Path(name).name
    if not clean.endswith(".py") or ".." in clean:
        return {"ok": False, "error": "Script must be a .py file"}
    target_dir = Path("custom_tests").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / clean
    try:
        target_file.write_text(content, encoding="utf-8")
        return {"ok": True, "name": clean, "path": str(target_file)}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def run_script(name: str) -> dict[str, Any]:
    """Execute a python script in subprocess and return status."""
    import subprocess
    import sys

    clean = Path(name).name
    repo_root = Path(__file__).resolve().parents[3]
    candidate = None
    for s_dir in script_directories():
        if (s_dir / clean).is_file():
            candidate = s_dir / clean
            break
    if not candidate:
        return {"ok": False, "error": f"Script {name} not found"}

    try:
        proc = subprocess.run(
            [sys.executable, str(candidate)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(repo_root),
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-2000:],
            "stderr": proc.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Execution timed out (30s limit)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_gate_tests(filter_pattern: str | None = None) -> dict[str, Any]:
    """Run gate tests via pytest in subprocess."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    gates_dir = repo_root / "tests" / "genesis_gates"
    cmd = [sys.executable, "-m", "pytest", str(gates_dir), "-q", "--tb=short"]
    if filter_pattern:
        cmd.extend(["-k", filter_pattern])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(repo_root))
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-3000:],
            "stderr": proc.stderr[-3000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Gate tests run timed out (60s limit)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

