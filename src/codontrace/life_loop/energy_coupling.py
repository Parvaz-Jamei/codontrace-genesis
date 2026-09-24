"""Domain-free energy coupling between individuals on the life-loop.

Applies a scheduled or per-tick transfer amount with conservation or
explicit loss residual. Emits ``EnergyCouplingEvent`` and ledger entries
whose fields compose with ``EnergyAccountingRecord`` patterns. No discipline
vocabulary and no second energy engine.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.contracts.life_loop_events import EnergyCouplingEvent
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_energy_coupling_v1"

CouplingFailReason = Literal[
    "not_attached",
    "insufficient_energy",
    "identical_endpoints",
    "banned_fragment",
    "non_finite",
]

COUPLING_FAIL_REASONS: frozenset[str] = frozenset(
    {
        "not_attached",
        "insufficient_energy",
        "identical_endpoints",
        "banned_fragment",
        "non_finite",
    }
)


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _optional_str(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _as_str(value, name)


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _as_nonneg_finite(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0:
        raise ConfigurationError(f"{name} must be >= 0.")
    return number


def _as_unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


@dataclass(frozen=True, slots=True)
class EnergyTransferLedgerEntry:
    """Dual-party transfer row composable with EnergyAccountingRecord fields.

    Overlapping names: organism_id, tick, action, runtime_atp_before,
    runtime_atp_after, energy_delta, blocked, blocked_reason, action_cost.
    Extra coupling fields: peer_id, coupling_id, requested, accepted, loss.
    """

    organism_id: str
    peer_id: str
    coupling_id: str
    tick: int
    action: str = "energy_coupling"
    runtime_atp_before: float = 0.0
    runtime_atp_after: float = 0.0
    energy_delta: float = 0.0
    action_cost: float = 0.0
    requested: float = 0.0
    accepted: float = 0.0
    loss: float = 0.0
    blocked: bool = False
    blocked_reason: str | None = None
    schema_version: str = "energy_transfer_ledger_entry_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "organism_id",
            _refuse_banned_fragment(
                _as_str(self.organism_id, "organism_id"), "organism_id"
            ),
        )
        object.__setattr__(
            self,
            "peer_id",
            _refuse_banned_fragment(_as_str(self.peer_id, "peer_id"), "peer_id"),
        )
        object.__setattr__(
            self,
            "coupling_id",
            _refuse_banned_fragment(
                _as_str(self.coupling_id, "coupling_id"), "coupling_id"
            ),
        )
        object.__setattr__(self, "tick", _as_int(self.tick, "tick", minimum=0))
        object.__setattr__(self, "action", _as_str(self.action, "action"))
        for name in (
            "runtime_atp_before",
            "runtime_atp_after",
            "energy_delta",
            "action_cost",
            "requested",
            "accepted",
            "loss",
        ):
            object.__setattr__(
                self, name, float(require_finite_float(name, getattr(self, name)))
            )
        if not isinstance(self.blocked, bool):
            raise ConfigurationError("blocked must be a bool.")
        if self.blocked:
            if self.blocked_reason is None:
                raise ConfigurationError("blocked records require blocked_reason.")
            object.__setattr__(
                self, "blocked_reason", _as_str(self.blocked_reason, "blocked_reason")
            )
        elif self.blocked_reason is not None:
            raise ConfigurationError("unblocked records must not carry blocked_reason.")
        computed = canonical_digest(self._body(), prefix="ecoupleled")
        object.__setattr__(
            self,
            "digest",
            _check_digest(self.digest, computed, "EnergyTransferLedgerEntry"),
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "organism_id": self.organism_id,
            "peer_id": self.peer_id,
            "coupling_id": self.coupling_id,
            "tick": self.tick,
            "action": self.action,
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "energy_delta": self.energy_delta,
            "action_cost": self.action_cost,
            "requested": self.requested,
            "accepted": self.accepted,
            "loss": self.loss,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    def as_energy_accounting_fields(self) -> dict[str, JsonValue]:
        """Subset overlapping EnergyAccountingRecord field names."""

        return {
            "organism_id": self.organism_id,
            "tick": self.tick,
            "action": self.action,
            "runtime_atp_before": self.runtime_atp_before,
            "runtime_atp_after": self.runtime_atp_after,
            "action_cost": self.action_cost,
            "action_reward": 0.0,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "energy_delta": self.energy_delta,
            "fitness_delta": None,
            "fitness_delta_status": "not_measured",
            "fitness_delta_source": None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EnergyTransferLedgerEntry:
        return cls(
            organism_id=_as_str(data.get("organism_id"), "organism_id"),
            peer_id=_as_str(data.get("peer_id"), "peer_id"),
            coupling_id=_as_str(data.get("coupling_id"), "coupling_id"),
            tick=_as_int(data.get("tick"), "tick", minimum=0),
            action=_as_str(data.get("action", "energy_coupling"), "action"),
            runtime_atp_before=float(
                require_finite_float(
                    "runtime_atp_before", data.get("runtime_atp_before", 0.0)
                )
            ),
            runtime_atp_after=float(
                require_finite_float(
                    "runtime_atp_after", data.get("runtime_atp_after", 0.0)
                )
            ),
            energy_delta=float(
                require_finite_float("energy_delta", data.get("energy_delta", 0.0))
            ),
            action_cost=float(
                require_finite_float("action_cost", data.get("action_cost", 0.0))
            ),
            requested=float(
                require_finite_float("requested", data.get("requested", 0.0))
            ),
            accepted=float(require_finite_float("accepted", data.get("accepted", 0.0))),
            loss=float(require_finite_float("loss", data.get("loss", 0.0))),
            blocked=bool(data.get("blocked", False)),
            blocked_reason=_optional_str(data.get("blocked_reason"), "blocked_reason"),
            schema_version=_as_str(
                data.get("schema_version", "energy_transfer_ledger_entry_v1"),
                "schema_version",
            ),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


@dataclass(frozen=True, slots=True)
class EnergyCoupling:
    """Signed per-tick (or scheduled) energy transfer between two individuals."""

    coupling_id: str
    source_id: str
    target_id: str
    amount: float
    loss_fraction: float = 0.0
    label: str | None = None
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "coupling_id",
            _refuse_banned_fragment(
                _as_str(self.coupling_id, "coupling_id"), "coupling_id"
            ),
        )
        object.__setattr__(
            self,
            "source_id",
            _refuse_banned_fragment(_as_str(self.source_id, "source_id"), "source_id"),
        )
        object.__setattr__(
            self,
            "target_id",
            _refuse_banned_fragment(_as_str(self.target_id, "target_id"), "target_id"),
        )
        if self.source_id == self.target_id:
            raise ConfigurationError("identical_endpoints")
        object.__setattr__(self, "amount", _as_nonneg_finite(self.amount, "amount"))
        object.__setattr__(
            self, "loss_fraction", _as_unit_interval(self.loss_fraction, "loss_fraction")
        )
        label = _optional_str(self.label, "label")
        if label is not None:
            label = _refuse_banned_fragment(label, "label")
        object.__setattr__(self, "label", label)
        computed = canonical_digest(self._body(), prefix="ecouplecfg")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "EnergyCoupling")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "coupling_id": self.coupling_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "amount": self.amount,
            "loss_fraction": self.loss_fraction,
            "label": self.label,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EnergyCoupling:
        return cls(
            coupling_id=_as_str(data.get("coupling_id"), "coupling_id"),
            source_id=_as_str(data.get("source_id"), "source_id"),
            target_id=_as_str(data.get("target_id"), "target_id"),
            amount=float(require_finite_float("amount", data.get("amount"))),
            loss_fraction=float(
                require_finite_float("loss_fraction", data.get("loss_fraction", 0.0))
            ),
            label=_optional_str(data.get("label"), "label"),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )

    def apply(
        self,
        balances: Mapping[str, float],
        *,
        tick: int,
        require_attached: bool = False,
        attached: bool = False,
        content_empty: bool = False,
        allow_partial: bool = False,
    ) -> tuple[
        dict[str, float],
        EnergyCouplingEvent,
        tuple[EnergyTransferLedgerEntry, EnergyTransferLedgerEntry],
        bool,
    ]:
        """Apply one transfer.

        Returns ``(new_balances, event, (source_entry, target_entry), conserved)``.
        ``conserved`` is True only when loss==0 and source+target deltas sum to 0.
        """

        tick_i = _as_int(tick, "tick", minimum=0)
        if not isinstance(require_attached, bool):
            raise ConfigurationError("require_attached must be a bool.")
        if not isinstance(attached, bool):
            raise ConfigurationError("attached must be a bool.")
        if not isinstance(content_empty, bool):
            raise ConfigurationError("content_empty must be a bool.")
        if not isinstance(allow_partial, bool):
            raise ConfigurationError("allow_partial must be a bool.")

        if self.source_id not in balances or self.target_id not in balances:
            raise ConfigurationError("balances must include source_id and target_id.")
        source_before = float(
            require_finite_float("source_balance", balances[self.source_id])
        )
        target_before = float(
            require_finite_float("target_balance", balances[self.target_id])
        )
        if source_before < 0.0 or target_before < 0.0:
            raise ConfigurationError("balances must be >= 0.")

        if require_attached and not attached:
            raise ConfigurationError("not_attached")

        requested = 0.0 if content_empty else float(self.amount)
        if requested > source_before:
            if not allow_partial:
                raise ConfigurationError("insufficient_energy")
            requested = source_before

        loss = requested * float(self.loss_fraction)
        accepted = requested - loss

        source_after = source_before - requested
        target_after = target_before + accepted
        if source_after < -1e-12:
            raise ConfigurationError("insufficient_energy")
        if source_after < 0.0:
            source_after = 0.0

        new_balances = dict(balances)
        new_balances[self.source_id] = source_after
        new_balances[self.target_id] = target_after

        event = EnergyCouplingEvent(
            source_id=self.source_id,
            target_id=self.target_id,
            delta_energy=accepted,
            tick=tick_i,
            coupling_id=self.coupling_id,
        )

        source_entry = EnergyTransferLedgerEntry(
            organism_id=self.source_id,
            peer_id=self.target_id,
            coupling_id=self.coupling_id,
            tick=tick_i,
            runtime_atp_before=source_before,
            runtime_atp_after=source_after,
            energy_delta=-requested,
            action_cost=requested,
            requested=requested,
            accepted=accepted,
            loss=loss,
        )
        target_entry = EnergyTransferLedgerEntry(
            organism_id=self.target_id,
            peer_id=self.source_id,
            coupling_id=self.coupling_id,
            tick=tick_i,
            runtime_atp_before=target_before,
            runtime_atp_after=target_after,
            energy_delta=accepted,
            action_cost=0.0,
            requested=requested,
            accepted=accepted,
            loss=loss,
        )

        conserved = (loss == 0.0) and abs(
            (source_after - source_before) + (target_after - target_before)
        ) <= 1e-9
        return new_balances, event, (source_entry, target_entry), conserved


__all__ = [
    "COUPLING_FAIL_REASONS",
    "SCHEMA_VERSION",
    "CouplingFailReason",
    "EnergyCoupling",
    "EnergyTransferLedgerEntry",
]
