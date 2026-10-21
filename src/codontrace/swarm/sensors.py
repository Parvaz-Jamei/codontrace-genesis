"""Typed, bounded sensor descriptors and explicit host-side normalization.

Receipt support is separate from filter/inference support. No driver execution,
implicit physical conversion, or claimed calibration from caller metadata.

The generic channel contract lives in ``codontrace.contracts.channels`` and the
FDC mapping in ``codontrace.swarm.adapters.fdc``; the names here are kept as
aliases of the same objects.
"""
from __future__ import annotations

from codontrace.contracts import channels as _channels
from codontrace.contracts import wire_validation as _wire
from codontrace.contracts.channels import scalar_frame as scalar_frame
from codontrace.contracts.channels import typed_value as typed_value
from codontrace.contracts.wire_validation import identifier as identifier
from codontrace.swarm.adapters.fdc import fdc_sample as fdc_sample

# Renamed aliases are plain assignments (same objects) so they are explicit
# module attributes for type checkers.
MODELS = _channels.MEASUREMENT_MODELS
TYPES = _channels.VALUE_TYPES
normalize = _channels.normalize_sample
descriptor = _channels.validate_descriptor
integer = _wire.bounded_int
text = _wire.bounded_text
object_keys = _wire.exact_keys
number = _wire.finite_number
canonical = _wire.wire_canonical

# No __all__, as before: every name below stays public and star-importable.
_REEXPORTS = (MODELS, TYPES, canonical, descriptor, fdc_sample, identifier, integer, normalize, number, object_keys,
              scalar_frame, text, typed_value)
