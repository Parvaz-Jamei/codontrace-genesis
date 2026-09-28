# CodonTrace Genesis — وضعیت شش ایده کشف (به‌روز زنده)

**تاریخ ساخت:** 2026-09-29 ~01:10 Asia/Tehran  
**Repo:** `Parvaz-Jamei/codontrace-genesis`  
**Tip فعلی (origin/main):** `3806a15`  
**منبع دستورات مالک:** `DISCOVERY_QUESTIONS_evolution_causal_collective_20260928.md` (+ چرخهٔ مشترک ۵+۲+۲)

این فایل **گزارش وضعیت عملیاتی** است، نه ادعای کشف. هر گام تمام‌شده اینجا به‌روز می‌شود. سقف ادعا تا اطلاع ثانوی: `phase2_design`.

---

## کجا هستیم / کجا می‌رویم

| مسیر | وضعیت | بعدی |
|------|--------|------|
| ایدهٔ ۴ | فاز۱+۲ طراحی+harness+JSONL موتور N≥۶۴+گیت+RESULT | بسته تحت `phase2_design` (پنجره FAIL صادق) |
| ایدهٔ ۲ | فاز۱+۲ طراحی+harness+JSONL موتور N≥۶۴+گیت+RESULT | بسته تحت `phase2_design` (G2 FAIL صادق) |
| ایدهٔ ۱ | فاز۱+۲ digest+harness+JSONL scored | موتور بسته‌حلقه در حال ساخت؛ بعد گیت+RESULT |
| ایدهٔ ۳ | همان Track C | همان |
| ایدهٔ ۵ | همان Track C | همان |
| ایدهٔ ۶ | همان Track C | همان |

**مسیر فعال الان:** Research → JSONL موتور بسته‌حلقه Track C (۱/۳/۵/۶) با `GenerationBoundaryObserver`؛ `9a6aff2` فقط harness-class می‌ماند.

---

## چرخهٔ فاز (برای هر ایده، بدون استثنا)

1. جست‌وجوی زندهٔ پیشینه  
2. پنج طوفان پیش از ساخت  
3. ساخت خروجی فاز  
4. دو طوفان پس از ساخت  
5. آزمون + دو طوفان نتیجه  
6. حداکثر ۲ بازتکرار؛ وگرنه unsolved/falsified  

Land هر فاز تمام‌شده همان روز به `main` (push سریع از ۱:۱).

---

## خلاصهٔ شش ایده (دستور مالک)

1. **آزمایش علّی هزینه‌دار** — مرز گذار از واکنش به جست‌وجوی علت  
2. **ارزش علیت زیر فشار انگل** — جدا کردن الگو از فرضیهٔ علّی  
3. **دانش علّی جمعی** — قانون فراتر از عمر یک عضو  
4. **پنجرهٔ برگشت‌پذیری** تاریخ تکاملی  
5. **قانون نمادین قابل انتقال** بین جهان‌ها  
6. **خودداری معرفتی** به‌عنوان صفت سازگارشونده  

ایده‌ها = شرایط کشف، نه کشف وعده‌داده‌شده. gap جست‌وجو ≠ novelty.

---

## وضعیت تفصیلی فازها

### ایدهٔ ۴ — reversibility window
- Phase1 boundary: on main  
- Phase2 digest: on main (`1f77d5c` مسیر)  
- Distinction lock: `CKPT-RELOCATE-RECOVERY-TOKEN-V1`  
- Harness + scored harness JSONL: `ecf7148` (harness-only)  
- Engine closed-loop N≥64: `24fc048` → Critic `5610878` → RESULT addenda `51e832b`  
- **Outcome:** wiring PASS؛ P(recover)=0؛ hypothesis_supported=false  

### ایدهٔ ۲ — causality under parasite pressure
- Phase1+2 digest on main  
- Sham: `SHAM-CUE-PREDPHASE-V1` ≠ NC-*  
- Engine N≥64 با ۴ سلول: همان مسیر ۴  
- **Outcome:** wiring PASS؛ G2 FAIL؛ pattern×pi collapse صادق؛ hyp=false  

