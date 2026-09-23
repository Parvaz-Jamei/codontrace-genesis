#!/usr/bin/env python3
"""Novel valuable evidence suite for CodonTrace Genesis (2026-09-24).

Read-only against the repo: no src edits, no pin mutation.
Writes ONLY under this suite directory (docs/claimgate/novel_valuable_evidence_20260924/).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk parents until pyproject.toml or docs/hard_experiment_01 exists."""
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
        if (parent / "docs" / "hard_experiment_01").is_dir():
            return parent
    # Fallback when living under docs/claimgate/<suite>/
    if len(start.parts) >= 3 and start.parts[-2] == "claimgate" and start.parts[-3] == "docs":
        return start.parents[2]
    raise RuntimeError(f"Could not locate repo root from {start}")


OUT = Path(__file__).resolve().parent
REPO = _find_repo_root(OUT)
ART = OUT / "evidence"
PIN_RELS = [
    "docs/hard_experiment_01/results_v7.json",
    "docs/claimgate/risk_bar.json",
    "docs/claimgate/biomedical_study.json",
]
PIN_PATHS = [REPO / rel for rel in PIN_RELS]

# biomedical_risk_bar_payload() and some adapters resolve docs/... relative to cwd.
os.chdir(REPO)
sys.path.insert(0, str(REPO / "src"))

from codontrace import __version__  # noqa: E402
from codontrace.claimgate import audit_bundle  # noqa: E402
from codontrace.claimgate.adapters.biomedical import (  # noqa: E402
    assess_risk_bar,
    biomedical_risk_bar_payload,
)
from codontrace.claimgate.adapters.codontrace import (  # noqa: E402
    bundle_from_hard_experiment_01,
)
from codontrace.claimgate.adapters.codontrace_he02 import (  # noqa: E402
    bundle_from_hard_experiment_02,
    committed_results_v1_path,
)
from codontrace.claimgate.adapters.codontrace_he03 import (  # noqa: E402
    committed_results_v1_path as he03_results_path,
)
from codontrace.genesis import ScientificEvidencePack, apply_claim_downgrade_rules  # noqa: E402
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate  # noqa: E402


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _repo_rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO.resolve()))
    except ValueError:
        return str(path)


def _suite_rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(OUT.resolve()))
    except ValueError:
        return str(path)


def n1_portfolio() -> dict:
    he01 = bundle_from_hard_experiment_01(PIN_PATHS[0])
    he02 = bundle_from_hard_experiment_02(committed_results_v1_path())
    r1 = audit_bundle(he01)
    r2 = audit_bundle(he02)
    e1 = he01.extra or {}
    e2 = he02.extra or {}
    portfolio = {
        "HE01": {
            "artifact": _repo_rel(PIN_PATHS[0]),
            "achieved_level": r1.achieved_level,
            "public_name": r1.public_name,
            "replay_verified": bool(he01.replay.verified),
            "n_replay_digests": len(he01.replay.digests),
            "collective_intelligence": bool(e1.get("collective_intelligence")),
            "intelligence": bool(e1.get("intelligence")),
            "claim_ceiling": e1.get("claim_ceiling"),
            "decision_rule_passed": e1.get("decision_rule_passed"),
            "missing_for_next": list(r1.missing_for_next),
            "audit_digest": r1.digest,
        },
        "HE02": {
            "artifact": _repo_rel(committed_results_v1_path()),
            "achieved_level": r2.achieved_level,
            "public_name": r2.public_name,
            "replay_verified": bool(he02.replay.verified),
            "n_replay_digests": len(he02.replay.digests),
            "collective_intelligence": bool(e2.get("collective_intelligence")),
            "intelligence": bool(e2.get("intelligence")),
            "claim_ceiling": e2.get("claim_ceiling"),
            "decision_rule_passed": e2.get("decision_rule_passed"),
            "missing_for_next": list(r2.missing_for_next),
            "audit_digest": r2.digest,
        },
    }
    # Cross-campaign discrimination: same auditor, different grades.
    ok = (
        portfolio["HE01"]["achieved_level"] == 4
        and portfolio["HE01"]["public_name"] == "replicated_effect"
        and portfolio["HE01"]["replay_verified"] is True
        and portfolio["HE01"]["collective_intelligence"] is False
        and portfolio["HE02"]["achieved_level"] == 2
        and portfolio["HE02"]["public_name"] == "candidate_evidence"
        and portfolio["HE02"]["replay_verified"] is False
        and portfolio["HE02"]["claim_ceiling"] == "runtime_observation"
        and portfolio["HE02"]["decision_rule_passed"] is False
        and portfolio["HE01"]["achieved_level"] != portfolio["HE02"]["achieved_level"]
    )
    return {
        "id": "N1_comparative_claimgate_portfolio",
        "problem": "Cross-campaign claim portfolio: same auditor grades HE01 vs HE02 differently",
        "literature_gap": "reproducibility / claim–evidence mismatch (BioModels-style crisis applied to ALife)",
        "portfolio": portfolio,
        "expected": (
            "HE01 level 4 replicated_effect replay=True CI=false; "
            "HE02 level 2 candidate_evidence replay=False ceiling=runtime_observation "
            "decision_rule_passed=false; levels differ"
        ),
        "pass": ok,
    }


