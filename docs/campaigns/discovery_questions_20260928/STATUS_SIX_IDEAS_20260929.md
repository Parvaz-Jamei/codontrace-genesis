# CodonTrace Genesis — وضعیت شش ایده کشف (به‌روز زنده)

**تاریخ ساخت:** 2026-09-29 ~01:10 Asia/Tehran  
**آخرین به‌روزرسانی:** 2026-09-29 ~01:15 Asia/Tehran  
**Repo:** `Parvaz-Jamei/codontrace-genesis`  
**Tip فعلی (origin/main):** `b81a47b`  
**منبع دستورات مالک:** `DISCOVERY_QUESTIONS_evolution_causal_collective_20260928.md` (+ چرخهٔ مشترک ۵+۲+۲)

این فایل **گزارش وضعیت عملیاتی** است، نه ادعای کشف. هر گام تمام‌شده اینجا به‌روز می‌شود. سقف ادعا تا اطلاع ثانوی: `phase2_design`. تست سبز ≠ تأیید علمی شش پرسش.

---

## قضاوت مالک (2026-09-29) — الزام فوری

بررسی تا tip حدود `022e8f5` (۵۹ تست مرتبط پاس): پیشرفت خوب در طراحی و اتصال کد، ولی **پاس‌شدن تست‌ها پاسخ شش پرسش علمی را تأیید نمی‌کند**.

| ایده‌ها | وضعیت نسبت به چهار فاز فایل |
|---|---|
| ۱، ۳، ۵، ۶ | مرزبندی و طرح فاز ۲ ثبت شده؛ harness و smoke ساخته شده. **فازهای کشفِ نتیجه و انتقال‌پذیری هنوز انجام نشده‌اند.** |
| ۲، ۴ | طراحی + اجرای ۶۴ seed + نتیجهٔ منفی ثبت شده؛ ولی ایرادهای زیر مانع تفسیر به‌عنوان **آزمون نهایی فرضیه**‌اند. **فازهای ۳ و ۴ کامل نیستند.** |

تیم در نظم پژوهشی و صداقت گزارش نتیجهٔ منفی خوب عمل کرده. **اول موارد ۱ تا ۴ را حل کند؛ اجرای seed بیشتر پیش از آن، ایراد سنجه و اتصال علّی را برطرف نمی‌کند.**

---

## اولویت اصلاح (مالک → تیم)

### P1 — مداخله باید به خود موتور برگردد (بالاترین)
- در `engine_ledger_coupler.py`: موتور وضعیت را به دفتر می‌دهد، اما تغییر یال/دانش/نشانگر دفتر مسیر بقای جمعیت موتور را عوض نمی‌کند.
- در JSONL ایدهٔ ۴: digest موتور برای هر seed×زمان در هر پنج سلول یکسان دیده شد.
- **لازم:** تست جفتی که با ثابت‌بودن بقیه، تغییر مداخله مسیر واقعی جمعیت را عوض کند.
- اگر دفتر فقط اندازه‌گیری است، نام/ادعای «اثر بر فرگشت» برداشته شود.

### P2 — سنجهٔ بقای ایدهٔ ۲ از جمعیت واقعی
- در `discovery_q_20260928_idea2_engine.py`: `survival_to_T` ترکیبی از گام‌های انرژی مثبت + امتیاز انرژی سه بازوی observer است؛ این‌ها جمعیت میزبان با تولیدمثل/انقراض مستقل نیستند.
- «فشار انگل» از تابع روی شاخص اکولوژی است، نه جمعیت انگل هم‌فرگشت‌کننده.
- مسیر فعلی برای کالیبراسیون مفید است، **نه** آزمون «ژن در برابر الگو در برابر استدلال علّی زیر فشار انگل».

### P3 — کنترل ایدهٔ ۴ هم‌سنگ
- در `contact_atp_ledger.py`: حذف داربست `E0`/`E1` را قطع می‌کند؛ کنترل تصادفی فقط `E5` را (تأیید مالک با seed ۳۰۱).
- تعداد یال، درجه، وزن تماس و ATP ازدست‌رفته باید دو طرف هم‌سنگ باشند.
- fallback «نزدیک‌ترین درجه» نباید بی‌صدا به‌عنوان تطبیق دقیق گزارش شود.

