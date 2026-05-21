from codontrace.genesis import AliveGateResult, describe_behavior
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis import GenesisEngine
from codontrace.trace import Trace, TraceEvent


def _trace_with_partner_event():
    trace = Trace()
    trace.append(TraceEvent(
        step=0,
        agent_id="org-a",
        codon="000",
        action="EAT_LUMEN",
        atp_before=1.0,
        atp_after=2.0,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta={"target_organism_id": "org-b", "resource_credit": 1.0},
    ))
    return trace


def test_behavior_descriptor_counts_non_capsule_social_events():
    descriptor = describe_behavior(
        _trace_with_partner_event(),
        AliveGateResult(True, 1, 1, 0, 0.0, 2.0, 0, 0, ()),
        social_interaction_count=1,
        partner_interaction_count=1,
    )
    assert descriptor.capsule_read_count == 0
    assert descriptor.social_interaction_count == 1
    assert descriptor.partner_interaction_count == 1


def test_social_partner_descriptor_matches_result_social_records():
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.social_partner_pilot_world(seed=1, tick_count=3)).run_ticks()
    assert result.social_interaction_records
    assert sum(d.social_interaction_count for d in result.behavior_descriptors) >= len(result.social_interaction_records)


def test_qd_descriptor_receives_nonzero_social_dimension_when_social_events_exist():
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.social_partner_pilot_world(seed=1, tick_count=3)).run_ticks()
    assert any(getattr(d, "social_interaction_count", 0) > 0 for d in result.behavior_descriptors)
