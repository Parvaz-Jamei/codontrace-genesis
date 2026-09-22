"""Discovery-wire (qd_search) + ESP32 Moj-ه bridge tests.

Default-off wire must leave digests/behavior unchanged. Wire-on uses
RandomProposer with no network. ESP32 tests use SimEsp32Bridge only —
no fabricated hardware campaigns. ClaimGate ceiling stays honest.
"""

from __future__ import annotations

import pytest

from codontrace.claimgate.adapters.esp32_bridge import (
    MoveCommand,
    MqttEsp32Transport,
    SensorReading,
    SerialEsp32Transport,
    SimEsp32Bridge,
    STRDisparityResult,
    TransportEsp32Bridge,
    compute_str_disparity,
    parse_sensor_payload,
    str_stop_criterion_met,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.discovery_witness import CLAIM_CEILING_DISCOVERY_CANDIDATE
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.novelty_proposer import RandomProposer
from codontrace.genesis.qd_search import (
    DiscoveryWireConfig,
    QDDescriptorConfig,
    QDSearchConfig,
    QDSearchRunner,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def _evaluator(genome: str) -> tuple[float, dict[str, float]]:
    ones = genome.count("1")
    return float(ones), {"ones": float(ones), "length": float(len(genome))}


def _base_config(**kwargs: object) -> QDSearchConfig:
    params: dict[str, object] = {
        "descriptor_config": QDDescriptorConfig(
            ("ones",), {"ones": 4}, {"ones": 0.0}, {"ones": 4.0}
        ),
        "generations": 4,
        "offspring_per_generation": 2,
        "seed": 42,
    }
    params.update(kwargs)
    return QDSearchConfig(**params)  # type: ignore[arg-type]


def test_phase_a_life_loop_digest_pin_unchanged_by_wire_and_esp32() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_discovery_wire_default_off_omitted_from_config_digest() -> None:
    off = _base_config()
    assert off.discovery_wire.enabled is False
    assert "discovery_wire" not in off.to_dict()
    # Explicit disabled config must match implicit default digest.
    explicit = _base_config(discovery_wire=DiscoveryWireConfig(enabled=False))
    assert off.digest() == explicit.digest()


def test_discovery_wire_off_run_digest_matches_legacy_shape() -> None:
    config = _base_config()
    result = QDSearchRunner(config, _evaluator).run(["0000"])
    assert result.discovery_wire_events == ()
    assert "discovery_wire_events" not in result.to_dict()
    # Reproducible with seed (legacy pin/behavior).
    again = QDSearchRunner(config, _evaluator).run(["0000"])
    assert result.digest() == again.digest()


def test_discovery_wire_on_with_random_proposer_no_network() -> None:
    wire = DiscoveryWireConfig(
        enabled=True,
        propose_every_n_generations=2,
        scale="S1",
        max_admissions_per_hook=1,
    )
    config = _base_config(discovery_wire=wire, generations=4)
    assert "discovery_wire" in config.to_dict()
    proposer = RandomProposer(seed=99)
    result = QDSearchRunner(config, _evaluator, proposer=proposer).run(["0000", "1111"])
    # Generations 1 and 3 (0-indexed 1, 3) fire when every 2 gens.
    assert len(result.discovery_wire_events) == 2
    for event in result.discovery_wire_events:
        assert event.candidate_id
        assert event.audit_digest
        assert event.claim_ceiling in {
            "runtime_observation",
            CLAIM_CEILING_DISCOVERY_CANDIDATE,
        }
        # Admit only when ceiling policy allows (accepted + discovery ceiling).
        if event.admitted_to_archive:
            assert event.accepted is True
            assert event.claim_ceiling == CLAIM_CEILING_DISCOVERY_CANDIDATE
            assert event.innovation_id is not None
    # Enabled wire changes digest vs default-off (expected).
    off = QDSearchRunner(_base_config(), _evaluator).run(["0000", "1111"])
    assert result.digest() != off.digest()


def test_discovery_wire_invalid_config_raises() -> None:
    with pytest.raises(ConfigurationError):
        DiscoveryWireConfig(enabled=True, propose_every_n_generations=0)
    with pytest.raises(ConfigurationError):
        DiscoveryWireConfig(enabled=True, scale="S9")  # type: ignore[arg-type]


# --- ESP32 Moj-ه -----------------------------------------------------------


def test_sim_esp32_bridge_move_and_sense() -> None:
    bridge = SimEsp32Bridge(distance=1.0, light=0.4)
    bridge.move(0.2, 0.2, 1.0)
    reading = bridge.read_sensor()
    assert isinstance(reading, SensorReading)
    assert reading.distance >= 0.0
    assert reading.light == pytest.approx(0.4)
    assert len(bridge.history) == 1
    assert isinstance(bridge.history[0], MoveCommand)


def test_parse_sensor_payload_pydantic_boundary() -> None:
    reading = parse_sensor_payload({"distance": 1.5, "light": 0.2, "bump": True})
    assert reading.bump is True
    with pytest.raises(ConfigurationError):
        parse_sensor_payload({"distance": -1.0, "light": 0.1})
    with pytest.raises(ConfigurationError):
        parse_sensor_payload({"distance": 1.0})  # missing light


def test_serial_and_mqtt_transports_fail_closed() -> None:
    with pytest.raises(ConfigurationError, match="fails closed"):
        SerialEsp32Transport().connect()
    with pytest.raises(ConfigurationError, match="fails closed"):
        MqttEsp32Transport().connect()
    with pytest.raises(ConfigurationError):
        TransportEsp32Bridge().move(0.1, 0.1, 0.1)
    with pytest.raises(ConfigurationError):
        TransportEsp32Bridge().read_sensor()


def test_str_disparity_synthetic_and_digest_stable() -> None:
    # Synthetic numbers only — not a hardware campaign.
    a = compute_str_disparity(
        {"distance": 1.0, "light": 0.5},
        {"distance": 0.5, "light": 0.5},
        transfer_method="none",
        notes=("synthetic",),
    )
    b = compute_str_disparity(
        {"distance": 1.0, "light": 0.5},
        {"distance": 0.5, "light": 0.5},
        transfer_method="none",
        notes=("synthetic",),
    )
    assert a.n_pairs == 2
    assert a.mean_abs_rel_error > 0.0
    assert a.digest() == b.digest()
    restored = STRDisparityResult(
        metric_names=a.metric_names,
        sim_values=a.sim_values,
        physical_values=a.physical_values,
        per_metric_abs_rel_error=a.per_metric_abs_rel_error,
        mean_abs_rel_error=a.mean_abs_rel_error,
        n_pairs=a.n_pairs,
        transfer_method=a.transfer_method,
        notes=a.notes,
        record_digest=a.record_digest,
    )
    assert restored.digest() == a.digest()


def test_str_stop_criterion_goal_section_11() -> None:
    # Before budget: never stop.
    assert (
        str_stop_criterion_met(
            n_real_tests=5,
            disparity_with_transfer=0.9,
            disparity_without_transfer=0.1,
        )
        is False
    )
    # After 20 real tests, transfer not better → stop.
    assert (
        str_stop_criterion_met(
            n_real_tests=20,
            disparity_with_transfer=0.40,
            disparity_without_transfer=0.35,
        )
        is True
    )
    # After 20, transfer better → continue.
    assert (
        str_stop_criterion_met(
            n_real_tests=20,
            disparity_with_transfer=0.20,
            disparity_without_transfer=0.35,
        )
        is False
    )


def test_docs_and_firmware_safety_markers_exist() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    doc = (root / "docs/design/ESP32_BRIDGE_v0.1.md").read_text(encoding="utf-8")
    assert "20 real tests" in doc
    assert "Zero claim that physical robots ran" in doc or "physical robots ran" in doc
    fw = (root / "firmware/esp32/main.py").read_text(encoding="utf-8")
    assert "Separate motor PSU" in fw or "Separate motor" in fw
    assert "Physical e-stop" in fw or "e-stop" in fw
    assert "DISARMED" in fw or "disarmed" in fw.lower()
