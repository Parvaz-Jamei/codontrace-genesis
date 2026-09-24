# نتایج کمپین‌های سخت cell↔microbe — ۲۰۲۶-۰۹-۲۴

**پروژه:** CodonTrace Genesis  
**شاخه:** `exp/cell-microbe-hard-campaigns` (روی #53 باز)  
**digest بسته:** `579fa46b33a613c1dc1c3b23a9a68a92…`

قفل معماری دست نخورده: یک `host_parasite`؛ **cell** = زیرگاه SemanticGenome؛
microbe/باکتری/ویروس = فقط برچسب معنایی؛ بدون فیزیک عفونت در `engine.py`؛
پین‌های BAIC بدون تغییر بایت.

---

## خلاصهٔ صادقانه برای کاربر

خواست این بود: تست‌های سلولی/میکروبی **سخت** با نتایج خوشگل — ولی **الکی نه**.

### چه چیزی واقعاً خفن بود؟
- **گرمای بذر (CM1):** بعضی بذرها زیر انگل پیچیدگی‌شان بالا می‌رود (مثلاً seed 7 با Δ=+3)، خیلی‌ها contingent می‌مانند (Δ=0). قانون «انگل همیشه پیچیدگی را بالا می‌برد» روی بستهٔ ترکیبی **رد** می‌شود؛ روی لبهٔ حمایتی هنوز support می‌شود ولی **هرگز** `complexity_emergence_proved` نمی‌شود.
- **جداسازی dual-null آنتروپی (CM3):** اختلاف آنتروپی biotic نسبت به content-null ≈ **0.444** (biotic مثبت، null صفر).
- **هزینهٔ generalism در ARD→FSD (CM4):** زیر انگل early=`ard_like` هزینه ≈ 0.239 → late=`fsd_like` ≈ 0.456؛ بازوهای null تقریباً تخت و `undeclared`.
- **Cornish (CM5):** نمرهٔ مشاهده 0.2 → مداخله‌ها [1.0, 1.0, 1.0] ولی `intervention_supported=False`.
- **قید Scanlan (CM6):** fitness غیرزیستیِ جهش‌بالا منهای جهش‌بالا زیر هم تکاملی ≈ **0.116** (فرضیه رد شد).

### چه چیزی متواضع / غیرالکی است؟
همهٔ فرضیه‌های علمی این بسته یا **رد** شدند یا سقف ClaimGate روی
`runtime_observation` / `candidate_evidence` ماند. هیچ ادعای Red Queen، ظهور
پیچیدگی، هویت ژن/CRISPR، فاژتراپی، BSL، یا OEE-MODES نیست. اگر فقط «پاس شدن
تست» می‌خواستید، این بسته تعمداً خلاف آن است — نتایج واقعی با مسیر ابطال.

---

## جدول کمپین‌ها

| ID | نتیجهٔ کلیدی | سقف صداقت |
|---|---|---|
| CM1 contingency | mixed hyp=False؛ edge hyp=True؛ emergence=False | runtime |
| CM2 genome Zaman | arms distinct؛ host≠parasite digests | runtime |
| CM3 entropy/Hamming | hyp=False؛ Δ biotic−null ≈ 0.444 | runtime |
| CM4 ARD→FSD | transition=True؛ hyp=False؛ هزینه بالا می‌رود | runtime |
| CM5 Cornish | match=True؛ support=False | candidate |
| CM6 Scanlan | hyp=False؛ gap fitness ≈ 0.116 | candidate |
| CM7 task–gene | map digests pairwise distinct؛ gene_id=False | runtime |

ClaimGate: نردبان `0`→`0` بدون صعود؛ ادعاهای ممنوع همگی fail-closed.

---

## منابع (واقعی)

Zaman 2014 doi:10.1371/journal.pbio.1002023؛ Scanlan 2015 doi:10.1093/molbev/msv032؛
Cornish JMLR 2026 / arXiv:2301.07210؛ Floreano 2007؛ Knoester 2008؛ Hall 2011؛
Koskella & Brockhurst 2014؛ Lopez Pascua 2014؛ Dolson MODES 2019؛ Channon 2024
(مقایسه‌گر — نه ادعای قبولی).

جزئیات کامل انگلیسی: `CELL_MICROBE_HARD_CAMPAIGN_RESULTS_20260924.md`.
