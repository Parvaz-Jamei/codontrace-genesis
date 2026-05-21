"""Central reproducible random-number manager for codontrace."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeAlias, TypeVar, cast, runtime_checkable

from codontrace._types import JsonValue

T = TypeVar("T")
RNGSnapshot: TypeAlias = dict[str, JsonValue]


@runtime_checkable
class RNGProtocol(Protocol):
    """Protocol for replay-auditable random streams.

    Same backend + same seed + same namespace + same draw schedule must replay.
    Different backends intentionally do not claim identical numeric streams.
    """

    @property
    def backend_kind(self) -> str: ...

    @property
    def namespace(self) -> str: ...

    @property
    def draw_count(self) -> int: ...

    def random(self) -> float: ...

    def randrange(self, start: int, stop: int | None = None) -> int: ...

    def choice(self, values: Sequence[T]) -> T: ...

    def fork(self, namespace: str) -> RNGProtocol: ...

    def snapshot(self, *, include_state: bool = False) -> dict[str, JsonValue]: ...

    def state_digest(self) -> str: ...


@dataclass(slots=True)
class RNGManager:
    """Seed-controlled RNG facade.

    All project randomness must flow through this class. The class wraps
    ``random.Random`` only inside this module so static tests can block hidden
    random usage elsewhere. ``snapshot(include_state=True)`` captures the exact
    stream position in a JSON-safe form so replay can resume from the middle of
    a run without using pickle.
    """

    seed: int | None = None
    namespace: str = "root"

    def __post_init__(self) -> None:
        material = self._material(self.seed, self.namespace)
        self._rng = random.Random(material)
        self._draw_count = 0

    _rng: random.Random = field(init=False, repr=False)
    _draw_count: int = field(default=0, init=False, repr=False)

    @property
    def backend_kind(self) -> str:
        """Return the replay backend identifier for manifests."""

        return "rng_manager"

    @property
    def draw_count(self) -> int:
        """Return the number of random draws consumed by this stream."""

        return self._draw_count

    def choice(self, values: Sequence[T]) -> T:
        """Choose one item from a non-empty sequence."""

        if not values:
            msg = "choice() requires a non-empty sequence."
            raise ValueError(msg)
        self._draw_count += 1
        return self._rng.choice(values)

    def randrange(self, start: int, stop: int | None = None) -> int:
        """Return a deterministic integer from ``range(start, stop)``."""

        self._draw_count += 1
        if stop is None:
            return self._rng.randrange(start)
        return self._rng.randrange(start, stop)

    def random(self) -> float:
        """Return a deterministic float in the half-open interval [0.0, 1.0)."""

        self._draw_count += 1
        return self._rng.random()

    def fork(self, namespace: str) -> RNGManager:
        """Create a deterministic child RNG for a named subsystem."""

        if not namespace:
            msg = "namespace must not be empty."
            raise ValueError(msg)
        return RNGManager(seed=self.seed, namespace=f"{self.namespace}/{namespace}")

    def snapshot(self, *, include_state: bool = False) -> RNGSnapshot:
        """Return a JSON-safe description of this RNG stream.

        By default this returns stream identity only. With ``include_state=True``
        it also includes the exact internal RNG state converted to lists and
        primitive JSON values. This intentionally avoids ``pickle`` so snapshots
        can be serialized safely and inspected by humans.
        """

        data: RNGSnapshot = {
            "seed": self.seed,
            "namespace": self.namespace,
            "draw_count": self._draw_count,
        }
        if include_state:
            data["backend_kind"] = self.backend_kind
            state = self._rng.getstate()
            data["state"] = {
                "version": int(state[0]),
                "internal": [int(value) for value in state[1]],
                "gauss": state[2],
            }
        return data

    @classmethod
    def restore(cls, snapshot: RNGSnapshot) -> RNGManager:
        """Restore an ``RNGManager`` from ``snapshot(include_state=True)`` output."""

        cls._validate_snapshot(snapshot)
        seed = snapshot["seed"]
        namespace = snapshot["namespace"]
        draw_count = snapshot["draw_count"]
        manager = cls(seed=cast(int | None, seed), namespace=cast(str, namespace))
        state_value = snapshot.get("state")
        if state_value is not None:
            if not isinstance(state_value, dict):
                msg = "Invalid RNG snapshot: state must be an object."
                raise ValueError(msg)
            version = state_value.get("version")
            internal = state_value.get("internal")
            gauss = state_value.get("gauss")
            if not isinstance(version, int):
                msg = "Invalid RNG snapshot: state.version must be an integer."
                raise ValueError(msg)
            if not isinstance(internal, list) or not all(isinstance(v, int) for v in internal):
                msg = "Invalid RNG snapshot: state.internal must be a list of integers."
                raise ValueError(msg)
            if gauss is not None and not isinstance(gauss, float):
                msg = "Invalid RNG snapshot: state.gauss must be a float or null."
                raise ValueError(msg)
            manager._rng.setstate(cast(Any, (version, tuple(internal), gauss)))
        manager._draw_count = cast(int, draw_count)
        return manager

    def state_digest(self) -> str:
        """Return a stable digest of stream identity and exact state."""

        payload = json.dumps(
            self.snapshot(include_state=True), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _material(seed: int | None, namespace: str) -> int:
        digest = hashlib.sha256(f"{seed!r}:{namespace}".encode()).hexdigest()
        return int(digest[:16], 16)

    @staticmethod
    def _validate_snapshot(snapshot: RNGSnapshot) -> None:
        required = {"seed", "namespace", "draw_count"}
        if not required.issubset(snapshot):
            missing = ", ".join(sorted(required - set(snapshot)))
            msg = f"Invalid RNG snapshot: missing {missing}."
            raise ValueError(msg)
        seed = snapshot["seed"]
        namespace = snapshot["namespace"]
        draw_count = snapshot["draw_count"]
        if seed is not None and not isinstance(seed, int):
            msg = "Invalid RNG snapshot: seed must be an integer or null."
            raise ValueError(msg)
        if not isinstance(namespace, str) or not namespace:
            msg = "Invalid RNG snapshot: namespace must be a non-empty string."
            raise ValueError(msg)
        if not isinstance(draw_count, int) or draw_count < 0:
            msg = "Invalid RNG snapshot: draw_count must be a non-negative integer."
            raise ValueError(msg)


# Backward-compatible explicit backend name used by scientific adapters/tests.
RNGManagerBackend = RNGManager


@dataclass(slots=True)
class NumpyGeneratorBackend:
    """Optional NumPy Generator backend with the same RNGProtocol contract.

    The core package does not import NumPy at module import time. Requesting this
    backend without installing ``codontrace[science]`` raises
    OptionalDependencyMissing. No equality with RNGManager numeric streams is
    claimed.
    """

    seed: int | None = None
    namespace: str = "root"

    def __post_init__(self) -> None:
        from codontrace.errors import OptionalDependencyMissing

        try:
            import numpy as np
        except ImportError as exc:  # pragma: no cover - depends on optional env
            raise OptionalDependencyMissing(
                "Install codontrace[science] to use NumpyGeneratorBackend."
            ) from exc
        material = RNGManager._material(self.seed, self.namespace)
        self._np = np
        self._rng = np.random.default_rng(material)
        self._draw_count = 0

    _rng: Any = field(init=False, repr=False)
    _np: Any = field(init=False, repr=False)
    _draw_count: int = field(default=0, init=False, repr=False)

    @property
    def backend_kind(self) -> str:
        return "numpy_generator"

    @property
    def draw_count(self) -> int:
        return self._draw_count

    def random(self) -> float:
        self._draw_count += 1
        return float(self._rng.random())

    def randrange(self, start: int, stop: int | None = None) -> int:
        self._draw_count += 1
        if stop is None:
            return int(self._rng.integers(0, start))
        return int(self._rng.integers(start, stop))

    def choice(self, values: Sequence[T]) -> T:
        if not values:
            msg = "choice() requires a non-empty sequence."
            raise ValueError(msg)
        self._draw_count += 1
        return values[int(self._rng.integers(0, len(values)))]

    def fork(self, namespace: str) -> NumpyGeneratorBackend:
        if not namespace:
            msg = "namespace must not be empty."
            raise ValueError(msg)
        return NumpyGeneratorBackend(seed=self.seed, namespace=f"{self.namespace}/{namespace}")

    def snapshot(self, *, include_state: bool = False) -> dict[str, JsonValue]:
        data: dict[str, JsonValue] = {
            "backend_kind": self.backend_kind,
            "seed": self.seed,
            "namespace": self.namespace,
            "draw_count": self._draw_count,
        }
        if include_state:
            data["state"] = _jsonable_rng_state(self._rng.bit_generator.state)
        return data

    def state_digest(self) -> str:
        payload = json.dumps(
            self.snapshot(include_state=True), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _jsonable_rng_state(value: Any) -> JsonValue:
    """Convert optional backend state into a deterministic JSON-like payload."""

    if isinstance(value, dict):
        return {
            str(k): _jsonable_rng_state(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, tuple):
        return [_jsonable_rng_state(v) for v in value]
    if isinstance(value, list):
        return [_jsonable_rng_state(v) for v in value]
    if hasattr(value, "tolist"):
        return _jsonable_rng_state(value.tolist())
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
