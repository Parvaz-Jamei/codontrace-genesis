# CodonTrace Genesis — دستور اجرایی ایجنت (موج ۰ اصلاحات → موج ۱ روش دقیق → موج ۲ و ۳)

تاریخ: 2026-09-11 · ریپو: https://github.com/Parvaz-Jamei/codontrace-genesis · main: `9583e08` (PR #19 merged) · هویت main: `0.3.0b4.dev0` · PyPI: `0.3.0b3`

این فایل یک prompt خودکفا برای ایجنت است. کل متن زیر خط را به ایجنت بده.

---

## PROMPT — از این‌جا به ایجنت بده

تو روی ریپوی CodonTrace Genesis (پکیج `codontrace`) کار می‌کنی. نام محصول همیشه «CodonTrace Genesis». کار را با Cloud Agent روی GitHub انجام بده؛ کلون محلی فقط برای تست ضروری. قوانین ثابت: کمترین tool call، بدون Drive، بدون tag/PyPI publish، بدون Phase M+، ClaimGate هرگز شل نمی‌شود، pinهای Phase A–E نمی‌شکنند (`life_loop_world(seed=7, tick_count=12, population=6)` spec `7d199ae5…7aac` / snapshot `76a5e62c…f43a`)، ادعای intelligence / collective_intelligence / AGI / Tokyo Type 1 passed / Avida replacement ممنوع. هر موج = یک PR جدا، squash-merge، گزارش کوتاه فارسی. قبل از هر موج علمی حداکثر ۲ سرچ هدفمند (نه ده سرچ).

ترتیب قفل است: موج ۰ → موج ۱ → موج ۲ → موج ۳. موج بعدی را شروع نکن تا Done موج قبلی تیک نخورده.

### موج ۰ — اصلاح ایرادات پیدا‌شده (PR: `fix(genesis): audit fixes after #19`)

ایرادات زیر با خواندن main @ `9583e08` تأیید شده‌اند؛ هر کدام را با یک commit جدا ببند:

#### A. بهداشت پکیج

- `src/codontrace/genesis/engine_FULL_RESTORE_0.3.0b2.py` (۱۶۲KB) یک بکاپ مرده است که داخل wheel می‌رود. حذف کن. قبلش با grep مطمئن شو هیچ import/tests به آن ارجاع ندارد. در CI (`ci.yml` step «Reject probe leftovers») الگوی `*_FULL_RESTORE*`, `*_backup*`, `*.orig` را هم رد کن.
- `CLAIMS.md` هدر می‌گوید `Version target: 0.3.0b3` / `Package: codontrace==0.3.0b3`. یک خط اضافه کن: «Development identity on main: `0.3.0b4.dev0` (unreleased; contains Phases H–L + HARD_EXPERIMENT_01). Published PyPI tip: `0.3.0b3` (Phases A–G).» نسخهٔ PyPI را دست نزن.
- `docs/CLAIM_LADDER.md` می‌گوید «…multi-agent intelligence library» و «Phase 2 candidate». این با انضباط ClaimGate ناسازگار است. عبارت intelligence را حذف کن و سند را «superseded — see CLAIMS.md §5» علامت بزن.
- سه نردبان ناسازگار وجود دارد: `CLAIMS.md` §5 (سطح ۰–۵)، `claim_gate.py::_CLAIM_LADDER_LEVELS` (۹ سطح: `metadata_only` … `claim_ready_research_alpha`)، و `docs/SCIENTIFIC_CLAIM_LADDER.md` + `docs/PHASE2_SCIENTIFIC_EVIDENCE_LADDER.md`. در موج ۰ فقط یک جدول نگاشت بنویس: `docs/CLAIM_LADDER_MAP.md` (۹ سطح داخلی → ۰–۵ عمومی). کد را در موج ۲ یکی می‌کنیم.
- CI: job جدید `lint-type` روی Ubuntu/3.12 با `ruff check src tests` و `mypy --strict src`؛ اول `continue-on-error: true`. اگر سبز شد در همان PR blocking کن؛ اگر قرمز شد، خطاها را در `BACKLOG.md` لیست کن و blocking نکن.

#### B. باگ‌های آماری در HARD_EXPERIMENT_01 (باید قبل از هر عدد گزارش‌شده درست شوند)

