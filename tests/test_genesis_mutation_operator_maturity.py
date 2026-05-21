from __future__ import annotations

import json
import os
import subprocess
import sys

from codontrace.genesis.phase1_runtime_maturity import (
    MutationOperatorAuditRecord,
    mutation_audit_from_structural_record,
    mutation_noop_audit,
)
from codontrace.genesis.replay_integrity import audit_replay_digest_policy_registry
from codontrace.genesis.structural_mutation import build_structural_mutation_record


def test_noop_mutation_has_explicit_blocked_reason_and_digest() -> None:
    record = mutation_noop_audit(
        parent_genome_digest="parent-digest",
        operator_name="bit_flip",
        reason="rate_zero",
        rng_seed=7,
        operator_parameters={"bit_flip_rate": 0.0},
    )
    assert record.validity_status == "blocked"
    assert record.blocked_reason == "rate_zero"
    assert record.before_genome_digest == record.after_genome_digest
    assert record.record_digest == MutationOperatorAuditRecord(**record.to_dict()).record_digest


def test_structural_mutation_record_is_lifted_to_phase1_operator_audit() -> None:
    structural = build_structural_mutation_record(
        parent_genome_digest="p",
        child_genome_digest="c",
        kind="insert",
        start_codon=1,
        end_codon=2,
        payload_digest="payload",
        rng_backend_kind="rng_manager",
        rng_state_digest_before="rng-before",
        rng_state_digest_after="rng-after",
        codon_width=3,
        before_tokens_digest="before-tokens",
        after_tokens_digest="after-tokens",
        rng_seed_or_stream_id="seed:12",
        validity_status="valid",
    )
    audit = mutation_audit_from_structural_record(structural, rng_seed=12)
    assert audit.mutation_kind == "insert"
    assert audit.operator_enabled is True
    assert audit.before_genome_digest == "p"
    assert audit.after_genome_digest == "c"
    assert audit.operator_parameters_digest
    assert audit.record_digest


def test_mutation_audit_digest_is_cross_process_stable() -> None:
    script = """
import json
from codontrace.genesis.phase1_runtime_maturity import mutation_noop_audit
record = mutation_noop_audit(parent_genome_digest='abc', operator_name='delete', reason='min_length_reached', rng_seed=3)
print(json.dumps(record.to_dict(), sort_keys=True))
"""
    env = {**os.environ, "PYTHONPATH": "src"}
    out1 = subprocess.check_output([sys.executable, "-c", script], text=True, env=env)
    out2 = subprocess.check_output([sys.executable, "-c", script], text=True, env=env)
    assert json.loads(out1)["record_digest"] == json.loads(out2)["record_digest"]


def test_phase1_mutation_records_have_replay_policy_registration() -> None:
    findings = audit_replay_digest_policy_registry()
    assert findings == ()
