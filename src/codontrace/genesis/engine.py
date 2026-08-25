"""Unified GENESIS experiment engine orchestration layer.

This module wires existing GENESIS primitives together for UI/API consumers. It
orchestrates population stepping, causal/capsule runtime, QD summaries,
evidence artifacts, and replay bundles. It does not reimplement organism logic,
invoke LLM providers, or claim a full GENESIS Engine.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Protocol, cast, runtime_checkable

from codontrace._types import JsonValue
from codontrace.actions import (
    ActionRegistry,
    ActionRuntimeConfig,
    default_action_registry,
    default_action_registry_manifest,
)
from codontrace.codon import CodonTable
from codontrace.genesis.adf_runtime import ADFExecutionPolicy, ADFMacroRegistry
from codontrace.genesis.api_audit import ActionWiringMatrix, export_action_wiring_matrix
from codontrace.genesis.artifacts import (
    ExperimentSummary,
    PopulationSnapshot,
    RawEventSchema,
    ReplayBundle,
    ReviewStatus,
    RunArtifactSchema,
    RunManifest,
    compute_source_digest,
    manifest_from_parts,
)
from codontrace.genesis.birth import (
    ADFInheritanceRecord,
    AIBirthInterventionRecord,
    BirthEvent,
    ChildGenomeResult,
    LearningInheritanceRecord,
    MutationAuditResult,
    MutationPlan,
    SkillCompressionRecord,
    SkillCompressionAblationPolicy,
)
from codontrace.genesis.capsule import CapsuleTransferConfig, NexusStigmergyLayer
from codontrace.genesis.capsule_validation import CapsuleAblationPolicy, CapsuleOutcomeWindow
# NOTE: Full content continues - this is a truncated test. Full restore will follow.
