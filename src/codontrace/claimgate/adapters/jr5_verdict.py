"""Compatibility name for the JR5 verdict; the code lives in ``codontrace.claimgate.jr5_verdict``.

The verdict sits in the claimgate core so the auditor can run it without
importing an adapter module (see the import-direction contracts).
"""

from __future__ import annotations

from codontrace.claimgate.jr5_verdict import (
    CLAIM,
    E4_WINDOW_SIGNS,
    PREREG_CONSTANTS_SHA256,
    PREREG_RECORD_DIGEST,
    SEALED_LOCK_DIGESTS,
    Interval,
    Jr5Evidence,
    Jr5Verdict,
    RunRecord,
    assert_jr5_red_queen_claim_allowed,
    evaluate_jr5_verdict,
    jr5_constants,
    jr5_run_grid,
    red_queen_exemption_holds,
    run_record_sha256,
    verify_jr5_verdict,
)

__all__ = [
    "CLAIM",
    "E4_WINDOW_SIGNS",
    "PREREG_CONSTANTS_SHA256",
    "PREREG_RECORD_DIGEST",
    "SEALED_LOCK_DIGESTS",
    "Interval",
    "Jr5Evidence",
    "Jr5Verdict",
    "RunRecord",
    "assert_jr5_red_queen_claim_allowed",
    "evaluate_jr5_verdict",
    "jr5_constants",
    "jr5_run_grid",
    "red_queen_exemption_holds",
    "run_record_sha256",
    "verify_jr5_verdict",
]
