"""T01/T04 ATP goes through the world ledger; grep-enforced no-bypass rules."""

from __future__ import annotations

import ast
import hashlib
import json
import keyword
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


LEDGER_OWNERS = {"energy.py", "atp_ledger.py"}
ALWAYS_PROTECTED = {"current_atp"}
PRIVATE_PROTECTED = {"_observer", "_verified", "_ledger"}  # protected on non-self receivers
SCALAR_ATP_FILES = {"experiments/t01_oee.py", "experiments/t04_contingency.py"}


def _protected(rel: str) -> set[str]:
    return ALWAYS_PROTECTED | ({"atp"} if rel in SCALAR_ATP_FILES else set())


def _is_ledger_adjust(value: ast.AST) -> bool:
    return (isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute)
            and value.func.attr == "adjust" and isinstance(value.func.value, ast.Attribute)
            and value.func.value.attr == "atp_ledger")


def atp_bypasses(source: str, rel: str) -> list[str]:
    """AST gate: every way to write an ATP balance field without the ledger.

    Catches ``x.f = / += / : T =``, ``setattr(x, "f", v)``,
    ``object.__setattr__(x, "f", v)`` / ``x.__setattr__("f", v)``,
    ``x.__dict__["f"] = v`` / ``vars(x)["f"] = v`` / ``x.__dict__.update(f=..)``,
    and ``dataclasses.replace(x, f=v)`` / ``replace(x, f=v)``.
    """

    if rel in LEDGER_OWNERS:
        return []
    prot = _protected(rel)
    out: list[str] = []

    def is_self(node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id in {"self", "cls"}

    def bad_attr(name: str, receiver: ast.AST | None) -> bool:
        if name in prot:
            return True
        return name in PRIVATE_PROTECTED and receiver is not None and not is_self(receiver)

    def const(node: ast.AST) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    def is_dict_view(node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute) and node.attr == "__dict__":
            return True
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "vars")

    def check_target(t: ast.AST, line: int) -> None:
        if isinstance(t, ast.Attribute) and bad_attr(t.attr, t.value):
            out.append(f"{rel}:{line}: assigns .{t.attr}")
        elif isinstance(t, ast.Subscript) and is_dict_view(t.value):
            key = const(t.slice)
            if key is not None and bad_attr(key, None if is_self(getattr(t.value, "value", t.value)) else t.value):
                out.append(f"{rel}:{line}: writes __dict__[{key!r}]")
        elif isinstance(t, (ast.Tuple, ast.List)):
            for e in t.elts:
                check_target(e, line)

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign):
            if _is_ledger_adjust(node.value):
                continue  # x.atp = self.atp_ledger.adjust(...) is the sanctioned path
            for t in node.targets:
                check_target(t, node.lineno)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            check_target(node.target, node.lineno)
        elif isinstance(node, ast.Call):
            f = node.func
            fname = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
            args = node.args
            if fname == "setattr" and len(args) >= 2 and (k := const(args[1])) and bad_attr(k, args[0]):
                out.append(f"{rel}:{node.lineno}: setattr {k!r}")
            elif fname == "__setattr__" and isinstance(f, ast.Attribute) and args:
                recv, key_arg = (args[0], args[1]) if len(args) >= 3 else (f.value, args[0])
                if (k := const(key_arg)) and bad_attr(k, recv):
                    out.append(f"{rel}:{node.lineno}: __setattr__ {k!r}")
            elif fname == "replace":
                for kw in node.keywords:
                    if kw.arg is not None and bad_attr(kw.arg, node.args[0] if node.args else None):
                        out.append(f"{rel}:{node.lineno}: replace(..., {kw.arg}=)")
            elif fname == "update" and isinstance(f, ast.Attribute) and is_dict_view(f.value):
                for kw in node.keywords:
                    if kw.arg is not None and bad_attr(kw.arg, f.value):
                        out.append(f"{rel}:{node.lineno}: __dict__.update({kw.arg}=)")
    return out


BYPASS_MUTANTS = [
    "acct.current_atp = 5.0",
    "acct.current_atp += 1",
    "acct.current_atp: float = 1.0",
    "setattr(acct, 'current_atp', 9.0)",
    "object.__setattr__(acct, 'current_atp', 9.0)",
    "acct.__setattr__('current_atp', 9.0)",
    "acct.__dict__['current_atp'] = 9.0",
    "vars(acct)['current_atp'] = 9.0",
    "acct.__dict__.update(current_atp=9.0)",
    "acct = dataclasses.replace(acct, current_atp=9.0)",
    "acct = replace(acct, current_atp=9.0)",
    "acct._observer = None",
    "setattr(acct, '_observer', None)",
    "object.__setattr__(acct, '_ledger', [])",
    "a, acct.current_atp = 1, 2.0",
]


@pytest.mark.parametrize("mutant", BYPASS_MUTANTS)
def test_static_gate_catches_every_bypass_form(mutant: str) -> None:
    assert atp_bypasses(mutant, "genesis/some_module.py"), mutant


@pytest.mark.parametrize("mutant", ["org.atp = 3.0", "setattr(org, 'atp', 3.0)",
                                    "org = dataclasses.replace(org, atp=3.0)",
                                    "object.__setattr__(org, 'atp', 3.0)"])
def test_static_gate_catches_scalar_atp_bypass(mutant: str) -> None:
    assert atp_bypasses(mutant, "experiments/t01_oee.py"), mutant


def test_static_gate_allows_reads_and_self_private_state() -> None:
    ok = "x = acct.current_atp\nself._ledger = []\ny = getattr(acct, 'current_atp')\n"
    assert atp_bypasses(ok, "genesis/some_module.py") == []


def test_no_atp_bypass_in_source() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC).as_posix()
        offenders.extend(atp_bypasses(path.read_text(encoding="utf-8"), rel))
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


_FORMS = ["{r}.{f} = 1.0", "{r}.{f} -= 1.0", "setattr({r}, '{f}', 1.0)",
          "object.__setattr__({r}, '{f}', 1.0)", "{r}.__setattr__('{f}', 1.0)",
          "{r}.__dict__['{f}'] = 1.0", "vars({r})['{f}'] = 1.0",
          "{r} = dataclasses.replace({r}, {f}=1.0)"]


@settings(max_examples=80, deadline=None)
@given(st.sampled_from(_FORMS), st.from_regex(r"[a-z][a-z0-9_]{0,8}", fullmatch=True)
       .filter(lambda r: r not in {"self", "cls"} and not keyword.iskeyword(r)),
       st.sampled_from(sorted(ALWAYS_PROTECTED | PRIVATE_PROTECTED)))
def test_static_gate_property(form: str, receiver: str, field_name: str) -> None:
    assert atp_bypasses(form.format(r=receiver, f=field_name), "genesis/x.py")