### P4 — ایدهٔ ۴: بازیابی نوآوری یک تبار + تاریخ منشعب
- خروجی فعلی: `recover=0` در تمام ۹۶۰ رکورد؛ ۸۵۵ رکورد با جمعیت صفر.
- برچسب `rare` کلاس ژنوتیپی/نوآوریِ به‌وجودآمده نیست؛ نشانگر بازیابی و digest شکست از ابتدا در scaffold هستند.
- **لازم:** از checkpoint واقعی، شاخه‌های جفتی دارای تبار و نوآوری قابل مشاهده؛ ابتدا نشان دهد کنترل اصلاً فرصت بازیابی دارد. وگرنه منحنی صفر قانون پنجره را نمی‌آزماید.

### P5 — smoke چهار ایدهٔ تازه = نتیجهٔ علمی نیست
- میان‌بُر ایدهٔ ۵ اعداد `0.85`/`0.40` را به تابع می‌دهد؛ دقت جهان ندیده نیست.
- هزینهٔ ایدهٔ ۱ و خودداری ایدهٔ ۶ فعلاً عملیات دفترند، نه صفت ارث‌پذیر با پیامد تبارشناختی.
- قبل از عبور از فاز ۲: سنجه‌ها از رفتار و بقای عامل‌ها محاسبه شوند.

### P6 — قانون فرایندی فایل قابل ممیزی
- برای هر فاز: رد قابل بررسیِ جست‌وجوی تازه، پنج دور طوفان پیش‌ساخت، تقسیم کار و تصمیم، دو دور نقد پس‌ساخت، آزمون، دو دور تحلیل نتیجه.
- نوآوری بین‌رشته‌ای با نزدیک‌ترین کارهای قبلی + پیش‌بینی متمایز، نه فقط برچسب «ترکیبی».
- **مانع Red Queen هنوز باز:** مورد مصنوعی با پارامتر قفل ~`−0.148` به حد `0.20` نمی‌رسد؛ تعریف «ثابت‌ماندن مجموعهٔ ژنوتیپ» هنگام تعویض اندازهٔ کلاس‌ها باید روشن شود.

---

## کجا هستیم / کجا می‌رویم (پس از نقد)

| مسیر | وضعیت صادق | بعدی (پس از P1–P4) |
|------|------------|---------------------|
| ایدهٔ ۴ | طراحی+harness+JSONL+نتیجهٔ منفی؛ **آزمون فرضیه کامل نیست** (P1,P3,P4) | coupler علی + کنترل هم‌سنگ + checkpoint تبار |
| ایدهٔ ۲ | همان؛ سنجه بقا/انگل کافی نیست (P2) | بقا از جمعیت واقعی + انگل هم‌فرگشت |
| ایدهٔ ۱/۳/۵/۶ | فاز۲ digest+smoke؛ **کشف نتیجه/انتقال‌پذیری نشده** (P5) | سنجه از رفتار عامل؛ بعد JSONL علمی |
| فرایند | گزارش پیشینه/طرح خوب؛ ممیزی چرخه ناقص (P6) | trail قابل ممیزی هر فاز + RQ fix |

**مسیر فعال الان:** P1 مسیر بازخورد coupler land (اندازه‌گیری؛ hyp=false). P2–P6 متر ADOPT/freeze؛ کد بعدی pause تا دستور مالک. Track C seed خاموش.

---

## چرخهٔ فاز (برای هر ایده، بدون استثنا)

1. جست‌وجوی زندهٔ پیشینه  
2. پنج طوفان پیش از ساخت  
3. ساخت خروجی فاز  
4. دو طوفان پس از ساخت  
5. آزمون + دو طوفان نتیجه  
6. حداکثر ۲ بازتکرار؛ وگرنه unsolved/falsified  

Land هر فاز تمام‌شده همان روز به `main` (push سریع).

---