- `statistical_protocol.py::_pooled_std` انحراف معیارِ الحاقِ دو گروه را می‌گیرد (واریانس بین‌گروهی را هم شامل می‌شود). این Cohen's d نیست و برای طرح paired غلط است. اصلاح: (a) تابع جدید `paired_effect_size(deltas)` → \(d_z = \bar{\Delta} / s_{\Delta}\) با ddof=1؛ (b) `_pooled_std` را به pooled SD واقعی \(\sqrt{((n_1-1)s_1^2+(n_2-1)s_2^2)/(n_1+n_2-2)}\) تبدیل کن. تست‌هایی که به عدد قبلی وابسته‌اند را صادقانه به‌روز کن (این digestهای موتور A–E نیست).
- `hard_experiment_01.py::_mean_last_tick_fitness` روی نبودِ tick/generation بی‌صدا `0.0` برمی‌گرداند → سوگیری به صفر. باید `None` برگرداند، جفت (seed) از تحلیل paired حذف شود، و در `HardExperiment01ArmRecord` فیلد `outcome_missing: bool` و در campaign `missing_outcomes_per_arm` ثبت شود.
- `_capsule_counts` «emissions» را `max(sources, utilities, transfers)` می‌گیرد — پروکسی مبهم. سه شمارنده را جدا ثبت کن.
- replay فقط seed 11 × treatment را چک می‌کند. باید هر ۳ (بعداً ۴) arm برای `seeds[0]` و `seeds[-1]` replay شود و همه match کنند.
- n=12 در doc «research default» نامیده شده، ولی طبق `StatisticalTestPolicy.tier_for_n(12)` خودِ ریپو = `exploratory_only`. برچسب را درست کن: 12 = smoke/exploratory؛ research = 30 (`min_research_grade_n`).
- `docs/HARD_EXPERIMENT_01.md` هیچ عددی ندارد. تا نتایج موج ۱ نیامده، بخش «Results: not yet recorded» صریح اضافه کن.
- `StatisticalTestPolicy` مدعی `ci_method="bca_bootstrap"` و `test_name="paired_permutation"` است و `PairedComparisonResult` CI می‌خواهد، ولی هیچ پیاده‌سازی‌ای وجود ندارد و HARD_EXPERIMENT_01 از `estimate_effect_size_lite` استفاده می‌کند. در موج ۰ فقط پیاده‌سازی dependency-free را اضافه کن (استفاده در موج ۱): `exact_sign_flip_permutation_p(deltas)` (برای n ≤ 20 شمارش کامل \(2^n\)؛ بزرگ‌تر Monte-Carlo با ۲۰۰۰۰ نمونه و seed ثابت) و `bootstrap_ci_paired(deltas, method="bca"|"percentile", resamples=10000, seed=…)` و `holm_correction(p_values)`. تست unit با مقادیر معلوم.

**Done موج ۰:** فایل مرده حذف؛ CI سبز؛ ruff/mypy job اضافه؛ نگاشت نردبان نوشته؛ توابع آماری درست + تست؛ pinهای A–E دست‌نخورده؛ نسخه همان `0.3.0b4.dev0`.

### موج ۱ — روشِ دقیق HARD_EXPERIMENT_01 (PR: `feat(genesis): HARD_EXPERIMENT_01 preregistered causal design + results`)

این همان «روشی که باید دقیق باشد» است. مبنا: Okasha & Otsuka 2020 (Price/Cov بدون مدل علّی صریح، علّیت نیست → DAG بنویس و بگو هر arm کدام یال را قطع می‌کند)، Goldsby et al. PNAS 2012 (طرح گرادیانِ هزینه 0/25/50 + تست isolation؛ یعنی dose-response و کنترل منفی، نه فقط on/off)، Pineau et al. JMLR 2021 (checklist: seeds، error bars، compute، config کامل). دو سرچ کوتاه برای تأیید همین سه مرجع کافی است.

1. **پیش‌ثبت (pre-registration) قبل از اجرا.** فایل `docs/HARD_EXPERIMENT_01_PREREG.md` را در یک commit جدا و قبل از هر عدد commit کن؛ digest آن را در payload کمپین با کلید `prereg_digest` ثبت کن. محتوا: سؤال؛ H1 جهت‌دار (`source_bias_on` > `source_bias_off` در terminal mean fitness)؛ H0؛ outcome اولیه (terminal mean fitness)؛ outcomeهای ثانویه (births، extinction/missing rate، adoption count)؛ armها؛ لیست seed؛ n؛ ticks/pop؛ طرح تحلیل؛ قاعدهٔ تصمیم؛ سقف ادعا برای هر الگوی نتیجه.

