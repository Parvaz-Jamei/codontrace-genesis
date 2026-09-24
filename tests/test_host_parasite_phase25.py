"""Phase 25: HE_HP locked-digest refresh note (Wave 6)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.host_parasite import (
    attach_he_hp_locked_digest_refresh,
    bundle_from_host_parasite_cou,
)
from codontrace.claimgate.adapters.host_parasite_prereg import (
    attach_host_parasite_preregistration,
    host_parasite_preregistration,
)
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_he_hp_refresh import (
    build_he_hp_locked_digest_refresh_note,
)

ROOT = Path(__file__).resolve().parents[1]
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)


def test_he_hp_refresh_replays_locks_and_keeps_pins() -> None:
    note = build_he_hp_locked_digest_refresh_note()
    assert note.baic_pins_untouched is True
    assert note.locks_still_valid is True
    assert note.wave5_does_not_invalidate_he_hp is True
    assert note.raises_claim_ladder is False
    assert note.red_queen_proved is False
    assert all(ok for _, ok in note.campaign_lock_status)
    assert len(note.campaign_lock_status) == 4


def test_attach_he_hp_refresh_requires_prereg_and_keeps_ladder() -> None:
    note = build_he_hp_locked_digest_refresh_note()
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do HE_HP locks still replay after Wave 5?",
        context_of_use="Phase 25 refresh note; BAIC pins untouched.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.1,),
        control_scores=(1.0,),
    )
    with pytest.raises(ConfigurationError, match="preregistration"):
        attach_he_hp_locked_digest_refresh(bundle, note)
    prereg = host_parasite_preregistration(
        question_of_interest="Do HE_HP locks still replay after Wave 5?",
        context_of_use="Phase 25 refresh note; BAIC pins untouched.",
        arms=("he_hp_refresh",),
        success_metrics=("refresh_digest", "locks_still_valid"),
        forbidden_claims=("red_queen_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    before = audit_bundle(ready).achieved_level
    attached = attach_he_hp_locked_digest_refresh(ready, note)
    record = attached.extra["he_hp_locked_digest_refresh"]
    assert record["baic_pins_untouched"] is True
    assert record["locks_still_valid"] is True
    assert audit_bundle(attached).achieved_level == before


def test_attach_he_hp_refresh_refuses_double_attach() -> None:
    note = build_he_hp_locked_digest_refresh_note()
    bundle = bundle_from_host_parasite_cou(
        question_of_interest="Do HE_HP locks still replay after Wave 5?",
        context_of_use="Phase 25 refresh note; BAIC pins untouched.",
        model_influence=1,
        decision_consequence=1,
        treatment_scores=(0.1,),
        control_scores=(1.0,),
    )
    prereg = host_parasite_preregistration(
        question_of_interest="Do HE_HP locks still replay after Wave 5?",
        context_of_use="Phase 25 refresh note; BAIC pins untouched.",
        arms=("he_hp_refresh",),
        success_metrics=("refresh_digest", "locks_still_valid"),
        forbidden_claims=("red_queen_proved",),
    )
    ready = attach_host_parasite_preregistration(bundle, prereg)
    attached = attach_he_hp_locked_digest_refresh(ready, note)
    with pytest.raises(ConfigurationError, match="already attached"):
        attach_he_hp_locked_digest_refresh(attached, note)


def test_baic_pins_byte_identical_phase25() -> None:
    for rel, expected in PIN_SPECS:
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, rel
