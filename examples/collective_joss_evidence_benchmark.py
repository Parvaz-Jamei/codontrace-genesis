#!/usr/bin/env python3
"""
CodonTrace Genesis — JOSS Evidence Benchmark Runner
====================================================================

This runner targets CodonTrace Genesis public alpha `0.3.0a2` while remaining
compatible with nearby development builds for local validation. It is a JOSS-safe,
feature-discovery and behavior-observability runner. It is not a
success-forcing app. It uses public CodonTrace/GENESIS APIs where possible, builds
scenario families, runs positive/negative controls, records evidence, and leaves
claim decisions conservative.

Design basis:
- Digital evolution should expose replication, heritable variation, differential
  success, resource competition, and measurement, following Avida-like practice.
- Quality Diversity should be tested as diverse high-performing behavior, not as
  an archive-only decoration.
- Multi-agent/social evaluation should use familiar/unfamiliar partners, ablation,
  competition/cooperation, and generalization signals rather than mean fitness.
- Open-endedness should track novelty, diversity, activity, survival, and collapse.

Recommended quick command from a source checkout of the current public-alpha branch:
    PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py \
      --out outputs/joss_evidence_quick --profile quick --seed-count 3 --ticks 10 --population 8

Recommended stronger command with 6 workers:
    PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py \
      --out outputs/joss_evidence_standard --profile strong --workers 6 --seed-count 12 --generations 40 --population 16 --continue-on-error

Recommended long-generation marathon command:
    PYTHONPATH=src python examples/collective_joss_evidence_benchmark.py \
      --out outputs/joss_evidence_publication --profile marathon --workers 6 --seed-count 24 --generations 80 --population 24 --per-run-timeout 240 --continue-on-error

Outputs:
- summary.json
- run_records.csv
- feature_matrix.csv
- counterfactual_pairs.csv
- behavior_diversity.csv
- mortality_breakdown.csv
- social_breakdown.csv
- qd_breakdown.csv
- claim_readiness.json
- report.html
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import os
import platform
import statistics
import sys
import time
import subprocess
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
from collections import Counter, defaultdict
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

RUNNER_NAME = "collective_joss_evidence_benchmark"
RUNNER_SCHEMA_VERSION = "collective_joss_evidence_benchmark_v1.1.0_public_alpha_a2"
TARGET_PUBLIC_CODONTRACE_VERSION = "0.3.0a2"
TARGET_RELEASE_DOI = "10.5281/zenodo.20337435"

GENOME_LIBRARY = {
    "replicator": "101111000",
    "tool_bias": "111000101",
    "memory_bias": "101010111",
    "capsule_bias": "110011001",
    "social_bias": "101001101",
    "low_activity": "000000000",
    "alternating": "101010101",
    "resource_seek": "111100000",
    "mutator_probe": "100111001",
    "long_mixed": "101111000110011001101010111",
}

RECORD_FAMILIES = [
    "energy_accounting_records",
    "death_reason_records",
    "death_classification_records",
    "action_cost_records",
    "action_reward_records",
    "action_precondition_records",
    "fitness_breakdown_records",
    "selection_fitness_records",
    "reproduction_attempt_records",
    "reproduction_gate_records",
    "birth_intent_records",
    "birth_request_records",
    "birth_event_records",
    "child_genome_records",
    "child_admission_records",
    "mutation_plan_records",
    "mutation_result_records",
    "structural_mutation_records",
    "learning_inheritance_records",
    "skill_compression_records",
    "adf_inheritance_records",
    "lineage_growth_records",
    "behavior_descriptors",
    "qd_archive_summary_records",
    "qd_selection_audit",
    "qd_parent_feedback_audit",
    "qd_selection_feedback_records",
    "capsule_adoption_records",
    "capsule_cost_records",
    "capsule_utility_records",
    "capsule_shuffle_records",
    "capsule_source_fitness_records",
    "memory_use_records",
    "delayed_reward_records",
    "signal_memory_link_records",
    "social_interaction_records",
    "partner_interaction_records",
    "role_records",
    "role_timeline_records",
    "role_contribution_records",
    "collective_coordination_records",
    "collective_ablation_records",
    "tool_chain_records",
    "inventory_records",
    "action_wiring_records",
    "generalization_records",
    "engine_frames",
    "engine_digest_audit",
    "strong_claim_ladder_records",
    "output_completeness_records",
    "export_status_records",
    "ai_birth_intervention_records",
    "evidence_status_records",
]

CRITICAL_SYMBOLS = [
    "GenesisEngine", "GenesisRuntimeProfile", "GenesisExperimentSpec", "GenesisEngineConfig",
    "PopulationConfigs", "ReproductionConfig", "MutationConfig", "StructuralMutationConfig",
    "EvolutionConfig", "QDArchiveConfig", "CapsuleTransferConfig", "EpisodicMemoryConfig",
    "BirthEvent", "ChildGenomeResult", "MutationAuditResult", "LearningInheritanceRecord",
    "SkillCompressionRecord", "ADFInheritanceRecord", "QDSelectionAuditRecord", "QDParentFeedback",
    "CapsuleAdoptionRecord", "CapsuleUtilityRecord", "MemoryUseEvidence", "DelayedRewardTrace",
    "ToolActionSpec", "ToolChainRecord", "InventoryState", "SocialInteractionEvent",
    "PartnerInteractionEvent", "BehaviorDescriptor", "EvidenceManifest", "ReplayBundle",
    "ScientificClaimGate", "evaluate_strong_claim_ladder", "FinalClaimManifest", "ReleaseEvidencePack",
    "Phase3ScientificSummary", "NegativeResultReport", "ReplayBundleIndex", "BenchmarkLeaderboardArtifact",
    "AblationMatrixArtifact", "ClaimDowngradeReport", "canonical_digest",
]


def safe_len(value: Any) -> int:
    try:
        if value is None:
            return 0
        return len(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def as_jsonable(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        return repr(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return repr(value)
        return value
    if isinstance(value, (list, tuple)):
        return [as_jsonable(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {str(k): as_jsonable(v, depth + 1) for k, v in value.items()}
    if is_dataclass(value):
        out: dict[str, Any] = {}
        for f in fields(value):
            try:
                out[f.name] = as_jsonable(getattr(value, f.name), depth + 1)
            except Exception as exc:
                out[f.name] = f"<error:{type(exc).__name__}>"
        return out
    if hasattr(value, "value") and isinstance(getattr(value, "value"), (str, int, float, bool)):
        return getattr(value, "value")
    return repr(value)


def safe_digest(obj: Any) -> str | None:
    if obj is None:
        return None
    for attr in ("artifact_digest", "record_digest", "manifest_digest", "replay_bundle_digest", "spec_digest"):
        val = getattr(obj, attr, None)
        if val:
            return str(val)
    run = getattr(obj, "run", None)
    if run is not None:
        val = getattr(run, "spec_digest", None)
        if val:
            return str(val)
    manifest = getattr(obj, "evidence_manifest", None)
    if manifest is not None:
        d = getattr(manifest, "digest", None)
        if callable(d):
            try:
                return str(d())
            except Exception:
                pass
    d = getattr(obj, "digest", None)
    if callable(d):
        try:
            return str(d())
        except Exception as exc:
            return f"digest_error:{type(exc).__name__}:{exc}"
    return None


def obj_get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(obj, Mapping) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def record_counts(result: Any) -> dict[str, int]:
    return {name: safe_len(getattr(result, name, None)) for name in RECORD_FAMILIES}


def aggregate_counter(records: Iterable[Any], names: Sequence[str]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for rec in records or ():
        found = None
        for name in names:
            found = obj_get(rec, name)
            if found is not None:
                break
        if found is not None:
            c[str(found)] += 1
    return dict(c)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("status\nempty_but_available\n", encoding="utf-8")
        return
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                keys.append(key); seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list, tuple)) else v for k, v in row.items()})


def replace_if_possible(obj: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    try:
        valid = {f.name for f in fields(obj)} if is_dataclass(obj) else set()
        filtered = {k: v for k, v in kwargs.items() if k in valid}
        if not filtered:
            return obj
        return replace(obj, **filtered)
    except Exception:
        return obj


def finite_mean(values: Sequence[float]) -> float | None:
    vals = [float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(float(v))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def build_profile_spec(g: Any, family: str, seed: int, ticks: int, population: int, variant: str) -> Any:
    """Build a public profile spec, then apply controlled public dataclass overrides."""
    rp = g.GenesisRuntimeProfile
    base_ticks = max(1, int(ticks))
    pop = max(1, int(population))
    if family == "empty":
        spec = rp.empty_world_smoke(seed=seed, tick_count=max(3, min(base_ticks, 6)))
    elif family == "evolution":
        spec = rp.evolution_pilot_world(seed=seed, tick_count=base_ticks, population=pop)
    elif family == "qd":
        # no_qd ablation uses the generic evolution world with QD disabled below.
        # Some qd-specific pilot versions assume qd instrumentation is on and can be
        # too slow or unsuitable for a disabled-QD ablation.
        if variant == "no_qd":
            spec = rp.evolution_pilot_world(seed=seed, tick_count=max(6, base_ticks), population=pop)
        else:
            spec = rp.qd_selection_pilot_world(seed=seed, tick_count=max(6, base_ticks), population=pop)
    elif family == "capsule":
        spec = rp.capsule_utility_pilot_world(seed=seed, tick_count=max(6, min(base_ticks, 16)))
    elif family == "memory":
        spec = rp.memory_delayed_reward_pilot_world(seed=seed, tick_count=max(6, min(base_ticks, 16)))
    elif family == "toolchain":
        spec = rp.toolchain_pilot_world(seed=seed, tick_count=max(6, min(base_ticks, 14)))
    elif family == "social":
        spec = rp.social_partner_pilot_world(seed=seed, tick_count=max(4, min(base_ticks, 12)))
    else:
        spec = rp.evolution_pilot_world(seed=seed, tick_count=base_ticks, population=pop)

    # Social partner profile is intentionally kept close to its official shape.
    # Some aggressive population/resource overrides can turn a social pilot into an
    # oversized app-like scenario and slow down source-checkout testing. We still
    # keep the variant label so output analysis can compare it, but we do not
    # force success or rewrite the social world here. The no_capsules ablation is
    # handled below because it is a clean public feature toggle.
    if family == "social" and variant in {"collective_mixed", "stress_all", "resource_regen", "scarce_resources"}:
        metadata = dict(getattr(spec, "metadata", {}) or {})
        metadata.update({"runner_variant": variant, "runner_family": family, "runner_schema": RUNNER_SCHEMA_VERSION, "social_profile_preserved": True})
        return replace_if_possible(spec, metadata=metadata)

    genome_mix = (
        GENOME_LIBRARY["replicator"], GENOME_LIBRARY["tool_bias"], GENOME_LIBRARY["memory_bias"],
        GENOME_LIBRARY["capsule_bias"], GENOME_LIBRARY["social_bias"], GENOME_LIBRARY["alternating"],
    )
    if variant in {"gene_diversity", "collective_mixed", "stress_all"}:
        genome_bits = tuple((genome_mix * ((pop // len(genome_mix)) + 2))[:pop])
        spec = replace_if_possible(spec, genome_bits=genome_bits, population_max=max(pop * 2, getattr(spec, "population_max", pop)))
    if variant == "long_genome":
        genome_bits = tuple((GENOME_LIBRARY["long_mixed"], GENOME_LIBRARY["resource_seek"], GENOME_LIBRARY["mutator_probe"]) * max(1, pop // 3))[:pop]
        spec = replace_if_possible(spec, genome_bits=genome_bits, population_max=max(pop * 2, getattr(spec, "population_max", pop)))

    # Engine toggles
    ec = getattr(spec, "engine_config", None)
    if ec is not None:
        ec_updates: dict[str, Any] = {}
        if variant == "no_memory":
            ec_updates["enable_memory"] = False
        if variant == "no_capsules":
            ec_updates["enable_capsules"] = False
        if variant == "no_qd":
            ec_updates["enable_qd"] = False
            ec_updates["qd_mode"] = "off"
        if variant in {"qd_pressure", "collective_mixed", "stress_all"}:
            ec_updates["enable_qd"] = True
            ec_updates["qd_mode"] = "selection_pressure"
        if variant in {"collective_mixed", "stress_all"}:
            ec_updates.update(enable_memory=True, enable_causal_graph=True, enable_capsules=True, enable_qd=True, qd_mode="selection_pressure", claim_level="experimental_engine")
        spec = replace_if_possible(spec, engine_config=replace_if_possible(ec, **ec_updates))

    pc = getattr(spec, "population_configs", None)
    if pc is not None:
        repro = getattr(pc, "reproduction", None)
        mut = getattr(pc, "mutation", None)
        death = getattr(pc, "death_monitoring", None)
        fitness = getattr(pc, "fitness", None)
        capsule_cfg = getattr(pc, "capsule_transfer", None)
        pc_updates: dict[str, Any] = {}
        if repro is not None:
            repro_updates: dict[str, Any] = {}
            if variant == "no_reproduction":
                repro_updates["enabled"] = False
            if variant in {"lamarckian", "collective_mixed", "stress_all"}:
                if hasattr(g, "InheritancePolicy"):
                    repro_updates["inheritance_policy"] = g.InheritancePolicy.LAMARCKIAN_COMPRESSED_LEARNING
                if hasattr(g, "SkillInheritanceMode"):
                    repro_updates["skill_inheritance_mode"] = g.SkillInheritanceMode.COMPRESSED_SKILL
                if hasattr(g, "ADFInheritanceMode"):
                    repro_updates["adf_inheritance_mode"] = g.ADFInheritanceMode.COMPRESS_SUCCESSFUL_BEHAVIOR_TO_ADF
                repro_updates["enable_skill_compression"] = True
                repro_updates["enable_lamarckian_learning_inheritance"] = True
            if variant in {"capacity_pressure", "stress_all"}:
                repro_updates["max_population"] = max(2, min(pop + 2, 10))
                repro_updates["offspring_placement"] = getattr(getattr(g, "OffspringPlacementPolicy", object), "BLOCKED_IF_NO_SPACE", getattr(repro, "offspring_placement", None))
            if variant in {"birth_friendly", "collective_mixed"}:
                repro_updates.update(min_runtime_atp=1.0, parent_atp_cost=0.2, offspring_atp_fraction=0.12, max_population=max(pop * 3, 16))
            pc_updates["reproduction"] = replace_if_possible(repro, **repro_updates)
        if mut is not None:
            mut_updates: dict[str, Any] = {}
            if variant == "no_mutation":
                mut_updates["bit_flip_rate"] = 0.0
                mut_updates["insertion_rate"] = 0.0
                mut_updates["deletion_rate"] = 0.0
            if variant in {"high_mutation", "gene_diversity", "stress_all"}:
                mut_updates.update(bit_flip_rate=0.08, insertion_rate=0.02, deletion_rate=0.01, max_genome_bits=256, policy="stress_structural_probe")
            pc_updates["mutation"] = replace_if_possible(mut, **mut_updates)
        structural = getattr(pc, "structural_mutation", None)
        if structural is not None and variant in {"high_mutation", "long_genome", "stress_all"}:
            pc_updates["structural_mutation"] = replace_if_possible(structural, bit_flip_rate=0.02, codon_insert_rate=0.02, codon_delete_rate=0.01, codon_duplicate_rate=0.015, codon_invert_rate=0.008, codon_translocate_rate=0.004, max_codons=512)
        if death is not None:
            death_updates: dict[str, Any] = {}
            # Keep death monitoring observable but avoid max-age overrides that can be
            # expensive in some engine builds. Mortality pressure is induced by ATP
            # scarcity below, not by forcing a new app-like death policy.
            if variant in {"mortality_pressure", "stress_all"}:
                death_updates.update(enabled=True, remove_on_runtime_atp_lte=0.0, emit_record_for_every_organism_tick=True, emit_energy_link_records=True)
            pc_updates["death_monitoring"] = replace_if_possible(death, **death_updates)
        if fitness is not None and variant in {"scarce_resources", "stress_all"}:
            pc_updates["fitness"] = replace_if_possible(fitness, penalty_blocked_action=1.2, penalty_atp_starvation=8.0, reward_reproduction=10.0, reward_lumen_eaten=3.0)
        if capsule_cfg is not None:
            cap_updates: dict[str, Any] = {}
            if variant == "no_capsules":
                cap_updates["enabled"] = False
            if variant in {"high_communication", "collective_mixed", "stress_all"}:
                cap_updates.update(enabled=True, min_confidence=0.1, min_source_fitness=0.0, max_capsules_per_tick=12, read_radius=3, capsule_ttl=64, max_adoptions_per_organism=4, allow_cross_lineage_transfer=True, emission_cost_runtime_atp=0.05, adoption_cost_learning_atp=0.1)
            pc_updates["capsule_transfer"] = replace_if_possible(capsule_cfg, **cap_updates)
        if variant in {"resource_regen", "collective_mixed", "stress_all"}:
            rr = getattr(pc, "runtime_resource_policy", None)
            if rr is not None:
                pc_updates["runtime_resource_policy"] = replace_if_possible(rr, respawn_enabled=True, respawn_rate=0.35, max_resources=max(pop * 3, 20), amount=2.0, status="runtime_effective")
        if variant in {"qd_pressure", "collective_mixed", "stress_all"}:
            pc_updates["qd_mode"] = "selection_pressure"
        updated_pc = replace_if_possible(pc, **pc_updates)
        spec_updates = {"population_configs": updated_pc}
        # Some engine versions still honor top-level compatibility config fields.
        # Mirror the controlled configs there too so ablations like no_reproduction
        # and no_mutation remain effective across versions.
        if "reproduction" in pc_updates:
            spec_updates["reproduction_config"] = pc_updates["reproduction"]
        if "mutation" in pc_updates:
            spec_updates["mutation_config"] = pc_updates["mutation"]
        if "structural_mutation" in pc_updates:
            spec_updates["structural_mutation_config"] = pc_updates["structural_mutation"]
        if "capsule_transfer" in pc_updates:
            spec_updates["capsule_transfer_config"] = pc_updates["capsule_transfer"]
        spec = replace_if_possible(spec, **spec_updates)

    if variant == "scarce_resources":
        spec = replace_if_possible(spec, initial_runtime_atp=6.0, initial_learning_atp=4.0, population_max=max(pop, 4))
    if variant == "mortality_pressure":
        spec = replace_if_possible(spec, initial_runtime_atp=2.5, initial_learning_atp=2.0, tick_count=max(3, min(getattr(spec, "tick_count", ticks), 8)))
    if variant == "energy_rich":
        spec = replace_if_possible(spec, initial_runtime_atp=35.0, initial_learning_atp=20.0, population_max=max(pop * 3, 16))
    if variant in {"collective_mixed", "stress_all"}:
        spec = replace_if_possible(spec, initial_runtime_atp=28.0, initial_learning_atp=18.0, population_max=max(pop * 3, 24), world_width=max(getattr(spec, "world_width", 4), 6), world_height=max(getattr(spec, "world_height", 4), 6))

    metadata = dict(getattr(spec, "metadata", {}) or {})
    metadata.update({"runner_variant": variant, "runner_family": family, "runner_schema": RUNNER_SCHEMA_VERSION})
    spec = replace_if_possible(spec, metadata=metadata)
    return spec


def extract_material_summary(spec: Any) -> dict[str, Any]:
    grid = getattr(spec, "element_grid", None)
    if grid is None:
        return {"status": "unavailable"}
    cells = getattr(grid, "cells", None)
    counts: Counter[str] = Counter()
    amount: Counter[str] = Counter()
    if isinstance(cells, Mapping):
        for _pos, payload in cells.items():
            if isinstance(payload, Mapping):
                for k, v in payload.items():
                    name = getattr(k, "value", str(k))
                    counts[str(name)] += 1
                    try:
                        amount[str(name)] += float(v)
                    except Exception:
                        pass
    return {"status": "measured", "cell_count": len(cells) if isinstance(cells, Mapping) else None, "element_presence": dict(counts), "element_amount": dict(amount)}


def extract_gene_summary(spec: Any) -> dict[str, Any]:
    genomes = tuple(getattr(spec, "genome_bits", ()) or ())
    lengths = [len(str(g)) for g in genomes]
    unique = len(set(genomes))
    gc_like = []
    for genome in genomes:
        s = str(genome)
        if s:
            gc_like.append((s.count("1") / len(s)))
    return {
        "genome_count": len(genomes),
        "unique_genomes": unique,
        "length_min": min(lengths) if lengths else None,
        "length_max": max(lengths) if lengths else None,
        "length_mean": finite_mean(lengths),
        "one_ratio_mean": finite_mean(gc_like),
        "sample": list(genomes[:5]),
    }


def run_engine(g: Any, family: str, seed: int, ticks: int, population: int, variant: str) -> dict[str, Any]:
    spec = build_profile_spec(g, family, seed, ticks, population, variant)
    started = time.time()
    result = g.GenesisEngine.from_spec(spec).run_ticks()
    elapsed = time.time() - started
    counts = record_counts(result)
    social_types = aggregate_counter(getattr(result, "social_interaction_records", ()) or (), ["interaction_type", "event_type", "kind"])
    partner_types = aggregate_counter(getattr(result, "partner_interaction_records", ()) or (), ["interaction_type", "event_type", "kind"])
    death_reasons = aggregate_counter(getattr(result, "death_reason_records", ()) or (), ["death_reason", "reason", "status_reason"])
    blocked_reasons = aggregate_counter(getattr(result, "action_precondition_records", ()) or (), ["blocked_reason", "reason", "status_reason"])
    qd_reasons = aggregate_counter(getattr(result, "qd_selection_audit", ()) or (), ["reason", "selection_reason", "status_reason", "fallback_reason"])
    qd_changed = 0
    for rec in getattr(result, "qd_selection_audit", ()) or ():
        if bool(obj_get(rec, "qd_changed_selection", default=False)):
            qd_changed += 1
    descriptors = getattr(result, "behavior_descriptors", ()) or ()
    descriptor_digests = set()
    for d in descriptors:
        sd = safe_digest(d) or obj_get(d, "behavior_digest") or repr(d)[:160]
        descriptor_digests.add(str(sd))
    return {
        "family": family,
        "variant": variant,
        "seed": seed,
        "ticks": ticks,
        "population": population,
        "duration_s": round(elapsed, 6),
        "result_digest": safe_digest(result),
        "spec_gene_summary": extract_gene_summary(spec),
        "spec_material_summary": extract_material_summary(spec),
        "counts": counts,
        "social_types": social_types,
        "partner_types": partner_types,
        "death_reasons": death_reasons,
        "blocked_reasons": blocked_reasons,
        "qd_reasons": qd_reasons,
        "qd_changed_selection_count": qd_changed,
        "unique_behavior_descriptors": len(descriptor_digests),
        "status": "passed",
    }


def make_plan(profile: str, seed_count: int) -> list[tuple[str, str]]:
    # Public profile aliases are intentionally friendly for JOSS/reviewer use.
    if profile == "standard":
        profile = "strong"
    elif profile == "extended":
        profile = "stress"
    elif profile == "publication":
        profile = "marathon"
    if profile == "smoke":
        return [
            ("evolution", "birth_friendly"),
            ("evolution", "no_reproduction"),
            ("capsule", "high_communication"),
            ("capsule", "no_capsules"),
            ("memory", "baseline"),
            ("memory", "no_memory"),
            ("qd", "qd_pressure"),
            ("evolution", "no_qd"),
            ("social", "collective_mixed"),
            ("social", "no_capsules"),
        ]
    base = [
        ("empty", "baseline"),
        ("evolution", "birth_friendly"),
        ("evolution", "gene_diversity"),
        ("evolution", "high_mutation"),
        ("evolution", "lamarckian"),
        ("evolution", "no_reproduction"),
        ("evolution", "no_mutation"),
        ("evolution", "capacity_pressure"),
        ("evolution", "mortality_pressure"),
        ("qd", "qd_pressure"),
        ("evolution", "no_qd"),
        ("capsule", "high_communication"),
        ("capsule", "no_capsules"),
        ("memory", "baseline"),
        ("memory", "no_memory"),
        ("toolchain", "baseline"),
        ("social", "collective_mixed"),
        ("social", "no_capsules"),
        ("social", "scarce_resources"),
        ("social", "resource_regen"),
    ]
    if profile in {"strong", "stress", "marathon"}:
        base.extend([
            ("evolution", "long_genome"),
            ("evolution", "energy_rich"),
            ("evolution", "scarce_resources"),
            ("qd", "collective_mixed"),
            ("capsule", "collective_mixed"),
            ("memory", "collective_mixed"),
            ("toolchain", "collective_mixed"),
            ("social", "stress_all"),
        ])
    if profile in {"stress", "marathon"}:
        base.extend([
            ("evolution", "stress_all"),
            ("qd", "stress_all"),
            ("capsule", "stress_all"),
            ("memory", "stress_all"),
            ("toolchain", "stress_all"),
        ])
    if profile == "marathon":
        base.extend([
            ("evolution", "collective_mixed"),
            ("evolution", "stress_all"),
            ("qd", "collective_mixed"),
            ("qd", "stress_all"),
            ("capsule", "high_communication"),
            ("capsule", "collective_mixed"),
            ("memory", "collective_mixed"),
            ("toolchain", "collective_mixed"),
            ("social", "collective_mixed"),
            ("social", "stress_all"),
            ("social", "no_capsules"),
            ("evolution", "mortality_pressure"),
            ("evolution", "capacity_pressure"),
        ])
    # keep order but remove exact duplicates to avoid accidental double-counting unless --repeat-per-scenario is used
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for item in base:
        if item not in seen:
            unique.append(item); seen.add(item)
    return unique


def parse_csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    items = {v.strip() for v in value.split(",") if v.strip()}
    return items or None


def build_tasks(plan: Sequence[tuple[str, str]], seed_start: int, seed_count: int, repeats: int) -> list[tuple[str, str, int, int]]:
    tasks: list[tuple[str, str, int, int]] = []
    for family, variant in plan:
        for seed in range(seed_start, seed_start + seed_count):
            for repeat_index in range(max(1, repeats)):
                tasks.append((family, variant, seed, repeat_index))
    return tasks


def build_counterfactuals(run_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in run_rows:
        if row.get("status") != "passed":
            continue
        by_key[(row["family"], int(row["seed"]))][row["variant"]] = row
    pairs = []
    comparisons = [
        ("capsule", "high_communication", "no_capsules", ["capsule_adoption_records", "capsule_utility_records", "social_interaction_records"]),
        ("social", "collective_mixed", "no_capsules", ["social_interaction_records", "partner_interaction_records", "capsule_adoption_records"]),
        ("memory", "baseline", "no_memory", ["memory_use_records", "delayed_reward_records"]),
        ("qd", "qd_pressure", "no_qd", ["qd_selection_audit", "qd_parent_feedback_audit"]),
        ("evolution", "high_mutation", "no_mutation", ["mutation_result_records", "birth_event_records", "child_genome_records"]),
        ("evolution", "birth_friendly", "no_reproduction", ["birth_event_records", "reproduction_gate_records"]),
    ]
    for (family, seed), variants in by_key.items():
        for comp_family, treatment, control, metrics in comparisons:
            if family != comp_family:
                continue
            tr = variants.get(treatment); ct = variants.get(control)
            if not tr or not ct:
                continue
            deltas = {}
            for metric in metrics:
                deltas[metric] = int(tr["counts"].get(metric, 0)) - int(ct["counts"].get(metric, 0))
            pairs.append({"family": family, "seed": seed, "treatment": treatment, "control": control, "deltas": deltas})
    return pairs


def claim_readiness(summary: dict[str, Any], counterfactuals: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts = summary["aggregate_counts"]
    social = counts.get("social_interaction_records", 0)
    partner = counts.get("partner_interaction_records", 0)
    birth = counts.get("birth_event_records", 0)
    mutation = counts.get("mutation_result_records", 0)
    memory = counts.get("memory_use_records", 0)
    delayed = counts.get("delayed_reward_records", 0)
    qd = counts.get("qd_selection_audit", 0)
    qd_parent = counts.get("qd_parent_feedback_audit", 0)
    capsule_util = counts.get("capsule_utility_records", 0)
    death = counts.get("death_reason_records", 0)
    behavior_unique = summary.get("unique_behavior_descriptors_total", 0)
    positive_capsule_deltas = [p for p in counterfactuals if p.get("family") in {"capsule", "social"} and p.get("deltas", {}).get("capsule_adoption_records", 0) > 0]
    positive_memory_deltas = [p for p in counterfactuals if p.get("family") == "memory" and p.get("deltas", {}).get("memory_use_records", 0) > 0]
    positive_qd_deltas = [p for p in counterfactuals if p.get("family") == "qd" and p.get("deltas", {}).get("qd_selection_audit", 0) > 0]
    return {
        "evolution_primitives_observed": birth > 0 and mutation > 0 and death > 0,
        "memory_primitives_observed": memory > 0 and delayed > 0,
        "capsule_primitives_observed": capsule_util > 0 and len(positive_capsule_deltas) > 0,
        "qd_primitives_observed": qd > 0 and qd_parent > 0,
        "social_interaction_observed": social > 0 and partner > 0,
        "behavior_diversity_observed": behavior_unique >= max(10, summary.get("runs_completed", 0)),
        "collective_intelligence_claim_ready": False,
        "collective_intelligence_reason": "Runner can observe social/capsule/memory/QD building blocks, but a real collective-intelligence claim needs stable group-over-individual improvement, non-capsule cooperation, role complementarity, unfamiliar-partner generalization, and communication ablation effect sizes across larger controlled campaigns.",
        "recommended_next_benchmark": "Increase --profile stress --seed-count 20 --ticks 60 --population 24 and compare collective_mixed vs no_capsules/no_memory/no_qd/no_reproduction with predefined effect-size gates.",
    }


def write_html_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    rows = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>" for k, v in summary.items() if k not in {"aggregate_counts", "death_reasons", "social_types", "qd_reasons", "warnings", "errors"})
    counts = "".join(f"<tr><td>{html.escape(k)}</td><td>{v}</td></tr>" for k, v in sorted(summary.get("aggregate_counts", {}).items()))
    warnings = "".join(f"<li>{html.escape(json.dumps(w, ensure_ascii=False))}</li>" for w in payload.get("warnings", [])) or "<li>none</li>"
    errors = "".join(f"<li>{html.escape(json.dumps(e, ensure_ascii=False))}</li>" for e in payload.get("errors", [])) or "<li>none</li>"
    html_text = f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>CodonTrace JOSS Evidence Benchmark Report</title>
<style>body{{font-family:Arial,Tahoma,sans-serif;margin:32px;line-height:1.7;background:#f7f7fb;color:#111}}.card{{background:white;border:1px solid #ddd;border-radius:14px;padding:18px;margin:16px 0;box-shadow:0 2px 10px #0001}}table{{width:100%;border-collapse:collapse;background:white}}td,th{{border:1px solid #ddd;padding:8px;text-align:left;direction:ltr}}th{{background:#eef}}code{{direction:ltr;unicode-bidi:embed;background:#f0f0f0;padding:2px 5px;border-radius:5px}}</style></head>
<body><h1>CodonTrace Genesis — JOSS Evidence Benchmark</h1>
<div class="card"><h2>حکم runner</h2><p><b>{html.escape(payload['status'])}</b></p><p>این runner ادعای هوش جمعی را hard-code نمی‌کند؛ فقط evidence، کنترل‌ها و counterfactualها را جمع می‌کند.</p></div>
<div class="card"><h2>خلاصه اجرا</h2><table>{rows}</table></div>
<div class="card"><h2>Aggregate Feature Counts</h2><table><tr><th>feature</th><th>count</th></tr>{counts}</table></div>
<div class="card"><h2>Claim Readiness</h2><pre dir="ltr">{html.escape(json.dumps(payload.get('claim_readiness', {}), indent=2, ensure_ascii=False))}</pre></div>
<div class="card"><h2>Warnings</h2><ul>{warnings}</ul></div>
<div class="card"><h2>Errors</h2><ul>{errors}</ul></div>
</body></html>"""
    path.write_text(html_text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="JOSS-safe evidence benchmark runner for CodonTrace Genesis")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--profile", choices=["smoke", "quick", "standard", "strong", "extended", "stress", "publication", "marathon"], default="standard", help="Scenario breadth: smoke < quick < standard/strong < extended/stress < publication/marathon")
    ap.add_argument("--seed-count", type=int, default=8, help="Number of seeds. Increase this for more repeated evolutionary trials.")
    ap.add_argument("--seed-start", type=int, default=1, help="First seed value; useful for continuing a later batch.")
    ap.add_argument("--ticks", type=int, default=24, help="Engine ticks/generations per run. --generations is an alias that overrides this.")
    ap.add_argument("--generations", type=int, default=None, help="Alias for --ticks, clearer for long evolutionary runs.")
    ap.add_argument("--population", type=int, default=14, help="Initial target population for profiles that support population override.")
    ap.add_argument("--workers", type=int, default=1, help="Parallel isolated subprocess workers. Use --workers 6 on your system.")
    ap.add_argument("--repeat-per-scenario", type=int, default=1, help="Repeat each family/variant/seed run; mostly useful for digest stability checks.")
    ap.add_argument("--max-runs", type=int, default=0, help="Optional cap on total planned runs for debugging; 0 means no cap.")
    ap.add_argument("--families", default=None, help="Comma filter, e.g. evolution,qd,capsule,memory,toolchain,social")
    ap.add_argument("--variants", default=None, help="Comma filter, e.g. collective_mixed,stress_all,no_capsules")
    ap.add_argument("--src-dir", default=None, help="Optional source checkout src directory to prepend to PYTHONPATH, e.g. --src-dir src")
    ap.add_argument("--library-zip-name", default=None, help="Optional expected zip filename for release identity warning")
    ap.add_argument("--expected-version", default=TARGET_PUBLIC_CODONTRACE_VERSION, help="Expected public CodonTrace version; mismatches are warnings, not failures")
    ap.add_argument("--continue-on-error", action="store_true")
    ap.add_argument("--no-isolate-runs", action="store_true", help="Run all scenarios in this process instead of subprocess isolation; disables parallel worker safety")
    ap.add_argument("--per-run-timeout", type=int, default=90, help="Timeout seconds for each isolated scenario")
    ap.add_argument("--single-run-mode", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--single-family", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--single-variant", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--single-seed", type=int, default=1, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.generations is not None:
        args.ticks = int(args.generations)
    args.workers = max(1, int(args.workers))
    args.seed_count = max(1, int(args.seed_count))
    args.seed_start = int(args.seed_start)
    args.repeat_per_scenario = max(1, int(args.repeat_per_scenario))

    effective_src_dir = args.src_dir or ("src" if Path("src").exists() else None)
    if effective_src_dir:
        src_path = str(Path(effective_src_dir).resolve())
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        os.environ["PYTHONPATH"] = src_path + (os.pathsep + os.environ.get("PYTHONPATH", "") if os.environ.get("PYTHONPATH") else "")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    try:
        import codontrace
        import codontrace.genesis as g
    except Exception:
        traceback.print_exc()
        return 2

    actual_version = getattr(codontrace, "__version__", None)
    if args.expected_version and actual_version != args.expected_version:
        warnings.append({
            "kind": "codontrace_version_mismatch_to_public_target",
            "expected_version": args.expected_version,
            "actual_version": actual_version,
            "classification": "provenance/version warning; rerun on the expected public release before publication-grade claims",
        })

    if args.single_run_mode:
        try:
            row = run_engine(g, str(args.single_family), int(args.single_seed), int(args.ticks), int(args.population), str(args.single_variant))
            print(json.dumps(row, ensure_ascii=False))
            return 0
        except Exception as exc:
            payload = {"family": args.single_family, "variant": args.single_variant, "seed": args.single_seed, "status": "error", "error": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=8)}
            print(json.dumps(payload, ensure_ascii=False))
            return 1

    # Public API surface checks
    missing = [name for name in CRITICAL_SYMBOLS if not hasattr(g, name)]
    if missing:
        errors.append({"kind": "missing_critical_public_symbols", "symbols": missing})

    release_artifact = getattr(g, "RELEASE_ARTIFACT_NAME", None)
    if args.library_zip_name and release_artifact != args.library_zip_name:
        warnings.append({
            "kind": "release_identity_mismatch_to_tested_zip",
            "expected_zip": args.library_zip_name,
            "actual_release_artifact_name": release_artifact,
            "classification": "packaging/provenance; normally does not change engine runtime behavior",
        })

    alias_names = ["Phase3ScientificSummary", "NegativeResultReport", "ReplayBundleIndex", "BenchmarkLeaderboardArtifact", "AblationMatrixArtifact", "ClaimDowngradeReport"]
    alias_offenders = [name for name in alias_names if getattr(g, name, None) is getattr(g, "ReleaseEvidencePack", object())]
    if alias_offenders:
        errors.append({"kind": "phase3_artifacts_alias_release_pack", "offenders": alias_offenders})

    plan = make_plan(args.profile, args.seed_count)
    family_filter = parse_csv_filter(args.families)
    variant_filter = parse_csv_filter(args.variants)
    if family_filter:
        plan = [p for p in plan if p[0] in family_filter]
    if variant_filter:
        plan = [p for p in plan if p[1] in variant_filter]
    tasks = build_tasks(plan, args.seed_start, args.seed_count, args.repeat_per_scenario)
    if args.max_runs and args.max_runs > 0:
        tasks = tasks[: int(args.max_runs)]

    run_rows: list[dict[str, Any]] = []

    def run_one_task(task: tuple[str, str, int, int]) -> dict[str, Any]:
        family, variant, seed, repeat_index = task
        if args.no_isolate_runs:
            row = run_engine(g, family, seed, args.ticks, args.population, variant)
        else:
            cmd = [
                sys.executable, str(Path(__file__).resolve()),
                "--out", str(out),
                "--profile", args.profile,
                "--ticks", str(args.ticks),
                "--population", str(args.population),
                "--single-run-mode",
                "--single-family", family,
                "--single-variant", variant,
                "--single-seed", str(seed),
            ]
            if effective_src_dir:
                cmd.extend(["--src-dir", str(Path(effective_src_dir).resolve())])
            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=args.per_run_timeout, env=os.environ.copy())
            text = (completed.stdout or "").strip().splitlines()
            if not text:
                raise RuntimeError(f"isolated run produced no JSON; rc={completed.returncode}; stderr={completed.stderr[:800]}")
            row = json.loads(text[-1])
            if completed.returncode != 0 or row.get("status") == "error":
                raise RuntimeError(f"isolated run failed rc={completed.returncode}: {row.get('error')} {row.get('message')}")
        row["repeat_index"] = repeat_index
        return row

    if args.no_isolate_runs or args.workers <= 1:
        for i, task in enumerate(tasks, start=1):
            family, variant, seed, repeat_index = task
            try:
                print(f"[runner] {i}/{len(tasks)} running family={family} variant={variant} seed={seed} repeat={repeat_index}", flush=True)
                row = run_one_task(task)
                print(f"[runner] {i}/{len(tasks)} done family={family} variant={variant} seed={seed} repeat={repeat_index} status={row.get('status')}", flush=True)
                run_rows.append(row)
            except subprocess.TimeoutExpired as exc:
                err = {"kind": "runtime_run_timeout", "family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "timeout_s": args.per_run_timeout}
                errors.append(err)
                run_rows.append({"family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "status": "timeout", "error": "TimeoutExpired", "message": str(exc)})
                if not args.continue_on_error:
                    break
            except Exception as exc:
                err = {"kind": "runtime_run_error", "family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "error": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=8)}
                errors.append(err)
                run_rows.append({"family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "status": "error", "error": type(exc).__name__, "message": str(exc)})
                if not args.continue_on_error:
                    break
    else:
        print(f"[runner] parallel mode: workers={args.workers}, planned_runs={len(tasks)}, ticks/generations={args.ticks}, population={args.population}", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_task = {executor.submit(run_one_task, task): task for task in tasks}
            for i, fut in enumerate(as_completed(future_to_task), start=1):
                family, variant, seed, repeat_index = future_to_task[fut]
                try:
                    row = fut.result()
                    print(f"[runner] {i}/{len(tasks)} done family={family} variant={variant} seed={seed} repeat={repeat_index} status={row.get('status')}", flush=True)
                    run_rows.append(row)
                except subprocess.TimeoutExpired as exc:
                    err = {"kind": "runtime_run_timeout", "family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "timeout_s": args.per_run_timeout}
                    errors.append(err)
                    run_rows.append({"family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "status": "timeout", "error": "TimeoutExpired", "message": str(exc)})
                    print(f"[runner] {i}/{len(tasks)} TIMEOUT family={family} variant={variant} seed={seed}", flush=True)
                    if not args.continue_on_error:
                        break
                except Exception as exc:
                    err = {"kind": "runtime_run_error", "family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "error": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=8)}
                    errors.append(err)
                    run_rows.append({"family": family, "variant": variant, "seed": seed, "repeat_index": repeat_index, "status": "error", "error": type(exc).__name__, "message": str(exc)})
                    print(f"[runner] {i}/{len(tasks)} ERROR family={family} variant={variant} seed={seed}: {type(exc).__name__}: {exc}", flush=True)
                    if not args.continue_on_error:
                        break

    aggregate: Counter[str] = Counter()
    deaths: Counter[str] = Counter()
    socials: Counter[str] = Counter()
    partners: Counter[str] = Counter()
    qd_reasons: Counter[str] = Counter()
    materials: Counter[str] = Counter()
    gene_unique_total = 0
    unique_behavior_total = 0
    digest_set: set[str] = set()
    for row in run_rows:
        if row.get("status") != "passed":
            continue
        aggregate.update(row.get("counts", {}))
        deaths.update(row.get("death_reasons", {}))
        socials.update(row.get("social_types", {}))
        partners.update(row.get("partner_types", {}))
        qd_reasons.update(row.get("qd_reasons", {}))
        gs = row.get("spec_gene_summary", {})
        gene_unique_total += int(gs.get("unique_genomes") or 0)
        ms = row.get("spec_material_summary", {})
        for k, v in (ms.get("element_presence", {}) or {}).items():
            materials[str(k)] += int(v)
        unique_behavior_total += int(row.get("unique_behavior_descriptors") or 0)
        if row.get("result_digest"):
            digest_set.add(str(row["result_digest"]))

    counterfactuals = build_counterfactuals(run_rows)
    summary = {
        "runner": RUNNER_NAME,
        "runner_schema_version": RUNNER_SCHEMA_VERSION,
        "status": "passed" if not errors else "failed",
        "profile": args.profile,
        "seed_start": args.seed_start,
        "seed_count": args.seed_count,
        "ticks": args.ticks,
        "generations": args.ticks,
        "population": args.population,
        "workers": args.workers,
        "repeat_per_scenario": args.repeat_per_scenario,
        "families_filter": args.families,
        "variants_filter": args.variants,
        "runs_planned": len(tasks),
        "runs_completed": sum(1 for r in run_rows if r.get("status") == "passed"),
        "runs_failed": sum(1 for r in run_rows if r.get("status") != "passed"),
        "duration_s": round(time.time() - started, 3),
        "codontrace_version": getattr(codontrace, "__version__", None),
        "target_public_version": TARGET_PUBLIC_CODONTRACE_VERSION,
        "expected_version": args.expected_version,
        "genesis_exports": len(getattr(g, "__all__", ())),
        "release_artifact_name": release_artifact,
        "unique_result_digests": len(digest_set),
        "aggregate_counts": dict(aggregate),
        "death_reasons": dict(deaths.most_common(50)),
        "social_types": dict(socials.most_common(50)),
        "partner_types": dict(partners.most_common(50)),
        "qd_reasons": dict(qd_reasons.most_common(50)),
        "material_presence_total": dict(materials),
        "gene_unique_total_across_runs": gene_unique_total,
        "unique_behavior_descriptors_total": unique_behavior_total,
        "counterfactual_pair_count": len(counterfactuals),
    }
    readiness = claim_readiness(summary, counterfactuals)

    # Flatten for CSVs
    per_run_rows = []
    feature_matrix = []
    behavior_rows = []
    for row in run_rows:
        flat = {"family": row.get("family"), "variant": row.get("variant"), "seed": row.get("seed"), "repeat_index": row.get("repeat_index"), "status": row.get("status"), "duration_s": row.get("duration_s"), "result_digest": row.get("result_digest"), "unique_behavior_descriptors": row.get("unique_behavior_descriptors")}
        for k, v in (row.get("counts", {}) or {}).items():
            flat[k] = v
            feature_matrix.append({"family": row.get("family"), "variant": row.get("variant"), "seed": row.get("seed"), "repeat_index": row.get("repeat_index"), "feature": k, "count": v})
        per_run_rows.append(flat)
        behavior_rows.append({"family": row.get("family"), "variant": row.get("variant"), "seed": row.get("seed"), "repeat_index": row.get("repeat_index"), "unique_behavior_descriptors": row.get("unique_behavior_descriptors"), "gene_summary": row.get("spec_gene_summary"), "material_summary": row.get("spec_material_summary")})

    write_csv(out / "run_records.csv", per_run_rows)
    write_csv(out / "feature_matrix.csv", feature_matrix)
    write_csv(out / "counterfactual_pairs.csv", counterfactuals)
    write_csv(out / "behavior_diversity.csv", behavior_rows)
    write_csv(out / "mortality_breakdown.csv", [{"reason": k, "count": v} for k, v in deaths.items()])
    write_csv(out / "social_breakdown.csv", [{"type": k, "count": v} for k, v in socials.items()])
    write_csv(out / "qd_breakdown.csv", [{"reason": k, "count": v} for k, v in qd_reasons.items()])

    run_config = {
        "runner": RUNNER_NAME,
        "runner_schema_version": RUNNER_SCHEMA_VERSION,
        "codontrace_version": getattr(codontrace, "__version__", None),
        "release_doi": TARGET_RELEASE_DOI,
        "target_public_version": TARGET_PUBLIC_CODONTRACE_VERSION,
        "expected_version": args.expected_version,
        "profile": args.profile,
        "seed_start": args.seed_start,
        "seed_count": args.seed_count,
        "ticks": args.ticks,
        "generations": args.ticks,
        "population": args.population,
        "workers": args.workers,
        "repeat_per_scenario": args.repeat_per_scenario,
        "families_filter": args.families,
        "variants_filter": args.variants,
        "max_runs": args.max_runs,
        "per_run_timeout": args.per_run_timeout,
        "continue_on_error": bool(args.continue_on_error),
        "claim_boundary": "This benchmark demonstrates reproducible instrumentation and candidate evidence surfaces. It is not a proof of collective intelligence.",
    }
    (out / "run_config.json").write_text(json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8")
    env_lines = [
        f"python_executable={sys.executable}",
        f"python_version={sys.version.replace(chr(10), ' ')}",
        f"platform={platform.platform()}",
        f"cwd={Path.cwd()}",
        f"codontrace_version={getattr(codontrace, '__version__', None)}",
        f"target_public_version={TARGET_PUBLIC_CODONTRACE_VERSION}",
        f"release_doi={TARGET_RELEASE_DOI}",
        f"runner={RUNNER_NAME}",
        f"runner_schema_version={RUNNER_SCHEMA_VERSION}",
    ]
    (out / "environment.txt").write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    payload = {"status": summary["status"], "summary": summary, "claim_readiness": readiness, "warnings": warnings, "errors": errors, "counterfactuals": counterfactuals, "run_rows_compact": per_run_rows[:200]}
    (out / "summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "claim_readiness.json").write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")
    write_html_report(out / "report.html", payload)

    # Manifest
    manifest = {
        "runner": RUNNER_NAME,
        "runner_schema_version": RUNNER_SCHEMA_VERSION,
        "target_public_version": TARGET_PUBLIC_CODONTRACE_VERSION,
        "release_doi": TARGET_RELEASE_DOI,
        "generated_files": sorted(p.name for p in out.iterdir() if p.is_file()),
        "recommended_interpretation": "Use this runner to discover regressions and collect JOSS-safe evidence artifacts. Do not claim collective intelligence unless claim_readiness, ablation analysis, external statistics, and archived benchmark evidence justify it.",
    }
    (out / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also produce a local zip of outputs, useful after running manually.
    try:
        with zipfile.ZipFile(out / "evidence_outputs.zip", "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in out.iterdir():
                if p.is_file() and p.name != "evidence_outputs.zip":
                    zf.write(p, arcname=p.name)
    except Exception as exc:
        warnings.append({"kind": "output_zip_failed", "error": type(exc).__name__, "message": str(exc)})

    print(json.dumps({"status": summary["status"], "runs_completed": summary["runs_completed"], "runs_failed": summary["runs_failed"], "aggregate_counts": summary["aggregate_counts"], "warnings": warnings, "errors": errors[:3], "out": str(out)}, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