2. **طرح آزمایش (۴ بازو + dose-response).**

| Arm | نقش | مداخله (do-operator) |
|---|---|---|
| `source_bias_on` | treatment | `min_source_fitness=2.0`, FITNESS_WEIGHTED |
| `source_bias_off` | mechanism ablation | `min_source_fitness=0.0`, THRESHOLD |
| `capsules_off` | channel off | `CapsuleTransferConfig.enabled=False` |
| `capsules_shuffled` (جدید) | negative control | کانال روشن، محتوا بهم‌ریخته با CapsuleShuffleMode غیر از OFF (همان چیزی که `swarm_coordination_candidate` تحت `shuffled_agent_control` می‌خواهد) |

چرا shuffled لازم است: فقط این کنترل «اثرِ محتوای اطلاعات» را از «اثرِ صرفِ وجود کانال/ترافیک/هزینه» جدا می‌کند. بدون آن، on vs capsules_off دو چیز را هم‌زمان تغییر می‌دهد.

Dose-response: `min_source_fitness ∈ {0.0, 1.0, 2.0, 4.0}` با FITNESS_WEIGHTED (بازوی 0.0 و 2.0 با جدول بالا مشترک‌اند). آزمون روند یکنوا: Spearman روی میانگین هر seed یا permutation trend با seed ثابت.

DAG صریح در doc: `min_source_fitness` gate → کدام کپسول adopt می‌شود → انتخاب action → ATP → terminal fitness. برای هر arm بنویس کدام یال قطع/دست‌کاری می‌شود. هیچ عبارت Price/Cov بدون ارجاع به این DAG.

3. **مقیاس.** دو پروفایل: smoke = همان الان (12 seed، 6 tick، pop 4؛ در CI می‌ماند) و research = 30 seed (`min_research_grade_n`)، 40 tick، pop 16 (همان baseline که CLAIMS.md §9 توصیه کرده). اول زمان یک arm × یک seed را بگیر؛ اگر کل کمپین research (30 × 6 arm) روی CI بیش از ~۲۰ دقیقه است، در CI اجرا نکن؛ با اسکریپت example خارج CI اجرا کن و خروجی را با digest در `docs/hard_experiment_01/results_v1.json` commit کن؛ CI فقط digest فایل را با محاسبهٔ مجدد روی smoke چک کند.

4. **آمار (دقیقاً این‌ها).** برای هر مقایسهٔ paired: \(d_z\) + BCa bootstrap 95% CI (10000) + p از exact sign-flip permutation؛ Holm روی سه مقایسهٔ اولیه (on vs off، on vs capsules_off، on vs shuffled)؛ از `PairedComparisonResult` استفاده کن و `claim_downgraded` وقتی CI صفر را شامل شود؛ `MultipleComparisonAudit(metric_count=3)` در payload. seedهایی که outcome ندارند حذف و شمارش می‌شوند (نه صفر).

5. **replay.** همهٔ armها برای `seeds[0]` و `seeds[-1]`؛ spec+result digest باید match کند؛ campaign بدون match ساخته نمی‌شود (رفتار فعلی حفظ).

6. **قاعدهٔ تصمیم (پیش‌ثبت‌شده، بدون استثنا).**
   - اگر CI برای on vs off و on vs shuffled صفر را شامل نشود، shuffled ≈ capsules_off باشد (CI شامل صفر)، و روند dose یکنوا و هم‌جهت باشد → از ClaimGate برچسب `intervention_supported` را با همهٔ flagهای لازمش بخواه (`intervention_result_artifact`, `intervention_result_digest`, `baseline_digest`, `treatment_digest`, `intervention_protocol_digest`, `effect_size`, `paired_seed_protocol_digest`, `claim_gate_decision_digest`). اگر allowed شد، سقف = `intervention_supported` (= سطح ۳ «Mechanism support» در CLAIMS.md). برچسب جدید اختراع نکن.
   - در غیر این صورت سقف همان `runtime_observation` می‌ماند و نتیجهٔ null/کوچک با همان صداقت ثبت می‌شود. null یک یافتهٔ معتبر است.
   - هیچ‌وقت `collective_intelligence*`.

