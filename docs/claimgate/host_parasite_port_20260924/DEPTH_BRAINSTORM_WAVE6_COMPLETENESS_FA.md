# کارگاه طراحی — حسابرسی کامل‌بودن موج ۶ (خلاصه فارسی)

**پروژه:** CodonTrace Genesis  
**پایه:** `main` در SHA `fa01873f8e565c66e8901282b3f8128d93fe925e` (ادغام اسکواش PR #48)  
**شاخه حسابرسی:** `docs/host-parasite-wave6-completeness-audit`

این سند خلاصهٔ پنج دور کارشناسی انگلیسی
(`DEPTH_BRAINSTORM_WAVE6_COMPLETENESS.md`) برای تصمیم‌گیری گام بعدی است.

## نقش‌ها

- **A** فرگشت دیجیتال / ALife  
- **B** صداقت میکروبی / ژنوم  
- **C** ClaimGate / راستی‌آزمایی علّی  

## دور ۱ — فهرست و شکار نقص

موج ۶ (فازهای ۲۴–۲۶) روی main نشسته: دود یک‌بستهٔ attach فازهای ۱۸–۲۳،
تازه‌سازی digestهای قفل‌شده HE_HP، پل آنتروپی×contingency فاز ۱۱×۲۱.
هر فاز `PHASE*_REVIEW.md` با موج ۱ و موج ۲ دارد.

**نقص‌های مشخص:**

1. **مسدودکننده (اسناد):** README هنوز می‌گفت موج ۶ روی
   `feat/host-parasite-wave6` / «this PR» است — در حالی که پس از #48 روی main است.
2. **مسدودکننده:** فاز ۲۶ بدون یادداشت شواهد Zaman/Adami و بدون توضیح
   companion-seed (`S+1000`/`S+2000`).
3. **مسدودکننده (صداقت):** DOI `10.3389/fevo.2021.750772` به اشتباه «Fortuna
   2021» نامیده شده بود؛ مقالهٔ واقعی Acosta & Zaman 2022 است.
4. **مسدودکننده:** عنوان اشتباه Fortuna 2017 در evidence برای DOI
   rstb.2016.0431.
5. **اسنادی:** ردیف پل موج ۶ در COMPARATOR_MATRIX نبود؛ تست double-attach فاز ۲۵
   نبود.

قفل‌های سخت سالم بودند: یک DomainProfile، بدون عفونت در `engine.py`، پینهای
BAIC دست‌نخورده، بدون `population/`، بدون ادعای Red Queen / درمان فاژی / CRISPR.

## دور ۲ — فشار ادبیات

DOIهای واقعی تأیید شد (Zaman 2014، Adami 2000، Acosta & Zaman 2022، Fortuna
2017 rstb، Cornish JMLR 2026، MODES، Channon، Goldsby، JaxLife). فشار کیفیت:
پروتکل‌های ClaimGate درست‌اند؛ باقی‌ماندهٔ کار بسته‌بندی صداقت شواهد و README
پس از ادغام است — نه فیزیک عفونت جدید و نه پورت JaxLife/Avida.

## دور ۳ — اصلاح یا رد

| نقص | تصمیم |
|-----|--------|
| README کهنه پس از #48 | **اصلاح** |
| یادداشت شواهد فاز ۲۶ + docstring companion-seed | **اصلاح** |
| نسبت‌دهی DOI به Acosta & Zaman | **اصلاح** |
| عنوان Fortuna 2017 | **اصلاح** |
| ردیف COMPARATOR + تست double-attach ۲۵ | **اصلاح** |
| `__all__` آداپتر | **رد** (الگوی موج‌های قبل؛ یکتای موج ۶ نیست) |
| هم‌تکاملی زنده / MLS / OEE / درمان / CRISPR / پروفایل جدا / پین BAIC | **رد** (قفل سخت) |

## دور ۴ — دروازه کامل‌بودن

**آیا موج ۶ برای این برش پورت soft-complete است؟**  
**بله، با شرط** اجرای اصلاحات P0/P1 بالا، سبز بودن pytest، پین‌های BAIC، و
diff خالی / نبود `engine.py` نسبت به main.

- **باید قبل از اعلام اتمام موج ۶:** D1–D5 (+ تست double-attach ۲۵)  
- **خوب است ولی ضروری نیست:** re-export در `__all__`؛ اتصال غنی‌تر env زنده  
- **خارج از محدوده:** عفونت در engine، DomainProfile جدا، MLS، صادرات هویت
  Avida، JaxLife HP، چندصندلی co-infection، HGT/CRISPR/درمان/BSL/بالینی، اثبات
  Red Queen یا OEE-MODES

## دور ۵ — امضا و بذرهای موج ۷ (فقط اگر شایسته)

نمرات پس از اصلاح: A/B/C همگی soft-complete را می‌پذیرند (کیفیت A کمی کمتر به‌خاطر
پل نازک دیجیتال، نه هم‌تکاملی زنده).

**بذر موج ۷:** هیچ فاز بیولوژی شماره‌دار جدید **شایسته نیست**. فقط جاروی اختیاری
اسناد تاریخی که هنوز «Fortuna 2021» می‌گویند (W7-a معوق؛ مرجع رسمی CITATIONS +
evidence اصلاح شده) — و رد هم‌تکاملی زنده در موتور.

## اصلاحات انجام‌شده در همین شاخه

- README: فازهای ۲۴–۲۶ روی main @ `fa01873`
- `evidence/phase26_entropy_contingency_bridge.md` + docstring فاز ۲۶
- CITATIONS + evidence: Acosta & Zaman 2022؛ عنوان درست Fortuna 2017
- COMPARATOR_MATRIX ردیف پل موج ۶
- تست double-attach فاز ۲۵
- CHALLENGES / REQUIREMENTS: ارجاع زنده به Acosta & Zaman

## یک‌خطی

موج ۶ پس از #48 نرم‌کامل است؛ نقص‌های صداقت DOI/عنوان و README کهنه در همین
حسابرسی درست شدند — بدون بذر بیولوژی موج ۷ و بدون باز کردن قفل‌ها.
