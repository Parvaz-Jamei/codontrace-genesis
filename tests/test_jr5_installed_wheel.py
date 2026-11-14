"""The JR5 verdict from an installed wheel, not from the source tree.

CI and the rest of the suite import ``codontrace`` from ``src/``, where every
data file is present whether or not the wheel ships it. These tests read the
claimgate data the way an installed package does (``importlib.resources``),
check that a missing file refuses instead of raising an OS error, and build
the wheel, install it into a fresh virtual environment and run the planted
valid positive through the verdict and the auditor there.

The wheel build needs setuptools (the build backend named in pyproject.toml)
in the running interpreter; CI installs it before the suite. Without it the
build tests skip, unless CODONTRACE_REQUIRE_WHEEL_TEST=1 (set in the
dedicated CI job), which turns the skip into a failure.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from importlib import resources
from pathlib import Path
from typing import Any

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate import jr5_verdict as verdict
from codontrace.errors import ConfigurationError
from tests.test_jr5_phase2c_verdict_adapter import bound_bundle, positive

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "codontrace"
_RESOURCES = {name: getattr(verdict, name) for name in dir(verdict) if name.endswith("_RESOURCE")}

pytestmark = pytest.mark.slow


def _packaged_source_files() -> set[str]:
    """Every non-Python file under src/codontrace, as a path inside the wheel."""

    return {
        path.relative_to(ROOT / "src").as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file() and path.suffix not in {".py", ".pyc"} and "__pycache__" not in path.parts
    }


def test_every_claimgate_resource_is_read_through_importlib_resources() -> None:
    """Each data file the verdict reads exists as a package resource and is a file shipped in data/.

    Basis: ``jr5_constants`` reads the names in the ``*_RESOURCE`` constants
    through ``importlib.resources.files("codontrace.claimgate")``, the API an
    installed package answers from its own files. The set of those names must
    equal the files in ``claimgate/data`` so no shipped file goes unread and
    no read file is missing.
    Expected: three resources (constants, record, deviations log), each
    readable, equal to the data directory listing.
    """

    package = resources.files("codontrace.claimgate")
    assert sorted(_RESOURCES.values()) == sorted(
        f"data/{p.name}" for p in (PACKAGE / "claimgate" / "data").iterdir() if p.is_file()
    )
    assert len(_RESOURCES) == 3
    for name in _RESOURCES.values():
        assert package.joinpath(name).read_bytes()


def test_a_missing_packaged_resource_refuses_and_the_auditor_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the deviations log the verdict refuses and the auditor grades the bundle, without an OS error.

    Basis: this is the state of a wheel built without the log (the R43-1
    defect). ``jr5_constants`` must turn the OS error into a
    ConfigurationError, and the exemption check must read that as "not
    proved", so ``audit_bundle`` keeps the global ban on red_queen_proved
    instead of raising. The resource name is pointed at a file that does not
    exist in the package.
    Expected: ConfigurationError from jr5_constants and from the verdict;
    audit level at most 1 with the red_queen_proved warning.
    """

    payload = bound_bundle(positive())
    monkeypatch.setattr(verdict, "_DEVIATIONS_RESOURCE", "data/not_shipped.md")
    with pytest.raises(ConfigurationError, match="not readable from the installed package"):
        verdict.jr5_constants()
    with pytest.raises(ConfigurationError):
        verdict.evaluate_jr5_verdict(payload["jr5_evidence"])
    report = audit_bundle(payload)
    assert report.achieved_level <= 1
    assert any("red_queen_proved" in warning for warning in report.warnings)


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel from a copy of the tree with the backend named in pyproject.toml."""

    if importlib.util.find_spec("setuptools") is None:
        if os.environ.get("CODONTRACE_REQUIRE_WHEEL_TEST") == "1":
            pytest.fail("setuptools is required to build the wheel in this job")
        pytest.skip("setuptools (the build backend) is not installed")
    tree = tmp_path_factory.mktemp("wheel-src")
    for name in ("pyproject.toml", "MANIFEST.in", "README.md", "LICENSE"):
        shutil.copy2(ROOT / name, tree / name)
    shutil.copytree(
        ROOT / "src",
        tree / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )
    out = tmp_path_factory.mktemp("wheel-out")
    build = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, setuptools.build_meta as b; print(b.build_wheel(sys.argv[1]))",
            str(out),
        ],
        cwd=tree,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert build.returncode == 0, build.stderr[-4000:]
    wheels = sorted(out.glob("codontrace-*.whl"))
    assert len(wheels) == 1, build.stdout[-2000:]
    return wheels[0]


def test_the_wheel_ships_every_package_data_file(built_wheel: Path) -> None:
    """Every non-Python file under src/codontrace is in the wheel.

    Basis: a file inside the package directory is there to be read at run
    time (claimgate prereg data, the RAG corpus, the ILW DAG, the console
    assets, py.typed); one that the package-data globs miss is absent from
    an install while every source-tree test still passes. The expected list
    is the directory listing, so a new data file that is not packaged fails
    here.
    Expected: the wheel's file list contains every such path, including
    codontrace/claimgate/data/jr5_deviations.md.
    """

    with zipfile.ZipFile(built_wheel) as wheel:
        names = set(wheel.namelist())
    assert "codontrace/claimgate/data/jr5_deviations.md" in names
    assert sorted(_packaged_source_files() - names) == []


_INSTALLED_CHECK = r"""
import json, sys
from pathlib import Path
import codontrace
from codontrace.claimgate import audit_bundle
from codontrace.claimgate import jr5_verdict as v
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
evidence = payload["jr5_evidence"]
k = v.jr5_constants()
out = v.evaluate_jr5_verdict(evidence)
v.verify_jr5_verdict(out.to_dict(), v.Jr5Evidence.from_dict(evidence))
report = audit_bundle(payload)
print(json.dumps({
    "module": codontrace.__file__,
    "n_constants": len(k),
    "outcome": out.outcome,
    "proved": out.red_queen_proved,
    "conditions": out.conditions,
    "claim": v.assert_jr5_red_queen_claim_allowed(out.to_dict(), evidence),
    "level": int(report.achieved_level),
}))
"""


def _install(wheel: Path, venv: Path) -> Path:
    """Create a fresh venv and unpack the pure-Python wheel into its purelib directory.

    The wheel format places a pure wheel's files at the root of purelib; this
    is what an installer does for such a wheel (codontrace has no runtime
    dependencies and no compiled parts). The venv has no pip and no access
    to the source tree.
    """

    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True, timeout=300)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    purelib = subprocess.run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    ).stdout.strip()
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(purelib)
    return python


def test_installed_wheel_proves_the_valid_positive(built_wheel: Path, tmp_path: Path) -> None:
    """The planted valid positive reaches proved and the same audit level from the installed package.

    Basis: the planted positive (all four E2 tests agree, E1 inside the
    registered margin, alternatives equivalent to 0, host time-shift effect
    below 0) gives outcome rq_consistent, conditions a-e true and
    red_queen_proved from the source tree, and the auditor grants level 4.
    The installed copy reads the same three data files from the wheel, so it
    must reach the same result. The check runs with ``python -I`` from a
    temporary directory, so neither the source tree nor PYTHONPATH is on the
    import path; the module path printed must be inside the venv.
    Expected: module under the venv; 26 constants keys; rq_consistent;
    conditions a-e true; proved; claim allowed; level 4, equal to the
    source-tree level.
    """

    payload = bound_bundle(positive())
    source_level = int(audit_bundle(payload).achieved_level)
    assert source_level == 4
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(payload), encoding="utf-8")
    python = _install(built_wheel, tmp_path / "venv")
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    run = subprocess.run(
        [str(python), "-I", "-c", _INSTALLED_CHECK, str(bundle_path)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert run.returncode == 0, run.stderr[-4000:]
    result: dict[str, Any] = json.loads(run.stdout.strip().splitlines()[-1])
    module = Path(result["module"]).resolve()
    assert module.is_relative_to((tmp_path / "venv").resolve())
    assert not module.is_relative_to(ROOT.resolve())
    assert result["n_constants"] == 26
    assert result["outcome"] == "rq_consistent"
    assert result["conditions"] == {key: True for key in ("a", "b", "c", "d", "e")}
    assert result["proved"] is True
    assert result["claim"] == "red_queen_proved"
    assert result["level"] == source_level == 4
