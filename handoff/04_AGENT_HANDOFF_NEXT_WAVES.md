# CodonTrace Genesis — Handoff به ایجنت بعدی (بعد از موج ۱c)

تاریخ: 2026-09-12. مخزن هدف: `Parvaz-Jamei/codontrace-genesis` (شاخهٔ `main` در `49b9f2c`). این فایل را همراه با `AGENT_PROMPT_WAVES_0_3.md` (قوانین ثابت، Addendum 1 و Addendum 2) و پوشهٔ `handoff/` به ایجنت جدید بده.

## بخش ۱ — وضعیت فعلی (فارسی، کوتاه)

### چه چیزی merge شده (روی main)

| PR | موج | نتیجه |
|---|---|---|
| #20–#22 | موج ۰ | اصلاح ایرادات audit |
| #23 (`460791c`) | موج ۱ | HE01 prereg + طرح چهاربازو + research v1 (null، dz=0) |
| #24 (`e58d983`) | موج ۱b | کالیبراسیون بقا + research v2 (adoptions 169، اما همهٔ بازوها bitwise-identical) |
| — (`49b9f2c`) | موج ۲ | ClaimGate auditor مستقل؛ v2 را `assay_invalid` برچسب می‌زند |

### دو کار موازی برای موج ۱c (فقط یکی باید merge شود)

1. **PR #25** (`cursor/fix-he01-assay-validity-f6b1`, draft) — از ایجنت قبلی. زیرلایهٔ `phase_e_substrate_world`. نتیجه: manipulation check شکست خورد (22/30 seed)، `assay_failed = true`. یعنی هنوز یک assay معتبر نیست.
2. **Patch من:** `handoff/0001-wave-1c-e2-coupling.patch` (commit `34f9da2` روی base `49b9f2c`؛ ۱۲ فایل، +6442/−128). زیرلایهٔ `life_loop_world` + یک knob اختیاری در موتور که یال DAG «capsule → action» (e2) را می‌سازد. نتیجه: manipulation check پاس شد، assay معتبر، اما واریانس بین seedها صفر است (sd = 0)، پس آمار جفتی تعریف‌نشده است (`dz_undefined`). سقف ClaimGate همچنان `runtime_observation`.

> چون این محیط به GitHub دسترسی push نداشت، کار من به‌صورت patch بسته شده و باید توسط ایجنت جدید روی مخزن اعمال و PR شود (دستور دقیق در بخش ۳).

### چرا v2 نامعتبر بود (ریشه، تأییدشده در کد)

- در `life_loop_world`، `adopt_causal_capsule` فقط یک گره/یال به گراف اضافه می‌کرد؛ `GenesisOrganism.step` هرگز گراف را برای انتخاب action نمی‌خواند → یال e2 در DAG وجود نداشت → همهٔ بازوها به‌ناچار یکسان.
- یک emitter، غذای تجدیدناپذیر (respawn هرگز زیر ارگانیسم نمی‌افتاد؛ `EAT_LUMEN` یک‌بار مصرف).
- Source fitness کپسول = «آخرین امتیاز انتخابی تیک قبل» → gate یک تابع پله‌ای است، نه پیوسته.

### چه چیزی در patch من هست (خلاصهٔ فنی)

- `CapsuleTransferConfig.adoption_effect_action: bool=False`, `adoption_substitutable_actions=("WAIT",)` — فقط وقتی True است در `to_dict` سریال می‌شود (digestهای قبلی دست‌نخورده).
- `GenesisOrganism`: bias کپسول فقط جای action «قابل‌جایگزینی» (WAIT) می‌نشیند؛ در `world_delta` کلیدهای `capsule_action_bias_*` ثبت می‌شود (manipulation check از همین‌ها می‌خواند).
- `RuntimeResourcePolicy.respawn_under_organisms=False`, `respawn_draws_per_tick=1` (پیش‌فرض خاموش).
- HE01 v3: نقش‌ها emitter (`101110000`، payload EAT_LUMEN، fitness 3.0) / poor-emitter (`010110000`، payload SENSE_DANGER، fitness 1.0) / receiver (`000000000`)؛ بازوی پنجم `oracle_capsule` (کنترل مثبت)؛ outcome اولیه `receiver_mean_terminal_runtime_atp`؛ کدهای `assay_failed_*` برای manipulation check؛ قانون شاهد منفی از «هم‌ارز نبودن» به «برتر نبودن» (`shuffled_better_than_capsules_off`) تغییر کرد؛ dose ladder به تست الگوی `step_up_then_saturate` با permutation.
- `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md` (digest `6d156e82…de8`)، `docs/hard_experiment_01/results_v3.json` (digest `e71321fa…aef`)، بخش «Results (research v3) — Wave 1c» در `docs/HARD_EXPERIMENT_01.md`، CLAIMS.md §4.4.
- ClaimGate adapter: `oracle_capsule → positive_control`، خواندن `primary_outcome` و `assay_manipulation_failures`؛ پیش‌فرض v3 با fallback به v2.
- اعداد v3 (۳۰ seed، 40 tick، جمعیت ۱۶): on 78.05 / off 70.575 / capsules_off 28.0 / shuffled 28.49 / oracle 78.375؛ gate فقط در بازوی treatment رد می‌کند (~۹۱ رد در هر seed)؛ dose 70.6→78.1→28.0 (p≈1e-4)؛ **sd=0 در همهٔ بازوها**.
- تست‌ها: `tests/test_hard_experiment_01.py` + adapters + auditor + pinهای Phase D/E سبز؛ ruff روی فایل‌های لمس‌شده پاک؛ `tools/check_core_boundary.py` سبز.