## خلاصهٔ شش ایده (دستور مالک)

1. آزمایش علّی هزینه‌دار — مرز گذار از واکنش به جست‌وجوی علت  
2. ارزش علیت زیر فشار انگل — جدا کردن الگو از فرضیهٔ علّی  
3. دانش علّی جمعی — قانون فراتر از عمر یک عضو  
4. پنجرهٔ برگشت‌پذیری تاریخ تکاملی  
5. قانون نمادین قابل انتقال بین جهان‌ها  
6. خودداری معرفتی به‌عنوان صفت سازگارشونده  

ایده‌ها = شرایط کشف، نه کشف وعده‌داده‌شده. gap جست‌وجو ≠ novelty. تست سبز ≠ تأیید علمی.

---

## وضعیت تفصیلی فازها (سقف صادق)

### ایدهٔ ۴ — reversibility window
- Phase1+2 digest / distinction `CKPT-RELOCATE-RECOVERY-TOKEN-V1` / harness / engine JSONL N≥64 / Critic / RESULT: **ثبت شده**
- **اما:** coupler یک‌طرفه؛ کنترل ناهم‌سنگ؛ recover=0 بدون فرصت بازیابی تبار → **فاز ۳/۴ علمی کامل نیست**

### ایدهٔ ۲ — causality under parasite pressure
- Sham `SHAM-CUE-PREDPHASE-V1`؛ JSONL چهار سلول؛ G2 FAIL صادق ثبت شده
- **اما:** survival/فشار انگل از جمعیت واقعی نیست → **آزمون نهایی فرضیه نیست**

### Track C — ۱ / ۳ / ۵ / ۶
- Phase1+2 digests؛ harness smoke؛ scored harness-class JSONL؛ Critic HOLD wiring
- **smoke ≠ نتیجه علمی** (P5)؛ موتور بسته‌حلقه تا رفع P1 و سنجه‌های رفتاری متوقف از ادعای کشف

---

## قفل‌های ایستاده (همیشه)

- Engine GENERAL؛ infection در `engine.py` ممنوع  
- No ClaimGate soft-pass؛ `red_queen_proved` / `hypothesis_supported` false تا earned  
- Sealed FAIL seeds `801–816` دست‌نخورده  
- GitHub prose: ordinary research English only  
- ESP32 Physical OFF  
- Role lock: ALife meters؛ EcoEvo ecology؛ ClaimCritic gate؛ XField Track C+ADOPT؛ Research land؛ genesis 28sep orchestrate+push  
- **جدید:** seed بیشتر قبل از P1–P4 ممنوع به‌عنوان «کشف»؛ smoke را RESULT ننویسید

---

## تقسیم کار فوری (پس از این نقد)

| اولویت | مالک اجرا | نقش پشتیبان |
|--------|-----------|-------------|
| P1 coupler علی + تست جفتی | Research (land) + ALife (متر جمعیت) | ClaimCritic gate |
| P2 بقا/انگل واقعی Idea2 | EcoEvo | Research land |
| P3 کنترل هم‌سنگ Idea4 | ALife + Research | ClaimCritic |
| P4 checkpoint تبار Idea4 | ALife | Research |
| P5 سنجه‌های رفتاری Track C | XField (طرح) → ALife/EcoEvo متر → Research | ClaimCritic |
| P6 trail ممیزی + RQ | ClaimCritic + Research | XField novelty prediction |

---

## تاریخچهٔ tipهای کلیدی

| Tip | محتوا |
|-----|--------|
| `51e832b` | RESULT addenda ۴/۲ (سقف طراحی؛ نه آزمون نهایی) |
| `022e8f5` | HOLD remediations identity/scaffold |
| `893f4f1` | Track C harness smoke |
| `9a6aff2` | Track C scored JSONL (harness-class only) |
| `d565e49` | Critic post-data Track C |
| `64ab1c5` | Live STATUS board |
| `bf060e5` | STATUS tip align |

---

## به‌روزرسانی‌ها (append-only)

