"""GENESIS ATP runtime and bounded learning ATP accounting."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace._numeric import finite_float, finite_json_dumps
from codontrace.energy import ATPAccount


@dataclass(slots=True)
class GenesisATPState:
    """GENESIS ATP state with separate runtime and learning accounts.

    ``runtime`` pays action/token execution. ``learning`` pays memory writes,
    consolidation, and learning-update attempts. The ledgers remain separate so
    controlled experiments can audit action energy separately from cognition-like
    bookkeeping. This is an accounting primitive, not a CausalGraph or discovery
    implementation.
    """

    runtime: ATPAccount
    learning: ATPAccount | None = None

    def __post_init__(self) -> None:
        finite_float("ATP_runtime.current_atp", self.runtime.current_atp, non_negative=True)
        if self.learning is not None:
            finite_float("ATP_learning.current_atp", self.learning.current_atp, non_negative=True)

    @classmethod
    def from_runtime(
        cls,
        runtime_atp: float,
        *,
        learning_atp: float = 0.0,
        learning_enabled: bool = False,
    ) -> GenesisATPState:
        """Create runtime ATP plus an optional learning account."""

        runtime_value = finite_float("runtime_atp", runtime_atp, non_negative=True)
        learning_value = finite_float("learning_atp", learning_atp, non_negative=True)
        learning = ATPAccount(learning_value) if learning_enabled else None
        return cls(runtime=ATPAccount(runtime_value), learning=learning)

    @property
    def runtime_available(self) -> float:
        """Return current ATP_runtime balance."""

        return self.runtime.current_atp

    @property
    def learning_available(self) -> float:
        """Return current ATP_learning balance, or zero when disabled."""

        return 0.0 if self.learning is None else self.learning.current_atp

    @property
    def learning_enabled(self) -> bool:
        """Return whether ATP_learning exists."""

        return self.learning is not None

    def can_execute(self, cost: float) -> bool:
        """Return whether runtime ATP can pay an action/token cost."""

        return self.runtime.can_pay(cost)

    def can_learn(self, cost: float) -> bool:
        """Return whether learning ATP can pay a memory/learning cost."""

        if self.learning is None:
            return cost == 0
        return self.learning.can_pay(cost)

    def debit_runtime(
        self,
        cost: float,
        *,
        tick: int,
        organism_id: str,
        codon: str,
        action: str,
        reason: str = "genesis_runtime_cost",
    ) -> int | None:
        """Debit runtime ATP without allowing negative balances."""

        return self.runtime.debit(
            cost,
            tick=tick,
            agent_id=organism_id,
            codon=codon,
            action=action,
            reason=reason,
        )

    def credit_runtime(
        self,
        amount: float,
        *,
        tick: int,
        organism_id: str,
        codon: str,
        action: str,
        reason: str,
    ) -> int:
        """Credit runtime ATP from Lumen/resource consumption."""

        return self.runtime.credit(
            amount,
            tick=tick,
            agent_id=organism_id,
            codon=codon,
            action=action,
            reason=reason,
        )

    def debit_learning(
        self,
        cost: float,
        *,
        tick: int,
        organism_id: str,
        reason: str,
        event_ref: str | None = None,
    ) -> int | None:
        """Debit ATP_learning for memory/consolidation work.

        Returns ``None`` when learning is disabled, cost is zero, or the account
        cannot pay. Runtime ATP is intentionally never touched by this method.
        """

        cost = finite_float("learning cost", cost, non_negative=True)  # type: ignore[assignment]
        if self.learning is None:
            return None
        action = "LEARNING_UPDATE" if event_ref is None else f"LEARNING_UPDATE:{event_ref[:12]}"
        return self.learning.debit(
            cost,
            tick=tick,
            agent_id=organism_id,
            codon="learning",
            action=action,
            reason=reason,
        )

    def credit_learning(
        self,
        amount: float,
        *,
        tick: int,
        organism_id: str,
        reason: str,
        source: str = "vitae",
    ) -> int:
        """Credit ATP_learning from a conceptual source such as Vitae."""

        amount = finite_float("learning credit amount", amount, non_negative=True)  # type: ignore[assignment]
        if self.learning is None:
            self.learning = ATPAccount(0.0)
        return self.learning.credit(
            amount,
            tick=tick,
            agent_id=organism_id,
            codon=source,
            action="CREDIT_LEARNING_ATP",
            reason=reason,
        )

    def transfer_vitae_to_learning(
        self,
        amount: float,
        *,
        tick: int,
        organism_id: str,
        conversion_rate: float = 1.0,
    ) -> int | None:
        """Credit ATP_learning from external Vitae-managed state.

        The caller owns ``vitae_store`` and must reduce it when this transfer is
        used. This method records the ATP_learning ledger side only.
        """

        amount = finite_float("transfer amount", amount, non_negative=True)  # type: ignore[assignment]
        conversion_rate = finite_float("conversion_rate", conversion_rate)  # type: ignore[assignment]
        if conversion_rate <= 0:
            msg = "conversion_rate must be > 0."
            raise ValueError(msg)
        credit = round(amount * conversion_rate, 10)
        if credit == 0:
            return None
        return self.credit_learning(
            credit,
            tick=tick,
            organism_id=organism_id,
            reason="vitae_to_learning_transfer",
            source="vitae",
        )

    def ledger_digest(self) -> str:
        """Return a deterministic digest for both ATP ledgers."""

        payload = {
            "runtime": self.runtime.ledger_digest(),
            "learning": None if self.learning is None else self.learning.ledger_digest(),
            "runtime_entries": len(self.runtime.ledger),
            "learning_entries": 0 if self.learning is None else len(self.learning.ledger),
        }
        encoded = finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-friendly ATP state."""

        return {
            "runtime": self.runtime.to_dict(),
            "learning": None if self.learning is None else self.learning.to_dict(),
            "learning_enabled": self.learning_enabled,
            "ledger_digest": self.ledger_digest(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> GenesisATPState:
        """Restore ATP state from ``to_dict()`` output."""

        runtime_raw = data.get("runtime")
        learning_raw = data.get("learning")
        if not isinstance(runtime_raw, dict):
            msg = "GenesisATPState.runtime must be an ATPAccount dictionary."
            raise ValueError(msg)
        learning = ATPAccount.from_dict(learning_raw) if isinstance(learning_raw, dict) else None
        return cls(runtime=ATPAccount.from_dict(runtime_raw), learning=learning)


@dataclass(frozen=True, slots=True)
class DualATPBudget:
    """Immutable read-only snapshot of separate runtime/learning ATP balances."""

    runtime_available: float
    learning_available: float = 0.0
    learning_enabled: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_available", finite_float("runtime_available", self.runtime_available, non_negative=True))
        object.__setattr__(self, "learning_available", finite_float("learning_available", self.learning_available, non_negative=True))

    @classmethod
    def from_state(cls, state: GenesisATPState) -> DualATPBudget:
        """Create a read-only budget snapshot from mutable ATP state."""

        return cls(
            runtime_available=state.runtime_available,
            learning_available=state.learning_available,
            learning_enabled=state.learning_enabled,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-safe snapshot."""

        return {
            "runtime_available": self.runtime_available,
            "learning_available": self.learning_available,
            "learning_enabled": self.learning_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> DualATPBudget:
        """Restore a read-only snapshot."""

        runtime = data.get("runtime_available")
        learning = data.get("learning_available", 0.0)
        enabled = data.get("learning_enabled", False)
        if isinstance(runtime, bool) or not isinstance(runtime, int | float):
            msg = "runtime_available must be numeric."
            raise ValueError(msg)
        if isinstance(learning, bool) or not isinstance(learning, int | float):
            msg = "learning_available must be numeric."
            raise ValueError(msg)
        if not isinstance(enabled, bool):
            msg = "learning_enabled must be boolean."
            raise ValueError(msg)
        return cls(
            runtime_available=finite_float("runtime_available", runtime, non_negative=True),
            learning_available=finite_float("learning_available", learning, non_negative=True),
            learning_enabled=enabled,
        )