### Track C — ایده‌های ۱ / ۳ / ۵ / ۶
- Phase1 boundaries + Phase2 digests: `5c101f5` / `100f794`  
- Post-build freeze Critic: sealed  
- Harness smoke: `893f4f1` → HOLD fixes `022e8f5`  
- Scored JSONL harness-class: `9a6aff2` (۱۰۲۴ خط؛ wall≈۰٫۲s)  
- Critic post-data: `d565e49` — wiring PASS؛ اندازه FAIL؛ **HOLD تا موتور بسته‌حلقه**  
- **در پرواز:** engine closed-loop JSONL  

---

## قفل‌های ایستاده (همیشه)

- Engine GENERAL؛ infection در `engine.py` ممنوع  
- No ClaimGate soft-pass؛ `red_queen_proved` / `hypothesis_supported` false تا earned  
- Sealed FAIL seeds `801–816` دست‌نخورده  
- GitHub prose: ordinary research English only (بدون AI/agent/Grok/Cursor/LLM)  
- ESP32 Physical OFF  
- Role lock: ALife meters؛ EcoEvo ecology؛ ClaimCritic gate؛ XField Track C+ADOPT؛ Research land؛ genesis 28sep orchestrate+push  

---

## تاریخچهٔ tipهای کلیدی

| Tip | محتوا |
|-----|--------|
| `51e832b` | RESULT addenda ۴/۲ |
| `893f4f1` | Track C harness smoke |
| `022e8f5` | HOLD remediations identity/scaffold |
| `9a6aff2` | Track C scored JSONL (harness-class) |
| `d565e49` | Critic post-data Track C |
| `64ab1c5` | Live STATUS_SIX_IDEAS board |
| `3806a15` | STATUS tip refresh + Drive sync note |

---

## به‌روزرسانی‌ها (append-only)

- **2026-09-29 01:10 +0330:** فایل ساخته شد؛ tip=`d565e49`؛ Track C در مسیر موتور بسته‌حلقه.
- **2026-09-29 01:12 +0330:** board روی main رفت (`64ab1c5`)؛ آپلود Drive handoff؛ DISCOVERY_QUESTIONS از قبل روی Drive بود؛ fast-push standing order فعال.
- **2026-09-29 01:13 +0330:** tip refresh روی main (`3806a15`)؛ Drive STATUS آپلود شد.

---

## Tokens / identity locks (انتهای سند)

```
CLAIM_CEILING=phase2_design
HYPOTHESIS_SUPPORTED=false
RED_QUEEN_PROVED=false
SOFT_PASS=forbidden
N_UNIT=run
ENGINE=GENERAL
SEALED_SEEDS=801-816
ESP32_PHYSICAL=OFF

IDEA4_TOKEN=CKPT-RELOCATE-RECOVERY-TOKEN-V1
IDEA4_OPS=control,scramble_contacts,cut_named_scaffold,cut_matched_random,ablate_knowledge_digest
IDEA2_SHAM=SHAM-CUE-PREDPHASE-V1
IDEA2_CELLS=baseline,pi_deception,do_ablation,sham_predphase

IDEA1_RIVAL=RP-LEDGER-ATP-DRAIN-V1
IDEA3_LAW=LAW-LEDGER-CONTACT-ATP-PARENT-V1
IDEA3_UNREACH=UNREACH-L-SINGLE-LIFETIME-V1
IDEA3_REV=REV-HIGH-NOISE-BLIND-ACCEPT-V1
IDEA5_WORLD=WORLD-FAMILY-CONTACT-ATP-V1
IDEA5_LAW_SHORT=LAW-SHORT-COMPOSABLE-V1
IDEA5_PROBE=PROBE-PRIVATE-VS-SKELETON-V1
IDEA5_THETA=0.80
IDEA6_USTAR=USTAR-RESTRAINT-V1
IDEA6_U_MEASURE=U-LEDGER-EVIDENCE-STRENGTH-V1

BUILDERS_ENGINE=build_engine_scaffold_ledger,build_idea2_engine_scaffold_ledger
BUILDERS_TRACK_C=build_idea{1,3,5,6}_scaffold_ledger
HARNESS_ONLY_TIPS=ecf7148,9a6aff2
ENGINE_JSONL_TIP_42=24fc048
CRITIC_GATE_42=5610878
CRITIC_GATE_TRACK_C_SCORED=d565e49
TIP_MAIN=3806a15
```
