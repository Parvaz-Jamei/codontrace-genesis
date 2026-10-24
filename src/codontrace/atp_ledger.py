"""Closed, absolute world ATP ledger (double-entry, exact, hash-chained).

Every ATP unit in a world lives in exactly one named account at all times:

* ``agent:<id>``      an organism's runtime balance (mirrors its ``ATPAccount``
                      or scalar ``atp`` field exactly);
* ``world:reservoir`` the world's free pool (founder and birth endowments are
                      drawn from it, death remainders return to it);
* ``world:clearing``  a transient account used inside one transfer scope
                      (e.g. host->parasite coupling); its residual is booked to
                      an explicit loss sink when the scope closes;
* ``source:<name>``   boundary inflows (resource inflow, task
                      rewards, the genesis endowment); balances are <= 0;
* ``sink:<name>``     boundary outflows (basal metabolism, birth cost,
                      dissipation); balances are >= 0;
* ``source:rounding`` / ``sink:rounding``  the residue of ``ATPAccount``'s
                      10-digit balance rounding (up to 5e-11 per entry), which
                      would otherwise create or destroy ATP silently.

Each posting moves one exact amount from one account to another, so the signed
sum of all accounts is identically zero (double entry; the same
row/column-sum-zero identity stock-flow-consistent agent-based models check
every period). Amounts are the exact double values the engine actually
stores, held as integers in units of 2^-1074, so the invariant is checked with ``==``, never with a tolerance, and the
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

Why: artificial-life resource models use explicit initial quantity, inflow
and outflow, and mass-conserving cellular automata make total matter an
invariant of the update. Cell ATP budgets partition all energy into
construction (growth) and maintenance, counted in ATP hydrolyses; the sink
names ``sink:basal`` (maintenance) and ``sink:birth`` (construction) follow it.

Representation (F6): every finite double is an integer multiple of 2^-1074,
so balances are stored as Python ints in units of 2^-1074. That is still exact
(identical to the ``Fraction`` values; every record serialises the same reduced
``"num/den"`` strings), but integer adds and compares are an order of magnitude
cheaper than ``Fraction`` arithmetic. The journal is bounded: the hash chain
head covers the whole history, while only the records since the last
checkpoint (every ``checkpoint_every`` ticks) are retained in memory, together
with that checkpoint (head + balances) so the retained window still replays
and verifies on its own. A ``record_sink`` callable can stream every record to
durable storage (e.g. a journal file) as it is closed.
"""

from __future__ import annotations

import hashlib
import json
import math
import weakref
from collections.abc import Callable, Iterable, Iterator, Mapping
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
    "ScalarATPBook",
    "WorldATPLedger",
    "verify_ledger_chain",
]

RESERVOIR = "world:reservoir"
CLEARING = "world:clearing"
GENESIS_SOURCE = "source:genesis"
ZERO_DIGEST = "0" * 64
_EXP = 1074  # every finite double is k * 2**-1074
_ONE = 1 << _EXP
_EXP_PLUS_1 = _EXP + 1
DEFAULT_CHECKPOINT_EVERY = 256


class ATPConservationError(AssertionError):
    """The closed ATP balance invariant failed."""


def _u(value: float | int | Fraction) -> int:
    """Exact amount in units of 2**-1074."""

    if type(value) is float:
        try:
            n, d = value.as_integer_ratio()
        except (OverflowError, ValueError):
            raise ValueError("ATP amount must be finite") from None
        return n << (_EXP_PLUS_1 - d.bit_length())
    if isinstance(value, bool):
        raise TypeError("ATP amount must be numeric, not bool")
    if isinstance(value, float):
        return _u(float(value))
    if isinstance(value, int):
        return value << _EXP
    if isinstance(value, Fraction):
        d = value.denominator
        if d & (d - 1) or d.bit_length() - 1 > _EXP:
            raise ValueError("ATP amount must be a dyadic rational (a float value)")
        return value.numerator << (_EXP - (d.bit_length() - 1))
    return _u(float(value))


def _q(value: float | int | Fraction) -> Fraction:
    return Fraction(_u(value), _ONE)


def _fu(units: int) -> str:
    """Reduced ``num/den`` string of ``units * 2**-1074`` (same as Fraction)."""

    if units == 0:
        return "0/1"
    mag = units if units > 0 else -units
    shift = min((mag & -mag).bit_length() - 1, _EXP)
    return f"{units >> shift}/{1 << (_EXP - shift)}"


