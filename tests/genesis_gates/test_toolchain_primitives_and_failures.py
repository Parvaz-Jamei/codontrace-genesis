from codontrace.actions import ActionContext, collect_resource_primitive_handler
from codontrace.world import World2D


def test_collect_resource_primitive_missing_resource_has_schema_safe_failure_reason():
    world = World2D(width=3, height=3)
    ctx = ActionContext(
        agent_id="agent", position=(1, 1), codon_bits="000", action_name="COLLECT_RESOURCE_OBJECT", step_index=0, world=world
    )
    result = collect_resource_primitive_handler(ctx)
    assert result.status == "blocked"
    assert result.reason == "missing_resource"
    assert result.world_delta is not None
    assert result.world_delta["action_precondition_allowed"] is False
    assert result.world_delta["inventory_before"] == {}
    assert result.world_delta["inventory_after"] == {}
