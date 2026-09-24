"""Phase 9: continuum / intervention analytics on HostParasiteWorld (refuse-safe)."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_analytics import (
    CONTINUUM_PHYSICS_SOURCE,
    ContinuumCellResult,
    ContinuumFactorialResult,
    InterventionContrastResult,
    ReciprocalObservationalContrast,
    run_continuum_factorial,
    run_intervention_contrast,
    run_reciprocal_observational_contrast,
)
from codontrace.genesis.host_parasite_world import _BAIC_PINS as _BAIC

REPO = Path(__file__).resolve().parents[1]
ANALYTICS_SRC = (
    REPO / "src" / "codontrace" / "genesis" / "host_parasite_analytics.py"
)
ENGINE_SRC = REPO / "src" / "codontrace" / "engine.py"

_BANNED_IMPORT_MARKERS = (
    "HostParasiteEnv",
    "codontrace.engine",
    "Infection",
)


def _sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def test_continuum_digest_sensitivity_on_coupling() -> None:
    result = run_continuum_factorial(
        factorial_id="fact_coupling",
        seeds=(0,),
        ticks=1,
        coupling_levels=(0.1, 0.5),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
    )
    assert len(result.cells) == 2
    assert result.cells[0].cell_digest != result.cells[1].cell_digest
    same = run_continuum_factorial(
        factorial_id="fact_coupling",
        seeds=(0,),
        ticks=1,
        coupling_levels=(0.1, 0.5),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
    )
    assert same.digest == result.digest
    assert same.cells[0].cell_digest == result.cells[0].cell_digest


def test_continuum_spatial_and_inherit_axes_change_digest() -> None:
    base = run_continuum_factorial(
        factorial_id="fact_axes",
        seeds=(1,),
        ticks=1,
        coupling_levels=(0.2,),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
    )
    spatial = run_continuum_factorial(
        factorial_id="fact_axes",
        seeds=(1,),
        ticks=1,
        coupling_levels=(0.2,),
        spatial_modes=("local_neighborhood",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
    )
    inherit = run_continuum_factorial(
        factorial_id="fact_axes",
        seeds=(1,),
        ticks=1,
        coupling_levels=(0.2,),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.5,),
        match_score_scales=(1.0,),
    )
    scale = run_continuum_factorial(
        factorial_id="fact_axes",
        seeds=(1,),
        ticks=1,
        coupling_levels=(0.2,),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(0.5,),
    )
    digests = {
        base.cells[0].cell_digest,
        spatial.cells[0].cell_digest,
        inherit.cells[0].cell_digest,
        scale.cells[0].cell_digest,
    }
    assert len(digests) == 4


def test_continuum_honesty_and_physics_source() -> None:
    result = run_continuum_factorial(
        factorial_id="fact_honest",
        seeds=(0,),
        ticks=1,
        coupling_levels=(0.1,),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
        interaction_value_compat=-0.5,
    )
    assert result.red_queen_proved is False
    assert result.intervention_supported is False
    assert result.raises_claim_ladder is False
    assert result.mutualism_equals_success is False
    assert result.continuum_physics_source == CONTINUUM_PHYSICS_SOURCE
    cell = result.cells[0]
    assert cell.continuum_physics_source == "world_meters"
    assert cell.mutualism_equals_success is False
    assert 0.0 <= cell.emergent_interaction_proxy <= 1.0
    assert "intervention_supported" in result.refuse_list
    assert "red_queen_proved" in result.refuse_list
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        ContinuumFactorialResult(
            factorial_id="bad",
            seeds=(0,),
            ticks=1,
            cells=result.cells,
            red_queen_proved=True,
        )
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        ContinuumFactorialResult(
            factorial_id="bad2",
            seeds=(0,),
            ticks=1,
            cells=result.cells,
            intervention_supported=True,
        )


def test_continuum_tampered_digest_and_banned_id() -> None:
    result = run_continuum_factorial(
        factorial_id="fact_tamper",
        seeds=(0,),
        ticks=1,
        coupling_levels=(0.1,),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
    )
    payload = result.to_dict()
    payload["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        ContinuumFactorialResult.from_dict(payload)
    cell_payload = result.cells[0].to_dict()
    again = ContinuumCellResult.from_dict(cell_payload)
    assert again.cell_digest == result.cells[0].cell_digest
    with pytest.raises(ConfigurationError, match="banned fragment"):
        run_continuum_factorial(
            factorial_id="infect_cell",
            seeds=(0,),
            ticks=0,
            coupling_levels=(0.1,),
            spatial_modes=("well_mixed",),
            inherit_levels=(0.0,),
            match_score_scales=(1.0,),
        )


def test_intervention_contrast_refuse_and_digests() -> None:
    result = run_intervention_contrast(
        contrast_id="ctr_freeze",
        seed=0,
        ticks=1,
        contrast_schedule_arm="freeze",
        claim_role="exploratory",
        smoke_only=True,
    )
    assert result.intervention_supported is False
    assert result.red_queen_proved is False
    assert result.identifiability == "observational_bounds"
    assert result.science_grade is False
    assert result.arms[0].arm_digest != result.arms[1].arm_digest
    assert result.effect_lower <= result.effect_delta <= result.effect_upper
    roundtrip = InterventionContrastResult.from_dict(result.to_dict())
    assert roundtrip.digest == result.digest
    with pytest.raises(ConfigurationError, match="intervention_supported"):
        InterventionContrastResult(
            contrast_id="bad",
            control_arm_id=result.control_arm_id,
            arms=result.arms,
            effect_delta=0.0,
            effect_lower=0.0,
            effect_upper=0.0,
            intervention_supported=True,
        )


def test_intervention_primary_requires_dual_null() -> None:
    with pytest.raises(ConfigurationError, match="dual_null"):
        run_intervention_contrast(
            contrast_id="ctr_primary_bad",
            seed=0,
            ticks=1,
            claim_role="primary",
            smoke_only=False,
            include_dual_null_arm=False,
        )
    ok = run_intervention_contrast(
        contrast_id="ctr_primary_ok",
        seed=0,
        ticks=1,
        claim_role="primary",
        smoke_only=False,
        include_dual_null_arm=True,
    )
    assert any(a.ablation_preset == "dual_null" for a in ok.arms)
    assert ok.intervention_supported is False


def test_intervention_smoke_cannot_be_primary() -> None:
    with pytest.raises(ConfigurationError, match="smoke_only"):
        run_intervention_contrast(
            contrast_id="ctr_smoke_primary",
            seed=0,
            ticks=1,
            claim_role="primary",
            smoke_only=True,
            include_dual_null_arm=True,
        )


def test_reciprocal_observational_contrast_refuse_safe() -> None:
    result = run_reciprocal_observational_contrast(
        contrast_id="recip_obs",
        seed=0,
        ticks=1,
        include_replay=True,
    )
    assert result.red_queen_proved is False
    assert result.intervention_supported is False
    assert result.freeze_arm.schedule_arm == "freeze"
    assert result.unlock_arm.schedule_arm == "unlock"
    assert result.replay_arm is not None
    assert result.replay_arm.schedule_arm == "replay_schedule"
    digests = {
        result.freeze_arm.arm_digest,
        result.unlock_arm.arm_digest,
        result.replay_arm.arm_digest,
    }
    assert len(digests) == 3
    again = ReciprocalObservationalContrast.from_dict(result.to_dict())
    assert again.digest == result.digest
    with pytest.raises(ConfigurationError, match="red_queen_proved"):
        ReciprocalObservationalContrast(
            contrast_id="bad_recip",
            seed=0,
            ticks=1,
            freeze_arm=result.freeze_arm,
            unlock_arm=result.unlock_arm,
            replay_arm=result.replay_arm,
            channel_delta_unlock_minus_freeze=0.0,
            red_queen_proved=True,
        )


def test_static_audit_no_env_engine_infection() -> None:
    text = ANALYTICS_SRC.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imported.add(mod)
            for alias in node.names:
                imported.add(f"{mod}.{alias.name}")
    joined = "\n".join(sorted(imported))
    assert "HostParasiteEnv" not in joined
    assert "codontrace.engine" not in joined
    assert "Infection" not in text
    assert "def step" not in text
    # Module must run World, not invent Env continuum physics.
    assert "HostParasiteWorld" in text
    assert CONTINUUM_PHYSICS_SOURCE in text
    engine_before = ENGINE_SRC.read_bytes()
    # Touch path only — content identity checked vs BAIC pins separately.
    assert engine_before  # non-empty
    for rel, expected in _BAIC:
        assert _sha(rel) == expected


def test_baic_pins_byte_identical() -> None:
    for rel, expected in _BAIC:
        assert _sha(rel) == expected
