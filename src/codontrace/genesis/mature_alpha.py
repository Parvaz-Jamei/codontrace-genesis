"""Mature Research Alpha stability, documentation, and security-evidence records.

These objects model release/evidence metadata only. They do not run external
security tools, publish packages, write files, or generate reports.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.api_audit import APIStabilityLevel


@dataclass(frozen=True, slots=True)
class APIStabilityMap:
    version: str
    experimental_symbols: tuple[str, ...] = ()
    alpha_symbols: tuple[str, ...] = ()
    stable_candidate_symbols: tuple[str, ...] = ()
    deprecated_symbols: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.version:
            raise ConfigurationError("APIStabilityMap.version must not be empty.")
        for attr in (
            "experimental_symbols",
            "alpha_symbols",
            "stable_candidate_symbols",
            "deprecated_symbols",
        ):
            object.__setattr__(self, attr, tuple(sorted(getattr(self, attr))))

    @property
    def covered_symbols(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(self.experimental_symbols)
                | set(self.alpha_symbols)
                | set(self.stable_candidate_symbols)
                | set(self.deprecated_symbols)
            )
        )

    def stability_for(self, symbol: str) -> APIStabilityLevel | None:
        if symbol in self.experimental_symbols:
            return APIStabilityLevel.EXPERIMENTAL
        if symbol in self.alpha_symbols:
            return APIStabilityLevel.ALPHA
        if symbol in self.stable_candidate_symbols:
            return APIStabilityLevel.STABLE_CANDIDATE
        if symbol in self.deprecated_symbols:
            return APIStabilityLevel.DEPRECATED
        return None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "experimental_symbols": list(self.experimental_symbols),
            "alpha_symbols": list(self.alpha_symbols),
            "stable_candidate_symbols": list(self.stable_candidate_symbols),
            "deprecated_symbols": list(self.deprecated_symbols),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> APIStabilityMap:
        return cls(
            _str(data, "version"),
            _str_tuple(data, "experimental_symbols"),
            _str_tuple(data, "alpha_symbols"),
            _str_tuple(data, "stable_candidate_symbols"),
            _str_tuple(data, "deprecated_symbols"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def build_api_stability_map(
    version: str,
    public_symbols: tuple[str, ...],
    *,
    default_level: APIStabilityLevel = APIStabilityLevel.ALPHA,
) -> APIStabilityMap:
    symbols = tuple(sorted(set(public_symbols)))
    if default_level == APIStabilityLevel.EXPERIMENTAL:
        return APIStabilityMap(version, experimental_symbols=symbols)
    if default_level == APIStabilityLevel.STABLE_CANDIDATE:
        return APIStabilityMap(version, stable_candidate_symbols=symbols)
    if default_level == APIStabilityLevel.DEPRECATED:
        return APIStabilityMap(version, deprecated_symbols=symbols)
    return APIStabilityMap(version, alpha_symbols=symbols)


def validate_api_stability_map(
    stability_map: APIStabilityMap, public_symbols: tuple[str, ...]
) -> tuple[str, ...]:
    covered = set(stability_map.covered_symbols)
    return tuple(sorted(symbol for symbol in set(public_symbols) if symbol not in covered))


def validate_api_stability_map_against_exports(
    stability_map: APIStabilityMap, exported_symbols: tuple[str, ...]
) -> tuple[str, ...]:
    """Return stability-map coverage errors for exported GENESIS symbols."""

    exported = set(exported_symbols)
    buckets = (
        ("experimental", stability_map.experimental_symbols),
        ("alpha", stability_map.alpha_symbols),
        ("stable_candidate", stability_map.stable_candidate_symbols),
        ("deprecated", stability_map.deprecated_symbols),
    )
    membership: dict[str, list[str]] = {}
    for bucket_name, symbols in buckets:
        for symbol in symbols:
            membership.setdefault(symbol, []).append(bucket_name)
    errors: list[str] = []
    for symbol in sorted(exported - set(membership)):
        errors.append(f"missing_export:{symbol}")
    for symbol in sorted(set(membership) - exported):
        errors.append(f"unknown_symbol:{symbol}")
    for symbol, names in sorted(membership.items()):
        if len(names) > 1:
            errors.append(f"duplicate_symbol:{symbol}")
    return tuple(errors)


@dataclass(frozen=True, slots=True)
class CompatibilityPolicy:
    version: str
    minimum_python: str
    supported_python_versions: tuple[str, ...]
    deprecation_window: str
    backward_compatibility_notes: str = ""
    experimental_api_policy: str = "Alpha APIs may change with changelog notes."

    def __post_init__(self) -> None:
        if not self.version or not self.minimum_python or not self.deprecation_window:
            raise ConfigurationError(
                "CompatibilityPolicy version/minimum/deprecation_window required."
            )
        object.__setattr__(
            self, "supported_python_versions", tuple(sorted(self.supported_python_versions))
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "minimum_python": self.minimum_python,
            "supported_python_versions": list(self.supported_python_versions),
            "deprecation_window": self.deprecation_window,
            "backward_compatibility_notes": self.backward_compatibility_notes,
            "experimental_api_policy": self.experimental_api_policy,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> CompatibilityPolicy:
        return cls(
            _str(data, "version"),
            _str(data, "minimum_python"),
            _str_tuple(data, "supported_python_versions"),
            _str(data, "deprecation_window"),
            _str(data, "backward_compatibility_notes", ""),
            _str(data, "experimental_api_policy", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DocumentationAuditConfig:
    required_sections: tuple[str, ...]
    required_docs: tuple[str, ...] = ()
    section_aliases: tuple[tuple[str, tuple[str, ...]], ...] = ()
    require_citation_section: bool = True
    require_security_section: bool = True
    require_release_evidence_section: bool = True
    require_non_goals_section: bool = True
    require_examples_section: bool = True
    require_api_overview: bool = True

    @classmethod
    def mature_alpha(cls) -> DocumentationAuditConfig:
        return cls(
            required_sections=(
                "installation",
                "quickstart",
                "genesis alignment",
                "non-goals",
                "claim limitations",
                "api overview",
                "examples",
                "release evidence",
                "citation",
                "security",
                "limitations",
            ),
            required_docs=(
                "README.md",
                "docs/api.md",
                "docs/non_goals.md",
                "docs/release_checklist.md",
            ),
            section_aliases=(
                ("installation", ("installation", "install")),
                ("quickstart", ("quickstart", "quick start")),
                ("genesis alignment", ("genesis alignment", "genesis foundation kernel status")),
                (
                    "non-goals",
                    (
                        "non-goals",
                        "non goals",
                        "what this library is not",
                        "limitations and non-claims",
                    ),
                ),
                (
                    "claim limitations",
                    ("claim limitations", "limitations and non-claims", "non-claims"),
                ),
                ("api overview", ("api overview", "core api", "public api", "api")),
                ("examples", ("examples", "example")),
                (
                    "release evidence",
                    ("release evidence", "release checklist", "release-readiness"),
                ),
                ("citation", ("citation", "citation / references", "references")),
                ("security", ("security", "security policy", "security evidence")),
                ("limitations", ("limitations", "limitations and non-claims", "non-claims")),
            ),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "required_sections": list(self.required_sections),
            "required_docs": list(self.required_docs),
            "section_aliases": [
                {"section": section, "aliases": list(aliases)}
                for section, aliases in self.section_aliases
            ],
            "require_citation_section": self.require_citation_section,
            "require_security_section": self.require_security_section,
            "require_release_evidence_section": self.require_release_evidence_section,
            "require_non_goals_section": self.require_non_goals_section,
            "require_examples_section": self.require_examples_section,
            "require_api_overview": self.require_api_overview,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DocumentationAuditResult:
    attempted: bool
    succeeded: bool
    checked_docs: tuple[str, ...]
    missing_sections: tuple[str, ...]
    stale_sections: tuple[str, ...]
    claim_audit_digest: str
    api_coverage_digest: str = ""
    reasons: tuple[str, ...] = ()
    missing_docs: tuple[str, ...] = ()
    missing_sections_by_doc: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "checked_docs": list(self.checked_docs),
            "missing_sections": list(self.missing_sections),
            "stale_sections": list(self.stale_sections),
            "claim_audit_digest": self.claim_audit_digest,
            "api_coverage_digest": self.api_coverage_digest,
            "reasons": list(self.reasons),
            "missing_docs": list(self.missing_docs),
            "missing_sections_by_doc": list(self.missing_sections_by_doc),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> DocumentationAuditResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _str_tuple(data, "checked_docs"),
            _str_tuple(data, "missing_sections"),
            _str_tuple(data, "stale_sections"),
            _str(data, "claim_audit_digest", ""),
            _str(data, "api_coverage_digest", ""),
            _str_tuple(data, "reasons"),
            _str_tuple(data, "missing_docs"),
            _str_tuple(data, "missing_sections_by_doc"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def audit_documentation_sections(
    docs: Mapping[str, str],
    required_sections: tuple[str, ...] | None = None,
    claim_audit_digest: str = "",
    config: DocumentationAuditConfig | None = None,
) -> DocumentationAuditResult:
    config = config or DocumentationAuditConfig(
        required_sections=required_sections or (),
        required_docs=(),
        section_aliases=(),
        require_citation_section=False,
        require_security_section=False,
        require_release_evidence_section=False,
        require_non_goals_section=False,
        require_examples_section=False,
        require_api_overview=False,
    )
    combined = "\n".join(docs.values()).lower()
    checked = tuple(sorted(docs))
    missing_docs = tuple(sorted(doc for doc in config.required_docs if doc not in docs))
    missing_sections = tuple(
        sorted(
            section
            for section in config.required_sections
            if not _section_present(combined, section, config)
        )
    )
    missing_by_doc: list[str] = []
    for doc in sorted(docs):
        lowered = docs[doc].lower()
        for section in config.required_sections:
            if not _section_present(lowered, section, config) and doc.lower().endswith("readme.md"):
                missing_by_doc.append(f"{doc}:{section}")
    stale = tuple(
        sorted(
            phrase
            for phrase in (
                "proves artificial life",
                "proves open-ended discovery",
                "state of the art",
                "automatic report writer",
            )
            if phrase in combined
        )
    )
    reasons: list[str] = []
    if missing_docs:
        reasons.append("missing_docs")
    if missing_sections:
        reasons.append("missing_sections")
    if stale:
        reasons.append("stale_sections")
    return DocumentationAuditResult(
        True,
        not reasons,
        checked,
        missing_sections,
        stale,
        claim_audit_digest,
        "",
        tuple(reasons) if reasons else ("documentation_audit_passed",),
        missing_docs,
        tuple(sorted(missing_by_doc)),
    )


def _section_aliases(section: str, config: DocumentationAuditConfig) -> tuple[str, ...]:
    aliases: list[str] = [section.lower()]
    for name, values in config.section_aliases:
        if name.lower() == section.lower():
            aliases.extend(value.lower() for value in values)
    return tuple(dict.fromkeys(aliases))


def _section_present(text: str, section: str, config: DocumentationAuditConfig) -> bool:
    aliases = _section_aliases(section, config)
    return any(alias in text for alias in aliases)


@dataclass(frozen=True, slots=True)
class SecurityEvidenceRecord:
    check_name: str
    status: str
    external_tool: str = ""
    evidence_url_or_digest: str = ""
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.check_name or not self.status:
            raise ConfigurationError("SecurityEvidenceRecord check_name/status required.")
        if self.status not in {"PASS", "FAIL", "NOT RUN", "NOT COMPLETED", "NOT APPLICABLE"}:
            raise ConfigurationError("SecurityEvidenceRecord.status is invalid.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "check_name": self.check_name,
            "status": self.status,
            "external_tool": self.external_tool,
            "evidence_url_or_digest": self.evidence_url_or_digest,
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SecurityEvidenceRecord:
        return cls(
            _str(data, "check_name"),
            _str(data, "status"),
            _str(data, "external_tool", ""),
            _str(data, "evidence_url_or_digest", ""),
            _str_tuple(data, "limitations"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


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
