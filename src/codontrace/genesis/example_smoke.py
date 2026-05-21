"""Example smoke-test contracts for GENESIS release validation.

This module defines library objects and optional helper functions only. Nothing
runs at import time, no CLI is exposed, and no files are written.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class ExampleSmokeCase:
    """Declarative example smoke contract."""

    name: str
    path: str
    expected_imports: tuple[str, ...] = ()
    expected_no_file_output: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.path:
            msg = "ExampleSmokeCase.name and path must not be empty."
            raise ConfigurationError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "path": self.path,
            "expected_imports": list(self.expected_imports),
            "expected_no_file_output": self.expected_no_file_output,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ExampleSmokeCase:
        return cls(
            name=_str(data, "name"),
            path=_str(data, "path"),
            expected_imports=_str_tuple(data, "expected_imports"),
            expected_no_file_output=_bool(data, "expected_no_file_output", True),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExampleSmokeResult:
    """Result object for optional caller-run example smoke checks."""

    attempted: bool
    succeeded: bool
    case_name: str
    reason: str
    stdout_digest: str | None = None
    created_files_count: int = 0
    executed: bool = False
    execution_status: str = "not_attempted"
    success_status: str = "not_attempted"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "case_name": self.case_name,
            "reason": self.reason,
            "stdout_digest": self.stdout_digest,
            "created_files_count": self.created_files_count,
            "executed": self.executed,
            "execution_status": self.execution_status,
            "success_status": self.success_status,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ExampleSmokeResult:
        return cls(
            attempted=_bool(data, "attempted", False),
            succeeded=_bool(data, "succeeded", False),
            case_name=_str(data, "case_name"),
            reason=_str(data, "reason"),
            stdout_digest=_optional_str(data.get("stdout_digest"), "stdout_digest"),
            created_files_count=_int(data, "created_files_count", 0),
            executed=_bool(data, "executed", False),
            execution_status=_str(data, "execution_status", "not_attempted"),
            success_status=_str(data, "success_status", "not_attempted"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def describe_example_smoke_cases(
    cases: Sequence[ExampleSmokeCase],
) -> tuple[ExampleSmokeResult, ...]:
    """Return non-executing smoke descriptions for callers to inspect."""

    return tuple(
        ExampleSmokeResult(
            attempted=False,
            succeeded=False,
            case_name=case.name,
            reason="contract_only_not_executed",
            stdout_digest=None,
            created_files_count=0,
            executed=False,
            execution_status="contract_only_not_executed",
            success_status="not_attempted",
        )
        for case in cases
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_str(value: object, key: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be a string or None."
        raise ConfigurationError(msg)
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        msg = f"{key} must be a list of strings."
        raise ConfigurationError(msg)
    return tuple(str(item) for item in raw)
