"""Release-readiness, artifact hygiene, and docs-consistency records.

These helpers model evidence from caller-provided data only. They do not publish,
read ZIP files, call CI providers, write files, or access the network.
"""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_audit import audit_docs_claims


def artifact_cache_file_issues(path: Path) -> tuple[str, ...]:
    """Return cache/build pollution entries found inside a built artifact.

    This checks the artifact contents directly. It intentionally does not fail
    because a source tree has a ``dist/`` directory after ``python -m build``.
    """

    forbidden_segments = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    forbidden_suffixes = (".pyc", ".pyo")

    def bad(name: str) -> bool:
        normalized = name.replace("\\", "/")
        segments = set(normalized.split("/"))
        if forbidden_segments & segments:
            return True
        if normalized.endswith(forbidden_suffixes):
            return True
        if "/build/" in f"/{normalized}/" or "/dist/" in f"/{normalized}/":
            return True
        if ".egg-info/" in normalized and any(
            part in normalized for part in ("SOURCES.txt", "PKG-INFO")
        ):
            # Wheel/sdist metadata is allowed in the artifact's own generated
            # metadata directories, including the standard setuptools sdist
            # layout ``<project>/src/<project>.egg-info``. Nested egg-info
            # directories elsewhere are treated as local source-tree pollution.
            parts = normalized.split("/")
            own_root_metadata = parts[0].endswith((".egg-info", ".dist-info"))
            own_src_metadata = (
                len(parts) >= 3 and parts[1] == "src" and parts[2].endswith(".egg-info")
            )
            if not (own_root_metadata or own_src_metadata):
                return True
        return False

    names: tuple[str, ...]
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as zip_archive:
            names = tuple(zip_archive.namelist())
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as tar_archive:
            names = tuple(member.name for member in tar_archive.getmembers())
    else:
        raise ConfigurationError(f"Unsupported artifact type: {path}")
    return tuple(sorted(name for name in names if bad(name)))


def assert_artifact_has_no_cache_files(path: Path) -> None:
    issues = artifact_cache_file_issues(path)
    if issues:
        raise ConfigurationError(
            f"Artifact {path.name} contains cache/build pollution: {', '.join(issues[:5])}"
        )