- **2026-09-29 01:10 +0330:** فایل ساخته شد؛ tip=`d565e49`؛ Track C در مسیر موتور بسته‌حلقه.
- **2026-09-29 01:12 +0330:** board روی main (`64ab1c5`)؛ Drive handoff؛ fast-push فعال.
- **2026-09-29 01:13 +0330:** tip refresh؛ Drive STATUS آپلود.
- **2026-09-29 01:15 +0330:** نقد مالک ثبت شد (P1–P6)؛ ۲/۴ آزمون نهایی نیستند؛ Track C نتیجهٔ علمی نیست؛ اولویت اول P1–P4 قبل از seed بیشتر؛ ابلاغ به تیم.

---

- **2026-09-29 01:12 +0330:** ADOPT — ClaimCritic GATE؛ XFieldInnov P5/P6 (metric redesign storm)؛ EcoEvo P2 (ecology redesign R1). Land فقط بعد از Critic freeze.
- **2026-09-29 01:16 +0330:** tip=`c9b26b5`؛ ADOPT P2/P5/P6 روی STATUS+Drive ثبت شد.
- **2026-09-29 01:13 +0330:** Research P1 ADOPT (Track C engine WIP discarded). ALife meters locked: P1 paired `engine_pop_path_digest` must differ across arms; P3 `match_exact` required (E0+E1 ⇒ 2 edges); P4 `window_test_valid` false if control recover=0.
- **2026-09-29 01:16 +0330:** جمع‌بندی مالک (صرفه‌جویی): P1 coupler+matched-control WIP روی tree؛ discovery tests سبز؛ land به‌عنوان مسیر اندازه‌گیری؛ طوفان اضافه pause تا دستور بعدی؛ Track C seed خاموش.

---

### ALife meter lock (P1/P3/P4) — 2026-09-29

**P1 paired causal:** emit `pre_intervene_pop_digest`, `engine_pop_path_digest` (GB ecology series after t_intervene), `coupler_affects_engine`. PASS = same seed/ticks/init; only ops_cell differs; digests match pre-intervene AND post digests differ across arms. FAIL = identical engine digests across cells → `ledger_only_warn=true`; no evolutionary-effect claim.

**P3 matched control:** emit edge ids, `n_edges_cut_*` (equal; scaffold E0+E1 ⇒ matched cuts 2), degree/weight/ATP sums, `match_exact:bool`. Silent nearest-degree fallback = FAIL. `match_exact=false` excludes arm from Combo E.

**P4 recovery opportunity:** require `control_recover_rate`, `window_test_valid`, `lineage_branching_real`, `innovation_observable`. recover=0 including control ⇒ `window_test_valid=false` (diagnostic only). Pre-placed rare/scaffold markers ≠ genotype innovation.

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
OWNER_CRITIQUE=2026-09-29-P1-P6
MORE_SEEDS_BEFORE_P1_P4=forbidden
SMOKE_IS_NOT_SCIENCE=true

IDEA4_TOKEN=CKPT-RELOCATE-RECOVERY-TOKEN-V1
IDEA4_OPS=control,scramble_contacts,cut_named_scaffold,cut_matched_random,ablate_knowledge_digest
IDEA4_BLOCKERS=coupler_one_way,unmatched_control_E5_vs_E0E1,recover0_no_lineage_opportunity
IDEA2_SHAM=SHAM-CUE-PREDPHASE-V1
IDEA2_CELLS=baseline,pi_deception,do_ablation,sham_predphase
IDEA2_BLOCKERS=survival_not_from_host_pop,parasite_pressure_not_coevo

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
ALIFE_P1_METER=engine_pop_path_digest,coupler_affects_engine
ALIFE_P3_METER=match_exact,n_edges_cut
ALIFE_P4_METER=window_test_valid,control_recover_rate
COUPLER_FEEDBACK_PATH=landed_measurement_only
PAUSED_STORMS_FOR_COST=true
PRIORITY_ORDER=P1_coupler,P2_idea2_survival,P3_matched_control,P4_lineage_ckpt,P5_behavioral_metrics,P6_process_audit_RQ
TIP_MAIN=b81a47b
```
