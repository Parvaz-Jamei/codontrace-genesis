# دستور مستقیم به ایجنت — Integrated Living World

مشکل معماری قطعی است: پایلوت‌های ۴×۴، یک ژنوم و ۶ تیک فقط component smoke
هستند. آن‌ها ثابت نمی‌کنند toolchain، VM، جهان، منابع، کپسول، تولیدمثل، جهش و
دودمان یک سامانهٔ واحد ساخته‌اند. پایلوت‌ها را حذف نکن، اما از آن‌ها claim
جهان کامل نساز.

## مأموریت

یک **Integrated Living World (ILW)** بساز که این زنجیره در یک `run_id`، یک
`WorldSpec`، یک scheduler و یک event ledger واقعاً طی شود:

```text
genome -> toolchain -> VM phenotype -> action -> resource/world consequence
-> experienced event -> capsule with provenance -> transport/accept/apply
-> receiver policy/action change -> survival/reproduction -> mutation/lineage
-> next ecological state
```

هر پیکان `edge_id`، telemetry before/after، attempt/success جدا، assay و
knockout مستقل داشته باشد. outcome injection، oracle در treatment و fitness
shortcut خارج از VM/world ممنوع است.

## کوچک‌ترین برش عمودی

- محیط فضایی با حداقل دو منبع محدود و تجدیدشونده و چند niche؛
- ژنوم جهش‌پذیر که exploration، harvest، move، emit/read/adopt و reproduction
  را کنترل کند؛
- هزینهٔ واقعی محاسبه، حرکت، کپی و نوآوری؛
- کپسول حاصل تجربهٔ واقعی عامل، نه payload دستی؛
- تغییر resource regime تا اطلاعات قدیمی گاهی منقضی شود؛
- organism phylogeny و capsule genealogy جدا ولی قابل join؛
- strategy تازگی/اعتماد/انتخاب منبع، trait قابل تکامل باشد، نه hard-code.

## مقیاس

`۴×۴ / ۶ tick` فقط S0 unit است. سپس:

- S1: integrated smoke، مثلاً ۱۶×۱۶ و حداقل یک birth/death cycle؛
- S2: pilot چندنسلی، مثلاً ۳۲×۳۲ با seedهای جدا؛
- S3: research، مثلاً ۶۴×۶۴ یا بیشتر و ده‌ها/صدها turnover؛
- S4: حداقل سه اندازه × سه horizon برای finite-size challenge.

اعداد دقیق بعد از benchmark و قبل از دیدن outcome قفل شوند. horizon را با
generation turnover، lineage depth و regime changes نیز گزارش کن، نه فقط tick.

## آزمایش اتصال

روی همان جهان این edge knockouts را بساز:

- `toolchain_to_action_off`
- `experience_to_capsule_off`
- `capsule_transport_off`
- `capsule_to_policy_off`
- `mutation_off`
- `ecological_feedback_off`
- `lineage_inheritance_off`

هر knockout فقط یک edge را قطع کند؛ cost و throughput با sham/yoked control
ثابت بماند. One-factor-at-a-time کافی نیست چون interaction را نمی‌بیند.
Morris برای screening؛ سپس fractional-factorial برای toggleها و
Definitive Screening Design سه‌سطحی برای factorهای پیوسته. حداقل interactionهای
`toolchain × capsule`، `capsule × ecology`، `mutation × capsule` و
`heterogeneity × population_size` برآورد شوند.

## گیت چندالگویی

طبق Pattern-Oriented Modeling یک ATP mean کافی نیست. جهان باید همزمان:

1. toolchain و phenotype معتبر بسازد؛
2. conservation انرژی/منبع را حفظ کند؛
3. چندنسلی persist کند و turnover واقعی داشته باشد؛
4. تنوع ژنتیکی/phenotypic غیرصوری نشان دهد؛
5. رقابت، niche و eco-evolutionary feedback بسازد؛
6. انتقال کپسول واقعاً action و descendant fitness را تغییر دهد؛
7. در null/yoked/edge-off این مسیر طبق پیش‌بینی قطع شود؛
8. در چند مقیاس جهت اثر را حفظ یا شکستش را صادقانه گزارش کند.

