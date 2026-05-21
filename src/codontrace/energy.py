"""Audit-ready ATP accounting with an immutable ledger."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from codontrace._types import JsonValue
from codontrace._numeric import finite_float, finite_json_dumps

LedgerKind = Literal["debit", "credit"]


@dataclass(frozen=True, slots=True)
class ATPLedgerEntry:
    """Immutable record for one ATP balance change."""

    entry_id: int
    tick: int
    agent_id: str
    codon: str
    action: str
    kind: LedgerKind
    amount: float
    balance_before: float
    balance_after: float
    reason: str

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly dictionary."""

        return {
            "entry_id": self.entry_id,
            "tick": self.tick,
            "agent_id": self.agent_id,
            "codon": self.codon,
            "action": self.action,
            "kind": self.kind,
            "amount": self.amount,
            "balance_before": self.balance_before,
            "balance_after": self.balance_after,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ATPLedgerEntry:
        """Restore one ledger entry from ``to_dict()`` output."""

        kind_value = _required_str(data, "kind")
        if kind_value not in {"debit", "credit"}:
            msg = "ATPLedgerEntry.kind must be 'debit' or 'credit'."
            raise ValueError(msg)
        kind: LedgerKind = "debit" if kind_value == "debit" else "credit"
        return cls(
            entry_id=_required_int(data, "entry_id"),
            tick=_required_int(data, "tick"),
            agent_id=_required_str(data, "agent_id"),
            codon=_required_str(data, "codon"),
            action=_required_str(data, "action"),
            kind=kind,
            amount=_required_float(data, "amount"),
            balance_before=_required_float(data, "balance_before"),
            balance_after=_required_float(data, "balance_after"),
            reason=_required_str(data, "reason"),
        )


@dataclass(slots=True)
class ATPAccount:
    """ATP account whose balance changes are captured in an append-only ledger.

    codontrace uses the documented **attempt-cost model**: if an action has enough
    ATP to be attempted, its cost is debited before world effects are checked.
    A later wall/resource block does not refund that attempt cost. If ATP is
    insufficient, no debit entry is created and the action is blocked.
    """

    initial_atp: float
    current_atp: float = field(default=0.0, init=False)
    _ledger: list[ATPLedgerEntry] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.initial_atp = finite_float("ATPAccount.initial_atp", self.initial_atp, non_negative=True)  # type: ignore[assignment]
        self.current_atp = float(self.initial_atp)

    @property
    def ledger(self) -> Sequence[ATPLedgerEntry]:
        """Return an immutable view of the ATP ledger."""

        return tuple(self._ledger)

    def can_pay(self, cost: float) -> bool:
        """Return whether this account can pay ``cost``."""

        self._validate_non_negative(cost, "cost")
        return self.current_atp >= cost

    def debit(
        self,
        cost: float,
        *,
        tick: int,
        agent_id: str,
        codon: str,
        action: str,
        reason: str,
    ) -> int | None:
        """Debit ATP and return the ledger entry id.

        Returns ``None`` when funds are insufficient or when ``cost`` is exactly
        zero. Zero-cost debits are intentional no-ops and do not create ledger
        entries.
        """

        self._validate_non_negative(cost, "cost")
        if cost == 0:
            return None
        if not self.can_pay(cost):
            return None
        before = self.current_atp
        after = round(before - cost, 10)
        self.current_atp = after
        return self._append(
            kind="debit",
            amount=cost,
            tick=tick,
            agent_id=agent_id,
            codon=codon,
            action=action,
            balance_before=before,
            balance_after=after,
            reason=reason,
        )

    def credit(
        self,
        amount: float,
        *,
        tick: int,
        agent_id: str,
        codon: str,
        action: str,
        reason: str,
    ) -> int:
        """Credit ATP and return the ledger entry id."""

        self._validate_non_negative(amount, "amount")
        before = self.current_atp
        after = round(before + amount, 10)
        self.current_atp = after
        return self._append(
            kind="credit",
            amount=amount,
            tick=tick,
            agent_id=agent_id,
            codon=codon,
            action=action,
            balance_before=before,
            balance_after=after,
            reason=reason,
        )

    def ledger_digest(self) -> str:
        """Return a stable digest of the full ATP ledger content."""

        payload = [entry.to_dict() for entry in self._ledger]
        encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def snapshot(self) -> dict[str, float | int | str]:
        """Return a small serializable snapshot including ledger content digest."""

        return {
            "initial_atp": self.initial_atp,
            "current_atp": self.current_atp,
            "ledger_entries": len(self._ledger),
            "ledger_digest": self.ledger_digest(),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        """Return full replay-safe ATP state, including ledger entries."""

        return {
            "initial_atp": self.initial_atp,
            "current_atp": self.current_atp,
            "ledger": [entry.to_dict() for entry in self._ledger],
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ATPAccount:
        """Restore full ATP state for deterministic replay continuation."""

        initial_atp = _required_float(data, "initial_atp")
        current_atp = _required_float(data, "current_atp")
        ledger_value = data.get("ledger")
        if not isinstance(ledger_value, list):
            msg = "ATPAccount.ledger must be a list."
            raise ValueError(msg)
        ledger: list[ATPLedgerEntry] = []
        for index, entry_value in enumerate(ledger_value):
            if not isinstance(entry_value, dict):
                msg = "ATPAccount.ledger entries must be dictionaries."
                raise ValueError(msg)
            entry = ATPLedgerEntry.from_dict(entry_value)
            if entry.entry_id != index:
                msg = "ATPAccount.ledger entry ids must be ordered from zero."
                raise ValueError(msg)
            ledger.append(entry)

        cls._validate_ledger(initial_atp=initial_atp, current_atp=current_atp, ledger=ledger)
        account = cls(initial_atp)
        account.current_atp = current_atp
        account._ledger = ledger
        return account

    @classmethod
    def from_current(cls, current_atp: float) -> ATPAccount:
        """Create an account whose starting and current balance equal ``current_atp``."""

        return cls(current_atp)

    def is_depleted(self) -> bool:
        """Return whether ATP is depleted."""

        return self.current_atp <= 0

    def _append(
        self,
        *,
        kind: LedgerKind,
        amount: float,
        tick: int,
        agent_id: str,
        codon: str,
        action: str,
        balance_before: float,
        balance_after: float,
        reason: str,
    ) -> int:
        if balance_after < 0:
            msg = "ATP balance cannot become negative."
            raise ValueError(msg)
        entry = ATPLedgerEntry(
            entry_id=len(self._ledger),
            tick=tick,
            agent_id=agent_id,
            codon=codon,
            action=action,
            kind=kind,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
        )
        self._ledger.append(entry)
        return entry.entry_id

    @staticmethod
    def _validate_ledger(
        *, initial_atp: float, current_atp: float, ledger: list[ATPLedgerEntry]
    ) -> None:
        running = round(initial_atp, 10)
        for entry in ledger:
            if entry.amount < 0:
                msg = "ATP ledger amount cannot be negative."
                raise ValueError(msg)
            if round(entry.balance_before, 10) != running:
                msg = "ATP ledger balance_before is not internally consistent."
                raise ValueError(msg)
            expected_after = (
                round(running - entry.amount, 10)
                if entry.kind == "debit"
                else round(running + entry.amount, 10)
            )
            if expected_after < 0:
                msg = "ATP ledger balance cannot become negative."
                raise ValueError(msg)
            if round(entry.balance_after, 10) != expected_after:
                msg = "ATP ledger balance_after is not internally consistent."
                raise ValueError(msg)
            running = expected_after
        if round(current_atp, 10) != running:
            msg = "ATPAccount.current_atp does not match restored ledger."
            raise ValueError(msg)

    @staticmethod
    def _validate_non_negative(value: float, name: str) -> None:
        finite_float(name, value, non_negative=True)


def _required_int(data: dict[str, JsonValue], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"{key} must be an integer."
        raise ValueError(msg)
    return value


def _required_float(data: dict[str, JsonValue], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        msg = f"{key} must be numeric."
        raise ValueError(msg)
    return finite_float(key, value)  # type: ignore[return-value]


def _required_str(data: dict[str, JsonValue], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ValueError(msg)
    return value


ATPBudget = ATPAccount
