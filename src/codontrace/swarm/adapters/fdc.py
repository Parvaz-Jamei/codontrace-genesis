"""Host-side mapping of FDCxCapSense readings (TI FDC1004 / FDC2x1x) to swarm channels.

Specialized adapter: it produces a channel (with a ``contracts.channels``
descriptor) and a sample payload from fields the host library already read.
It is not a firmware driver.
"""
from __future__ import annotations

from typing import Any

from codontrace.contracts.wire_validation import bounded_int as integer
from codontrace.contracts.wire_validation import bounded_text as text
from codontrace.contracts.wire_validation import exact_keys as object_keys
from codontrace.contracts.wire_validation import finite_number as number
from codontrace.contracts.wire_validation import identifier

__all__ = ['fdc_sample']


def fdc_sample(reading: dict[str, Any], *, variant: str, config_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map host-provided FDCxCapSense reading fields; not a firmware driver.

    Original registers/configuration stay in metadata. Never reconstruct missing
    clock/LC data or turn a library error's zero placeholder into a valid value.
    """
    identifier(config_id)
    if variant not in ('FDC1004', 'FDC1004-Q1', 'FDC2212', 'FDC2214', 'FDC2112', 'FDC2114'):
        raise ValueError('unknown FDC variant')
    common = {'channel', 'status'}
    direct = variant.startswith('FDC1004')
    keys = {'raw24', 'capacitancePf', 'capdacCode', 'capdacEnabled', 'diagnosticFlags'} if direct else {'rawCode', 'frequencyHz', 'frefHz', 'finSelMultiplier', 'frefDivider', 'dataReady'}
    row = object_keys(reading, common | keys)
    integer(row['channel'], high=1 if variant.endswith('12') else 3);text(row['status'])
    if row['status'] not in {'Ok', 'I2cError', 'Timeout', 'InvalidArgument', 'DeviceNotFound', 'InvalidDeviceId', 'MeasurementNotReady', 'NotSupported'}:
        raise ValueError('unknown FDC status')
    valid = row['status'] == 'Ok'; metadata = {'variant': variant, 'library': 'FDCxCapSense', **row}
    if direct:
        if type(row['raw24']) is not int or not -(2**23) <= row['raw24'] < 2**23: raise ValueError('signed 24-bit FDC reading required')
        integer(row['capdacCode'], high=31);integer(row['diagnosticFlags'],high=65535)
        if type(row['capdacEnabled']) is not bool: raise ValueError('CAPDAC flag must be boolean')
        value = number(row['capacitancePf']) if valid else None
        channel = {'quantity': 'capacitance', 'unit': 'F', 'descriptor': {
            'value_type': 'scalar', 'measurement_model': 'direct', 'feature_id': 'fdc-electrode',
            'source_unit': 'pF', 'config_id': config_id, 'vendor': 'Texas Instruments', 'device_model': variant,
            'normalization': {'method': 'affine', 'scale': 1e-12, 'offset': 0., 'output_unit': 'F', 'evidence_id': 'SI-prefix'}}}
    else:
        integer(row['rawCode'],high=(2**12-1 if variant.startswith('FDC211') else 2**28-1))
        # CHx_FIN_SEL: b01 = divide by 1, b10 = divide by 2; b11 is reserved (FDC2x1x datasheet,
        # CLOCK_DIVIDERS_CHx). FDCxCapSense reports the multiplier (1 or 2), 0 when unread.
        number(row['frequencyHz']);number(row['frefHz'],low=0);integer(row['finSelMultiplier'],high=2);integer(row['frefDivider'],high=1023)
        if type(row['dataReady']) is not bool: raise ValueError('dataReady must be boolean')
        if variant.startswith('FDC211') and valid: raise ValueError('FDC211x frequency conversion is not supported in FDCxCapSense 0.6.13')
        valid = valid and row['dataReady']
        if valid and (row['frefHz'] <= 0 or row['frequencyHz'] <= 0 or row['finSelMultiplier'] not in (1,2) or row['frefDivider'] < 1):
            raise ValueError('valid resonant frequency requires clock/multiplier metadata')
        value = number(row['frequencyHz']) if valid else None
        channel = {'quantity': 'frequency', 'unit': 'Hz', 'descriptor': {'value_type': 'scalar',
            'measurement_model': 'derived', 'model_id': 'FDC2x1x-reference-clock', 'feature_id': 'fdc-electrode',
            'source_unit': 'Hz', 'config_id': config_id, 'vendor': 'Texas Instruments', 'device_model': variant}}
    return channel, {'value': value, 'valid': valid, 'status': 'ok' if valid else row['status'] if row['status'] != 'Ok' else 'not_ready',
                     'config_id': config_id, 'metadata': metadata}
