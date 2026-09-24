"""Phase 25 — HE_HP locked-digest refresh note (Wave 6).

Documents which HE_HP campaign digests remain valid after Waves 5–6 without
editing BAIC pins. Replay hygiene only — no new biology claims, no infection
physics in engine.py, pins byte-identical forever.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload
from codontrace.genesis.host_parasite_continuum import run_vt_spatial_factorial
from codontrace.genesis.host_parasite_cornish import run_cornish_intervention_campaign
from codontrace.genesis.host_parasite_evolvability import run_evolvability_falsification
from codontrace.genesis.host_parasite_zaman import run_zaman_three_arm_campaign
from codontrace.genesis.text_digest import sha256_text_file

SCHEMA = "host_parasite_he_hp_locked_digest_refresh_v1"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HE_HP_PATH = _REPO_ROOT / "docs" / "hard_experiment_hp" / "locked_campaign_digests.json"
_BAIC_PINS = (
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


def _digest_body(body: Mapping[str, object]) -> str:
    return canonical_digest(canonical_payload(dict(body)))


def _assert_baic_pins_untouched() -> None:
    for rel, expected in _BAIC_PINS:
        path = _REPO_ROOT / rel
        got = sha256_text_file(path)
        if got != expected:
            raise ConfigurationError(f"BAIC pin drift for {rel}: got {got}")


@dataclass(frozen=True, slots=True)
class HeHpLockedDigestRefreshNote:
    """Wave-6 honesty note: HE_HP locks still replay; BAIC pins untouched."""

    schema: str
    locked_digest: str
    campaign_lock_status: tuple[tuple[str, bool], ...]
    baic_pins_untouched: bool
    locks_still_valid: bool
    wave5_does_not_invalidate_he_hp: bool
    raises_claim_ladder: bool
    red_queen_proved: bool
    refresh_digest: str

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "locked_digest": self.locked_digest,
            "campaign_lock_status": {
                name: ok for name, ok in self.campaign_lock_status
            },
            "baic_pins_untouched": True,
            "locks_still_valid": self.locks_still_valid,
            "wave5_does_not_invalidate_he_hp": True,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "wave": 6,
            "phase": 25,
            "note": (
                "HE_HP Phase 7–9 locked campaign digests still replay after "
                "Waves 5–6. BAIC pins remain byte-identical; Wave-5 protocols "
                "are additive and do not rewrite these locks."
            ),
            "domain_profile": "host_parasite",
            "he_hp_path": "docs/hard_experiment_hp/locked_campaign_digests.json",
        }
        body["refresh_digest"] = self.refresh_digest or _digest_body(
            {
                k: body[k]
                for k in body
                if k not in {"refresh_digest", "digest", "campaign_digest"}
            }
        )
        body["campaign_digest"] = body["refresh_digest"]
        body["digest"] = body["refresh_digest"]
        return body


_HE_HP_SCHEMA = "hard_experiment_hp_locked_digests_v1"
_REQUIRED_HE_HP_CAMPAIGNS = (
    "zaman_three_arm",
    "vt_spatial_factorial",
    "evolvability_falsification",
    "cornish_intervention",
)


def validate_he_hp_locked_pack(locked: Mapping[str, object]) -> None:
    """Fail-closed schema / honesty checks for the HE_HP locked JSON pack.

    Does not mutate BAIC pins. Rejects packs that claim engine infection
    physics, flip honesty flags, or drop the locked schema identity.
    """

    if not isinstance(locked, Mapping):
        raise ConfigurationError("HE_HP locked pack must be a mapping.")
    if locked.get("schema") != _HE_HP_SCHEMA:
        raise ConfigurationError(
            f"HE_HP pack schema must be {_HE_HP_SCHEMA!r}; got {locked.get('schema')!r}."
        )
    if locked.get("engine_infection_physics") != "not_in_engine_core":
        raise ConfigurationError(
            "HE_HP pack must keep engine_infection_physics='not_in_engine_core'."
        )
    if locked.get("baic_pins_untouched") is not True:
        raise ConfigurationError("HE_HP pack must declare baic_pins_untouched=True.")
    if locked.get("intervention_supported") is not False:
        raise ConfigurationError("HE_HP pack must keep intervention_supported=False.")
    if locked.get("red_queen_proved") is not False:
        raise ConfigurationError("HE_HP pack must keep red_queen_proved=False.")
    if locked.get("complexity_emergence_proved") is not False:
        raise ConfigurationError("HE_HP pack must keep complexity_emergence_proved=False.")
    if locked.get("mutualism_equals_success") is not False:
        raise ConfigurationError("HE_HP pack must keep mutualism_equals_success=False.")
    campaigns = locked.get("campaigns")
    if not isinstance(campaigns, Mapping):
        raise ConfigurationError("HE_HP pack campaigns must be a mapping.")
    missing = [name for name in _REQUIRED_HE_HP_CAMPAIGNS if name not in campaigns]
    if missing:
        raise ConfigurationError(f"HE_HP pack missing campaigns: {missing}")
    if not isinstance(locked.get("locked_digest"), str) or not str(locked.get("locked_digest")).strip():
        raise ConfigurationError("HE_HP pack locked_digest must be a non-empty string.")


def build_he_hp_locked_digest_refresh_note() -> HeHpLockedDigestRefreshNote:
    """Replay HE_HP locks and assert BAIC pins; return honesty refresh note."""

    _assert_baic_pins_untouched()
    if not _HE_HP_PATH.is_file():
        raise ConfigurationError(f"missing HE_HP locked pack: {_HE_HP_PATH}")
    locked = json.loads(_HE_HP_PATH.read_text(encoding="utf-8"))
    validate_he_hp_locked_pack(locked)

    campaigns = locked["campaigns"]
    status: list[tuple[str, bool]] = []

    zaman = run_zaman_three_arm_campaign(
        seeds=tuple(campaigns["zaman_three_arm"]["seeds"]),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    status.append(
        (
            "zaman_three_arm",
            zaman.to_dict()["campaign_digest"]
            == campaigns["zaman_three_arm"]["campaign_digest"],
        )
    )

    vt = run_vt_spatial_factorial(
        seeds=tuple(campaigns["vt_spatial_factorial"]["seeds"]),
        vt_levels=(0.0, 1.0),
        spatial_modes=("well_mixed", "local_neighborhood"),
        interaction_value=-1.0,
        request_claim_ceiling="candidate_evidence",
    )
    status.append(
        (
            "vt_spatial_factorial",
            vt.to_dict()["factorial_digest"]
            == campaigns["vt_spatial_factorial"]["factorial_digest"],
        )
    )

    evol = run_evolvability_falsification(
        seeds=tuple(campaigns["evolvability_falsification"]["seeds"]),
        steps=3,
        request_claim_ceiling="candidate_evidence",
    )
    status.append(
        (
            "evolvability_falsification",
            evol.to_dict()["assay_digest"]
            == campaigns["evolvability_falsification"]["assay_digest"],
        )
    )

    cornish = run_cornish_intervention_campaign(
        seeds=tuple(campaigns["cornish_intervention"]["seeds"]),
        preregistration_digest=str(
            campaigns["cornish_intervention"]["preregistration_digest"]
        ),
    )
    status.append(
        (
            "cornish_intervention",
            cornish.to_dict()["campaign_digest"]
            == campaigns["cornish_intervention"]["campaign_digest"],
        )
    )

    if not all(ok for _, ok in status):
        failed = [name for name, ok in status if not ok]
        raise ConfigurationError(f"HE_HP locked digests failed replay: {failed}")

    locked_digest = str(locked["locked_digest"])
    preview = {
        "schema": SCHEMA,
        "locked_digest": locked_digest,
        "campaign_lock_status": {name: ok for name, ok in status},
        "baic_pins_untouched": True,
        "locks_still_valid": True,
        "wave5_does_not_invalidate_he_hp": True,
        "raises_claim_ladder": False,
        "red_queen_proved": False,
        "wave": 6,
        "phase": 25,
        "domain_profile": "host_parasite",
    }
    return HeHpLockedDigestRefreshNote(
        schema=SCHEMA,
        locked_digest=locked_digest,
        campaign_lock_status=tuple(status),
        baic_pins_untouched=True,
        locks_still_valid=True,
        wave5_does_not_invalidate_he_hp=True,
        raises_claim_ladder=False,
        red_queen_proved=False,
        refresh_digest=_digest_body(preview),
    )


__all__ = [
    "SCHEMA",
    "HeHpLockedDigestRefreshNote",
    "build_he_hp_locked_digest_refresh_note",
]