برای cumulative cultural evolution تا چهار معیار Mesoudi و Thornton همزمان
پاس نشده‌اند claim نکن: innovation، social transmission، performance
improvement و تکرارِ بهبود ترتیبی در نسل‌ها.

## telemetry اجباری

```text
run_id, seed, tick, generation, world_spec_digest,
event_id, causal_parent_ids, edge_id,
actor_id, lineage_id, genome_digest,
source_id, capsule_id, capsule_parent_id, payload_digest, provenance_digest,
attempted, accepted, applied, blocked_reason,
state_before_digest, state_after_digest,
energy_delta, resource_delta, fitness_proxy_delta
```

Replay باید final digest را bitwise بازسازد. required-edge coverage در
integrated run باید ۱۰۰٪ باشد. attempt، accepted و applied هرگز یک counter
نباشند.

## ترتیب commitها

1. **ILW-0:** فقط `INTEGRATION_DAG.json` و تست fail-first برای orphan subsystem
   و event بدون consumer.
2. **ILW-1:** WorldSpec، scheduler، event ledger و seed namespace مشترک؛
   adapterهای فعلی حفظ شوند.
3. **ILW-2:** اتصال کامل زنجیرهٔ genome تا lineage در محیط دو-resource.
4. **ILW-3:** integrated smoke با replay، conservation و edge coverage؛
   بدون claim علمی.
5. **ILW-4:** prereg الگوها، interactionها، scale، horizon، seed و stop rule؛
   سپس pilot.
6. **ILW-5:** campaign factorial/ablation و scale challenge.
7. **ILW-6:** MODES، phylogeny و novelty+learnability فقط exploratory.

## معیار پذیرش milestone اول

- یک command و یک spec کل جهان را اجرا کند؛
- toolchain و capsule روی همان agents و همان run باشند؛
- تجربه به capsule، capsule به action متفاوت، action به resource/energy و
  آن اثر به reproduction/ancestry متصل باشد؛
- چند turnover نسلی بدون fixture outcome رخ دهد؛
- replay، conservation و تمام assays پاس شوند؛
- هر required edge هم telemetry غیرصفر و هم knockout معتبر داشته باشد؛
- smoke هیچ ladder promotion صادر نکند.

## خطوط قرمز

پایلوت جداگانهٔ جدید، بزرگ‌کردن نمایشی شبکه، config cherry-pick، ATP-only
claim، oracle treatment، تست ضعیف‌شده، شکستن Phase A–E pins، tag/PyPI و
افزایش ClaimGate ممنوع. سقف فعلی `runtime_observation` است. نام علمی فعلی
`integrated eco-evolutionary runtime` است، نه intelligence/AGI/collective
intelligence.

## پاسخ قبل از کدنویسی

حداکثر ۱۰ خط فارسی بده: DAG فعلی، orphanها، کوچک‌ترین برش عمودی، فایل‌های
درگیر، تست fail-first، و تأیید اینکه ClaimGate و pinها تغییر نمی‌کنند. سپس
ILW-0 را در یک commit مستقل اجرا کن.

## منابع اصلی

- Pattern-Oriented Modeling: https://doi.org/10.1098/rstb.2011.0180
- Global sensitivity / ضعف OAT: https://doi.org/10.1016/j.envsoft.2010.04.012
- Definitive Screening Designs: https://doi.org/10.1080/00224065.2011.11917841
- MODES Toolbox: https://doi.org/10.1162/artl_a_00280
- Cumulative cultural evolution: https://doi.org/10.1098/rspb.2018.0712
- Social learning strategies: https://doi.org/10.1126/science.1184719
- Phylotrack: https://doi.org/10.48550/arXiv.2405.09389
- Model docking: https://doi.org/10.1007/BF01299065

نسخهٔ تفصیلی: `handoff/INTEGRATED_LIVING_WORLD_PLAN.md`
