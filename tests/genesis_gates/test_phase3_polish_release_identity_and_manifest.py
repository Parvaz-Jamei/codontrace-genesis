from __future__ import annotations

from pathlib import Path

import codontrace
from codontrace.codon import Codon, CodonTable
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.ribosome import Ribosome


def test_release_identity_is_a25_unified_runtime() -> None:
    assert codontrace.__version__ == "0.3.0a1"


def test_manifest_hashes_use_real_codon_table_and_genome_spec() -> None:
    base = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1, seed=7)).run_ticks()
    custom_table = CodonTable.genesis_v0().extend(Codon("1000", "ADF_1000", 0.2, "test ADF action"))
    custom = GenesisEngine.from_spec(
        GenesisExperimentSpec(
            genome_bits=("1000",),
            tick_count=1,
            seed=7,
            ribosome=Ribosome(codon_table=custom_table, codon_table_version="test_adf"),
            codon_table=custom_table,
        )
    ).run_ticks()

    assert custom.manifest.codon_table_hash != "genesis_v0"
    assert custom.manifest.genome_spec_hash != "default_from_ribosome"
    assert custom.manifest.codon_table_hash != base.manifest.codon_table_hash
    assert custom.manifest.adf_vocabulary_hash != base.manifest.adf_vocabulary_hash


def test_replay_is_deterministic_for_same_spec_and_seed() -> None:
    spec = GenesisExperimentSpec(tick_count=2, seed=123)
    first = GenesisEngine.from_spec(spec).run_ticks()
    second = GenesisEngine.from_spec(spec).run_ticks()

    assert first.replay_bundle.digest() == second.replay_bundle.digest()
    assert first.manifest.digest() == second.manifest.digest()



def test_no_stale_producer_version_in_official_examples() -> None:
    stale = "codontrace-prepublish-pilot-audited"
    examples = (
        "examples/genesis_evolution_pilot.py",
        "examples/genesis_qd_selection_pilot.py",
        "examples/genesis_capsule_utility_pilot.py",
        "examples/genesis_memory_delayed_reward_pilot.py",
        "examples/genesis_toolchain_pilot.py",
        "examples/genesis_social_partner_pilot.py",
    )
    for example in examples:
        text = Path(example).read_text(encoding="utf-8")
        assert stale not in text
        assert "RELEASE_LABEL" in text


def test_official_qd_pilot_manifest_uses_central_release_label(tmp_path) -> None:
    import json

    from codontrace.genesis import RELEASE_LABEL
    from examples import genesis_qd_selection_pilot

    outputs = genesis_qd_selection_pilot.run(tmp_path)
    manifest = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
    assert manifest["producer_version"] == RELEASE_LABEL


def test_phase2_hashes_do_not_seed_replay_with_placeholder_claim_gate_digest() -> None:
    import inspect

    from codontrace.genesis import engine

    source = inspect.getsource(engine._phase2_hashes)
    assert "overclaims_rejected" not in source
    assert "claim_gate_decision_digest" not in source
    assert "phase2_claim_decision_digest" not in source
