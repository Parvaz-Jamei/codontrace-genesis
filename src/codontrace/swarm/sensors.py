"""Typed, bounded sensor descriptors and explicit host-side normalization.

Receipt support is separate from filter/inference support. No driver execution,
implicit physical conversion, or claimed calibration from caller metadata.

The generic channel contract lives in ``codontrace.contracts.channels`` and the
FDC mapping in ``codontrace.swarm.adapters.fdc``; the names here are kept as
aliases of the same objects.
"""
from __future__ import annotations

from codontrace.contracts.channels import MEASUREMENT_MODELS as MODELS
from codontrace.contracts.channels import VALUE_TYPES as TYPES
from codontrace.contracts.channels import normalize_sample as normalize
from codontrace.contracts.channels import scalar_frame, typed_value
from codontrace.contracts.channels import validate_descriptor as descriptor
from codontrace.contracts.wire_validation import bounded_int as integer
from codontrace.contracts.wire_validation import bounded_text as text
from codontrace.contracts.wire_validation import exact_keys as object_keys
from codontrace.contracts.wire_validation import finite_number as number
from codontrace.contracts.wire_validation import identifier
from codontrace.contracts.wire_validation import wire_canonical as canonical
from codontrace.swarm.adapters.fdc import fdc_sample

# No __all__, as before: every name below stays public and star-importable.
_REEXPORTS = (MODELS, TYPES, canonical, descriptor, fdc_sample, identifier, integer, normalize, number, object_keys,
              scalar_frame, text, typed_value)