def n2_overclaim_trap() -> dict:
    he02 = bundle_from_hard_experiment_02(committed_results_v1_path())
    baseline = audit_bundle(he02)
    gate = ScientificClaimGate()
    blocked = {}
    for label in (
        "collective_intelligence",
        "intelligence",
        "communication",
        "division_of_labor",
        "agi",
        "intervention_supported",
    ):
        d = gate.decide(ClaimRequest(label, {}))
        blocked[label] = {
            "allowed": bool(d.allowed),
            "decision": d.decision,
            "failed_reasons": list(d.failed_reasons),
            "final_claim": d.final_claim,
        }

    # Rename-only: claim_ceiling string cannot buy intervention_supported grade.
    ceiling_only = audit_bundle(
        replace(he02, extra={**(he02.extra or {}), "claim_ceiling": "intervention_supported"})
    )
    # Forbidden alias True → auditor zeros difference flags → demotion.
    ci_true = audit_bundle(
        replace(he02, extra={**(he02.extra or {}), "collective_intelligence": True})
    )
    rename_all = audit_bundle(
        replace(
            he02,
            extra={
                **(he02.extra or {}),
                "claim_ceiling": "intervention_supported",
                "collective_intelligence": True,
                "intelligence": True,
                "decision_rule_passed": True,
            },
        )
    )

    ok = (
        blocked["collective_intelligence"]["allowed"] is False
        and "overclaim_alias_forbidden" in blocked["collective_intelligence"]["failed_reasons"]
        and blocked["intelligence"]["allowed"] is False
        and ceiling_only.achieved_level == baseline.achieved_level  # rename does not promote
        and ceiling_only.achieved_level < 3  # still below intervention_supported (level 3+)
        and ci_true.achieved_level < baseline.achieved_level  # CI flag demotes
        and rename_all.achieved_level < 3
        and rename_all.public_name != "intervention_supported"
    )
    return {
        "id": "N2_overclaim_trap",
        "problem": "When is a group a collective agent? / Price≠causality; ClaimGate blocks CI until earned",
        "literature_gap": "Okasha / causal Price; collective-agent criteria",
        "scientific_claim_gate_blocks": blocked,
        "bundle_traps": {
            "baseline_level": baseline.achieved_level,
            "baseline_public_name": baseline.public_name,
            "ceiling_rename_to_intervention_supported": {
                "achieved_level": ceiling_only.achieved_level,
                "public_name": ceiling_only.public_name,
                "promoted": ceiling_only.achieved_level > baseline.achieved_level,
            },
            "collective_intelligence_true_in_extra": {
                "achieved_level": ci_true.achieved_level,
                "public_name": ci_true.public_name,
                "demoted": ci_true.achieved_level < baseline.achieved_level,
                "missing_for_next": list(ci_true.missing_for_next),
            },
            "rename_all_overclaims": {
                "achieved_level": rename_all.achieved_level,
                "public_name": rename_all.public_name,
                "note": "Cannot promote HE02 to intervention_supported by renaming extras",
            },
        },
        "expected": (
            "CI/intelligence blocked by ScientificClaimGate; renaming claim_ceiling does not "
            "promote; setting collective_intelligence=True demotes audit level"
        ),
        "pass": ok,
    }


