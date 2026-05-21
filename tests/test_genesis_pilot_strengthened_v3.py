from __future__ import annotations

import json
from pathlib import Path

from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_toolchain_pilot_has_successful_end_to_end_chain(tmp_path: Path) -> None:
    from examples.genesis_toolchain_pilot import run

    paths = run(tmp_path)
    summary = json.loads(Path(paths["summary"]).read_text(encoding="utf-8"))
    records = _load_jsonl(Path(paths["records"]))
    assert summary["chain_success"] is True
    assert summary["claim_allowed_for_tool_use"] is True
    assert summary["successful_tool_actions"] >= 3
    assert summary["tool_reward_total"] > 0.0
    assert "COLLECT_RESOURCE" in summary["successful_chain_actions"]
    assert "DEPOSIT_RESOURCE" in summary["successful_chain_actions"]
    assert any(
        item["allowed"] is True
        and (
            item["inventory_before"] != item["inventory_after"]
            or item["world_state_before_digest"] != item["world_state_after_digest"]
            or float(item["reward_delta"] or 0.0) > 0.0
        )
        for item in records
    )


def test_toolchain_records_inventory_world_reward_and_failure_reasons(tmp_path: Path) -> None:
    from examples.genesis_toolchain_pilot import run

    paths = run(tmp_path)
    records = _load_jsonl(Path(paths["records"]))
    for item in records:
        assert "record_digest" in item
        assert "effect_digest" in item
        assert "precondition_passed" in item
        assert "world_state_before_digest" in item
        assert "world_state_after_digest" in item
        if item["allowed"] is True:
            assert item["blocked_reason"] is None
            assert item["precondition_passed"] is True
            assert (
                item["inventory_before"] != item["inventory_after"]
                or item["world_state_before_digest"] != item["world_state_after_digest"]
                or float(item["reward_delta"] or 0.0) != 0.0
            )
        else:
            assert item["blocked_reason"] in {
                "missing_resource",
                "missing_required_item",
                "recipe_inputs_missing",
                "target_cell_locked",
                "terrain_requirement_missing",
                "resource_depleted",
                "inventory_capacity_reached",
                "wrong_target",
                "out_of_range",
                "action_disabled_by_config",
                "no_toolchain_action_observed",
                "unknown",
            }


def test_toolchain_pilot_replay_is_deterministic(tmp_path: Path) -> None:
    from examples.genesis_toolchain_pilot import run

    first = run(tmp_path / "a")
    second = run(tmp_path / "b")
    assert Path(first["summary"]).read_text(encoding="utf-8") == Path(second["summary"]).read_text(encoding="utf-8")
    assert Path(first["records"]).read_text(encoding="utf-8") == Path(second["records"]).read_text(encoding="utf-8")


def test_capsule_behavioral_adoption_changes_target_digest_and_positive_utility(tmp_path: Path) -> None:
    from examples.genesis_capsule_utility_pilot import run

    paths = run(tmp_path)
    summary = json.loads(Path(paths["summary"]).read_text(encoding="utf-8"))
    records = _load_jsonl(Path(paths["records"]))
    positive = [
        item
        for item in records
        if item["adoption_success"] is True
        and item["state_changed"] is True
        and float(item["utility_delta"] or 0.0) > 0.0
        and item["target_behavior_digest_before"] != item["target_behavior_digest_after"]
        and item["behavior_digest_before"] == item["target_behavior_digest_before"]
        and item["behavior_digest_after"] == item["target_behavior_digest_after"]
        and item["utility_protocol_digest"]
    ]
    assert summary["claim_allowed_for_capsule_usefulness"] is True
    assert summary["positive_utility_records"] >= 1
    assert positive
    assert all(item["source_fitness_status"] in {"measured", "last_known"} for item in positive)
    assert all("source_fitness_status_original" in item for item in positive)


def test_capsule_utility_replay_is_deterministic(tmp_path: Path) -> None:
    from examples.genesis_capsule_utility_pilot import run

    first = run(tmp_path / "a")
    second = run(tmp_path / "b")
    assert Path(first["summary"]).read_text(encoding="utf-8") == Path(second["summary"]).read_text(encoding="utf-8")
    assert Path(first["records"]).read_text(encoding="utf-8") == Path(second["records"]).read_text(encoding="utf-8")


def test_social_non_capsule_event_has_resource_or_fitness_delta(tmp_path: Path) -> None:
    from examples.genesis_social_partner_pilot import run

    paths = run(tmp_path)
    summary = json.loads(Path(paths["summary"]).read_text(encoding="utf-8"))
    events = _load_jsonl(Path(paths["records"]))
    non_capsule = [e for e in events if not str(e["interaction_type"]).startswith("capsule")]
    assert summary["claim_allowed_for_social_interaction"] is True
    assert summary["claim_allowed_for_social_intelligence"] is False
    assert summary["non_capsule_social_events"] >= 1
    assert summary["distinct_partner_pairs"] >= 1
    assert summary["resource_or_fitness_delta_events"] >= 1
    assert non_capsule
    for event in non_capsule:
        assert event["source_organism_id"] != event["target_organism_id"]
        assert event["target_organism_id"] != "environment"
        assert event["interaction_type"] != "capsule_interaction"
        assert (
            float(event["resource_delta_source"] or 0.0) != 0.0
            or float(event["resource_delta_target"] or 0.0) != 0.0
            or float(event["fitness_delta_source"] or 0.0) != 0.0
            or float(event["fitness_delta_target"] or 0.0) != 0.0
            or bool(event["world_state_delta"])
        )


def test_social_events_exclude_environment_target_from_social_metrics() -> None:
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.social_partner_pilot_world(seed=3)).run_ticks()
    assert result.partner_interaction_records
    assert all(getattr(item, "target_organism_id", "") != "environment" for item in result.partner_interaction_records)


def test_release_docs_reference_current_phase3_artifact_and_phase1_base() -> None:
    evidence = Path("RELEASE_EVIDENCE.md").read_text(encoding="utf-8")
    matrix = Path("docs/FEATURE_WIRING_MATRIX.md").read_text(encoding="utf-8")
    assert "codontrace-0.3.0a1-release-bundle.zip" in evidence
    assert "phase1-strong-core" not in evidence
    assert "deadcode-wiring" not in evidence
    assert "Toolchain" in matrix and "chain_success=True" in matrix
    assert "Capsule usefulness" in matrix and "positive_utility_observed" in matrix
    assert "Social interaction" in matrix and "non_capsule_social_events" in matrix
