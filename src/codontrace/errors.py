"""Explicit public exception types for CodonTrace."""

from __future__ import annotations


class CodonTraceError(Exception):
    """Base class for all CodonTrace public API errors."""


class ConfigurationError(CodonTraceError, ValueError):
    """Raised when a user-provided configuration is invalid."""


class PlacementError(CodonTraceError, ValueError):
    """Raised when agents or world objects cannot be placed safely."""


class InvalidDensityError(ConfigurationError):
    """Raised when a density value is outside [0, 1] or contradictory."""


class InvalidWorldSizeError(ConfigurationError):
    """Raised when a generated world size is invalid."""


class ScenarioValidationError(ConfigurationError):
    """Raised when a scenario-level configuration is invalid."""


class UnsupportedActionError(CodonTraceError, ValueError):
    """Raised when an action name is unsupported by the selected registry."""


class InsufficientATPError(CodonTraceError, ValueError):
    """Raised when an ATP operation cannot be paid for."""


class ReplayError(CodonTraceError, ValueError):
    """Raised when replay/export data cannot be restored safely."""


class PluginError(CodonTraceError, ValueError):
    """Raised when plugin discovery or plugin registration fails."""


class OptionalDependencyMissing(CodonTraceError, ImportError):
    """Raised when an optional scientific backend is requested but not installed."""