def _fs(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canon(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse(text: str) -> int:
    num, den = (int(x) for x in text.split("/"))
    return _u(Fraction(num, den))


def agent_account(agent_id: str) -> str:
    return f"agent:{agent_id}"


class _AgentHook:
    """Observer binding one ATPAccount to the ledger (never serialized itself)."""

    __slots__ = ("account", "agent_id", "ledger")

    def __init__(self, ledger: WorldATPLedger, agent_id: str, account: ATPAccount | None = None) -> None:
        self.ledger = ledger
        self.agent_id = agent_id
        self.account = account

    def __call__(self, entry: ATPLedgerEntry) -> None:
        self.ledger._on_entry(self.agent_id, entry, self.account)

    def __reduce__(self) -> tuple[object, ...]:
        raise TypeError("an attached ATP ledger hook cannot be serialized or copied; detach first")


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


# Internal posting tuple: (seq, tick, src, dst, units, memo)
_Post = tuple[int, int, str, str, int, str]


class WorldATPLedger:
    """One world's closed ATP ledger. See the module docstring."""

    def __init__(self, world_id: str = "world", *, checkpoint_every: int = DEFAULT_CHECKPOINT_EVERY,
                 record_sink: Callable[[dict[str, Any]], None] | None = None) -> None:
        if checkpoint_every < 1:
            raise ValueError("checkpoint_every must be >= 1")
        self.world_id = str(world_id)
        self.checkpoint_every = int(checkpoint_every)
        self.record_sink = record_sink
        self._bal: dict[str, int] = {RESERVOIR: 0, CLEARING: 0}
        self._bounded: set[str] = set()  # source:* / sink:* keys (sign-checked)
        self._agents: set[str] = set()
        self._pending: list[_Post] = []
        self._seq = 0
        self._scope: str | None = None
        self._scope_gross = 0
        self._scope_ulps = 0
        self._scope_expect: float | None = None
        # (mark, account, entry_count before commit) of the last pushed entry;
        # if the account never committed it, its postings are reverted.
        self._inflight: tuple[tuple[int, int, int, int, int], ATPAccount, int] | None = None
        self._new_keys: list[str] = []
        self._touched: dict[int, tuple[ATPAccount, Any]] = {}
        # Attached ATPAccounts. Copying/pickling an account alone detaches it;
        # copying/pickling the ledger carries its accounts and re-attaches them.
        self._accounts: dict[str, ATPAccount] = {}
        # Pull-mode cursors (sync_accounts): agent -> (entries booked, last entry).
        self._cursors: dict[str, tuple[int, Any]] = {}
        self._records: list[dict[str, Any]] = []
        self._base: dict[str, Any] | None = None  # checkpoint the window starts at
        self._head = ZERO_DIGEST
        self.ticks_checked = 0

    # ------------------------------------------------------------------ core
    def post(self, src: str, dst: str, amount: float | Fraction, *, tick: int, memo: str) -> None:
        """Move ``amount`` (>= 0) from ``src`` to ``dst``. Zero is a no-op."""

        self._post_u(src, dst, _u(amount), tick, memo)

    def _settle_inflight(self) -> None:
        """Two-phase push: an entry's postings stand only once its account
        has committed the entry. If anything between the hook and the
        account's commit raised (e.g. a wrapping observer), the account is
        unchanged, so the postings are reverted here, before any other
        ledger operation can observe them."""

        inflight, self._inflight = self._inflight, None
        if inflight is not None:
            mark, account, count = inflight
            if account.entry_count() == count:
                self._revert(mark)

    def _post_u(self, src: str, dst: str, amt: int, tick: int, memo: str) -> None:
        self._settle_inflight()
        if amt < 0:
            raise ValueError("posting amount must be >= 0; swap src/dst")
        if amt == 0:
            return
        bal = self._bal
        for acct in (src, dst):
            if acct not in bal:
                self._check_name(acct)
                self._new_keys.append(acct)
                bal[acct] = 0
                if acct.startswith(("source:", "sink:")):
                    self._bounded.add(acct)
        bal[src] -= amt
        bal[dst] += amt
        if src == CLEARING or dst == CLEARING:
            self._scope_gross += amt
        self._pending.append((self._seq, int(tick), src, dst, amt, str(memo)))
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
        self._post_u(source, RESERVOIR, _u(amount), tick, "reservoir_inflow")

    def draw_from_reservoir(self, dst: str, amount: float | Fraction, *, tick: int, memo: str,
                            inflow_source: str = "source:inflow") -> None:
        """Pay ``amount`` from the reservoir; any shortfall first enters as explicit inflow."""

        amt = _u(amount)
        short = amt - self._bal[RESERVOIR]
        if short > 0:
            if not inflow_source.startswith("source:"):
                raise ValueError("reservoir inflow must come from a source:* account")
            self._post_u(inflow_source, RESERVOIR, short, tick, "reservoir_inflow")
        self._post_u(RESERVOIR, dst, amt, tick, memo)

    # ----------------------------------------------------------------- agents
    def open_agent(self, agent_id: str, balance: float | Fraction, *, tick: int,
                   funded_from: str = RESERVOIR, memo: str = "endowment") -> None:
        """Open an agent account and fund its starting balance."""

        if self._scope is not None:
            raise ATPConservationError("cannot open an agent account inside a transfer scope")
        if agent_id in self._agents:
            raise ATPConservationError(f"agent {agent_id!r} already has an account")
        self._agents.add(agent_id)
        self._bal[agent_account(agent_id)] = 0
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
            self._post_u(key, to, rem, tick, memo)
        elif rem < 0:
            # A negative scalar balance (legacy experiments allow ATP debt) is
            # written off from an explicit source, never from the reservoir.
            self._post_u("source:debt_writeoff", key, -rem, tick, memo + "_debt")
        self._agents.discard(agent_id)
        del self._bal[key]

    def adjust(self, agent_id: str, current: float, delta: float, *, tick: int,
               source: str, sink: str) -> float:
        """Return ``current + delta`` (the engine's own float arithmetic) and book
        the exact realised change from ``source`` (gain) or to ``sink`` (loss)."""

        new = current + delta
        realised = _u(new) - _u(current)
        if realised > 0:
            self._post_u(source, agent_account(agent_id), realised, tick, source)
        elif realised < 0:
            self._post_u(agent_account(agent_id), sink, -realised, tick, sink)
        return new

    def settle(self, agent_id: str, current: float, new: float, *, tick: int,
               source: str, sink: str) -> float:
        """Book the exact change ``current -> new`` (a value the engine already
        computed with its own arithmetic) and return ``new`` unchanged."""

        realised = _u(new) - _u(current)
        if realised > 0:
            self._post_u(source, agent_account(agent_id), realised, tick, source)
        elif realised < 0:
            self._post_u(agent_account(agent_id), sink, -realised, tick, sink)
        return new

    def transfer(self, payer: str, payee: str, paid: float, received: float, *, tick: int,
                 name: str) -> None:
        """Agent-to-agent transfer whose legs the engine computed as floats:
        ``paid`` leaves ``payer``, ``received`` reaches ``payee``, the exact
        difference goes to ``sink:<name>_loss``; a payee that got more than the
        payer paid raises (no tolerance)."""

        with self.transfer_scope(name, tick=tick, magnitude=max(abs(paid), abs(received))):
            self._post_u(agent_account(payer), CLEARING, _u(paid), tick, name)
            self._post_u(CLEARING, agent_account(payee), _u(received), tick, name)

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
        state["record_sink"] = None  # a sink is an external resource; not copied
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
        for aid, account in self._accounts.items():
            account.set_observer(_AgentHook(self, aid, account))

    # ------------------------------------------------- pull-mode (functional)
    def reissue_accounts(self, accounts: Mapping[str, ATPAccount], *, tick: int, reason: str,
                         declared: Mapping[str, float]) -> dict[str, float]:
        """Explicitly replace accounts that a declared boundary rebuilt under the same id.

        Only for the boundaries in ``REISSUE_REASONS`` (the phase-3 host
        hold, which puts the locked hosts back with their birth reserve).
        ``declared`` is the boundary's own snapshot: id -> balance it
        installed. Every id whose history no longer extends what was booked,
        and every new id, must be declared and hold exactly its declared
        balance; it is closed to ``sink:<reason>`` and reopened from
        ``source:<reason>`` with its history replayed. Ids that vanished are
        closed to ``sink:<reason>``. Anything else raises, so a reissue can
        not create or remove more than the boundary declares. Plain
        ``sync_accounts`` still raises on any rewrite.
        """

        if reason not in REISSUE_REASONS:
            raise ATPConservationError(f"undeclared reissue boundary {reason!r}")
        if declared.keys() - accounts.keys():
            raise ATPConservationError(f"{reason}: declared ids missing: {sorted(declared.keys() - accounts.keys())}")
        rewritten: list[str] = []
        for aid, account in sorted(accounts.items()):
            cur = self._cursors.get(aid)
            if cur is not None:
                start, last = cur
                n_now = account.entry_count()
                if not (n_now < start or (start > 0 and account.entry_at(start - 1) != last)):
                    continue
            rewritten.append(aid)
        for aid in rewritten:
            account = accounts[aid]
            if aid not in declared:
                raise ATPConservationError(f"{reason}: {aid!r} rebuilt but not declared by the boundary")
            if _u(account.current_atp) != _u(float(declared[aid])):
                raise ATPConservationError(
                    f"{reason}: {aid!r} reopened at {account.current_atp!r}, declared {declared[aid]!r}")
        for aid in rewritten:
            if aid in self._cursors:
                del self._cursors[aid]
                self.close_agent(aid, tick=tick, to=f"sink:{reason}", memo=reason)
        return self.sync_accounts(accounts, tick=tick, open_from=f"source:{reason}", close_to=f"sink:{reason}")

    def sync_accounts(self, accounts: Mapping[str, ATPAccount], *, tick: int,
                      open_from: str = "source:birth_endowment",
                      close_to: str = "sink:death_remainder") -> dict[str, float]:
        """Book every ``ATPAccount`` entry not yet booked, by agent id.

        For engines that rebuild organisms each step (``to_dict``/``from_dict``
        clones carry the full append-only entry history), so a push observer
        would be lost on every clone. Each entry is booked exactly like the
        push observer does (debit -> ``sink:<action>``, credit ->
        ``source:<action>``, 10-digit rounding -> ``*:rounding``).

        * an id seen for the first time is opened with its ``initial_atp``
          from ``open_from`` and its whole history is replayed;
        * an id that disappeared is closed (remainder to ``close_to``);
        * an account whose history no longer extends what was booked (fewer
          entries, or a different entry at the cursor) is a rewrite and
          raises; so does a balance that differs from its booked history.

        Returns the mirrors (agent id -> current balance) for ``close_tick``.
        """

        if self._scope is not None:
            raise ATPConservationError("sync_accounts inside a transfer scope")
        for aid in sorted(self._cursors.keys() - accounts.keys()):
            del self._cursors[aid]
            if aid in self._agents:
                self.close_agent(aid, tick=tick, to=close_to)
        mirrors: dict[str, float] = {}
        for aid, account in accounts.items():
            n_now = account.entry_count()
            cur = self._cursors.get(aid)
            if cur is None:
                if aid in self._agents:
                    raise ATPConservationError(f"agent {aid!r} is already owned by another booking path")
                self.open_agent(aid, account.initial_atp, tick=tick, funded_from=open_from,
                                memo="birth_endowment" if open_from == "source:birth_endowment" else "opened")
                start = 0
            else:
                start, last = cur
                if n_now < start or (start > 0 and account.entry_at(start - 1) != last):
                    raise ATPConservationError(f"agent {aid!r}: ATP history was rewritten (bypass)")
            if n_now > start:
                mark = self._mark()
                try:
                    for entry in account.entries_since(start):
                        self._book_entry(aid, entry)
                except BaseException:
                    self._revert(mark)
                    raise
                self._cursors[aid] = (n_now, account.entry_at(n_now - 1))
            elif cur is None:
                self._cursors[aid] = (0, None)
            mirrors[aid] = account.current_atp
        return mirrors

    # ------------------------------------------------------------ rollback
    def _mark(self) -> tuple[int, int, int, int, int]:
        return (len(self._pending), self._seq, len(self._new_keys), self._scope_gross, self._scope_ulps)

    def _revert(self, mark: tuple[int, int, int, int, int]) -> None:
        """Undo every posting after ``mark`` exactly (integer units reverse exactly)."""

        self._inflight = None

        n, seq, nk, gross, ulps = mark
        for p in reversed(self._pending[n:]):
            self._bal[p[2]] += p[4]
            self._bal[p[3]] -= p[4]
        for key in self._new_keys[nk:]:
            if self._bal.get(key) == 0:
                del self._bal[key]
                self._bounded.discard(key)
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
        self._settle_inflight()
        mark = self._mark()
        try:
            self._book_entry(agent_id, entry)
        except BaseException:
            self._revert(mark)
            raise
        if account is not None:
            self._inflight = (mark, account, account.entry_count())

    def _book_entry(self, agent_id: str, entry: ATPLedgerEntry) -> None:
        # The nominal amount moves against the counterparty; ATPAccount's
        # 10-digit rounding of the balance is booked separately against
        # source:rounding / sink:rounding, so it is accounted for, not hidden.
        key = agent_account(agent_id)
        label = (entry.action or entry.reason).split(":", 1)[0]
        nominal = _u(entry.amount)
        realised = _u(entry.balance_after) - _u(entry.balance_before)
        self._check_balance_rounding(entry)
        if entry.kind == "credit":
            src = CLEARING if self._scope is not None else f"source:{label}"
            self._post_u(src, key, nominal, entry.tick, entry.reason)
            drift = realised - nominal
        else:
            dst = CLEARING if self._scope is not None else f"sink:{label}"
            self._post_u(key, dst, nominal, entry.tick, entry.reason)
            drift = realised + nominal
        if drift > 0:
            self._post_u("source:rounding", key, drift, entry.tick, "balance_rounding")
        elif drift < 0:
            self._post_u(key, "sink:rounding", -drift, entry.tick, "balance_rounding")

    @staticmethod
    def _check_balance_rounding(entry: ATPLedgerEntry) -> None:
        """The realised delta may differ from the nominal amount only by
        ATPAccount's own arithmetic: ``after = round(fl(before +/- amount), 10)``.
        So the float step is at most half an ulp (``float_error``) and the
        decimal rounding at most 0.5e-10 plus half an ulp of ``after``;
        checked exactly in integer units. Anything more raises."""

        amount = entry.amount if entry.kind == "credit" else -entry.amount
        x = entry.balance_before + amount
        float_error(x, entry.balance_before, amount)
        d = abs(_u(entry.balance_after) - _u(x))
        if (2 * d - _ulp_units(entry.balance_after)) * 10**10 > _ONE:
            raise ATPConservationError(
                f"entry {entry.entry_id}: balance moved {_fu(_u(entry.balance_after) - _u(entry.balance_before))}"
                f" for a {entry.kind} of {entry.amount!r} (more than its 10-digit rounding)")

    @contextmanager
    def transfer_scope(self, name: str, *, tick: int, magnitude: float = 0.0,
                       expected_loss: float | None = None) -> Iterator[None]:
        """Route agent debits/credits through the clearing account, exactly.

        On exit the clearing residual must be explained exactly, with no
        tolerance window:

        * with ``expected_loss`` (the loss the engine itself computed), the
          residual must equal it exactly; it goes to ``sink:<name>_loss``;
        * without it, a residual >= 0 goes to ``sink:<name>_loss`` and a
          negative residual (receiver got more than the payer paid) raises.

        Float rounding inside the caller's arithmetic is not forgiven but
        booked: the caller reports each rounded operation's exact error with
        ``book_rounding`` (see ``float_error``), which posts it between
        ``world:clearing`` and ``source:rounding`` / ``sink:rounding``.
        Exact because every finite binary64 is an integer multiple of 2^-1074
        and the error of a rounded sum is itself
        representable. ``magnitude`` is accepted for API stability and unused.
        If the body raises, the scope's postings are reverted and every
        touched ATPAccount is restored (atomic transfer).
        """

        del magnitude
        if self._scope is not None:
            raise ATPConservationError("nested transfer scopes are not allowed")
        self._scope = name
        self._scope_gross = 0
        self._scope_ulps = 0
        self._scope_expect = expected_loss
        self._touched = {}
        mark = self._mark()
        try:
            yield
        except BaseException:
            self._revert(mark)
            for account, state in self._touched.values():
                account._restore(state)
            raise
        finally:
            self._scope = None
            touched, self._touched = self._touched, {}
        self._settle_inflight()
        residual = self._bal[CLEARING]
        expected_loss, self._scope_expect = self._scope_expect, None
        try:
            if expected_loss is not None and residual != _u(expected_loss):
                raise ATPConservationError(
                    f"transfer {name!r}: clearing residual {_fu(residual)} != engine loss "
                    f"{_fu(_u(expected_loss))} (creation or destruction)")
            if residual < 0:
                raise ATPConservationError(f"transfer {name!r} created {_fu(-residual)} ATP")
        except ATPConservationError:
            self._revert(mark)
            for account, state in touched.values():
                account._restore(state)
            raise
        if residual > 0:
            self._post_u(CLEARING, f"sink:{name}_loss", residual, tick, f"{name}_loss")

    def expect_loss(self, loss: float) -> None:
        """Inside a scope: the clearing residual must equal ``loss`` exactly."""

        if self._scope is None:
            raise ATPConservationError("expect_loss outside a transfer scope")
        self._scope_expect = loss

    def book_rounding(self, err_units: int, *, tick: int, memo: str = "float_rounding") -> None:
        """Book one rounded float operation's exact error (units of 2^-1074)
        inside a transfer scope: ``err > 0`` leaves clearing to
        ``sink:rounding``, ``err < 0`` enters clearing from ``source:rounding``."""

        if self._scope is None:
            raise ATPConservationError("book_rounding outside a transfer scope")
        if err_units > 0:
            self._post_u(CLEARING, "sink:rounding", err_units, tick, memo)
        elif err_units < 0:
            self._post_u("source:rounding", CLEARING, -err_units, tick, memo)

    # -------------------------------------------------------------- invariant
    def balance(self, account: str) -> Fraction:
        self._settle_inflight()
        return Fraction(self._bal.get(account, 0), _ONE)

    def agent_balance(self, agent_id: str) -> Fraction:
        self._settle_inflight()
        return Fraction(self._bal[agent_account(agent_id)], _ONE)

    @property
    def open_agents(self) -> frozenset[str]:
        return frozenset(self._agents)

    def has_agent(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def _totals_u(self) -> dict[str, int]:
        src = sum(v for k, v in self._bal.items() if k.startswith("source:"))
        snk = sum(v for k, v in self._bal.items() if k.startswith("sink:"))
        agents = sum(self._bal[agent_account(a)] for a in self._agents)
        return {"sources_in": -src, "sinks_out": snk, "agents": agents,
                "reservoir": self._bal[RESERVOIR], "clearing": self._bal[CLEARING]}

    def totals(self) -> dict[str, Fraction]:
        self._settle_inflight()
        return {k: Fraction(v, _ONE) for k, v in self._totals_u().items()}

    def check(self, mirrors: Mapping[str, float] | None = None) -> None:
        """Raise ``ATPConservationError`` unless every invariant holds exactly."""

        self._settle_inflight()

        bal = self._bal
        total = sum(bal.values())
        if total != 0:
            raise ATPConservationError(f"ledger does not balance: sum={_fu(total)}")
        if bal[CLEARING] != 0 and self._scope is None:
            raise ATPConservationError("clearing account not empty outside a transfer")
        if bal[RESERVOIR] < 0:
            raise ATPConservationError("reservoir is negative")
        for k in self._bounded:
            v = bal.get(k, 0)
            if v > 0 and k.startswith("source:"):
                raise ATPConservationError(f"{k} has a positive balance")
            if v < 0 and k.startswith("sink:"):
                raise ATPConservationError(f"{k} has a negative balance")
        if mirrors is not None:
            if len(mirrors) != len(self._agents) or not self._agents.issuperset(mirrors):
                live = set(mirrors)
                ghost = sorted(self._agents - live)[:5]
                orphan = sorted(live - self._agents)[:5]
                raise ATPConservationError(f"agent set mismatch: ghost={ghost} unledgered={orphan}")
            for aid, value in mirrors.items():
                if _u(value) != bal["agent:" + aid]:
                    raise ATPConservationError(
                        f"agent {aid!r} balance {value!r} != ledger {_fu(bal['agent:' + aid])} (bypass)")

    def check_agents(self, mirrors: Mapping[str, float]) -> None:
        """Cheap mid-tick bypass check: agent set and balances only (the
        global sum and sign checks run in ``check``/``close_tick``)."""

        self._settle_inflight()

        bal = self._bal
        if len(mirrors) != len(self._agents) or not self._agents.issuperset(mirrors):
            self.check(mirrors)
        for aid, value in mirrors.items():
            if _u(value) != bal["agent:" + aid]:
                self.check(mirrors)

    def _balances_str(self) -> dict[str, str]:
        return {k: _fu(v) for k, v in sorted(self._bal.items())}

    def state_digest(self) -> str:
        self._settle_inflight()
        return _sha(_canon(self._balances_str()))

    def close_tick(self, tick: int, mirrors: Mapping[str, float] | None = None) -> str:
        """Check the invariant, chain this tick's postings, return the new head."""

        self.check(mirrors)
        totals = self._totals_u()
        args = {
            "world_id": self.world_id,
            "tick": int(tick),
            "postings": [{"seq": p[0], "tick": p[1], "src": p[2], "dst": p[3], "amount": _fu(p[4]),
                          "memo": p[5]} for p in self._pending],
            "totals": {k: _fu(v) for k, v in sorted(totals.items())},
            "open_agents": len(self._agents),
        }
        balances = self._balances_str()
        record: dict[str, Any] = {"previous": self._head, "action": "atp_tick",
                                  "args": args, "state_digest": _sha(_canon(balances))}
        digest = _sha(_canon(record))
        record["digest"] = digest
        self._head = digest
        self._pending = []
        self._new_keys = []
        self.ticks_checked += 1
        if self.record_sink is not None:
            self.record_sink(record)
        self._records.append(record)
        if self.ticks_checked % self.checkpoint_every == 0:
            # Bounded journal: drop the retained window and start a new one at
            # this checkpoint (head + exact balances), so memory is O(window)
            # and journal_records() still verifies from journal_base().
            self._base = {"head": digest, "ticks_checked": self.ticks_checked,
                          "balances": balances}
            self._records = []
        return self._head

    @property
    def head(self) -> str:
        """Replay digest: head of the hash chain over all closed ticks."""

        return self._head

    def journal_records(self) -> tuple[dict[str, Any], ...]:
        """Records closed since ``journal_base()`` (the whole chain if None)."""

        return tuple(self._records)

    def journal_base(self) -> dict[str, Any] | None:
        """Checkpoint the retained window starts at (None = genesis)."""

        return None if self._base is None else dict(self._base)


def verify_ledger_chain(records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
                        base: Mapping[str, Any] | None = None) -> str:
    """Recompute the chain and every tick's conservation from the postings alone.

    ``base`` is a checkpoint from ``WorldATPLedger.journal_base()`` when the
    records are a bounded window. Returns the head digest; raises
    ``ATPConservationError`` on any break.
    """

    if base is None:
        prev, bal = ZERO_DIGEST, {}
    else:
        prev = str(base["head"])
        bal = {k: _parse(v) for k, v in base["balances"].items()}
        if sum(bal.values()) != 0:
            raise ATPConservationError("checkpoint balances do not sum to zero")
    for i, rec in enumerate(records):
        body = {k: v for k, v in rec.items() if k != "digest"}
        if rec.get("previous") != prev or _sha(_canon(body)) != rec.get("digest"):
            raise ATPConservationError(f"hash chain broken at record {i}")
        for p in rec["args"]["postings"]:
            amt = _parse(p["amount"])
            bal[p["src"]] = bal.get(p["src"], 0) - amt
            bal[p["dst"]] = bal.get(p["dst"], 0) + amt
        if sum(bal.values()) != 0:
            raise ATPConservationError(f"replayed postings do not balance at record {i}")
        prev = rec["digest"]
    return prev


class ScalarATPBook:
    """World ledger for runners whose ATP is a plain float field on
    per-individual objects (T02/T03/T05).

    Each object gets a stable ledger id on first sight. The id is kept in
    the book, not on the object, so model objects are never modified: a map
    from ``id(obj)`` to ``(weakref, ledger id)``. The weakref callback drops
    the entry when the object is collected, and lookups check the weakref
    still points at the same object, so a reused ``id()`` never inherits an
    old ledger id. ``settle`` opens new objects (births, founders), closes
    vanished ones (deaths) and checks every field against the ledger
    exactly, so a write that skipped ``assign`` is caught at the next
    settle. ``carry`` keeps an id when a runner rebuilds an object that is
    the same individual (migration).

    Copying or serializing the book together with its population keeps each
    id with the matching copied object: the state is written as
    ``(object, id)`` pairs and the map is rebuilt on load.

    The book and its population must be copied together, in one call
    (``copy.deepcopy((book, population))``, or one serialization of both). A book
    copied on its own binds its ids to private copies of the individuals,
    not to the real ones, so a later ``settle`` would close every open
    account as a death and reopen each individual as a birth: balances still
    add up but lineage is lost. To catch this, the first ``settle`` after a
    copy or load raises ``ATPConservationError`` if the book has open
    accounts, the population is not empty and not one of its members has an
    id in the book. Note that copying the book alone also copies every live
    individual it still tracks.
    """

    def __init__(self, world_id: str, fields: tuple[str, ...] = ("atp",), *,
                 ledger: WorldATPLedger | None = None) -> None:
        self.ledger = WorldATPLedger(world_id) if ledger is None else ledger
        self.fields = tuple(fields)
        self._next = 0
        self._ids: dict[int, tuple[weakref.ref[Any], str]] = {}
        self._restored = False

    def _bind(self, obj: object, lid: str) -> None:
        key = id(obj)
        ids = self._ids

        def _drop(ref: weakref.ref[Any], key: int = key) -> None:
            entry = ids.get(key)
            if entry is not None and entry[0] is ref:
                del ids[key]

        ids[key] = (weakref.ref(obj, _drop), lid)

    def _lookup(self, obj: object) -> str | None:
        entry = self._ids.get(id(obj))
        if entry is not None and entry[0]() is obj:
            return entry[1]
        return None

    def _id(self, obj: object) -> str:
        lid = self._lookup(obj)
        if lid is None:
            lid = f"i{self._next}"
            self._next += 1
            self._bind(obj, lid)
        return lid

    def carry(self, new: object, old: object) -> None:
        """``new`` is the same individual as ``old`` (same balances)."""

        self._bind(new, self._id(old))

    def __getstate__(self) -> dict[str, Any]:
        state = {k: v for k, v in self.__dict__.items() if k not in ("_ids", "_restored")}
        live = [(ref(), lid) for ref, lid in self._ids.values()]
        state["_id_pairs"] = [(o, lid) for o, lid in live if o is not None]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        pairs: list[tuple[object, str]] = state.pop("_id_pairs", [])
        self.__dict__.update(state)
        self._ids = {}
        for obj, lid in pairs:
            self._bind(obj, lid)
        self._restored = True

    def _key(self, obj: object, field: str) -> str:
        return f"{self._id(obj)}:{field}" if len(self.fields) > 1 else self._id(obj)

    def assign(self, obj: object, field: str, new: float, *, tick: int,
               source: str, sink: str) -> float:
        """Book ``obj.field -> new`` exactly; the caller stores the return."""

        key = self._key(obj, field)
        if not self.ledger.has_agent(key):
            raise ATPConservationError(f"assign to unledgered individual {key!r}")
        return self.ledger.settle(key, float(getattr(obj, field)), new, tick=tick,
                                  source=source, sink=sink)

    def settle(self, population: Iterable[object], *, tick: int, close: bool = True,
               open_from: str = "source:birth_endowment",
               close_to: str = "sink:death_remainder") -> str | None:
        led = self.ledger
        population = list(population)
        if self._restored:
            if (led.open_agents and population
                    and all(self._lookup(obj) is None for obj in population)):
                raise ATPConservationError(
                    "ScalarATPBook was copied or loaded without its population: none of "
                    f"the {len(population)} individuals has an id in this book, but "
                    f"{len(led.open_agents)} accounts are open; copy the book and the "
                    "population together in one call")
            self._restored = False
        mirrors: dict[str, float] = {}
        for obj in population:
            for field in self.fields:
                key = self._key(obj, field)
                value = float(getattr(obj, field))
                if key in mirrors:
                    raise ATPConservationError(f"one individual listed twice: {key!r}")
                if not led.has_agent(key):
                    led.open_agent(key, value, tick=tick, funded_from=open_from, memo="birth")
                mirrors[key] = value
        for key in sorted(led.open_agents - set(mirrors)):
            led.close_agent(key, tick=tick, to=close_to)
        if close:
            return led.close_tick(tick, mirrors)
        led.check(mirrors)
        return None


def _ulp_units(x: float) -> int:
    """``ulp(x)`` in units of 2^-1074 (exact: an ulp is a power of two)."""

    return _u(math.ulp(x))


REISSUE_REASONS = frozenset({"host_hold"})
"""Declared boundaries allowed to rebuild accounts under the same id."""


def float_error(result: float, *terms: float) -> int:
    """Exact rounding error, in units of 2^-1074, of ``result = fl(sum(terms))``
    (pass ``-b`` for a subtraction): ``sum(terms) - result``, computed in
    integers, so it is exact for every finite double.

    ``result`` must be ONE correctly rounded (round-to-nearest) operation on
    the terms, so the error is at most half an ulp of ``result``. Anything
    larger is not rounding but created or destroyed ATP, and raises; the
    check is exact (``2*|err| <= ulp(result)`` in integer units)."""

    err = sum(_u(t) for t in terms) - _u(result)
    if 2 * abs(err) > _ulp_units(result):
        raise ATPConservationError(
            f"{_fu(err)} ATP is not a rounding error of {result!r} (more than half an ulp)")
    return err


def coupling_rounding_units(source_before: float, source_after: float, target_before: float,
                            target_after: float, requested: float, accepted: float, loss: float,
                            paid: float | None = None, gained: float | None = None) -> int:
    """Signed sum of the exact rounding errors that separate a transfer's
    clearing residual from the engine's own ``loss``.

    Engine arithmetic: ``source_after = fl(source_before - requested)``,
    ``target_after = fl(target_before + accepted)``,
    ``accepted = fl(requested - loss)`` and, when the booked legs are float
    differences, ``paid = fl(source_before - source_after)``,
    ``gained = fl(target_after - target_before)``. Then exactly
    ``paid_booked - gained_booked = loss + returned value``.
    """

    e_sa = float_error(source_after, source_before, -requested)
    e_ta = float_error(target_after, target_before, accepted)
    e_acc = float_error(accepted, requested, -loss)
    total = e_sa + e_ta + e_acc
    if paid is not None:
        total -= float_error(paid, source_before, -source_after)
    if gained is not None:
        total += float_error(gained, target_after, -target_before)
    return total

