from __future__ import annotations

from codontrace import SemanticGenome, WhiteBoxAgent


def test_white_box_agent_quick_factory_creates_valid_agent() -> None:
    agent = WhiteBoxAgent.quick(
        genome=["101", "111", "000"],
        atp=5.0,
        position=(1, 1),
    )

    assert agent.id == "agent-1"
    assert agent.position == (1, 1)
    assert agent.atp_account.current_atp == 5.0
    assert agent.genome.to_codons() == ("101", "111", "000")


def test_white_box_agent_quick_accepts_existing_semantic_genome() -> None:
    genome = SemanticGenome.from_codons(["000", "101"])
    agent = WhiteBoxAgent.quick(genome=genome, agent_id="custom")

    assert agent.id == "custom"
    assert agent.genome is genome


def test_white_box_agent_quick_accepts_compact_genome_string() -> None:
    agent = WhiteBoxAgent.quick(genome="101111000", initial_atp=6.0)

    assert agent.genome.to_codons() == ("101", "111", "000")
    assert agent.atp_account.current_atp == 6.0


def test_white_box_agent_quick_rejects_both_atp_names() -> None:
    import pytest

    from codontrace import ConfigurationError

    with pytest.raises(ConfigurationError, match="Provide either initial_atp or atp"):
        WhiteBoxAgent.quick(genome="000", initial_atp=5.0, atp=4.0)