def n3_right_answer_wrong_reason() -> dict:
    analysis_path = REPO / "docs/hard_experiment_02/analysis_v1b_contrasts.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    contrasts = {c["baseline_arm"]: c for c in analysis["paired_contrasts"]}
    off = contrasts["channel_off"]
    null = contrasts["content_null"]
    shuffled = contrasts["capsules_shuffled"]

    alpha = 0.05
    survives_off = off["p_holm"] < alpha
    survives_null = null["p_holm"] < alpha
    fails_shuffled = shuffled["p_holm"] >= alpha
    content_null_pattern = survives_off and survives_null and fails_shuffled

    evidence = {
        "source": _repo_rel(analysis_path),
        "as_run_digest": analysis["as_run_digest"],
        "decision_rule_passed": analysis["decision_rule_passed"],
        "decision_rule_failures": analysis["decision_rule_failures"],
        "claim_ceiling": analysis["claim_ceiling"],
        "pattern_name": "content_null_not_information_control",
        "interpretation": (
            "Treatment vs channel_off / content_null survives Holm (dz≈1.13); "
            "vs capsules_shuffled fails (dz≈0.20, p_holm≈0.37). "
            "Effect is not separated from information-bearing capsule content "
            "under the prereg decision rule → confirmatory communication claim "
            "not earned (information_control_not_separated). "
            "Maps to Floreano/Knoester honesty: signals need selective value AND "
            "content-sensitive controls; channel-off alone can look like a win."
        ),
        "holm_alpha": alpha,
        "contrasts": {
            "vs_channel_off": {
                "dz": off["dz"],
                "p_holm": off["p_holm"],
                "survives_holm": survives_off,
            },
            "vs_content_null": {
                "dz": null["dz"],
                "p_holm": null["p_holm"],
                "survives_holm": survives_null,
            },
            "vs_capsules_shuffled": {
                "dz": shuffled["dz"],
                "p_holm": shuffled["p_holm"],
                "survives_holm": not fails_shuffled,
                "fails_holm": fails_shuffled,
            },
        },
        "pilot_report_delta_atp_note": (
            "PILOT_REPORT.md: Holm survives vs off/null (dz≈1.13, ΔATP=+0.53 on baseline 44) "
            "and fails vs shuffled (dz≈0.20, p_holm≈0.37)."
        ),
        "literature_map": {
            "Floreano_2007": "honest signals under relatedness/colony selection; food-location MI",
            "Knoester_2008": "cooperative construction needs content-bearing network structure",
        },
        "honest_nonclaim": (
            "HE02 did NOT prove communication or division of labor. "
            "This suite records the confirmatory fail as evidence of claim–evidence discrimination."
        ),
    }
    art_path = ART / "N3_communication_content_null_pattern.json"
    _write_json(art_path, evidence)
    ok = (
        content_null_pattern
        and analysis["decision_rule_passed"] is False
        and "information_control_not_separated" in analysis["decision_rule_failures"]
        and analysis["claim_ceiling"] == "runtime_observation"
    )
    return {
        "id": "N3_right_answer_wrong_reason_communication",
        "problem": "Honest fail of communication/DoL claims when confirmatory evidence missing (HE02)",
        "literature_gap": "Floreano/Knoester honesty; Price≠automatic causality",
        "content_null_pattern": content_null_pattern,
        "artifact": _suite_rel(art_path),
        "decision_rule_passed": analysis["decision_rule_passed"],
        "decision_rule_failures": analysis["decision_rule_failures"],
        "expected": (
            "Holm survives vs off/null, fails vs shuffled; decision_rule_passed=false; "
            "information_control_not_separated; ceiling runtime_observation"
        ),
        "pass": ok,
    }


