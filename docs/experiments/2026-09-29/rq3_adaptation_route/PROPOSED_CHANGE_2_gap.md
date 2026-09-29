diff --git a/src/codontrace/genesis/measurements/antagonist_population.py b/src/codontrace/genesis/measurements/antagonist_population.py
new file mode 100644
--- /dev/null
+++ b/src/codontrace/genesis/measurements/antagonist_population.py
@@ -0,0 +1,17 @@
+"""RQ-3 wiring gap: the substrate persistence opt-in cannot reach this arm.
+
+`build_idea4_engine_spec(..., ecology="persistence_safe")`
+(src/codontrace/genesis/campaigns/discovery_q_20260928_idea4_engine.py:66-132) returns a
+`GenesisRuntimeProfile` whose population_configs carry the softened ecology:
+respawn_rate 1.0 with amount 12.0, basal_runtime_atp_cost 0.15, initial_runtime_atp 24.0,
+min_runtime_atp 3.0.
+
+RQ-3 runs `StructuralRQArm.boot_structural`, which builds its own
+`LifeLoopEcologyArm.boot(...)` from module constants (STRUCT_BASAL_ATP_COST 0.05,
+STRUCT_RESOURCE_BOLUS_AMOUNT 20.0, food patches from the caller) and never receives the
+idea-4 profile. The antagonist roster's starvation is governed by
+`AntagonistPopulation.maintenance_cost` (0.05) against the energy its contacts earn, so a
+host-side persistence profile cannot keep that roster alive. Two consequences:
+
+1. Round 3 as specified cannot make the antenna survive by passing the opt-in, because the
+   parameter does not travel to this arm.
+2. The smallest honest fix is a substrate-level knob that both paths consume: one
+   `antagonist_maintenance_cost` value on the arm, defaulting to the standing value and set
+   from the same profile field the opt-in already controls.
+
+Proposed wiring, to be supplied as a real diff once the manager confirms which file owns
+the knob:
+
+* `StructuralRQArm.boot_structural(..., antagonist_maintenance_cost: float | None = None)`
+  forwards the value into `AntagonistPopulation.founders(..., maintenance_cost=...)`.
+* `AntagonistPopulation.founders` accepts `maintenance_cost` and passes it through, so the
+  standing default stays byte-identical.
+* The campaign harness passes the value it reads from the substrate profile, and records it
+  in `run_manifest.json` together with the commit sha and config digest.
+
+No top-up and no safety rule is added: strict starvation death stays, per the round-2
+decision (option b).
*** End Patch
