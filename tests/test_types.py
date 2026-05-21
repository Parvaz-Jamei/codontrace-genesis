from __future__ import annotations

from codontrace._types import JsonValue, Position


def test_internal_type_aliases_have_single_source() -> None:
    assert Position is not None
    assert JsonValue is not None
