"""Edits of docs/prereg/jr5/DEVIATIONS.md used by the JR5 log-integrity tests.

Each case is what someone would write who edits the log and then refreshes
``record.json`` so the record is not stale. Both log checks (the
preregistration copy and the claimgate copy) must refuse every case in
``ATTACKS`` with the message fragment given, and accept ``valid_append``.
The fragments are the error texts of ``verify_deviations_log``; the
expected outcome follows from the rule each case breaks, named in its
comment.
"""

from __future__ import annotations

import re
from collections.abc import Callable

PLAN_PIN = "577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382"
LOCK_START = "633aa9c84336e946fc7d8e3e2178acc658caeed791f5a484bbe7d0814264b757"
RUNS = (
    "- Runs: no JR5 run has started, the pilot included, so no endpoint moves to exploratory. "
    "This is the author's declaration. What the repository shows at this entry: no JR5 run "
    "script, campaign module or run output is committed (no path under `runs/` names JR5, "
    "and the only JR5 script is the E1 power simulation, which runs no engine arm).\n"
)


def entry(heading: str, digest_lines: str) -> str:
    """One log entry in the layout of the real log, preceded by a blank line."""

    return f"\n## {heading}\n\n- Reason: test-only entry; locked plan files unchanged.\n{digest_lines}{RUNS}"


def pin_line(old: str = PLAN_PIN, new: str = PLAN_PIN, indent: str = "") -> str:
    return f"{indent}- Record digest: `{old}` -> `{new}`\n"


def _starts(text: str) -> list[int]:
    return [m.start() for m in re.finditer(r"^## ", text, re.M)]


def valid_append(text: str) -> str:
    """A well-formed entry appended after the accepted log: accepted."""

    return text + entry("2099-01-01: synthetic log-only entry", pin_line())


def _delete_last_two(text: str) -> str:
    # Deletion: the two 2026-11-09 entries after the main checkpoint go; the
    # rest still chains and ends at the plan pin, but the log is shorter than
    # the last checkpoint.
    return text[: _starts(text)[-2] - 1]


def _delete_lock_start(text: str) -> str:
    # Lock-start deletion: the first remaining entry's old digest is a4f76d60...,
    # not the lock digest 633aa9c8....
    s = _starts(text)
    return text[: s[0]] + text[s[1] :]


def _rewrite_reason(text: str) -> str:
    # Reason rewrite in the third entry: digests and chain unchanged, only the
    # bytes inside an accepted checkpoint differ.
    third = _starts(text)[2]
    at = text.index("- Reason: ", third) + len("- Reason: ")
    return text[:at] + "nothing to report. " + text[at:]


def _rewrite_lock_start_reason(text: str) -> str:
    # The lock-start entry keeps its digest line but its Reason changes, so its
    # pinned text hash no longer matches.
    at = text.index("- Reason: ") + len("- Reason: ")
    return text[:at] + "minor fixes. " + text[at:]


def _full_replacement(text: str) -> str:
    # Full replacement by one fabricated entry that ends at the plan pin.
    return "# JR5 deviations\n" + entry("2026-11-01: lock", pin_line("a" * 64, PLAN_PIN))


def _forged_lock_start(text: str) -> str:
    # Full replacement by one entry that starts at the real lock digest but is
    # not the lock-start entry's text.
    return "# JR5 deviations\n" + entry("2026-11-01: lock", pin_line(LOCK_START, PLAN_PIN))


def _chain_break_in_append(text: str) -> str:
    # The appended entry's old digest is not the previous entry's new digest.
    return text + entry("2099-01-01: chain break", pin_line(old="b" * 64))


def _wrong_last_digest(text: str) -> str:
    # The appended entry chains but names another plan digest.
    return text + entry("2099-01-01: other plan", pin_line(new="c" * 64))


def _two_digest_lines(text: str) -> str:
    # One appended entry with two record-digest lines; the second would hide
    # a plan change behind the first.
    return text + entry("2099-01-01: two lines", pin_line() + pin_line(new="d" * 64))


def _indented_digest_line(text: str) -> str:
    # The only digest line of the appended entry does not start the line;
    # an unanchored pattern would read it, the anchored one finds none.
    return text + entry("2099-01-01: indented", pin_line(indent="  "))


def _stray_text_after_checkpoint(text: str) -> str:
    # Text that is not a new entry, written straight after the last accepted
    # entry, extends that entry instead of appending one.
    return text + "- Note: added later to the last accepted entry.\n" + entry("2099-01-01: after", pin_line())


ATTACKS: dict[str, tuple[Callable[[str], str], str]] = {
    "deletion": (_delete_last_two, "does not start with the accepted log"),
    "lock_start_deletion": (_delete_lock_start, "does not start at the lock digest"),
    "reason_rewrite": (_rewrite_reason, "does not start with the accepted log"),
    "lock_start_reason_rewrite": (_rewrite_lock_start_reason, "not the pinned lock-start entry"),
    "full_replacement": (_full_replacement, "does not start at the lock digest"),
    "forged_lock_start": (_forged_lock_start, "not the pinned lock-start entry"),
    "chain_break_in_append": (_chain_break_in_append, "do not chain"),
    "wrong_last_digest": (_wrong_last_digest, "does not name the locked plan digest"),
    "two_digest_lines": (_two_digest_lines, "exactly one record-digest line"),
    "indented_digest_line": (_indented_digest_line, "exactly one record-digest line"),
    "stray_text_after_checkpoint": (_stray_text_after_checkpoint, "must be whole appended entries"),
}