7. **خروجی.** `docs/HARD_EXPERIMENT_01.md` بخش Results: جدول (arm, n, mean, sd, \(d_z\), CI95, p_holm)، جدول dose، نرخ extinction هر arm، replay status، سقف نهایی ClaimGate، Limitations (life_loop overlay ≠ Avida ISA؛ terminal fitness ≠ instinct؛ …). CLAIMS.md §4/§6 را فقط با همان سطحی که ClaimGate داد به‌روز کن.

**Done موج ۱:** prereg commit جلوتر از نتایج؛ ۴ arm + dose؛ 30 seed research با CI/permutation/Holm؛ replay ۲ seed × همه armها؛ اعداد در doc؛ سقف ClaimGate مستند؛ pinهای A–E دست‌نخورده.

### موج ۲ — ClaimGate به‌عنوان ممیز مستقل (PR: `feat(claimgate): simulator-agnostic evidence auditor`)

وجه تمایز محصول همین است. ورودی را عمومی کن، سخت‌گیری را کم نکن.

- Subpackage جدا: `src/codontrace/claimgate/` با صفر import از `codontrace.genesis.engine/population/…` (در `tools/check_core_boundary.py` قاعدهٔ AST اضافه کن). فقط به `claim_gate.py`, `statistical_protocol.py`, `canonical.py` وابسته باشد؛ اگر لازم شد این سه را به `claimgate/` منتقل و در جای قبلی re-export کن.
- یک نردبان واحد: نام‌های عمومی = CLAIMS.md §5 (۰–۵). ۹ سطح داخلی `_CLAIM_LADDER_LEVELS` طبق `docs/CLAIM_LADDER_MAP.md` (موج ۰) نگاشت می‌شوند؛ `StrongClaimLadderResult` فیلد `public_level: int` می‌گیرد. سه سند نردبان قدیمی → یک `docs/CLAIM_LADDER.md` کوتاه که به CLAIMS.md ارجاع دهد.
- اسکیمای ورودی `claimgate_bundle_v1` (JSON): `software{name,version,commit}`, `seeds[]`, `config_digest`, `preregistration_digest?`, `arms[{name, role∈{treatment,mechanism_ablation,channel_off,negative_control,dose}, n}]`, `outcomes[{metric, values_by_arm{arm:[per-seed]}}]`, `comparisons[{a,b,effect_size,ci_low,ci_high,p,test,correction}]`, `replay{verified, digests[]}`, `artifacts[{path,sha256}]`, `limitations[]`.
- ممیز: `audit_bundle(bundle) -> ClaimAuditReport{achieved_level 0–5, missing_for_next[], warnings[], digest}`، deterministic، قواعد = CLAIMS.md §5 + ۱۲ قاعدهٔ §8. سطح ۴ بدون CI و ≥۱۶ seed نه؛ سطح ۵ بدون artifact آرشیوشده/DOI نه. forbidden aliasها همان می‌مانند.
- آداپترها: `adapters/codontrace.py` کامل (از HardExperiment01Campaign → bundle)؛ `adapters/avida.py` اسکلت: فایل‌های `.dat` Avida (`average.dat`, `tasks.dat`, `time.dat`) = متن whitespace-separated با هدر کامنت `#  N: column name`؛ هر پوشهٔ run = یک seed؛ نگاشت arm را کاربر می‌دهد؛ `adapters/mabe2.py` اسکلت: CSV خروجی DataFile.ADD_COLUMN. fixture مصنوعی کوچک برای هر دو در `tests/fixtures/`. ادعای پشتیبانی کامل Avida/MABE نکن.
- CLI: `python -m codontrace.claimgate audit bundle.json` → سطح + missing. مثال: `examples/claimgate_audit_hard_experiment_01.py`. سند یک‌صفحه‌ای `docs/CLAIMGATE_STANDALONE.md`.

**Done موج ۲:** ممیز مستقل + سه آداپتر (یکی کامل، دو اسکلت) + تست + CLI + doc؛ boundary check سبز؛ HARD_EXPERIMENT_01 دقیقاً همان سطحی را از ممیز می‌گیرد که موج ۱ ثبت کرد.

### موج ۳ — پیش‌نویس پروتکل روش‌شناسی (PR: `docs(protocol): claim ladder protocol v0.1`)