@dataclass(frozen=True, slots=True)
class ReleaseReadinessProfile:
    profile_name: str
    required_gates: tuple[str, ...]
    allowed_not_completed: tuple[str, ...] = ()
    requires_hosted_ci: bool = False
    requires_pip_audit: bool = False
    requires_claim_audit: bool = True
    requires_api_audit: bool = True
    requires_citation: bool = False
    requires_supply_chain: bool = False
    requires_no_critical_limitations: bool = False

    def __post_init__(self) -> None:
        if self.profile_name not in {"prepublic", "testpypi", "pypi", "mature_alpha"}:
            raise ConfigurationError("Unsupported ReleaseReadinessProfile.profile_name.")
        if len(set(self.required_gates)) != len(self.required_gates):
            raise ConfigurationError("ReleaseReadinessProfile.required_gates must be unique.")

    @classmethod
    def prepublic(cls) -> ReleaseReadinessProfile:
        return cls(
            "prepublic",
            (
                "compileall",
                "pytest",
                "ruff",
                "mypy",
                "build",
                "twine",
                "wheel_smoke",
                "claim_audit",
                "api_audit",
                "zip_hygiene",
            ),
            ("hosted_ci", "pip_audit"),
            requires_hosted_ci=False,
            requires_pip_audit=False,
            requires_citation=False,
            requires_supply_chain=False,
        )

    @classmethod
    def testpypi(cls) -> ReleaseReadinessProfile:
        return cls(
            "testpypi",
            cls.prepublic().required_gates,
            ("hosted_ci", "pip_audit"),
            requires_hosted_ci=False,
            requires_pip_audit=False,
            requires_citation=False,
            requires_supply_chain=False,
        )

    @classmethod
    def pypi(cls) -> ReleaseReadinessProfile:
        return cls(
            "pypi",
            cls.prepublic().required_gates
            + ("hosted_ci", "pip_audit", "citation", "docs_consistency", "supply_chain"),
            (),
            requires_hosted_ci=True,
            requires_pip_audit=True,
            requires_citation=True,
            requires_supply_chain=True,
            requires_no_critical_limitations=True,
        )

    @classmethod
    def mature_alpha(cls) -> ReleaseReadinessProfile:
        return cls(
            "mature_alpha",
            cls.pypi().required_gates
            + ("validation_bundle", "limitations", "evidence_bundle", "scenario_suite"),
            (),
            requires_hosted_ci=True,
            requires_pip_audit=True,
            requires_citation=True,
            requires_supply_chain=True,
            requires_no_critical_limitations=True,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "profile_name": self.profile_name,
            "required_gates": list(self.required_gates),
            "allowed_not_completed": list(self.allowed_not_completed),
            "requires_hosted_ci": self.requires_hosted_ci,
            "requires_pip_audit": self.requires_pip_audit,
            "requires_claim_audit": self.requires_claim_audit,
            "requires_api_audit": self.requires_api_audit,
            "requires_citation": self.requires_citation,
            "requires_supply_chain": self.requires_supply_chain,
            "requires_no_critical_limitations": self.requires_no_critical_limitations,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReleaseReadinessProfile:
        return cls(
            _str(data, "profile_name"),
            _str_tuple(data, "required_gates"),
            _str_tuple(data, "allowed_not_completed"),
            _bool(data, "requires_hosted_ci", False),
            _bool(data, "requires_pip_audit", False),
            _bool(data, "requires_claim_audit", True),
            _bool(data, "requires_api_audit", True),
            _bool(data, "requires_citation", False),
            _bool(data, "requires_supply_chain", False),
            _bool(data, "requires_no_critical_limitations", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ArtifactHygieneRecord:
    artifact_name: str
    contains_dist: bool
    contains_build: bool
    contains_pycache: bool
    contains_test_cache: bool
    contains_egg_info: bool
    contains_venv: bool
    suspicious_entries: tuple[str, ...] = ()
    passed: bool = False

    def __post_init__(self) -> None:
        failed = any(
            (
                self.contains_dist,
                self.contains_build,
                self.contains_pycache,
                self.contains_test_cache,
                self.contains_egg_info,
                self.contains_venv,
                bool(self.suspicious_entries),
            )
        )
        object.__setattr__(self, "passed", not failed)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "artifact_name": self.artifact_name,
            "contains_dist": self.contains_dist,
            "contains_build": self.contains_build,
            "contains_pycache": self.contains_pycache,
            "contains_test_cache": self.contains_test_cache,
            "contains_egg_info": self.contains_egg_info,
            "contains_venv": self.contains_venv,
            "suspicious_entries": list(self.suspicious_entries),
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ArtifactHygieneRecord:
        return cls(
            _str(data, "artifact_name"),
            _bool(data, "contains_dist", False),
            _bool(data, "contains_build", False),
            _bool(data, "contains_pycache", False),
            _bool(data, "contains_test_cache", False),
            _bool(data, "contains_egg_info", False),
            _bool(data, "contains_venv", False),
            _str_tuple(data, "suspicious_entries"),
            _bool(data, "passed", False),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DocsConsistencyRecord:
    checked_sections: tuple[str, ...]
    version_mentions: tuple[str, ...]
    stale_version_mentions: tuple[str, ...]
    stale_scope_phrases: tuple[str, ...]
    claim_audit_digest: str
    passed: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "checked_sections": list(self.checked_sections),
            "version_mentions": list(self.version_mentions),
            "stale_version_mentions": list(self.stale_version_mentions),
            "stale_scope_phrases": list(self.stale_scope_phrases),
            "claim_audit_digest": self.claim_audit_digest,
            "passed": self.passed,
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DocsConsistencyRecord:
        return cls(
            _str_tuple(data, "checked_sections"),
            _str_tuple(data, "version_mentions"),
            _str_tuple(data, "stale_version_mentions"),
            _str_tuple(data, "stale_scope_phrases"),
            _str(data, "claim_audit_digest", ""),
            _bool(data, "passed", False),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DocsConsistencyConfig:
    current_version: str
    allow_historical_versions: bool = True
    historical_doc_names: tuple[str, ...] = ("CHANGELOG.md", "RELEASE_EVIDENCE.md")
    current_scope_doc_names: tuple[str, ...] = ("README.md", "docs/api.md", "docs/concepts.md")
    roadmap_doc_names: tuple[str, ...] = ("README.md", "BACKLOG.md")
    allow_history_in_readme: bool = True
    current_scope_markers: tuple[str, ...] = ("Current status", "Release status", "Mature Alpha")
    current_scope_required_phrases: tuple[str, ...] = ()
    forbidden_current_scope_phrases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.current_version:
            raise ConfigurationError("DocsConsistencyConfig.current_version must not be empty.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "current_version": self.current_version,
            "allow_historical_versions": self.allow_historical_versions,
            "historical_doc_names": list(self.historical_doc_names),
            "current_scope_doc_names": list(self.current_scope_doc_names),
            "roadmap_doc_names": list(self.roadmap_doc_names),
            "allow_history_in_readme": self.allow_history_in_readme,
            "current_scope_markers": list(self.current_scope_markers),
            "current_scope_required_phrases": list(self.current_scope_required_phrases),
            "forbidden_current_scope_phrases": list(self.forbidden_current_scope_phrases),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DocsConsistencyConfig:
        return cls(
            _str(data, "current_version"),
            _bool(data, "allow_historical_versions", True),
            _str_tuple(data, "historical_doc_names"),
            _str_tuple_default(
                data,
                "current_scope_doc_names",
                ("README.md", "docs/api.md", "docs/concepts.md"),
            ),
            _str_tuple_default(data, "roadmap_doc_names", ("README.md", "BACKLOG.md")),
            _bool(data, "allow_history_in_readme", True),
            _str_tuple_default(
                data,
                "current_scope_markers",
                ("Current status", "Release status", "Mature Alpha"),
            ),
            _str_tuple(data, "current_scope_required_phrases"),
            _str_tuple(data, "forbidden_current_scope_phrases"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def evaluate_artifact_hygiene(
    paths: tuple[str, ...], artifact_name: str = "artifact"
) -> ArtifactHygieneRecord:
    normalized = tuple(path.replace("\\", "/") for path in paths)
    contains_dist = any(_has_segment(path, "dist") for path in normalized)
    contains_build = any(_has_segment(path, "build") for path in normalized)
    contains_pycache = any("__pycache__" in path for path in normalized)
    contains_test_cache = any(
        any(segment in path for segment in (".pytest_cache", ".mypy_cache", ".ruff_cache"))
        for path in normalized
    )
    contains_egg_info = any(
        path.endswith(".egg-info") or ".egg-info/" in path for path in normalized
    )
    contains_venv = any(
        _has_segment(path, ".venv") or _has_segment(path, "venv") for path in normalized
    )
    suspicious = tuple(
        sorted(
            path
            for path in normalized
            if path.endswith((".exe", ".dll", ".so")) or "/.git/" in f"/{path}/"
        )
    )
    return ArtifactHygieneRecord(
        artifact_name,
        contains_dist,
        contains_build,
        contains_pycache,
        contains_test_cache,
        contains_egg_info,
        contains_venv,
        suspicious,
    )


def evaluate_docs_consistency(
    docs: Mapping[str, str],
    current_version: str | None = None,
    config: DocsConsistencyConfig | None = None,
) -> DocsConsistencyRecord:
    if config is None:
        if current_version is None:
            raise ConfigurationError("current_version or DocsConsistencyConfig is required.")
        config = DocsConsistencyConfig(current_version=current_version)
    version_re = re.compile(r"v?0\.2\.0a\d+")
    checked = tuple(sorted(docs))
    mentions = tuple(sorted({item for text in docs.values() for item in version_re.findall(text)}))
    normalized_current = (
        config.current_version
        if config.current_version.startswith("v")
        else f"v{config.current_version}"
    )
    allowed_versions = {config.current_version, normalized_current}
    historical = set(config.historical_doc_names) if config.allow_historical_versions else set()
    stale_versions: list[str] = []
    for name, text in docs.items():
        if name in historical:
            continue
        for item in version_re.findall(text):
            if item in allowed_versions:
                continue
            if _version_mention_is_historical(name, text, item, config):
                continue
            stale_versions.append(f"{name}:{item}")
    stale_phrases = _stale_scope_phrases(docs, config)
    claim_audit = audit_docs_claims(docs)
    reasons: list[str] = []
    if stale_versions:
        reasons.append("stale_version_mentions")
    if stale_phrases:
        reasons.append("stale_scope_phrases")
    if not claim_audit.succeeded:
        reasons.append("claim_audit_blockers")
    return DocsConsistencyRecord(
        checked,
        mentions,
        tuple(sorted(stale_versions)),
        stale_phrases,
        claim_audit.digest(),
        not reasons,
        tuple(reasons) if reasons else ("docs_consistency_passed",),
    )


def _version_mention_is_historical(
    name: str, text: str, version: str, config: DocsConsistencyConfig
) -> bool:
    if name in set(config.historical_doc_names):
        return True
    lines = text.splitlines()
    for line in lines:
        if version not in line:
            continue
        lowered = line.lower()
        if lowered.strip().startswith("current ") or any(
            marker.lower() in lowered for marker in config.current_scope_markers
        ):
            return False
        if "old label" in lowered or "stale" in lowered:
            return False
        if any(
            word in lowered
            for word in ("history", "roadmap", "previous", "earlier", "changelog", "past")
        ):
            return True
    # Allow historical version mentions outside explicit current-status lines.
    return True


def _stale_scope_phrases(
    docs: Mapping[str, str], config: DocsConsistencyConfig | None = None
) -> tuple[str, ...]:
    patterns = [
        "proves discovery",
        "state of the art",
        "state-of-the-art",
        "legacy alpha proves",
        "a23 proves discovery",
        "full map-elites search loop implemented",
        "automatic experiment runner",
    ]
    if config is not None:
        patterns.extend(config.forbidden_current_scope_phrases)
    historical = (
        set(config.historical_doc_names) if config and config.allow_historical_versions else set()
    )
    found: list[str] = []
    for name, text in sorted(docs.items()):
        lowered = text.lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if pattern_lower in lowered and not _phrase_is_negated_or_non_goal(
                lowered, pattern_lower
            ):
                found.append(f"{name}:{pattern}")
        if name not in historical and config is not None:
            for required in config.current_scope_required_phrases:
                if required.lower() not in lowered:
                    found.append(f"{name}:missing:{required}")
    return tuple(sorted(found))


def _phrase_is_negated_or_non_goal(text: str, phrase: str) -> bool:
    for line in text.splitlines():
        if phrase not in line:
            continue
        window = line.lower()
        return any(
            marker in window
            for marker in (
                "does not",
                "do not",
                "not ",
                "no ",
                "without",
                "non-goal",
                "non-claim",
                "out of scope",
                "doesn't",
            )
        )
    return False


def _has_segment(path: str, segment: str) -> bool:
    return segment in tuple(part for part in path.split("/") if part)


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)


def _str_tuple_default(
    data: Mapping[str, JsonValue], key: str, default: tuple[str, ...]
) -> tuple[str, ...]:
    raw = data.get(key)
    if raw is None:
        return default
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)
