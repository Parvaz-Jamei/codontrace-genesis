from __future__ import annotations

import pytest

from codontrace import Action, Codon, CodonTable


def test_default_minimal_mapping_is_complete() -> None:
    table = CodonTable.default_minimal()
    assert table.decode("000").action == Action.WAIT
    assert table.decode("111").action == Action.COLLECT_RESOURCE
    assert len(table.actions()) == 8


def test_unknown_codon_fails_clearly() -> None:
    with pytest.raises(KeyError):
        CodonTable.default_minimal().decode("222")


def test_custom_codon_table_extend_does_not_mutate_original() -> None:
    base = CodonTable([Codon("000", Action.WAIT, 0.1)])
    extended = base.extend(Codon("001", Action.SENSE_RESOURCE, 0.4))
    assert not base.validate("001")
    assert extended.validate("001")
    assert [codon.bits for codon in extended.actions()] == ["000", "001"]


def test_codon_table_has_no_mutable_register_method() -> None:
    assert not hasattr(CodonTable.default_minimal(), "register")
