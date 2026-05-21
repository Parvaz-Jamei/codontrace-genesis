from __future__ import annotations

import pytest

from codontrace.genesis.replay_integrity import ReplayDigestClassPolicy, resolve_class_path


def test_resolve_class_path_rejects_unqualified_name() -> None:
    with pytest.raises(ValueError, match="no module separator"):
        resolve_class_path("NotAQualifiedClass")


def test_resolve_class_path_rejects_missing_class_name() -> None:
    with pytest.raises(ValueError, match="Invalid class path"):
        resolve_class_path("codontrace.genesis.")


def test_resolve_class_path_rejects_missing_module_name() -> None:
    with pytest.raises(ValueError, match="Invalid class path"):
        resolve_class_path(".Something")


def test_resolve_class_path_imports_valid_class() -> None:
    assert (
        resolve_class_path("codontrace.genesis.replay_integrity.ReplayDigestClassPolicy")
        is ReplayDigestClassPolicy
    )
