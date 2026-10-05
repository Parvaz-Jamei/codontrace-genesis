"""Read-only check of the public GitHub release.

Nothing in this module pushes, resets, or imports the evolution engine.
A newer release is reported. A clean git checkout may fast-forward.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TypedDict, cast

CANONICAL_REMOTE = "https://github.com/Parvaz-Jamei/codontrace-genesis.git"
LATEST_RELEASE_URL = "https://api.github.com/repos/Parvaz-Jamei/codontrace-genesis/releases/latest"
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
_PRE = {"a": 0, "b": 1, "rc": 2}
_VERSION = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:(?P<pre>a|b|rc)(?P<n>\d+))?$")


class ReleaseState(TypedDict):
    currentVersion: str
    currentCommit: str | None
    latestVersion: str | None
    latestCommit: str | None
    updateAvailable: bool
    behindMain: bool
    releaseAhead: bool
    lastChecked: float
    checking: bool
    error: str | None
    checkout: bool
    htmlUrl: str | None


def installed_version() -> str:
    try:
        return version("codontrace")
    except PackageNotFoundError:
        pass
    for parent in Path(__file__).resolve().parents:
        pyproject = parent / "pyproject.toml"
        if not pyproject.is_file():
            continue
        for raw in pyproject.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("#") or not line.startswith("version ="):
                continue
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
        break
    return "unknown"


def version_key(value: str) -> tuple[int, int, int, int, int] | None:
    match = _VERSION.fullmatch(value.strip())
    if match is None:
        return None
    pre = match.group("pre")
    rank = 3 if pre is None else _PRE[pre]
    number = 0 if match.group("n") is None else int(match.group("n"))
    return (int(match.group("major")), int(match.group("minor")), int(match.group("patch")), rank, number)


def newer_release(latest: str | None, current: str) -> bool:
    if not latest:
        return False
    left = version_key(latest)
    right = version_key(current)
    if left is None or right is None:
        return False
    return left > right


def find_checkout() -> Path | None:
    seeds = [Path(__file__).resolve(), Path.cwd().resolve()]
    seen: set[Path] = set()
    for seed in seeds:
        for parent in (seed, *seed.parents):
            if parent in seen:
                continue
            seen.add(parent)
            if (parent / ".git").exists() and _names_codontrace(parent):
                return parent
    return None


def _names_codontrace(root: Path) -> bool:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return False
    for raw in pyproject.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("name ="):
            return "codontrace" in line
    return False


def _git(args: list[str], *, cwd: Path | None = None, timeout: float = 20) -> tuple[str | None, str | None]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=None if cwd is None else str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "git failed").strip()
        return None, detail
    return proc.stdout.strip(), None


def _latest_release() -> tuple[str | None, str | None, str | None]:
    request = urllib.request.Request(
        LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "codontrace-console",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return None, None, str(exc)
    if not isinstance(payload, dict):
        return None, None, "release payload was not an object"
    tag = payload.get("tag_name")
    page = payload.get("html_url")
    if not isinstance(tag, str) or not tag.strip():
        return None, None, "release had no tag"
    url = page if isinstance(page, str) else None
    return tag.strip(), url, None


def _remote_main() -> tuple[str | None, str | None]:
    text, error = _git(["ls-remote", CANONICAL_REMOTE, "refs/heads/main"], timeout=12)
    if error or text is None:
        return None, error or "ls-remote returned nothing"
    token = text.split()
    if not token:
        return None, "ls-remote returned nothing"
    return token[0], None


def _blank(current: str, checkout: bool, commit: str | None) -> ReleaseState:
    return {
        "currentVersion": current,
        "currentCommit": commit,
        "latestVersion": None,
        "latestCommit": None,
        "updateAvailable": False,
        "behindMain": False,
        "releaseAhead": False,
        "lastChecked": 0,
        "checking": False,
        "error": None,
        "checkout": checkout,
        "htmlUrl": None,
    }


_LOCK = threading.Lock()
_STATE: ReleaseState = _blank(installed_version(), find_checkout() is not None, None)


def release_state() -> ReleaseState:
    with _LOCK:
        return cast(ReleaseState, dict(_STATE))


def refresh_release(*, force: bool = False) -> ReleaseState:
    with _LOCK:
        fresh = _STATE["lastChecked"] > 0 and (time.time() - _STATE["lastChecked"]) < CHECK_INTERVAL_SECONDS
        if _STATE["checking"] or (fresh and not force and _STATE["error"] is None):
            return cast(ReleaseState, dict(_STATE))
        _STATE["checking"] = True
    report = _probe()
    with _LOCK:
        _STATE.update(report)
        _STATE["checking"] = False
        _STATE["lastChecked"] = time.time()
        return cast(ReleaseState, dict(_STATE))


def _probe() -> ReleaseState:
    root = find_checkout()
    current = installed_version()
    commit: str | None = None
    full = ""
    if root is not None:
        found, _error = _git(["rev-parse", "HEAD"], cwd=root, timeout=8)
        if found:
            full = found
            commit = found[:12]
    tag, page, release_error = _latest_release()
    remote, remote_error = _remote_main()
    behind = bool(full and remote and full != remote)
    errors: list[str] = []
    if tag is None and release_error:
        errors.append(release_error)
    if remote is None and remote_error and tag is None:
        errors.append(remote_error)
    return {
        "currentVersion": current,
        "currentCommit": commit,
        "latestVersion": tag,
        "latestCommit": remote[:12] if remote else None,
        "updateAvailable": newer_release(tag, current) or behind,
        "behindMain": behind,
        "releaseAhead": newer_release(tag, current),
        "lastChecked": time.time(),
        "checking": False,
        "error": "; ".join(errors) if errors else None,
        "checkout": root is not None,
        "htmlUrl": page,
    }


def pull_checkout(root: Path) -> tuple[bool, str]:
    """Fast-forward ``origin/main``. Never pushes and never discards local edits."""
    if not _names_codontrace(root) or not (root / ".git").exists():
        return False, "This folder is not a CodonTrace checkout. Nothing was changed."
    dirty, dirty_error = _git(["status", "--porcelain"], cwd=root, timeout=8)
    if dirty_error or dirty is None:
        return False, dirty_error or "git status failed. Nothing was changed."
    if dirty.strip():
        return False, "The checkout has local changes. They were left untouched, and nothing was pushed."
    remotes, remote_error = _git(["remote"], cwd=root, timeout=8)
    if remote_error or remotes is None:
        return False, remote_error or "git remote failed. Nothing was changed."
    if "origin" not in remotes.split():
        return False, "This checkout has no origin remote. Nothing was pulled and nothing was pushed."
    pulled, pull_error = _git(["pull", "--ff-only", "origin", "main"], cwd=root, timeout=60)
    if pull_error or pulled is None:
        return False, pull_error or "git pull failed. Nothing was pushed."
    return True, pulled or "Already up to date."


def update_checkout() -> tuple[bool, str]:
    root = find_checkout()
    if root is None:
        return False, "This install is not a git checkout. The console does not run pip and does not push."
    return pull_checkout(root)


def start_release_monitor() -> None:
    def loop() -> None:
        while True:
            try:
                refresh_release(force=True)
            except Exception:
                pass
            time.sleep(CHECK_INTERVAL_SECONDS)

    threading.Thread(target=loop, name="console-release-check", daemon=True).start()
