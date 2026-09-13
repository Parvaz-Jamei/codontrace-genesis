# CodonTrace Genesis — Handoff به ایجنت بعدی (بعد از موج ۱c)

تاریخ: 2026-09-12. مخزن هدف: `Parvaz-Jamei/codontrace-genesis` (شاخهٔ `main` در `49b9f2c`).
این فایل را **همراه با** `AGENT_PROMPT_WAVES_0_3.md` (قوانین ثابت، Addendum 1 و Addendum 2) و پوشهٔ `handoff/` به ایجنت جدید بده.

> Canonical Drive copy: https://drive.google.com/file/d/1qX_jl8cJgKgqs5foAY29vnyzDKtTdr9Q/view
> Archived into repo on 2026-09-13. Wave 1c–1e + E6 + ILW-0…6 already on `wave-1d-seed-variance` (do not re-apply Wave 1c patch).

---

## بخش ۱ — وضعیت فعلی (فارسی، کوتاه)

### چه چیزی merge شده (روی `main`)
| PR | موج | نتیجه |
|---|---|---|
| #20–#22 | موج ۰ | اصلاح ایرادات audit |
| #23 (`460791c`) | موج ۱ | HE01 prereg + طرح چهاربازو + research v1 (null، dz=0) |
| #24 (`e58d983`) | موج ۱b | کالیبراسیون بقا + research v2 (adoptions 169، اما همهٔ بازوها bitwise-identical) |
| — (`49b9f2c`) | موج ۲ | ClaimGate auditor مستقل؛ v2 را `assay_invalid` برچسب می‌زند |

### دو کار موازی برای موج ۱c (فقط یکی باید merge شود)
1. **PR #25** (`cursor/fix-he01-assay-validity-f6b1`, draft) — manipulation check شکست (22/30)، `assay_failed = true`.
2. **Patch:** `handoff/0001-wave-1c-e2-coupling.patch` (base `49b9f2c`) — assay معتبر، اما sd=0 → `dz_undefined`. سقف `runtime_observation`.

> **Status 2026-09-13:** Wave 1c patch already applied on branch (`0077b46`). Continue from Wave 1e / ILW / HE02 — do not re-apply.

### قوانین ثابت (§2)
- حداقل tool call؛ گزارش کوتاه فارسی؛ بدون tag/PyPI مگر دستور صریح.
- ClaimGate هرگز شل نمی‌شود. نام محصول **CodonTrace Genesis**.
- ادعاهای ممنوع: intelligence / collective_intelligence / AGI / «Tokyo Type 1 passed» / «جایگزین Avida».
- pinهای Phase A–E نباید بشکنند (life_loop_world seed=7… digests unchanged).
- هویت `0.3.0b4.dev0`.
- هر موج یک PR، squash-merge.
- هر knob: frozen dataclass slots=True, enabled=False, ConfigurationError in __post_init__, to_dict non-defaults only, canonical_digest, one DAG edge, pin+runtime tests.

---

## بخش ۳ — PROMPT (اصلی؛ از Drive handoff)

```
You are continuing CodonTrace Genesis (repo Parvaz-Jamei/codontrace-genesis, main at 49b9f2c).
Read AGENT_PROMPT_WAVES_0_3.md (rules, Addendum 1, Addendum 2) and AGENT_HANDOFF_NEXT_WAVES.md first. Apply every standing rule in §2 of the handoff verbatim. Minimal tool calls; no play-by-play; short Persian report at the end of each wave.

STEP 0 — Land Wave 1c (exactly one merges) — DONE on wave-1d-seed-variance / PR #27 path.
STEP 1 — Wave 1d seed variance — DONE (through 1e / SCHEMA v6).
STEP 2 — E6 morris + ODD — DONE.
STEP 3 — HARD_EXPERIMENT_02 (Addendum 2: E1 + E2 + E5), prereg FIRST
3.1 docs/HARD_EXPERIMENT_02_PREREG.md (dated, hashed) with DAG, arms, seeds, decision rule, and the E2 2×2 pattern prediction, before code.
3.2 E1: FoodPatchSignalConfig(enabled=False, patch_count, patch_radius, signal_decay); MOVE_TOWARD_CAPSULE_TARGET only when enabled; payload_informativeness = MI(capsule payload, food location). DAG: capsule_payload → movement → ATP.
3.3 E2: DemeSelectionConfig(enabled=False, deme_size, migration_rate, deme_selection_weight); 2×2 {kin on/off} × {deme selection on/off}.
3.4 E5: SteppingStoneRewardConfig(enabled=False, tiers) — knob inside HE02, ablation arm.
3.5 Smoke in CI, research (30 seeds) outside CI, results_v1.json, ClaimGate adapter, CLAIMS.md §4.5 at granted ceiling only.
STEP 4 — HARD_EXPERIMENT_03 (E3): TaskSwitchCostConfig, gorelick_nmi, IsolationAssay. Prereg first.
STEP 5 — conditional E4 ScaffoldConfig (only if HE02 Holm signal), E7 RecordPolicy/perf, then Wave 3 CLAIM_LADDER_PROTOCOL_v0.1.md.

Reporting per wave (Persian, ≤10 lines): PR link, assay valid?, decision rule passed?, ClaimGate label, pins status, identity, anything deferred.
```

## بخش ۴ — فایل‌های این handoff
- `handoff/0001-wave-1c-e2-coupling.patch` — sha256 starts `af6db978e31ec381` (already applied).
- `AGENT_PROMPT_WAVES_0_3.md` — **MISSING on Drive**; see `AGENT_PROMPT_WAVES_0_3.STITCHED_INCOMPLETE.md` + `MISSING_AGENT_PROMPT_WAVES_0_3.md`.

## بخش ۵ — مراجع
Okasha & Otsuka 2020; Goldsby et al. 2012; Grimm et al. 2005/2020; Nosek et al. 2018; Lakens 2017; Morris 1991 / Campolongo 2007; Gorelick et al. 2004.