## بخش ۲ — قوانین ثابت (همان‌هایی که در `AGENT_PROMPT_WAVES_0_3.md` هست؛ عیناً)

- حداقل tool call، بدون گزارش لحظه‌به‌لحظه، بدون Google Drive، بدون tag/PyPI مگر دستور صریح.
- ClaimGate هرگز شل نمی‌شود. هیچ Phase حرفی جدید (M به بعد). نام محصول همیشه **CodonTrace Genesis**.
- ادعاهای ممنوع: intelligence / collective_intelligence / AGI / «Tokyo Type 1 passed» / «جایگزین Avida».
- pinهای Phase A–E نباید بشکنند: `life_loop_world(seed=7, tick_count=12, population=6)` → spec `7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac`، snapshot `76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a`.
- هویت `0.3.0b4.dev0` می‌ماند (PyPI tip `0.3.0b3`).
- هر موج یک PR، squash-merge؛ گزارش کوتاه فارسی در پایان هر موج.
- هر knob جدید موتور: `@dataclass(frozen=True, slots=True)`، `enabled=False` پیش‌فرض، اعتبارسنجی در `__post_init__` با `ConfigurationError`، در `to_dict` فقط وقتی غیرپیش‌فرض است سریال شود (پایداری digest)، `digest()` با `canonical_digest`، هر knob ↔ یک یال DAG، و دو تست اجباری: «pinها با X خاموش تغییر نمی‌کنند» و «X روشن حداقل یک رکورد runtime را عوض می‌کند».

## بخش ۳ — PROMPT برای ایجنت جدید (از این‌جا کپی کن)

