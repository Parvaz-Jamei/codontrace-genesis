"""T01/T04 ATP goes through the world ledger; grep-enforced no-bypass rules."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.atp_ledger import ATPConservationError, verify_ledger_chain
from codontrace.experiments.models import ExecutionTrack
from codontrace.experiments.t01_oee import T01OEERunner
from codontrace.experiments.t04_contingency import T04ContingencyRunner

SRC = Path(__file__).resolve().parents[1] / "src" / "codontrace"


def _h(x: object) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, default=repr).encode()).hexdigest()


# Pins computed at origin/main 89ecd78 (before the ledger).
T01_PINS = {
    "REAL_SELECTION_WITH_QD": "84617e9e9d55e6cd7991d42d2385febc54e694218f2daaaf5889b02acd32fbfa",
    "NEUTRAL_DRIFT_CONTROL": "6a23cfb046b2ffc233c56e6b629cb0076cd53496ac801516b98dbe502b7baf9f",
}


@pytest.mark.parametrize("arm", sorted(T01_PINS))
def test_t01_byte_identical_and_checked_every_generation(arm: str) -> None:
    r = T01OEERunner(seed=7, arm=arm, population_size=32, generations=120, track=ExecutionTrack.REFERENCE)
    s = r.run()
    got = _h([repr(s), [repr(m) for m in r.metrics_history], [(o.genome, o.atp.hex(), o.age) for o in r.population]])
    assert got == T01_PINS[arm]
    assert r.atp_ledger.ticks_checked == len(r.metrics_history) + 1  # founders + each generation
    assert verify_ledger_chain(r.atp_ledger.journal_records()) == r.atp_ledger.head
    assert r.atp_ledger.balance("source:task_reward") < 0


def test_t04_byte_identical_and_chain_verifies() -> None:
    r = T04ContingencyRunner(seed=11, population_size=32, generations=60, track=ExecutionTrack.REFERENCE,
                             replay_branches=2, history_count=1)
    s = r.run()
    assert _h([repr(s), [(o.genome, o.atp.hex(), o.age) for o in r.population]]) == (
        "0de4469420b069578330222ba9932964c999f1d22a3ac023f71dc0d86583b1ae")
    assert verify_ledger_chain(r.atp_ledger.journal_records()) == r.atp_ledger.head
    r.atp_ledger.check({o.ledger_id: o.atp for o in r.population})


def test_t01_bypass_detected() -> None:
    r = T01OEERunner(seed=1, population_size=16, generations=10, track=ExecutionTrack.REFERENCE)
    r.initialize_population()
    r.step_generation(1)
    r.population[0].atp += 1.0  # outside the ledger
    with pytest.raises(ATPConservationError, match="bypass"):
        r.step_generation(2)


@settings(max_examples=20, deadline=None)
@given(seed=st.integers(0, 2**31 - 1), arm=st.sampled_from(sorted(T01_PINS)), gens=st.integers(1, 40))
def test_t01_conservation_property(seed: int, arm: str, gens: int) -> None:
    r = T01OEERunner(seed=seed, arm=arm, population_size=16, generations=gens, track=ExecutionTrack.REFERENCE)
    r.run()
    r.atp_ledger.check({o.ledger_id: o.atp for o in r.population})
    t = r.atp_ledger.totals()
    assert t["agents"] + t["reservoir"] == t["sources_in"] - t["sinks_out"]
    assert verify_ledger_chain(r.atp_ledger.journal_records()) == r.atp_ledger.head


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def test_no_atp_bypass_in_source() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        text = _strip_comments(path.read_text(encoding="utf-8"))
        if rel != "energy.py" and re.search(r"\.current_atp\s*(\+|-|\*|/)?=(?!=)", text):
            offenders.append(f"{rel}: assigns ATPAccount.current_atp")
    for rel in ("experiments/t01_oee.py", "experiments/t04_contingency.py"):
        text = _strip_comments((SRC / rel).read_text(encoding="utf-8"))
        if re.search(r"\.atp\s*(\+|-|\*|/)=", text):
            offenders.append(f"{rel}: in-place .atp update")
        if len(re.findall(r"\.atp\s*=(?!=)", text)) != 1 or "self.atp_ledger.adjust(" not in text:
            offenders.append(f"{rel}: .atp written other than via atp_ledger.adjust")
    hp = _strip_comments((SRC / "genesis/host_parasite_world.py").read_text(encoding="utf-8"))
    if hp.count("ATPAccount(") != 1:
        offenders.append("host_parasite_world.py: ATPAccount created outside _open_account")
    if re.search(r"self\.accounts\[[^\]]+\]\s*=(?!=)", hp.replace("self.accounts[member_id] = acct", "")):
        offenders.append("host_parasite_world.py: account inserted outside _open_account")
    if hp.count("self.accounts.pop(") != 1:
        offenders.append("host_parasite_world.py: account removed outside _close_account")
    assert not offenders, offenders
