import pytest

from codontrace.codon import Codon, CodonTable
from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    ADFCompressionScore,
    ADFMacro,
    ADFPattern,
    ADFProposal,
    GenesisCodonTable,
    expand_adf_macro,
    extend_codon_table_with_adfs,
    macro_from_proposal,
)


def _proposal(bits="1000", status="accepted"):
    pattern = ADFPattern("p", ("WAIT", "MOVE_TOWARD"), ("000", "011"), 2, 3, 0, 1, ("org",), ("r",))
    score = ADFCompressionScore("p", 6, 3, 3.0, 3, None, 0.0, True, ("thresholds_passed",))
    return ADFProposal("prop", pattern, score, bits, "ADF_1000", 0.2, status=status)


def test_base_table_unchanged_and_accepted_adf_extends():
    base = GenesisCodonTable.default_v0()
    extended = extend_codon_table_with_adfs(base, [_proposal()])
    assert len(base.actions()) == 8
    assert extended.decode("1000").action_name == "ADF_1000"


def test_collision_rejected():
    base = CodonTable([Codon("1000", "EXISTING", 0.0)])
    with pytest.raises(ConfigurationError):
        extend_codon_table_with_adfs(base, [_proposal(bits="1000")])


def test_macro_expansion_is_traceable_and_no_dynamic_code():
    proposal = _proposal()
    macro = macro_from_proposal(proposal)
    result = expand_adf_macro("ADF_1000", [macro])
    assert isinstance(macro, ADFMacro)
    assert result.expanded
    assert result.expanded_actions == ("WAIT", "MOVE_TOWARD")
    assert result.blocked_reason is None
