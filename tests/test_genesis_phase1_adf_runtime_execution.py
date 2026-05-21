from __future__ import annotations

from codontrace.actions import ActionContext, ActionResult, default_action_registry
from codontrace.codon import Codon, CodonTable
from codontrace.genesis import (
    ADFCompressionScore,
    ADFPattern,
    ADFProposal,
    GenesisCodonTable,
    GenesisOrganism,
    Ribosome,
    extend_codon_table_with_adfs,
)
from codontrace.specs import CodonTableSpec, GenomeSpec
from codontrace.trace import Trace
from codontrace.world import World2D


def _proposal(bits: str = "1000") -> ADFProposal:
    pattern = ADFPattern("p", ("WAIT", "MOVE_TOWARD"), ("000", "011"), 2, 3, 0, 1, ("org",), ("r",))
    score = ADFCompressionScore("p", 6, 3, 3.0, 3, None, 0.0, True, ("thresholds_passed",))
    return ADFProposal("prop", pattern, score, bits, f"ADF_{bits}", 0.2, status="accepted")


def test_adf_four_bit_codon_uses_longest_match_not_three_bit_prefix() -> None:
    table = extend_codon_table_with_adfs(GenesisCodonTable.default_v0(), [_proposal("1000")])
    result = Ribosome(table).translate("1000")

    assert [(token.bits, token.action) for token in result.compiled_brain.tokens] == [
        ("1000", "ADF_1000")
    ]
    assert result.skipped_tail_bits == ""


def test_mixed_base_and_adf_genome_decodes_deterministically() -> None:
    table = extend_codon_table_with_adfs(GenesisCodonTable.default_v0(), [_proposal("1000")])
    result = Ribosome(table).translate("0001000001")

    assert [(token.bits, token.action) for token in result.compiled_brain.tokens] == [
        ("000", "WAIT"),
        ("1000", "ADF_1000"),
        ("001", "SENSE_FOOD"),
    ]
    assert (
        result.compiled_brain.digest()
        == Ribosome(table).translate("0001000001").compiled_brain.digest()
    )


def test_prefix_overlap_policy_is_deterministic_longest_match() -> None:
    spec = CodonTableSpec(GenomeSpec(codon_width=2, alphabet=("0", "1"), name="binary2"))
    table = CodonTable(
        [
            Codon.from_sequence("10", "SHORT", 0.0, spec=spec.genome_spec),
            Codon("1000", "LONG", 0.0),
        ],
        spec=spec,
    )

    result = Ribosome(table).translate("1000")

    assert [(token.bits, token.action) for token in result.compiled_brain.tokens] == [
        ("1000", "LONG")
    ]


def test_genesis_organism_executes_adf_token_in_trace() -> None:
    table = extend_codon_table_with_adfs(GenesisCodonTable.default_v0(), [_proposal("1000")])
    ribosome = Ribosome(table)

    def adf_handler(ctx: ActionContext) -> ActionResult:
        return ActionResult.executed(
            reason="adf_executed",
            position_after=ctx.position,
            world_delta={"adf_runtime": True},
        )

    organism = GenesisOrganism.from_bits(
        "org", "0001000", initial_runtime_atp=5.0, ribosome=ribosome
    )
    organism.action_registry = default_action_registry().extend("ADF_1000", adf_handler)
    trace = Trace()
    organism.step(World2D(2, 2), trace)
    event = organism.step(World2D(2, 2), trace)

    assert event.codon == "1000"
    assert event.action == "ADF_1000"
    assert event.status == "executed"
    assert event.world_delta["adf_runtime"] is True