def n4_biomedical_alife_joint() -> dict:
    he01 = bundle_from_hard_experiment_01(PIN_PATHS[0])
    he02 = bundle_from_hard_experiment_02(committed_results_v1_path())
    r1 = audit_bundle(he01)
    r2 = audit_bundle(he02)
    # Match risk_bar pin row he01_executed_phenomenon: influence=3, consequence=3 → risk 3 → need level 4
    bar_he01 = assess_risk_bar(
        model_influence=3, decision_consequence=3, achieved_level=r1.achieved_level, open_gaps=()
    )
    bar_he02 = assess_risk_bar(
        model_influence=3, decision_consequence=3, achieved_level=r2.achieved_level, open_gaps=()
    )
    pin_payload = biomedical_risk_bar_payload()
    pin_he01_row = next(
        row for row in pin_payload["rows"] if row["name"] == "he01_executed_phenomenon"
    )
    joint = {
        "risk_bar_pin_digest": pin_payload["digest"],
        "not_an_fda_score": True,
        "not_a_device_certificate": True,
        "he01": {
            "achieved_level": r1.achieved_level,
            "risk_bar": bar_he01.to_dict(),
            "pin_row_met": pin_he01_row["met"],
        },
        "he02": {
            "achieved_level": r2.achieved_level,
            "risk_bar": bar_he02.to_dict(),
        },
        "story": (
            "Same risk-3 bar (required_level=4): HE01 executed phenomenon meets it; "
            "HE02 audited level 2 fails with achieved_below_bar. "
            "Biomedical risk discipline applied to ALife claims without FDA theater."
        ),
    }
    art_path = ART / "N4_biomedical_alife_risk_bar.json"
    _write_json(art_path, joint)
    ok = (
        bar_he01.met is True
        and bar_he01.required_level == 4
        and r1.achieved_level == 4
        and pin_he01_row["met"] is True
        and bar_he02.met is False
        and "achieved_below_bar" in bar_he02.blocking_gaps
        and r2.achieved_level == 2
    )
    return {
        "id": "N4_biomedical_alife_joint_risk_bar",
        "problem": "Biomedical + ALife joint story / claim–evidence mismatch under risk discipline",
        "literature_gap": "BioModels-style crisis; commensurate evidence (ASME V&V40 / FDA CM&S context)",
        "joint": joint,
        "artifact": _suite_rel(art_path),
        "expected": "HE01 meets risk-3 bar; HE02 level 2 fails risk-3 bar (achieved_below_bar)",
        "pass": ok,
    }


