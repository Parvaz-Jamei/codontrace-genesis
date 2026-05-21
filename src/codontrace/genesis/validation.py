"""Dependency-free validation pack for GENESIS research-library objects.

The validation pack returns typed Python results only. It does not write files,
run a command-line tool, generate reports, or perform network access.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib  # type: ignore[import-not-found]

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation issue produced by a validation helper."""

    path: str
    severity: str
    code: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warning", "error"}:
            msg = "ValidationIssue.severity must be info, warning, or error."
            raise ConfigurationError(msg)
        if not self.code:
            msg = "ValidationIssue.code must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "path": self.path,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationIssue:
        return cls(
            path=_str(data, "path", ""),
            severity=_str(data, "severity"),
            code=_str(data, "code"),
            message=_str(data, "message", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validation result; no file writing or report generation."""

    attempted: bool
    succeeded: bool
    issues: tuple[ValidationIssue, ...]

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "issues": [issue.to_dict() for issue in self.issues],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ValidationResult:
        raw_issues = data.get("issues", [])
        if not isinstance(raw_issues, list):
            msg = "ValidationResult.issues must be a list."
            raise ConfigurationError(msg)
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            issues=tuple(ValidationIssue.from_dict(_mapping(item, "issue")) for item in raw_issues),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_roundtrip(obj: Any) -> ValidationResult:
    """Validate ``to_dict``/``from_dict`` roundtrip for one public object."""

    issues: list[ValidationIssue] = []
    cls = type(obj)
    if not hasattr(obj, "to_dict") or not hasattr(cls, "from_dict"):
        issues.append(
            ValidationIssue(
                "object", "error", "roundtrip_missing", "object lacks to_dict/from_dict"
            )
        )
    else:
        try:
            roundtripped = cls.from_dict(obj.to_dict())
            if roundtripped.to_dict() != obj.to_dict():
                issues.append(
                    ValidationIssue(
                        "object", "error", "roundtrip_changed", "roundtrip changed serialized form"
                    )
                )
        except Exception as exc:  # pragma: no cover - message is part of audit result
            issues.append(ValidationIssue("object", "error", "roundtrip_failed", str(exc)))
    return ValidationResult(attempted=True, succeeded=not issues, issues=tuple(issues))


def validate_digest_stability(obj: Any) -> ValidationResult:
    """Validate digest stability across serialization when supported."""

    issues: list[ValidationIssue] = []
    if not hasattr(obj, "digest"):
        issues.append(ValidationIssue("object", "error", "digest_missing", "object lacks digest()"))
    elif hasattr(obj, "to_dict") and hasattr(type(obj), "from_dict"):
        before = obj.digest()
        after_obj = type(obj).from_dict(obj.to_dict())
        after = after_obj.digest()
        if before != after:
            issues.append(
                ValidationIssue(
                    "object", "error", "digest_changed", "digest changed after roundtrip"
                )
            )
    return ValidationResult(attempted=True, succeeded=not issues, issues=tuple(issues))


def validate_no_app_drift_project_metadata(
    project_root: str | Path | None = None,
) -> ValidationResult:
    """Parse pyproject metadata and detect app/CLI/dependency drift."""

    issues: list[ValidationIssue] = []
    if project_root is None:
        return ValidationResult(True, True, ())
    root = Path(project_root)
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return ValidationResult(
            True,
            False,
            (
                ValidationIssue(
                    "pyproject.toml", "error", "missing_pyproject", "pyproject.toml is missing"
                ),
            ),
        )
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = _toml_mapping(data.get("project", {}), "project")
    deps = project.get("dependencies", [])
    if not isinstance(deps, list):
        issues.append(
            ValidationIssue(
                "project.dependencies",
                "error",
                "dependencies_not_list",
                "dependencies must be a list",
            )
        )
        deps = []
    if deps:
        issues.append(
            ValidationIssue(
                "project.dependencies",
                "error",
                "runtime_dependencies_present",
                "runtime dependencies must remain empty",
            )
        )
    suspicious = {
        "flask",
        "fastapi",
        "streamlit",
        "gradio",
        "dash",
        "jupyter",
        "notebook",
        "matplotlib",
        "pandas",
        "numpy",
        "scipy",
        "sklearn",
        "scikit-learn",
        "gymnasium",
        "openai",
        "anthropic",
        "langchain",
        "networkx",
        "plotly",
    }
    for dep in deps:
        normalized = (
            str(dep)
            .split("[", 1)[0]
            .split("<", 1)[0]
            .split(">", 1)[0]
            .split("=", 1)[0]
            .strip()
            .lower()
        )
        if normalized in suspicious:
            issues.append(
                ValidationIssue(
                    "project.dependencies",
                    "error",
                    "suspicious_runtime_dependency",
                    f"suspicious runtime dependency: {normalized}",
                )
            )
    for key in ("scripts", "gui-scripts"):
        if key in project:
            issues.append(
                ValidationIssue(
                    f"project.{key}", "error", "app_entry_point", f"[project.{key}] must be absent"
                )
            )
    entry_points = project.get("entry-points")
    if entry_points:
        issues.append(
            ValidationIssue(
                "project.entry-points",
                "warning",
                "entry_points_review_needed",
                "entry points must be explicitly justified as non-app drift",
            )
        )
    optional = project.get("optional-dependencies", {})
    if isinstance(optional, Mapping):
        for group, group_deps in optional.items():
            if str(group) != "dev" and group_deps:
                issues.append(
                    ValidationIssue(
                        f"project.optional-dependencies.{group}",
                        "warning",
                        "optional_dependency_review",
                        "non-dev optional dependencies require review",
                    )
                )
    if not project.get("name"):
        issues.append(
            ValidationIssue("project.name", "error", "missing_name", "project name is missing")
        )
    if not project.get("version"):
        issues.append(
            ValidationIssue(
                "project.version", "error", "missing_version", "project version is missing"
            )
        )
    if not (root / "src" / "codontrace" / "py.typed").exists():
        issues.append(
            ValidationIssue(
                "src/codontrace/py.typed", "error", "missing_py_typed", "py.typed is missing"
            )
        )
    return ValidationResult(
        True, not any(item.severity == "error" for item in issues), tuple(issues)
    )


def validate_citation_metadata(
    project_root: str | Path, *, strict: bool = True
) -> ValidationResult:
    """Validate minimal CITATION.cff metadata without external validators."""

    root = Path(project_root)
    issues: list[ValidationIssue] = []
    citation = root / "CITATION.cff"
    pyproject = root / "pyproject.toml"
    if not citation.exists():
        severity = "error" if strict else "warning"
        return ValidationResult(
            True,
            not strict,
            (
                ValidationIssue(
                    "CITATION.cff", severity, "missing_citation", "CITATION.cff is missing"
                ),
            ),
        )
    text = citation.read_text(encoding="utf-8")
    py_version = ""
    if pyproject.exists():
        project = _toml_mapping(
            tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}), "project"
        )
        py_version = str(project.get("version", ""))
    cff_version = _extract_cff_scalar(text, "version")
    if py_version and cff_version and py_version != cff_version:
        issues.append(
            ValidationIssue(
                "CITATION.cff.version",
                "error",
                "citation_version_mismatch",
                "CITATION.cff version does not match pyproject",
            )
        )
    for field in ("title", "message", "license"):
        if not _extract_cff_scalar(text, field):
            issues.append(
                ValidationIssue(
                    f"CITATION.cff.{field}",
                    "error" if strict else "warning",
                    "missing_cff_field",
                    f"missing {field}",
                )
            )
    if "authors:" not in text:
        issues.append(
            ValidationIssue(
                "CITATION.cff.authors",
                "error" if strict else "warning",
                "missing_authors",
                "authors are missing",
            )
        )
    if "repository-code:" not in text and "url:" not in text:
        issues.append(
            ValidationIssue(
                "CITATION.cff.repository",
                "warning",
                "missing_repository",
                "repository URL is missing",
            )
        )
    if pyproject.exists():
        project = _toml_mapping(
            tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}), "project"
        )
        license_value = project.get("license")
        project_license = license_value if isinstance(license_value, str) else ""
        cff_license = _extract_cff_scalar(text, "license")
        if project_license and cff_license and project_license != cff_license:
            issues.append(
                ValidationIssue(
                    "CITATION.cff.license",
                    "warning",
                    "license_mismatch",
                    "license differs from pyproject",
                )
            )
    return ValidationResult(
        True, not any(issue.severity == "error" for issue in issues), tuple(issues)
    )


def validate_release_evidence_consistency(
    metadata: Mapping[str, JsonValue], *, release_candidate: bool = False
) -> ValidationResult:
    """Validate caller-provided release evidence metadata without reading files."""

    issues: list[ValidationIssue] = []
    version = metadata.get("version")
    artifact = metadata.get("artifact")
    if isinstance(version, str) and isinstance(artifact, str) and version not in artifact:
        issues.append(
            ValidationIssue(
                "metadata.artifact",
                "warning",
                "version_not_in_artifact",
                "artifact name does not include version",
            )
        )
    allowed = {"PASS", "FAIL", "NOT RUN", "NOT COMPLETED", "NOT APPLICABLE"}
    gates = (
        "compileall",
        "pytest",
        "ruff",
        "mypy",
        "build",
        "twine",
        "hosted_ci",
        "pip_audit",
        "wheel_smoke",
        "example_smoke",
        "zip_hygiene",
        "citation",
        "claim_audit",
        "api_audit",
    )
    for key in gates:
        value = metadata.get(key)
        if value is not None and value not in allowed:
            issues.append(
                ValidationIssue(
                    f"metadata.{key}", "warning", "unknown_gate_status", "unexpected gate status"
                )
            )
        if value == "FAIL":
            issues.append(
                ValidationIssue(f"metadata.{key}", "error", "gate_failed", f"{key} failed")
            )
    if release_candidate:
        for key in ("hosted_ci", "wheel_smoke"):
            if metadata.get(key) != "PASS":
                issues.append(
                    ValidationIssue(
                        f"metadata.{key}",
                        "error",
                        "rc_gate_required",
                        f"{key} must be PASS for RC mode",
                    )
                )
        if metadata.get("pip_audit") == "NOT COMPLETED" and not metadata.get("pip_audit_reason"):
            issues.append(
                ValidationIssue(
                    "metadata.pip_audit",
                    "warning",
                    "pip_audit_reason_missing",
                    "NOT COMPLETED needs a reason",
                )
            )
    return ValidationResult(
        True, not any(issue.severity == "error" for issue in issues), tuple(issues)
    )


def _extract_cff_scalar(text: str, key: str) -> str:
    match = re.search(
        rf"^{re.escape(key)}:\s*[\"']?([^\n\"']+)[\"']?\s*$", text, flags=re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _toml_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        msg = f"{name} must be an object."
        raise ConfigurationError(msg)
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value
