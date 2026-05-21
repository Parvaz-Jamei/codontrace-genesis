from __future__ import annotations

from codontrace.codon import Codon, CodonTable
from codontrace.genesis.adf_runtime import ADFExecutionPolicy, ADFMacroDefinition, ADFMacroRegistry
from codontrace.genesis.artifacts import RawEventSchema
from codontrace.genesis.engine import _execution_source_digest
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.ribosome import Ribosome
from codontrace.trace import Trace
from codontrace.world import World2D


def _adf_organism() -> GenesisOrganism:
    table = CodonTable([Codon("000", "ADF_PAIR", 0.0)])
    registry = ADFMacroRegistry().register(
        ADFMacroDefinition(
            macro_id="ADF_PAIR",
            primitive_actions=("WAIT", "MOVE_EAST"),
            body_codons=("000", "001"),
        )
    )
    return GenesisOrganism.from_bits(
        "org-adf",
        "000",
        ribosome=Ribosome(table),
        execution_source_enabled=True,
        adf_macro_registry=registry,
        adf_execution_policy=ADFExecutionPolicy(max_expansion_length=4),
    )


def test_adf_expanded_each_primitive_has_source_record() -> None:
    trace = Trace()
    event = _adf_organism().step(World2D(4, 4), trace)

    records = event.world_delta["codon_execution_records"]
    assert isinstance(records, list)
    assert [record["resolved_action"] for record in records] == ["WAIT", "MOVE_EAST"]
    assert len(records) == 2
    assert all(record["source"]["macro_id"] == "ADF_PAIR" for record in records)
    assert all(record["source"]["macro_stack"] == ["ADF_PAIR"] for record in records)
    assert all(record["trace_event_ref"] for record in records)


def test_execution_source_digest_includes_all_adf_primitive_records() -> None:
    trace = Trace()
    event = _adf_organism().step(World2D(4, 4), trace)
    payload = event.to_dict()
    raw = RawEventSchema(0, "event", payload)
    full_digest = _execution_source_digest((raw,), enabled=True)

    delta = dict(payload["world_delta"])
    records = list(delta["codon_execution_records"])
    assert len(records) == 2
    delta["codon_execution_records"] = records[:1]
    payload_without_second = dict(payload)
    payload_without_second["world_delta"] = delta
    truncated_digest = _execution_source_digest(
        (RawEventSchema(0, "event", payload_without_second),), enabled=True
    )

    assert full_digest != truncated_digest