فقط بعد از Done موج ۲. یک فایل: `docs/protocol/CLAIM_LADDER_PROTOCOL_v0.1.md` (~۶ صفحه)، عنوان کاری «A Claim Ladder for Computational Evolution / ALife Experiments». ساختار: (۱) انگیزه: بحران بازتولیدپذیری (Pineau 2021)، ODD برای ABM (Grimm et al.)، ASME V&V 40 context-of-use؛ (۲) سطح‌های ۰–۵ با شواهد لازم و anti-patternها (event count ≠ outcome؛ Cov ≠ علّیت)؛ (۳) رده‌بندی مداخله‌ها: mechanism ablation، channel-off، shuffled/negative control، dose-response، heldout؛ (۴) کف آماری: paired seeds، effect size + CI، permutation، correction، ردهٔ n؛ (۵) الزام replay/digest؛ (۶) مثال کارشده = HARD_EXPERIMENT_01 با همان سطحی که ممیز داد؛ (۷) نسبت با MODES و Channon 2024: آن‌ها measurement procedure هستند، این claim grading است — مکمل، نه جایگزین؛ (۸) محدودیت‌ها؛ (۹) پیوست checklist Yes/No/NA به سبک Pineau. هدف: ALIFE workshop / late-breaking. هیچ ادعای جایگزینی PRISMA/CONSORT.

**Done موج ۳:** فایل پروتکل + checklist؛ لینک از README (یک خط)؛ بدون کد جدید.

### گزارش‌دهی

بعد از هر موج: ۳–۵ خط فارسی: چه merge شد (SHA)، سقف ClaimGate فعلی، اعداد کلیدی، بلاکر. بین موج‌ها «خوب؟» نپرس؛ فقط اگر بلاکر واقعی (approval merge، تصمیم مقیاس، CI قرمزِ محیطی) هست بپرس.

---

## ADDENDUM (2026-09-12) — موج ۱c: اعتبار assay قبل از موج ۳

