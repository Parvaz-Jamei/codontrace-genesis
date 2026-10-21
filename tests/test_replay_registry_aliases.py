"""Replay digest registry keeps every class path it had at 74c7b3f (merge of #115)."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from codontrace.genesis.replay_integrity import replay_digest_class_policies
from codontrace.genesis.replay_policy_audit import audit_replay_policy_coverage

OLD = 'codontrace.claimgate.adapters.esp32_bridge.STRDisparityResult'
NEW = 'codontrace.genesis.transferability.STRDisparityResult'
KEYS_74C7B3F = Path(__file__).with_name('replay_policy_keys_74c7b3f.json')


def test_old_and_new_str_paths_both_pass_the_audit():
    for path in (OLD, NEW):
        report = audit_replay_policy_coverage((path,))
        assert report['passed'] is True, report
    assert audit_replay_policy_coverage((OLD, NEW))['passed'] is True


def test_alias_has_the_same_policy():
    policies = {p.class_path: p for p in replay_digest_class_policies()}
    old, new = policies[OLD], policies[NEW]
    assert old.class_path != new.class_path
    assert replace(old, class_path=NEW) == new


def test_every_key_present_on_74c7b3f_is_still_registered():
    before = set(json.loads(KEYS_74C7B3F.read_text(encoding='utf-8')))
    now = {p.class_path for p in replay_digest_class_policies()}
    assert before - now == set()


def test_alias_resolves_to_the_same_class():
    """The runtime import-direction test checks that replay_integrity itself does not load the adapter."""
    import subprocess
    import sys
    code = ("from codontrace.genesis.replay_integrity import resolve_class_path\n"
            f"cls = resolve_class_path({OLD!r})\n"
            "from codontrace.claimgate.adapters.esp32_bridge import STRDisparityResult\n"
            "assert cls is STRDisparityResult\n")
    subprocess.run([sys.executable, '-c', code], check=True)
