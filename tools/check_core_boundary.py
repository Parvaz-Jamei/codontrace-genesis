"""AST-based boundary guard for keeping Studio/UI/server code out of CodonTrace core.

This checker intentionally scans Python import structure instead of raw text.
Comments, docs, and string literals may mention Studio technologies for policy
or handoff documentation; actual core imports may not depend on them.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FORBIDDEN_TOP_LEVEL_MODULES: frozenset[str] = frozenset(
    {
        "fastapi",
        "starlette",
        "uvicorn",
        "websockets",
        "websocket",
        "socketio",
        "react",
        "vite",
        "tauri",
        "flask",
        "django",
        "quart",
    }
)

FORBIDDEN_DYNAMIC_IMPORTS: frozenset[str] = FORBIDDEN_TOP_LEVEL_MODULES


@dataclass(frozen=True)
class BoundaryViolation:
    path: Path
    lineno: int
    module: str
    reason: str

    def format(self) -> str:
        return f"{self.path}:{self.lineno}: forbidden {self.reason}: {self.module!r}"


def _top_level(module_name: str | None) -> str:
    if not module_name:
        return ""
    return module_name.split(".", 1)[0]


def _string_literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def scan_python_source(path: Path, *, root: Path | None = None) -> tuple[BoundaryViolation, ...]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - compileall reports this too.
        rel = path.relative_to(root) if root and path.is_relative_to(root) else path
        return (BoundaryViolation(rel, exc.lineno or 0, "<syntax-error>", "syntax error"),)

    rel_path = path.relative_to(root) if root and path.is_relative_to(root) else path
    violations: list[BoundaryViolation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = _top_level(alias.name)
                if top in FORBIDDEN_TOP_LEVEL_MODULES:
                    violations.append(
                        BoundaryViolation(rel_path, node.lineno, alias.name, "import")
                    )
        elif isinstance(node, ast.ImportFrom):
            top = _top_level(node.module)
            if top in FORBIDDEN_TOP_LEVEL_MODULES:
                violations.append(
                    BoundaryViolation(rel_path, node.lineno, node.module or "", "from-import")
                )
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if call_name in {"__import__", "importlib.import_module"} and node.args:
                module_name = _string_literal(node.args[0])
                top = _top_level(module_name)
                if top in FORBIDDEN_DYNAMIC_IMPORTS:
                    violations.append(
                        BoundaryViolation(
                            rel_path,
                            node.lineno,
                            module_name or "",
                            "dynamic import",
                        )
                    )
    return tuple(violations)


def iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))


def scan_paths(paths: Iterable[Path], *, root: Path | None = None) -> tuple[BoundaryViolation, ...]:
    violations: list[BoundaryViolation] = []
    for path in iter_python_files(paths):
        violations.extend(scan_python_source(path, root=root))
    return tuple(violations)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path.cwd()
    paths = [Path(item) for item in args] if args else [Path("src/codontrace")]
    violations = scan_paths(paths, root=root)
    if violations:
        for violation in violations:
            print(violation.format(), file=sys.stderr)
        return 1
    print("core-boundary-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