علت: نتایج v2 (PR #23) در همهٔ ۴ بازو عیناً یکی است (mean fitness 0.164375, adoptions 169/169/0/169, dz 0.0, CI [0,0]). این «null قابل تفسیر» نیست؛ manipulation realized نشده. با ۳۰ seed × ۴۰ tick، برابریِ بیت‌به‌بیت بین بازوها یعنی مداخله هیچ متغیر میانیِ DAG را تغییر نداده.

- **Manipulation check اجباری (قبل از تفسیر outcome).** برای هر seed ثبت و مقایسه کن: (a) مجموعهٔ digest کپسول‌های adopt‌شده در on ≠ off؛ (b) محتوای adopt‌شده در shuffled ≠ on؛ (c) capsules_off adoptions = 0؛ (d) شمارندهٔ `rejected_by_source_fitness` در on > 0. اگر (a) یا (b) یا (d) برقرار نباشد → `assay_failed: manipulation_not_realized`. اگر outcome بین بازوها در ≥ ۹۰٪ seedها دقیقاً برابر باشد → warning `arms_bitwise_identical`.
- **گیت bypass شده است.** `accept_provisional_source_fitness=True` عملاً `min_source_fitness=2.0` را خنثی می‌کند (adoptions on = off = 169). در treatment False کن. آستانهٔ مطلق 2.0 با fitness ~0.16 بی‌معناست؛ آستانه را به‌صورت quantile (مثلاً median fitness منبع در همان tick) پیش‌ثبت کن.
- **آیا adoption اصلاً به رفتار وصل است؟** در overlay `life_loop_world` بررسی کن که محتوای کپسول adopt‌شده انتخاب action/ATP را تغییر می‌دهد یا فقط record می‌شود. اگر inert است، یال content → action در این substrate وجود ندارد و سؤال روی این substrate جواب‌پذیر نیست. به `GenesisRuntimeProfile.phase_e_substrate_world()` برو (طبق CLAIMS.md، capsule slotها در Phase E «change subsequent action choice, ATP, or task eligibility»). این تغییر substrate را به‌عنوان amendment ثبت کن، نه در سکوت.
- **تولیدمثل حذف شده.** ژنوم v2 (EAT, EMIT, WAIT / EAT, WAIT, WAIT) COPY ندارد → births = 0 → «next-generation fitness» تعریف‌نشده است و با prereg (که next-generation می‌گفت) ناسازگار. births > 0 شرط اعتبار است و باید در جدول گزارش شود.
- **Amendment رسمی.** هر تغییر نسبت به `HARD_EXPERIMENT_01_PREREG.md` (کالیبراسیون v2، substrate، آستانه، ژنوم) در `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md` با digest جدا؛ campaign هم `prereg_digest` هم `amendment_digest` را ثبت کند. digest prereg قدیمی را با دیزاین تغییریافته دوباره استفاده نکن.
- **جداسازی seed کالیبراسیون از seed تحلیل.** کالیبراسیون بقا (ATP، food، basal…) فقط روی pilot seeds 1000–1009؛ seedهای تحلیل (11–40) تا قبل از قفل شدن config اجرا نشوند (garden of forking paths).
- **Positive control.** یک بازوی `oracle_capsule` که کپسولش payload مستقیماً fitness‌افزا حمل می‌کند؛ اگر این بازو هم dz = 0 بدهد، assay مرده است و هیچ null‌ای قابل تفسیر نیست. نتیجهٔ آن در جدول می‌آید ولی وارد سه contrast اولیه نمی‌شود.
- **ممیز (claimgate) — قاعدهٔ اعتبار assay قبل از سطح ۲:** `manipulation_check_passed`، `positive_control_detected` (یا دلیل مستند)، واریانس outcome > 0 در هر بازو، births > 0 وقتی claim دربارهٔ نسل بعد است. بدون این‌ها سقف = سطح ۱ با برچسب `assay_invalid`، نه «interpretable null». متن PR #24 و CLAIMS.md §4.4 را به همین اصلاح کن.
- موج ۳ فقط بعد از موج ۱c (یا اثر واقعی، یا null با manipulation check پاس‌شده و positive control مثبت). مثال کارشدهٔ پروتکل همین داستان باشد: «چطور نردبان یک null نامعتبر را گرفت».

---

## ADDENDUM 2 (2026-09-12) — ارتقای موتور برای این‌که «جواب بدهد» (HARD_EXPERIMENT_02)

تشخیص: v2 صفر داد چون کپسول‌ها ارزش انتخابی ندارند: هیچ task‌ای وجود ندارد که بدون اطلاعاتِ دیگری حل نشود، هیچ ساختار خویشاوندی/گروهی نیست که صداقت سیگنال را پاداش دهد، و adoption به action وصل نیست. ادبیات دقیقاً می‌گوید ارتباط و DoL تحت چه شرایطی تکامل می‌یابد؛ آن شرایط را به‌عنوان knob آزمایشی (نه پیش‌فرض) به موتور اضافه کن. همه چیز default-off، pinهای A–E دست‌نخورده، بدون Phase letter جدید؛ همه در `codontrace.genesis.hard_experiment_02` + ماژول‌های مکانیزم.

### قالب کد (اجباری برای هر مکانیزم جدید)

`XConfig` = `@dataclass(frozen=True, slots=True)` با `enabled: bool = False`، اعتبارسنجی در `__post_init__` با `ConfigurationError`، `to_dict()`، `digest()` از `canonical_digest`؛ یک `XRecord` digest-backed برای هر رخداد؛ یک knob ablation صریح که با do-operator در DAG نگاشت شده باشد؛ تست «A–E pins unchanged with X disabled»؛ تست «X enabled changes at least one runtime record» (manipulation check واحد); `tools/check_core_boundary.py` سبز؛ بدون وابستگی جدید در `dependencies = []`.

### E1 — اطلاعات باید ارزش انتخابی داشته باشد: task «مکان غذا» (اولویت ۱)

مرجع: Floreano, Mitri, Magnenat, Keller, Curr Biol 17(6):514–519 (2007), doi:10.1016/j.cub.2007.01.058 — ربات‌ها سیگنال «مکان غذا» می‌دهند؛ ارتباط فقط وقتی تکامل می‌یابد که ارزش داشته باشد. Knoester, McKinley, Ofria, GECCO 2008, doi:10.1145/1389095.1389130 — taskهایی که بدون تبادل پیام حل‌نشدنی‌اند (ساخت شبکه/توزیع داده). پیاده‌سازی: `FoodPatchSignalConfig(enabled, patch_spawn_period_ticks, patch_lifetime_ticks, visibility_radius, patch_atp)`: patch غذا در سلول تصادفی (RNG قطعی) ظاهر می‌شود و فقط تا `visibility_radius` دیده می‌شود؛ payload کپسول = مختصات patch؛ action جدید `MOVE_TOWARD_CAPSULE_TARGET` (نیازمند MOVE در ISA — اگر نیست، اول MOVE را با هزینهٔ ATP اضافه کن). `FoodPatchSignalRecord(tick, emitter_id, receiver_id, payload_digest, target_true, moved, ate_at_target)`. Manipulation check طبیعی: `payload_informativeness = I(payload; true_patch_location)` (mutual information) — در capsules_shuffled باید ≈ 0 باشد؛ در treatment > 0. این همان متغیر میانیِ DAG است که v2 نداشت.

### E2 — خویشاوندی × سطح انتخاب، طرح 2×2 با پیش‌بینی الگو (اولویت ۱، هم‌زمان با E1)

مرجع: Floreano 2007 (همان): ارتباطِ صادق فقط در (انتخاب سطح کلنی) یا (خویشاوندی بالا)؛ در (انتخاب فردی × نامرتبط) سیگنالِ فریبنده تکامل می‌یابد. Knoester 2008: germline دیجیتال تکامل‌پذیری همکاری را زیاد می‌کند. MLS1/MLS2: Damuth & Heisler 1988 Biol Philos 3:407–430؛ Okasha 2006 Evolution and the Levels of Selection (OUP). روش پیش‌بینی الگو: Grimm et al. 2005 Science 310:987–991 (pattern-oriented modelling). پیاده‌سازی: `DemeSelectionConfig(enabled, level: INDIVIDUAL|GERMLINE_GROUP, founder_relatedness: CLONAL|MIXED, replication_trigger: MEAN_FITNESS|TASK_COUNT, deme_size, deme_count)` روی `collective_deme` موجود؛ در GERMLINE_GROUP کل deme از germline تکثیر می‌شود (الگوی GermlineReplication Avida که ریپو دارد). `DemeReplicationRecord`. پیش‌بینی پیش‌ثبت‌شده (الگو، نه یک contrast):

| سلول | payload_informativeness | yield گروه vs shuffled |
|---|---|---|
| GERMLINE × CLONAL | بالا | ↑ (اثر اصلی) |
| GERMLINE × MIXED | متوسط | ↑ ضعیف |
| INDIVIDUAL × CLONAL | متوسط (kin) | ↑ ضعیف |
| INDIVIDUAL × MIXED | ≈ 0 یا منفی (فریب: payload ضد‌همبسته با patch) | ≈ 0 |

اگر الگو با همین ترتیب ظاهر شود، شاهد خیلی قوی‌تر از یک dz تنهاست (رد شدن چند پیش‌بینی مستقل). تحلیل: interaction در paired-permutation دو-عاملی + Holm؛ هر ۴ سلول با ۴ بازوی HE01 (on/off/channel-off/shuffled) = 16 بازو × 30 seed — زمان را اول با pilot اندازه بگیر؛ اگر لازم شد بازوی `source_bias_off` را حذف کن (سؤال HE02 دربارهٔ source-bias نیست).

### E3 — هزینهٔ task-switching + متریک DoL درست (HARD_EXPERIMENT_03، بعد از HE02)

مرجع: Goldsby, Dornhaus, Kerr, Ofria, PNAS 109(34):13686–13691 (2012), doi:10.1073/pnas.1202233109 — گرادیان هزینه 0/25/50 سیکل → DoL؛ تست isolation (متخصص‌ها تنها نمی‌توانند). متریک: Gorelick, Bertram, Killeen, Fewell, Am Nat 164:677–682 (2004), doi:10.1086/424968 — DoL = mutual information نرمال‌شده: \(D_{task} = I(X;Y)/H(Y)\), \(D_{indiv} = I(X;Y)/H(X)\), \(D_{sym} = I/[H(X)H(Y)]\) روی ماتریس فرد×task. پیاده‌سازی: دو resource A/B با action EAT_A/EAT_B؛ `TaskSwitchCostConfig(enabled, switch_cost_atp ∈ {0, moderate, high})`؛ `codontrace.genesis.metrics.division_of_labor.gorelick_nmi(matrix)`؛ IsolationAssay: ژنوتیپ‌های تکامل‌یافته را جدا در محیط تک‌نفره اجرا کن و افت performance را گزارش کن (این همان «isolation drop» معیار کار جمعی در roadmap است). هر DoL-metric فعلی که NMI نیست را با برچسب legacy نگه دار.

### E4 — Ecological scaffolding: patch + dispersal دوره‌ای (فقط اگر HE02 سیگنال نشان داد)

مرجع: Black, Bourrat, Rainey, Nat Ecol Evol 4:426–436 (2020), doi:10.1038/s41559-019-1086-9 — منابع لکه‌ای + dispersal بین لکه‌ها با بنیان‌گذار تک‌سلولی، خودبه‌خود خواص داروینی سطح جمعی می‌سازد و DoL تولیدمثلی را ترجیح می‌دهد. پیاده‌سازی: `ScaffoldConfig(enabled, patch_count, dispersal_period_ticks, founders_per_patch=1, patch_resource_budget)`؛ `PatchLineageRecord`؛ متریک: واریانس بین-patch در yield نسبت به درون-patch (پروکسی export-of-fitness میکود؛ Michod 2007 PNAS 104(suppl 1):8613–8618). بدون group-fitness دستی — گروه‌بودگی باید از ساختار اکولوژیک بیرون بیاید.

### E5 — پاداش پلکانی + کالیبراسیون نرخ جهش (knob داخل HE02/03)

مرجع: Lenski, Ofria, Pennock, Adami, Nature 423:139–144 (2003), doi:10.1038/nature01568 — ویژگی پیچیده فقط وقتی تکامل می‌یابد که اجزای ساده‌تر هم پاداش بگیرند. Wilke, Wang, Ofria, Lenski, Adami, Nature 412:331–333 (2001) — survival of the flattest؛ نرخ جهش بالا رژیم انتخاب را عوض می‌کند. پیاده‌سازی: `SteppingStoneRewardConfig(enabled, component_rewards: tuple[float,...])` برای اجزای task جمعی (emit صحیح، move به هدف، eat در هدف)؛ نرخ جهش per-site (پیش‌فرض Avida 0.0075) در MutationConfig صریح و پیش‌ثبت‌شده؛ sweep روی pilot seeds.

### E6 — کالیبراسیون با تحلیل حساسیت، نه دستی (پیش‌نیاز HE02)

مرجع: Thiele, Kurth, Grimm, JASSS 17(3):11 (2014) — روش‌های SA/کالیبراسیون برای ABM؛ Morris (1991) elementary effects برای screening؛ Saltelli et al. 2008 Global Sensitivity Analysis: The Primer (Wiley). مستندسازی: ODD protocol — Grimm et al. 2020 JASSS 23(2):7 (ریپو `docs/ODD_REPORTING.md` دارد؛ پر کن). پیاده‌سازی: `codontrace.genesis.sensitivity.morris_screen(knob_ranges, model_fn, trajectories=10, seed)` dependency-free؛ روی ۸ knob‌ای که در v2 دستی عوض شد + نرخ جهش، خروجی‌ها: extinction_rate، adoptions، births، payload_informativeness. فقط pilot seeds 1000–1009. خروجی commit: `docs/hard_experiment_02/sensitivity_v1.json` + جدول μ*/σ در doc. config نهایی HE02 از این جدول انتخاب و بعد prereg می‌شود.

### E7 — کارایی (بدون تغییر معناشناسی)

اول cProfile روی یک arm × یک seed research؛ سپس: `RecordPolicy(level: MINIMAL|FULL)` تا خانواده‌های رکورد ۱۶۰۴تایی فقط وقتی لازم است جمع شوند؛ digest فقط در انتهای run (همان کاری که در #22 شد، رسمی و تست‌شده)؛ مسیر numpy اختیاری فقط تحت extra `[science]` و فقط اگر تست «digest برابر با مسیر pure-Python» پاس شود. سقف صریح در doc: پایتون خالص به مقیاس Avida (۱۰⁵ update) نمی‌رسد؛ Goldsby-scale ادعا نمی‌شود.

### ترتیب اجرا و «نه»ها

E6 → (E1 + E2 + E5 در HE02 با prereg و همان انضباط آماری موج ۱ + manipulation check + positive control) → E3 در HE03 → E4 فقط مشروط. E7 هر جا profile گفت. نه: همهٔ E‌ها هم‌زمان؛ Phase letter جدید؛ group-fitness دست‌ساز؛ ادعای communication/DoL/CI قبل از ClaimGate؛ تغییر پیش‌فرض‌های A–E.
