"""ESP32 Moj-ه ``SensorReading`` as swarm channels with ``contracts.channels`` descriptors.

The firmware reports ``distance`` and ``light`` as uncalibrated device values
and ``bump`` as a switch (``firmware/esp32/main.py``), so the descriptors say
``measurement_model='raw'`` and carry the source unit the caller names
(default ``device_unit``); no physical unit is invented. A calibration is added
by the caller as an explicit ``normalization`` with its own evidence id.
``SensorReading`` itself is unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace.contracts.channels import normalize_sample, validate_descriptor
from codontrace.contracts.wire_validation import identifier
from codontrace.swarm.devices.esp32 import SensorReading

__all__ = ['ESP32_CHANNEL_FIELDS', 'esp32_channels', 'esp32_samples']

ESP32_CHANNEL_FIELDS = ('distance', 'light', 'bump')


def esp32_channels(*, config_id: str, source_unit: str = 'device_unit',
                   normalization: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Channel definitions (quantity, unit, descriptor) for the three reading fields."""
    identifier(config_id)
    normalization = dict(normalization or {})
    if set(normalization) - {'distance', 'light'}:
        raise ValueError('normalization is only defined for distance and light')
    out: dict[str, dict[str, Any]] = {}
    for field in ESP32_CHANNEL_FIELDS:
        if field == 'bump':
            d: dict[str, Any] = {'value_type': 'boolean', 'measurement_model': 'raw', 'feature_id': 'esp32_bump',
                                 'source_unit': 'switch', 'config_id': config_id}
            unit = 'switch'
        else:
            d = {'value_type': 'scalar', 'measurement_model': 'raw', 'feature_id': f'esp32_{field}',
                 'source_unit': source_unit, 'config_id': config_id}
            unit = source_unit
            if field in normalization:
                d['normalization'] = dict(normalization[field])
                unit = d['normalization']['output_unit']
        out[field] = {'quantity': field, 'unit': unit, 'descriptor': validate_descriptor(d)}
    return out


def esp32_samples(reading: SensorReading, channels: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Normalized samples (``contracts.channels.normalize_sample``) for one reading."""
    if not isinstance(reading, SensorReading):
        raise TypeError('SensorReading required')
    values = reading.to_dict()
    out = {}
    for field in ESP32_CHANNEL_FIELDS:
        channel = dict(channels[field])
        payload = {'value': values[field], 'valid': True, 'status': 'ok',
                   'config_id': channel['descriptor']['config_id']}
        out[field] = normalize_sample(payload, channel)
    return out