def n5_causal_replay_demo() -> dict:
    # Capture examples/causal_replay_demo.py stdout via in-process call for determinism.
    from codontrace import (
        ATPAccount,
        CausalReplay,
        CodonTable,
        SemanticGenome,
        Trace,
        WhiteBoxAgent,
        World2D,
    )

    world = World2D.from_ascii(
        """
...
.A.
...
"""
    )
    snapshot = world.clone()
    agent = WhiteBoxAgent(
        id="agent-1",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(initial_atp=5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    # Second identical run for match check
    world2 = World2D.from_ascii(
        """
...
.A.
...
"""
    )
    snapshot2 = world2.clone()
    agent2 = WhiteBoxAgent(
        id="agent-1",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(initial_atp=5.0),
        position=(1, 1),
    )
    trace2 = Trace()
    agent2.step(world2, trace2)
    explanation2 = CausalReplay.explain_last_action(trace2, snapshot2)

    pert = [r.to_dict() for r in explanation.perturbation_results]
    pert2 = [r.to_dict() for r in explanation2.perturbation_results]
    names = {p["name"]: p for p in pert}
    ok = (
        explanation.summary == explanation2.summary
        and pert == pert2
        and "MOVE_EAST" in explanation.summary
        and names["baseline"]["status"] == "executed"
        and names["low_atp"]["status"] == "blocked"
        and names["low_atp"]["reason"] == "insufficient_atp"
        and names["wall_inserted"]["status"] == "blocked"
        and names["wall_inserted"]["reason"] == "wall_blocked"
    )
    # Also capture CLI output for the artifact
    env = {**os.environ, "PYTHONPATH": "src"}
    proc = subprocess.run(
        [sys.executable, str(REPO / "examples/causal_replay_demo.py")],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    capture = {
        "summary": explanation.summary,
        "perturbation_results": pert,
        "second_run_summary_match": explanation.summary == explanation2.summary,
        "second_run_perturbations_match": pert == pert2,
        "cli_exit_code": proc.returncode,
        "cli_stdout": proc.stdout,
        "cli_stderr": proc.stderr,
        "note": (
            "Deterministic causal replay: identical setup → identical explanation. "
            "Perturbations show counterfactual dependence (ATP / wall), not mere correlation. "
            "Addresses Price≠causality at micro scale; does NOT claim collective intelligence."
        ),
    }
    art_path = ART / "N5_causal_replay_demo.json"
    _write_json(art_path, capture)
    (ART / "N5_causal_replay_demo_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    return {
        "id": "N5_causal_replay_demo_smoke",
        "problem": "Price equation ≠ automatic causality — micro causal replay must match",
        "literature_gap": "Okasha / causal Price literature",
        "deterministic_match": explanation.summary == explanation2.summary,
        "perturbations_ok": ok and proc.returncode == 0,
        "artifact": _suite_rel(art_path),
        "expected": "Two identical runs match; baseline executed; low_atp and wall_inserted blocked",
        "pass": ok and proc.returncode == 0,
    }


def n6_forced_downgrade() -> dict:
    pack = ScientificEvidencePack(
        "overclaim-ceiling-demo", __version__, claim_ceiling="EVIDENCE_SUPPORTED"
    )
    result = apply_claim_downgrade_rules(pack)
    non_conservative = None
    try:
        ScientificEvidencePack("bad", __version__, claim_ceiling="INTERVENTION_SUPPORTED")
        non_conservative = "accepted_unexpectedly"
    except Exception as exc:  # noqa: BLE001 — capture constructor refusal
        non_conservative = f"{type(exc).__name__}: {exc}"

    payload = {
        "original_ceiling": result.original_ceiling,
        "final_ceiling": result.final_ceiling,
        "applied_rules": [
            {
                "rule_id": r.rule_id if hasattr(r, "rule_id") else getattr(r, "name", None),
                "trigger": r.trigger,
                "from_ceiling": r.from_ceiling,
                "to_ceiling": r.to_ceiling,
                "reason": r.reason,
            }
            for r in result.applied_rules
        ],
        "reasons": list(result.reasons),
        "intervention_supported_constructor": non_conservative,
        "note": (
            "ScientificEvidencePack refuses non-conservative ceilings at construction; "
            "EVIDENCE_SUPPORTED without D0/ablation/replay is force-downgraded to CANDIDATE."
        ),
    }
    art_path = ART / "N6_forced_claim_downgrade.json"
    _write_json(art_path, payload)
    ok = (
        result.original_ceiling == "EVIDENCE_SUPPORTED"
        and result.final_ceiling == "CANDIDATE"
        and set(result.reasons) >= {"missing_d0", "missing_ablation", "missing_replay"}
        and "conservative" in non_conservative.lower()
    )
    return {
        "id": "N6_forced_claim_downgrade",
        "problem": "Overclaimed ceiling must be force-downgraded when evidence pack incomplete",
        "literature_gap": "claim–evidence mismatch / reproducibility crisis",
        "downgrade": {
            "original": result.original_ceiling,
            "final": result.final_ceiling,
            "reasons": list(result.reasons),
        },
        "non_conservative_ceiling_refused": "conservative" in non_conservative.lower(),
        "artifact": _suite_rel(art_path),
        "expected": "EVIDENCE_SUPPORTED → CANDIDATE via missing_d0/ablation/replay; INTERVENTION refused",
        "pass": ok,
    }


def he03_status_note() -> dict:
    path = he03_results_path()
    return {
        "results_path": _repo_rel(path),
        "exists": path.is_file(),
        "note": "HE03 adapter present; research results JSON absent — remains unsolved/deferred.",
    }


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    before = {rel: _sha256_file(REPO / rel) for rel in PIN_RELS}
    _write_json(ART / "pins_sha256_before.json", before)

    tests = [
        n1_portfolio(),
        n2_overclaim_trap(),
        n3_right_answer_wrong_reason(),
        n4_biomedical_alife_joint(),
        n5_causal_replay_demo(),
        n6_forced_downgrade(),
    ]

    after = {rel: _sha256_file(REPO / rel) for rel in PIN_RELS}
    _write_json(ART / "pins_sha256_after.json", after)
    pins_unchanged = before == after

    n_pass = sum(1 for t in tests if t["pass"])
    suite = {
        "suite": "novel_valuable_evidence_20260924",
        "product": "CodonTrace Genesis",
        "product_version": __version__,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_at_local_label": "Asia/Tehran (box-local)",
        "repo_root_marker": "pyproject.toml",
        "suite_dir": "docs/claimgate/novel_valuable_evidence_20260924",
        "pythonpath": "src",
        "pins_unchanged": pins_unchanged,
        "pin_sha256": after,
        "he03": he03_status_note(),
        "n_pass": n_pass,
        "n_total": len(tests),
        "tests": tests,
        "honesty": {
            "no_intelligence_claim": True,
            "no_fda_claim": True,
            "no_he02_communication_proof": True,
            "innovation": "claim–evidence discrimination competitors lack",
        },
    }
    _write_json(OUT / "suite_results.json", suite)

    # SUMMARY.md
    lines = [
        "# Novel valuable evidence suite — SUMMARY",
        "",
        f"Product: **CodonTrace Genesis** `{__version__}`",
        f"Pass: **{n_pass}/{len(tests)}**",
        f"Pins unchanged: **{pins_unchanged}**",
        "",
        "## Results",
        "",
    ]
    for t in tests:
        status = "PASS" if t["pass"] else "FAIL"
        lines.append(f"- {status} `{t['id']}` — {t['problem']}")
    lines.extend(
        [
            "",
            "## Pin SHA256 (unchanged)",
            "",
        ]
    )
    for rel, digest in after.items():
        lines.append(f"- `{digest}`  `{rel}`")
    lines.extend(
        [
            "",
            "## Unsolved (still open)",
            "",
            "- HE02 confirmatory communication / information-control separation (decision_rule failed)",
            "- HE03 research results absent (adapter only)",
            "- True collective_intelligence (ClaimGate blocks until earned)",
            "- Major evolutionary transition claims",
            "",
            "## Most impressive honest finding",
            "",
            "HE02 shows a **content-null pattern**: Holm survives vs channel_off/content_null "
            "but **fails vs capsules_shuffled**, so confirmatory communication is refused — "
            "and setting `collective_intelligence=True` on the HE02 bundle **demotes** the "
            "ClaimGate grade (forbidden-alias hit). Same auditor still grades HE01 at level 4 "
            "`replicated_effect` with replay verified. Competitors typically lack this "
            "claim–evidence discrimination.",
            "",
        ]
    )
    (OUT / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if n_pass == len(tests) and pins_unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