```
You are continuing CodonTrace Genesis (repo Parvaz-Jamei/codontrace-genesis, main at 49b9f2c).
Read AGENT_PROMPT_WAVES_0_3.md (rules, Addendum 1, Addendum 2) and AGENT_HANDOFF_NEXT_WAVES.md first. Apply every standing rule in §2 of the handoff verbatim. Minimal tool calls; no play-by-play; short Persian report at the end of each wave.

STEP 0 — Land Wave 1c (decide between the two competing implementations; exactly one merges)
0.1  git checkout -b cursor/wave-1c-e2-coupling main   (main must be 49b9f2c; if main moved, rebase and re-run tests)
     git am --3way handoff/0001-wave-1c-e2-coupling.patch
0.2  Verify: ruff check on the 12 touched files; python -m pytest -q tests/test_hard_experiment_01.py tests/test_claimgate_adapters.py tests/test_claimgate_auditor.py tests/test_genesis_phase_e_substrate.py tests/test_genesis_phase_d_multigen_evidence.py tests/test_genesis_scientific_gaps_2026.py; python tools/check_core_boundary.py; then the full suite once. Phase A–E pins must be unchanged.
0.3  Push and open a DRAFT PR titled "fix(he01): Wave 1c e2 coupling + valid manipulation check (v3)". Body must state: alternative to #25; assay valid (manipulation check passed 30/30); limitation sd=0 across seeds → dz_undefined, decision rule not passed; ceiling stays runtime_observation; pins unchanged; identity 0.3.0b4.dev0; no tag/publish.
0.4  Decision rule between PRs: merge the one whose committed results_v3.json has assay_failed=false AND CI green. As of this handoff that is the patch (PR #25 has assay_failed=true, manipulation check failed 22/30). Close the other PR unmerged with a one-line comment pointing to the merged one. Do NOT merge both (same file names: docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md, docs/hard_experiment_01/results_v3.json).

STEP 1 — Wave 1d: give the seeds variance (PR "fix(he01): Wave 1d seed-dependent calibration (v4)")
Problem: in v3 the overlay is deterministic given fixed roles and full-grid food, so all 30 seeds yield identical outcomes (sd=0); paired statistics are undefined and the shuffled-vs-off contrast (+0.4875) has zero variance.
1.1  Write docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md BEFORE any campaign run (dated, hashed; do not rewrite Amendment 01 or the frozen prereg). Declare: (a) role placement permuted by a seed-derived RNG (deterministic per seed, replayable); (b) food not on every cell: seed-derived subset with coverage in [0.5, 0.8] and respawn_draws_per_tick reduced so respawn is stochastic; (c) primary outcome unchanged (receiver_mean_terminal_runtime_atp); (d) analysis seeds 11–40 unchanged, pilot 1000–1009 for calibration only; (e) same decision rule as Amendment 01 (Holm over 3 contrasts, non-superiority for shuffled, step_up_then_saturate dose pattern); (f) pass criterion for the calibration itself: sd>0 in every analysis arm on pilot seeds, manipulation check still 100 %.
1.2  Implement in src/codontrace/genesis/hard_experiment_01.py only (no new engine semantics): _calibrated_genomes / _calibration_food_cells take the seed; SCHEMA_VERSION="hard_experiment_01_v4"; committed_research_results_path() → results_v4.json; keep v3 path function. Any new RuntimeResourcePolicy/CapsuleTransferConfig field must follow the config template (default off, conditional to_dict).
1.3  Pilot on seeds 1000–1009 first (smoke scale allowed); only then the 30-seed research campaign; commit results_v4.json; add "Results (research v4)" to docs/HARD_EXPERIMENT_01.md and update CLAIMS.md §4.4. Adapter default → v4 with fallback v3→v2. Report the honest outcome: if Holm-corrected on-vs-off is null, say null; if positive, the label may rise at most to intervention_supported ONLY if every flag in CLAIMS.md §5 is satisfied by artifacts (intervention_result_artifact, digests, effect_size, paired_seed_protocol_digest, claim_gate_decision_digest). Never above that in this wave.
1.4  Tests: seed-permuted placement is deterministic per seed and differs across seeds; food coverage bounds; sd>0 at smoke scale over ≥3 seeds; manipulation check still passes; pins unchanged.

STEP 2 — E6 first (prerequisite of HE02): PR "feat(genesis): morris screening + ODD reporting"
2.1  src/codontrace/genesis/sensitivity.py: morris_screen(spec_factory, factors, *, trajectories, levels, seed) → elementary effects (mu*, sigma) per factor, deterministic, pure stdlib. Factors: initial_atp, basal_cost, food_amount, respawn_draws_per_tick, min_source_fitness, death_patience, mutation_rate. Output artifact docs/hard_experiment_02/sensitivity_v1.json with digest.
2.2  docs/ODD_REPORTING.md following Grimm et al. 2020 (ODD: Overview, Design concepts, Details) for life_loop_world + HE01 overlays. Link from docs/PHASE_INDEX.md.
2.3  Tests: morris_screen deterministic for fixed seed; factor ordering stable; artifact digest stable.

STEP 3 — HARD_EXPERIMENT_02 (Addendum 2: E1 + E2 + E5), prereg FIRST
3.1  docs/HARD_EXPERIMENT_02_PREREG.md (dated, hashed) with DAG, arms, seeds, decision rule, and the E2 2×2 pattern prediction, before code.
3.2  E1: FoodPatchSignalConfig(enabled=False, patch_count, patch_radius, signal_decay); new codon behaviour MOVE_TOWARD_CAPSULE_TARGET only when enabled; payload_informativeness = mutual information between capsule payload and food location (stdlib math). DAG edge: capsule_payload → movement → ATP.
3.3  E2: DemeSelectionConfig(enabled=False, deme_size, migration_rate, deme_selection_weight); 2×2 arms {kin on/off} × {deme selection on/off}; preregistered ordinal pattern.
3.4  E5: SteppingStoneRewardConfig(enabled=False, tiers) — knob inside HE02, ablation arm.
3.5  Smoke in CI, research (30 seeds) outside CI, committed results_v1.json, ClaimGate adapter entry, CLAIMS.md §4.5 at the granted ceiling only.

STEP 4 — HARD_EXPERIMENT_03 (E3): TaskSwitchCostConfig(enabled=False, switch_cost), gorelick_nmi division-of-labour metric, IsolationAssay (organism re-run alone vs in group). Prereg first. Same PR discipline.

STEP 5 — conditional E4 ScaffoldConfig (only if HE02 shows a Holm-surviving signal), E7 RecordPolicy/perf (no semantic change; pins byte-identical), then Wave 3 docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md (PR "docs(protocol): claim ladder protocol v0.1").

Reporting per wave (Persian, ≤10 lines): PR link, assay valid?, decision rule passed?, ClaimGate label, pins status, identity, anything deferred.
```

## بخش ۴ — فایل‌های این handoff

- `handoff/0001-wave-1c-e2-coupling.patch` — commit کامل موج ۱c (base `49b9f2c`)، قابل اعمال با `git am --3way`. sha256 (۱۶ رقم اول): `af6db978e31ec381`.
- `AGENT_PROMPT_WAVES_0_3.md` — قوانین + Addendum 1 (موج ۱c) + Addendum 2 (E1–E7 با مرجع).

## بخش ۵ — مراجع کلیدی که نباید گم شوند

Okasha & Otsuka 2020 (DAG انتخاب چندسطحی)؛ Goldsby et al. 2012 (task-switching → DoL)؛ Grimm et al. 2005/2020 (pattern-oriented modelling, ODD)؛ Nosek et al. 2018 (prereg)؛ Lakens 2017 (equivalence/non-superiority)؛ Morris 1991 / Campolongo 2007 (screening)؛ Gorelick et al. 2004 (NMI برای DoL).
