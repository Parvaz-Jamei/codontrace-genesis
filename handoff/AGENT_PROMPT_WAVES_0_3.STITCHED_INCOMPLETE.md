# AGENT_PROMPT_WAVES_0_3 — STITCHED INCOMPLETE (2026-09-13)

> **WARNING:** Full `02_AGENT_PROMPT_WAVES_0_3.md` was listed in Drive MANIFEST but **not found** as a file.
> This file concatenates recovered shards only (`02a` + `02bc` + `02d`). Do **not** treat as the locked manager prompt.
> Prefer uploading the real file to Drive/repo when available.
> Standing rules also restated in `04_AGENT_HANDOFF_NEXT_WAVES.md` §2 and in agent memory (knob template, ClaimGate, Persian reports).

---

# 02a — موج 0 (از AGENT_PROMPT_WAVES_0_3.md)

ریپو CodonTrace Genesis. محصول همیشه همین نام. ClaimGate شل نشود. pin A–E: spec 7d199ae5…7aac snapshot 76a5e62c…f43a. هویت 0.3.0b4.dev0. بدون tag/PyPI. یک PR per موج.

موج 0: حذف engine_FULL_RESTORE؛ هویت در CLAIMS؛ CLAIM_LADDER superseded؛ CLAIM_LADDER_MAP؛ lint-type job؛ paired_effect_size dz؛ outcome missing=None نه 0؛ شمارنده‌های کپسول جدا؛ replay همه بازوها seeds[0] و [-1]؛ n=12 exploratory نه research؛ BCa + sign-flip + Holm dependency-free.

Done: فایل مرده حذف، آمار درست، pin دست‌نخورده.


---

# 02b — موج 1 HARD_EXPERIMENT_01

Prereg قبل از عدد. 4 بازو: source_bias_on / off / capsules_off / capsules_shuffled. Dose min_source_fitness. DAG: gate → adopt → action → ATP → fitness. آمار: dz + BCa 95% + sign-flip + Holm روی 3 contrast. Research 30 seed / 40 tick / pop 16 خارج CI. سقف intervention_supported فقط اگر CI on-vs-off و on-vs-shuffled صفر را نگیرد و shuffled≈off و dose هم‌جهت. وگرنه runtime_observation. هیچ collective_intelligence.

# 02c — موج 2 و 3
موج 2: src/codontrace/claimgate صفر import از genesis.engine. نردبان عمومی CLAIMS.md §5. bundle JSON. audit_bundle. آداپتر codontrace کامل، avida/mabe2 اسکلت. CLI python -m codontrace.claimgate audit.
موج 3: docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md بعد از Done موج 2 و بعد از 1c معتبر.


---

# 02d — ADDENDA (موج 1c + ارتقای موتور E1–E7)
منبع کامل: AGENT_PROMPT_WAVES_0_3.md در workspace همین پروژه (commit b5945f5).

## ADDENDUM 1 — موج 1c اعتبار assay
نتایج v2 در هر 4 بازو bitwise-identical است (mean 0.164375). این null قابل تفسیر نیست.
Manipulation check اجباری. accept_provisional_source_fitness در treatment باید False. اگر capsule به action وصل نیست یال e2 غایب است. births>0 شرط اعتبار نسل بعد. Amendment رسمی با digest جدا. pilot 1000–1009 جدا از analysis 11–40. oracle_capsule کنترل مثبت. بدون manipulation check سقف = runtime_observation / assay_invalid. موج 3 فقط بعد از 1c معتبر.

## ADDENDUM 2 — قالب کد اجباری
XConfig frozen slots enabled=False، ConfigurationError، to_dict شرطی، digest canonical، تست pin خاموش + تست enabled تغییر runtime.

E1 FoodPatchSignalConfig + MOVE_TOWARD_CAPSULE_TARGET + MI payload. Floreano 2007, Knoester 2008.
E2 DemeSelectionConfig 2x2 GERMLINE/INDIVIDUAL x CLONAL/MIXED. Grimm POM.
E3 TaskSwitchCostConfig + gorelick_nmi + IsolationAssay. Goldsby 2012, Gorelick 2004.
E4 ScaffoldConfig فقط اگر HE02 سیگنال Holm داشت. Black 2020.
E5 SteppingStoneRewardConfig. Lenski/Ofria 2003.
E6 morris_screen پیش‌نیاز HE02. Grimm ODD 2020.
E7 RecordPolicy بدون تغییر معنا.
ترتیب: E6 → HE02 (E1+E2+E5) → HE03 (E3) → E4 شرطی. بدون Phase M+.

جزئیات اجرایی Step 0–5 در 04_AGENT_HANDOFF_NEXT_WAVES.md و 01_CHAT_KNOWLEDGE.md.
