"""P10: STR in genesis.transferability, swarm.devices / swarm.adapters ESP32 surfaces, shared MQTT setup."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from codontrace.claimgate.adapters import esp32_bridge
from codontrace.genesis import transferability
from codontrace.swarm.adapters.esp32 import esp32_channels, esp32_samples
from codontrace.swarm.devices import esp32
from codontrace.swarm.transport import mqtt_session

# compute_str_disparity on this input at refactor/engine-integration-p9 (09ef212).
STR_DIGEST_P9 = 'e2ab1b30af69935392cdd755c1487cf0913b9cedab2218fc9ab63d3e667db92c'


def test_shim_reexports_the_same_objects():
    for name in esp32.__all__:
        assert getattr(esp32_bridge, name) is getattr(esp32, name)
    for name in transferability.__all__:
        assert getattr(esp32_bridge, name) is getattr(transferability, name)
    assert sorted(esp32_bridge.__all__) == sorted([*esp32.__all__, *transferability.__all__])
    from codontrace.claimgate import adapters
    assert adapters.SensorReading is esp32.SensorReading
    assert adapters.STRDisparityResult is transferability.STRDisparityResult


def test_str_record_is_unchanged():
    r = transferability.compute_str_disparity({'a': 1.0, 'b': 2.5, 'c': 0.0}, {'a': 0.8, 'b': 3.0, 'd': 1.0},
                                              transfer_method='none', notes=('n',))
    assert r.record_digest == STR_DIGEST_P9 and r.mean_abs_rel_error == 0.183333333333
    assert transferability.STRDisparityResult(**{**r.to_dict()}).record_digest == STR_DIGEST_P9


def test_replay_registry_points_at_the_engine_module():
    from codontrace.genesis.replay_integrity import _DIGEST_FIELDS_BY_CLASS
    assert _DIGEST_FIELDS_BY_CLASS['codontrace.genesis.transferability.STRDisparityResult'] == ('record_digest',)
    assert not [k for k in _DIGEST_FIELDS_BY_CLASS if 'esp32' in k]


def test_loopback_firmware_path_still_resolves():
    transport = esp32.LoopbackEsp32Transport()
    transport.connect()
    transport.set_sim_sensors(1.5, 0.25, True)
    reply = json.loads(transport.transact(json.dumps({'cmd': 'sense'})))
    assert esp32.parse_sensor_payload(reply) == esp32.SensorReading(1.5, 0.25, True)


def test_mqtt_transport_fails_closed_with_the_same_messages():
    with pytest.raises(Exception, match='fails closed: no broker configured'):
        esp32.MqttEsp32Transport().connect()
    t = esp32.MqttEsp32Transport(broker_url='mqtt://x', allow_connect=True)
    expected = 'broker connect not available' if mqtt_session.paho_available() else 'paho-mqtt not available'
    with pytest.raises(Exception, match=expected):
        t.connect()


def test_session_properties_and_client_setup(monkeypatch):
    mqtt = pytest.importorskip('paho.mqtt.client')
    assert mqtt_session.session_expiry_properties(None, 'genesis-x') is None
    with pytest.raises(ValueError, match='1..604800'):
        mqtt_session.session_expiry_properties(0, 'stable')
    with pytest.raises(ValueError, match='1..604800'):
        mqtt_session.session_expiry_properties(True, 'stable')
    with pytest.raises(ValueError, match='explicit stable client_id'):
        mqtt_session.session_expiry_properties(60, 'genesis-abc')
    assert mqtt_session.session_expiry_properties(60, 'stable').SessionExpiryInterval == 60
    calls = []

    class Client:
        def __init__(self, *args, **kwargs): calls.append(('client', args, kwargs))
        def reconnect_delay_set(self, **kwargs): calls.append(('backoff', kwargs))
        def username_pw_set(self, *args): calls.append(('auth', args))
        def tls_set(self, **kwargs): calls.append(('tls', kwargs))
    monkeypatch.setattr(mqtt, 'Client', Client)
    mqtt_session.mqtt_v5_client('cid', username='u', password='p', ca_file=None)
    assert [c[0] for c in calls] == ['client', 'backoff', 'auth', 'tls']
    assert calls[0][2] == {'client_id': 'cid', 'protocol': mqtt.MQTTv5, 'manual_ack': True}
    assert calls[1][1] == {'min_delay': 1, 'max_delay': 60}


def test_reading_maps_to_described_channels():
    channels = esp32_channels(config_id='cfg1')
    assert {k: v['descriptor']['value_type'] for k, v in channels.items()} == \
        {'distance': 'scalar', 'light': 'scalar', 'bump': 'boolean'}
    assert all(v['descriptor']['measurement_model'] == 'raw' for v in channels.values())
    samples = esp32_samples(esp32.SensorReading(2.0, 0.5, True), channels)
    assert samples['distance']['value'] == 2.0 and samples['bump']['value'] is True
    assert samples['light']['source_unit'] == 'device_unit' and len(samples['light']['descriptor_digest']) == 64
    cal = esp32_channels(config_id='cfg1', normalization={'distance': {
        'method': 'affine', 'output_unit': 'm', 'evidence_id': 'cal1', 'scale': 0.01, 'offset': 0.0}})
    assert cal['distance']['unit'] == 'm'
    assert esp32_samples(esp32.SensorReading(200.0, 0.5), cal)['distance']['value'] == 2.0
    with pytest.raises(ValueError):
        esp32_channels(config_id='cfg1', normalization={'bump': {}})
    with pytest.raises(TypeError):
        esp32_samples(SimpleNamespace(distance=1, light=1, bump=False), channels)
