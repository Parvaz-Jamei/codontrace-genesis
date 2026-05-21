from codontrace.genesis import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.substrate_runtime import (
    GenesisWorldState,
    SubstrateActionBridge,
    SubstrateRuntimeConfig,
)
from codontrace.world import World2D


def test_substrate_bridge_action_audit_and_manifest_source_of_truth():
    bridge = SubstrateActionBridge(SubstrateRuntimeConfig(source_of_truth="element_grid"))
    state = GenesisWorldState(World2D(3, 3), source_of_truth="world2d")
    new_state, audit = bridge.apply_action(state, "EAT_LUMEN", (1, 1))

    assert audit["Lu_consumption_attempted"] is True
    assert new_state.source_of_truth == "element_grid"
    assert new_state.element_grid is not None

    engine = GenesisEngine.from_spec(
        GenesisExperimentSpec(tick_count=1, substrate_bridge_mode="world2d_mirror")
    )
    result = engine.run_ticks()
    assert result.manifest.runtime_hashes["substrate_bridge_mode"] == "world2d_mirror"
