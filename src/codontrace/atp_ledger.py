"""Closed, absolute world ATP ledger (double-entry, exact, hash-chained).

Every ATP unit in a world lives in exactly one named account at all times:

* ``agent:<id>``      an organism's runtime balance (mirrors its ``ATPAccount``
                      or scalar ``atp`` field exactly);
* ``world:reservoir`` the world's free pool (founder and birth endowments are
                      drawn from it, death remainders return to it);
* ``world:clearing``  a transient account used inside one transfer scope
                      (e.g. host->parasite coupling); its residual is booked to
                      an explicit loss sink when the scope closes;
* ``source:<name>``   boundary inflows (Avida-style resource inflow, task
                      rewards, the genesis endowment); balances are <= 0;
* ``sink:<name>``     boundary outflows (basal metabolism, birth cost,
                      dissipation); balances are >= 0;
* ``source:rounding`` / ``sink:rounding``  the residue of ``ATPAccount``'s
                      10-digit balance rounding (up to 5e-11 per entry), which
                      would otherwise create or destroy ATP silently.

Each posting moves one exact amount from one account to another, so the signed
sum of all accounts is identically zero (double entry, Pacioli 1494; the same
row/column-sum-zero identity the stock-flow-consistent agent-based models check
every period: Godley & Lavoie 2007; Caiani et al. 2016, JEDC 69; Baldauf 2023
sfctools, JOSS 8(87) 4980; Reissl, Fierro, Lamperti & Roventini 2024 DSK-SFC,
LEM WP 2024/09, Ecological Economics 2025, doi:10.1016/j.ecolecon.2025.108641). Amounts are exact
rationals (``fractions.Fraction`` of the IEEE-754 values the engine actually
stores), so the invariant is checked with ``==``, never with a tolerance, and the
realised delta (after ``ATPAccount``'s 10-digit rounding) is what is booked.

``close_tick`` checks, every tick:

1. sum of every account == 0 (conservation; no creation or destruction);
2. every open agent account == the engine's own balance for that agent
   (no bypass: a balance changed outside the ledger is caught);
3. the set of open agents == the set of live agents (no orphan/ghost energy);
4. source accounts <= 0, sink accounts >= 0, reservoir >= 0.

and appends a record to an in-memory hash chain ``{previous, action, args,
state_digest, digest}`` (the same record shape as
``codontrace.genesis.journal``), so a replay digest of the whole energy history
is ``ledger.head``. The engine layer does not import the journal module; a
caller can persist ``journal_records()`` into any journal.

Why: Avida models resources with explicit initial quantity, inflow and outflow
(Ofria & Wilke 2004; Ofria, Bryson & Wilke 2009), and Flow-Lenia makes Lenia
mass-conservative so total matter is an invariant of the update (Plantec et al.
2023, ALIFE; Plantec et al. 2025, Artificial Life 31(2), doi:10.1162/artl_a_00471).
Cell-biology ATP budgets partition all energy into construction (growth) and
maintenance, counted in ATP hydrolyses (Lynch & Marinov 2015 PNAS; Lynch 2024,
Evolutionary Cell Biology, OUP ch. "The Costs of Cellular Features"); the sink
names below follow that partition.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from codontrace.energy import ATPAccount, ATPLedgerEntry

__all__ = [
    "CLEARING",
    "GENESIS_SOURCE",
    "RESERVOIR",
    "ATPConservationError",
    "ATPPosting",
    "WorldATPLedger",
    "verify_ledger_chain",
]

RESERVOIR = "world:reservoir"
CLEARING = "world:clearing"
GENESIS_SOURCE = "source:genesis"
ZERO_DIGEST = "0" * 64
# Relative bound on float-subtraction excess inside one transfer (a few ulps).
ROUNDING_BOUND = Fraction(1, 2**48)


class ATPConservationError(AssertionError):
    """The closed ATP balance invariant failed."""


def _q(value: float | int | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("ATP amount must be numeric, not bool")
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        raise ValueError("ATP amount must be finite")
    return Fraction(f)


def _fs(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canon(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def agent_account(agent_id: str) -> str:
    return f"agent:{agent_id}"


class _AgentHook:
    """Picklable, deepcopy-safe observer binding one ATPAccount to the ledger."""

    __slots__ = ("account", "agent_id", "ledger")

    def __init__(self, ledger: WorldATPLedger, agent_id: str, account: ATPAccount | None = None) -> None:
        self.ledger = ledger
        self.agent_id = agent_id
        self.account = account

    def __call__(self, entry: ATPLedgerEntry) -> None:
        self.ledger._on_entry(self.agent_id, entry, self.account)

    def __reduce__(self) -> tuple[object, ...]:
        # Never serialise the live ledger through a hook (ATPAccount drops its
        # hook on copy; this guards any other holder).
        raise TypeError("an attached ATP ledger hook cannot be pickled or copied; detach first")


@dataclass(frozen=True, slots=True)
class ATPPosting:
    """One double-entry posting: ``amount`` leaves ``src`` and enters ``dst``."""

    seq: int
    tick: int
    src: str
    dst: str
    amount: Fraction
    memo: str

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "tick": self.tick, "src": self.src, "dst": self.dst,
                "amount": _fs(self.amount), "memo": self.memo}


class WorldATPLedger:
    """One world's closed ATP ledger. See the module docstring."""

    def __init__(self, world_id: str = "world") -> None:
        self.world_id = str(world_id)
        self._bal: dict[str, Fraction] = {RESERVOIR: Fraction(0), CLEARING: Fraction(0)}
        self._agents: set[str] = set()
        self._pending: list[ATPPosting] = []
        self._seq = 0
        self._scope: str | None = None
        self._scope_gross = Fraction(0)
        self._scope_ulps = Fraction(0)
        self._new_keys: list[str] = []
        self._touched: dict[int, tuple[ATPAccount, Any]] = {}
        # Attached ATPAccounts. Copying/pickling an account alone detaches it
        # (it must not drag or book into this ledger); copying/pickling the
        # ledger carries its accounts and re-attaches them to the copy.
        self._accounts: dict[str, ATPAccount] = {}
        self._records: list[dict[str, Any]] = []
        self._head = ZERO_DIGEST
        self.ticks_checked = 0

    # ------------------------------------------------------------------ core
    def post(self, src: str, dst: str, amount: float | Fraction, *, tick: int, memo: str) -> None:
        """Move ``amount`` (>= 0) from ``src`` to ``dst``. Zero is a no-op."""

        amt = _q(amount)
        if amt < 0:
            raise ValueError("posting amount must be >= 0; swap src/dst")
        if amt == 0:
            return
        for acct in (src, dst):
            self._check_name(acct)
            if acct not in self._bal:
                self._new_keys.append(acct)
        self._bal[src] = self._bal.get(src, Fraction(0)) - amt
        self._bal[dst] = self._bal.get(dst, Fraction(0)) + amt
        if CLEARING in (src, dst):
            self._scope_gross += amt
        self._pending.append(ATPPosting(self._seq, int(tick), src, dst, amt, str(memo)))
        self._seq += 1

    def _check_name(self, acct: str) -> None:
        if acct in (RESERVOIR, CLEARING) or acct.startswith(("source:", "sink:")):
            return
        if acct.startswith("agent:") and acct[6:] in self._agents:
            return
        raise ATPConservationError(f"posting to unknown or closed account {acct!r}")

    def fund_reservoir(self, amount: float | Fraction, *, tick: int, source: str = GENESIS_SOURCE) -> None:
        """Boundary inflow into the reservoir (``source`` must be ``source:*``)."""

        if not source.startswith("source:"):
            raise ValueError("reservoir inflow must come from a source:* account")
        self.post(source, RESERVOIR, amount, tick=tick, memo="reservoir_inflow")

    def draw_from_reservoir(self, dst: str, amount: float | Fraction, *, tick: int, memo: str,
                            inflow_source: str = "source:inflow") -> None:
        """Pay ``amount`` from the reservoir; any shortfall first enters as explicit inflow."""

        amt = _q(amount)
        short = amt - self._bal[RESERVOIR]
        if short > 0:
            self.fund_reservoir(short, tick=tick, source=inflow_source)
        self.post(RESERVOIR, dst, amt, tick=tick, memo=memo)

    # ----------------------------------------------------------------- agents
    def open_agent(self, agent_id: str, balance: float | Fraction, *, tick: int,
                   funded_from: str = RESERVOIR, memo: str = "endowment") -> None:
        """Open an agent account and fund its starting balance."""

        if self._scope is not None:
            raise ATPConservationError("cannot open an agent account inside a transfer scope")
        if agent_id in self._agents:
            raise ATPConservationError(f"agent {agent_id!r} already has an account")
        self._agents.add(agent_id)
        self._bal[agent_account(agent_id)] = Fraction(0)
        if funded_from == RESERVOIR:
            self.draw_from_reservoir(agent_account(agent_id), balance, tick=tick, memo=memo)
        else:
            self.post(funded_from, agent_account(agent_id), balance, tick=tick, memo=memo)

    def close_agent(self, agent_id: str, *, tick: int, to: str = RESERVOIR, memo: str = "death_remainder") -> None:
        """Move an agent's whole remaining balance to ``to`` and close the account."""

        key = agent_account(agent_id)
        if self._scope is not None:
            raise ATPConservationError("cannot close an agent account inside a transfer scope")
        if agent_id not in self._agents:
            raise ATPConservationError(f"agent {agent_id!r} has no open account")
        rem = self._bal[key]
        if rem > 0:
            self.post(key, to, rem, tick=tick, memo=memo)
        elif rem < 0:
            # A negative scalar balance (legacy experiments allow ATP debt) is
            # written off from an explicit source, never from the reservoir.
            self.post("source:debt_writeoff", key, -rem, tick=tick, memo=memo + "_debt")
        self._agents.discard(agent_id)
        del self._bal[key]

    def adjust(self, agent_id: str, current: float, delta: float, *, tick: int,
               source: str, sink: str) -> float:
        """Return ``current + delta`` (the engine's own float arithmetic) and book
        the exact realised change from ``source`` (gain) or to ``sink`` (loss)."""

        new = current + delta
        realised = _q(new) - _q(current)
        if realised > 0:
            self.post(source, agent_account(agent_id), realised, tick=tick, memo=source)
        elif realised < 0:
            self.post(agent_account(agent_id), sink, -realised, tick=tick, memo=sink)
        return new

    # ---------------------------------------------------- ATPAccount observer
    def attach(self, agent_id: str, account: ATPAccount, *, tick: int,
               funded_from: str = RESERVOIR, memo: str = "endowment") -> None:
        """Open ``agent_id`` with ``account``'s balance and observe its entries."""

        self.open_agent(agent_id, account.current_atp, tick=tick, funded_from=funded_from, memo=memo)
        account.set_observer(_AgentHook(self, agent_id, account))
        self._accounts[agent_id] = account

    def detach(self, agent_id: str, account: ATPAccount | None, *, tick: int,
               to: str = RESERVOIR, memo: str = "death_remainder") -> None:
        self.close_agent(agent_id, tick=tick, to=to, memo=memo)
        stored = self._accounts.pop(agent_id, None)
        for acct in (account, stored):
            if acct is not None:
                acct.set_observer(None)

    def __getstate__(self) -> dict[str, Any]:
        if self._scope is not None:
            raise ATPConservationError("cannot copy a ledger inside a transfer scope")
        state = dict(self.__dict__)
        state["_touched"] = {}
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        for aid, account in self._accounts.items():
            account.set_observer(_AgentHook(self, aid, account))

    # ------------------------------------------------------------ rollback
    def _mark(self) -> tuple[int, int, int, Fraction, Fraction]:
        return (len(self._pending), self._seq, len(self._new_keys), self._scope_gross, self._scope_ulps)

    def _revert(self, mark: tuple[int, int, int, Fraction, Fraction]) -> None:
        """Undo every posting after ``mark`` exactly (Fractions reverse exactly)."""

        n, seq, nk, gross, ulps = mark
        for p in reversed(self._pending[n:]):
            self._bal[p.src] += p.amount
            self._bal[p.dst] -= p.amount
        for key in self._new_keys[nk:]:
            if key in self._bal and self._bal[key] == 0:
                del self._bal[key]
        del self._pending[n:], self._new_keys[nk:]
        self._seq, self._scope_gross, self._scope_ulps = seq, gross, ulps

    def _on_entry(self, agent_id: str, entry: ATPLedgerEntry, account: ATPAccount | None = None) -> None:
        """Book one ATPAccount entry. Called BEFORE the account commits it;
        all-or-nothing: on any error no posting survives and the account is
        untouched (it only commits after this returns)."""

        if agent_id not in self._agents:
            raise ATPConservationError(f"entry for agent {agent_id!r} with no open account")
        if self._scope is not None and account is not None and id(account) not in self._touched:
            self._touched[id(account)] = (account, account._state())
        mark = self._mark()
        try:
            self._book_entry(agent_id, entry)
        except BaseException:
            self._revert(mark)
            raise

    def _book_entry(self, agent_id: str, entry: ATPLedgerEntry) -> None:
        # The nominal amount moves against the counterparty; ATPAccount's
        # 10-digit rounding of the balance is booked separately against
        # source:rounding / sink:rounding, so it is accounted for, not hidden.
        key = agent_account(agent_id)
        label = entry.action or entry.reason
        nominal = _q(entry.amount)
        realised = _q(entry.balance_after) - _q(entry.balance_before)
        if self._scope is not None:
            # Rounding allowance: the caller's legs are float differences of
            # balances of this magnitude (one ulp each for before/after/amount).
            mag = max(abs(entry.balance_before), abs(entry.balance_after), abs(entry.amount))
            self._scope_ulps += 3 * Fraction(math.ulp(mag))
        if entry.kind == "credit":
            src = CLEARING if self._scope is not None else f"source:{label}"
            self.post(src, key, nominal, tick=entry.tick, memo=entry.reason)
            drift = realised - nominal
        else:
            dst = CLEARING if self._scope is not None else f"sink:{label}"
            self.post(key, dst, nominal, tick=entry.tick, memo=entry.reason)
            drift = realised + nominal
        if drift > 0:
            self.post("source:rounding", key, drift, tick=entry.tick, memo="balance_rounding")
        elif drift < 0:
            self.post(key, "sink:rounding", -drift, tick=entry.tick, memo="balance_rounding")

    @contextmanager
    def transfer_scope(self, name: str, *, tick: int, magnitude: float = 0.0) -> Iterator[None]:
        """Route agent debits/credits through the clearing account.

        On exit a positive clearing residual is booked to ``sink:<name>_loss``.
        A negative residual means the receiver got more than the payer paid.
        Engine callers derive both legs from float differences of balances
        (e.g. ``before - after``), and each such IEEE-754 subtraction can be
        off by half an ulp, so a receiver can gain up to a few ulps more than
        the payer lost (observed: 2^-49 after 30 HP ticks). That excess is
        bounded by three ulps of each touched balance plus
        ``ROUNDING_BOUND * gross`` (gross = sum of both legs) and is
        booked exactly from ``source:rounding``; anything larger is creation
        and raises. Either way every unit is still accounted for exactly.
        If the body raises, the scope's postings are reverted.
        """

        if self._scope is not None:
            raise ATPConservationError("nested transfer scopes are not allowed")
        self._scope = name
        self._scope_gross = Fraction(0)
        # ``magnitude``: largest float the caller's legs were computed from.
        self._scope_ulps = 3 * Fraction(math.ulp(abs(float(magnitude))))
        self._touched = {}
        mark = self._mark()
        try:
            yield
        except BaseException:
            # Atomic scope: revert every posting and every touched account,
            # so the clearing residual is 0 and ledger == accounts again.
            self._revert(mark)
            for account, state in self._touched.values():
                account._restore(state)
            raise
        finally:
            self._scope = None
            self._touched = {}
        residual = self._bal[CLEARING]
        if residual < 0:
            if -residual > ROUNDING_BOUND * self._scope_gross + self._scope_ulps:
                raise ATPConservationError(f"transfer {name!r} created {_fs(-residual)} ATP")
            self.post("source:rounding", CLEARING, -residual, tick=tick, memo=f"{name}_float_rounding")
        elif residual > 0:
            self.post(CLEARING, f"sink:{name}_loss", residual, tick=tick, memo=f"{name}_loss")

    # -------------------------------------------------------------- invariant
    def balance(self, account: str) -> Fraction:
        return self._bal.get(account, Fraction(0))

    def agent_balance(self, agent_id: str) -> Fraction:
        return self._bal[agent_account(agent_id)]

    @property
    def open_agents(self) -> frozenset[str]:
        return frozenset(self._agents)

    def totals(self) -> dict[str, Fraction]:
        src = sum((v for k, v in self._bal.items() if k.startswith("source:")), Fraction(0))
        snk = sum((v for k, v in self._bal.items() if k.startswith("sink:")), Fraction(0))
        agents = sum((self._bal[agent_account(a)] for a in self._agents), Fraction(0))
        return {"sources_in": -src, "sinks_out": snk, "agents": agents,
                "reservoir": self._bal[RESERVOIR], "clearing": self._bal[CLEARING]}

    def check(self, mirrors: Mapping[str, float] | None = None) -> None:
        """Raise ``ATPConservationError`` unless every invariant holds exactly."""

        total = sum(self._bal.values(), Fraction(0))
        if total != 0:
            raise ATPConservationError(f"ledger does not balance: sum={_fs(total)}")
        if self._bal[CLEARING] != 0 and self._scope is None:
            raise ATPConservationError("clearing account not empty outside a transfer")
        if self._bal[RESERVOIR] < 0:
            raise ATPConservationError("reservoir is negative")
        for k, v in self._bal.items():
            if k.startswith("source:") and v > 0:
                raise ATPConservationError(f"{k} has a positive balance")
            if k.startswith("sink:") and v < 0:
                raise ATPConservationError(f"{k} has a negative balance")
        if mirrors is not None:
            live = set(mirrors)
            if live != self._agents:
                ghost = sorted(self._agents - live)[:5]
                orphan = sorted(live - self._agents)[:5]
                raise ATPConservationError(f"agent set mismatch: ghost={ghost} unledgered={orphan}")
            for aid, value in mirrors.items():
                if _q(value) != self._bal[agent_account(aid)]:
                    raise ATPConservationError(
                        f"agent {aid!r} balance {value!r} != ledger {_fs(self._bal[agent_account(aid)])} (bypass)")

    def state_digest(self) -> str:
        return _sha(_canon({k: _fs(v) for k, v in sorted(self._bal.items())}))

    def close_tick(self, tick: int, mirrors: Mapping[str, float] | None = None) -> str:
        """Check the invariant, chain this tick's postings, return the new head."""

        self.check(mirrors)
        totals = self.totals()
        args = {
            "world_id": self.world_id,
            "tick": int(tick),
            "postings": [p.to_dict() for p in self._pending],
            "totals": {k: _fs(v) for k, v in sorted(totals.items())},
            "open_agents": len(self._agents),
        }
        record: dict[str, Any] = {"previous": self._head, "action": "atp_tick",
                                  "args": args, "state_digest": self.state_digest()}
        digest = _sha(_canon(record))
        record["digest"] = digest
        self._records.append(record)
        self._head = digest
        self._pending = []
        self.ticks_checked += 1
        return self._head

    @property
    def head(self) -> str:
        """Replay digest: head of the hash chain over all closed ticks."""

        return self._head

    def journal_records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._records)


def verify_ledger_chain(records: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    """Recompute the chain and every tick's conservation from the postings alone.

    Returns the head digest; raises ``ATPConservationError`` on any break.
    """

    prev = ZERO_DIGEST
    bal: dict[str, Fraction] = {}
    for i, rec in enumerate(records):
        body = {k: v for k, v in rec.items() if k != "digest"}
        if rec.get("previous") != prev or _sha(_canon(body)) != rec.get("digest"):
            raise ATPConservationError(f"hash chain broken at record {i}")
        for p in rec["args"]["postings"]:
            num, den = (int(x) for x in p["amount"].split("/"))
            amt = Fraction(num, den)
            bal[p["src"]] = bal.get(p["src"], Fraction(0)) - amt
            bal[p["dst"]] = bal.get(p["dst"], Fraction(0)) + amt
        if sum(bal.values(), Fraction(0)) != 0:
            raise ATPConservationError(f"replayed postings do not balance at record {i}")
        prev = rec["digest"]
    return prev
