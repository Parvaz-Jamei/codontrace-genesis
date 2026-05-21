from __future__ import annotations

from codontrace.genesis import GenesisOrganism, Ribosome
from codontrace.genesis.ribosome import BrainTokenSource, CodonExecutionRecord
from codontrace.trace import Trace
from codontrace.world import World2D


def test_compiled_brain_source_map_and_execution_record_when_enabled() -> None:
    result = Ribosome.genesis_v0().translate("000001")
    first = result.compiled_brain.tokens[0]
    assert first.source is not None
    assert first.source.genome_pos == 0
    assert first.source.codon == first.bits

    organism = GenesisOrganism.from_bits(
        "org",
        "000001",
        initial_runtime_atp=10,
        execution_source_enabled=True,
    )
    trace = Trace()
    event = organism.step(World2D(3, 3), trace)
    record = event.world_delta["codon_execution_record"]
    assert record["source"]["codon"] == event.codon
    assert event.world_delta["codon_execution_record_digest"]
    restored = CodonExecutionRecord.from_dict(record)
    assert restored.source == BrainTokenSource.from_dict(record["source"])


def test_execution_source_map_disabled_by_default() -> None:
    organism = GenesisOrganism.from_bits("org", "000001", initial_runtime_atp=10)
    event = organism.step(World2D(3, 3), Trace())
    assert "codon_execution_record" not in event.world_delta
