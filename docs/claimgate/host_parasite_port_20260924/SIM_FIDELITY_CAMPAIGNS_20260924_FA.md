# وفاداری شبیه‌سازی علمی + تمایز ClaimGate — ۲۰۲۶-۰۹-۲۴

**پروژه:** CodonTrace Genesis  
**شاخه:** `sim-fidelity-campaigns-20260924`  
**نوک main:** `9bdad1f`  
**pack_digest:** `46184d6d86782344905142c0db06595e20fcddb4bc0be3683be99e5244faa751`

## به زبان ساده (برای دانشجوی کارشناسی)

شبیه‌سازی می‌تواند اثر ببیند ولی claim ثابت‌شده را قفل می‌کند.

1. در SF1، وقتی هزینهٔ generalism صفر است جمعیت‌ها ناپایدار می‌شوند؛ با هزینهٔ ۰٫۷، همزیستی دیجیتال برمی‌گردد (الگوی Quigley).
2. در SF2، آنتروپی کدون زیر فشار زیستی حدود **۰٫۴۴** بالاتر از کنترل غیرزیستی است — ولی `complexity_emergence_proved` همچنان False است.
3. در SF3 برچسب‌ها از ARD-like به FSD-like می‌روند و هزینهٔ generalism بالا می‌رود — بدون ادعای Red Queen ثابت‌شده.
4. **SF4 پس از De-toy D1:** با type-II و ماتریس قطر-غالب روی پورت، چرخه در ۵/۵ بذر دیده شد؛ DOI درست Sci Rep است؛ `red_queen_proved` همچنان False است (موفقیت ساختاری ≠ اثبات).
5. در DX1 همان اعداد «جذاب» (Δentropy≈۰٫۴۴، جهش هزینه≈۰٫۲۲) هنوز **۱۷ از ۱۷** ادعای افراطی (هوش، Red Queen، MODES-passed، فاژتراپی، …) را مسدود می‌کند.
6. در DX7 امتیاز مشاهده‌ای **۰٫۲** است ولی مداخله‌های اجباری **۱٫۰ / ۱٫۰ / ۱٫۰**؛ با این حال `intervention_supported=False` می‌ماند (قاعدهٔ Cornish).
7. در DX5 امتیاز intact **۰٫۲۰** در برابر content_null **۱٫۰۰** است؛ بدون بازوی content-null سقف `candidate_evidence` رد می‌شود.
8. در DX3 اندازه‌گیری Tokyo Type 1 / MODES مجاز است (`measurement_only`) ولی `tokyo_type1_passed` و `modes_passed` همیشه رد می‌شوند.
9. در DX2 عدد Price (کوواریانس≈۰٫۱۵) به‌عنوان تشخیص موجود است؛ `major_transition_proved` باز نمی‌شود (Okasha: Price≠علیّت).
10. فیزیک عفونت داخل `engine.py` نیست؛ فقط روی پورت `host_parasite` است (DX8 / SF8).
11. پین‌های BAIC دست‌نخورده ماندند؛ نردبان ClaimGate بالا نرفت.
12. جمع‌بندی: Genesis می‌تواند نشانه‌های کیفی coevolution را شبیه‌سازی کند و هم‌زمان ادعاهای خطرناک را قفل کند — این همان تمایز «نه فقط یک Avida دیگر» است.

## ماتریس A — وفاداری شبیه‌سازی

| شناسه | نتیجه | نکته |
|---|---|---|
| SF1_coexistence_cost_of_generalism | **SUCCESS** | 10.1098/rspb.2012.0769 |
| SF2_biotic_vs_abiotic_entropy | **SUCCESS** | 10.1371/journal.pbio.1002023 |
| SF3_ard_fsd_cost_mixing_proxy | **SUCCESS** | 10.1098/rspb.2014.2297 |
| SF4_type2_diagonal_multihost_cycling | **SUCCESS** | 10.1038/srep10004 |
| SF5_dual_genome_digest_divergence | **SUCCESS** | 10.1371/journal.pbio.1002023 |
| SF6_cornish_intervention_refuse | **SUCCESS** | arXiv:2301.07210 |
| SF7_replay_digest_stability | **SUCCESS** | internal:ENGINE_REPLAY_CONTRACT |
| SF8_engine_hygiene_no_infection | **SUCCESS** | internal:ARCHITECTURE_PORTS |

## ماتریس B — تمایز ClaimGate

| شناسه | نتیجه | تیتر تضاد |
|---|---|---|
| DX1_claimladder_theatrical_failclosed | **SUCCESS** | biotic Δentropy=0.444, ARD→FSD cost jump=0.217, yet 17/17 overclaims still blocked |
| DX2_okasha_price_not_causality | **SUCCESS** | Price covariance=0.147420 available as diagnostic; ClaimGate keeps major_transition_proved=False (Ok |
| DX3_channon_modes_measurement_only | **SUCCESS** | measurement_only ALLOWED (tokyo_type1_measurement_only); tokyo_type1_passed / modes_passed* REFUSED |
| DX4_replay_integrity_spectacle | **SUCCESS** | Identical seeds → identical digests; seed+1 → mismatch; forged intervention_supported attach → Confi |
| DX5_content_null_he_trap | **SUCCESS** | intact mean_score=0.20 vs content_null=1.00; without content_null arm, candidate_evidence is refused |
| DX6_cross_domain_auditor_posture | **SUCCESS** | host_parasite DomainProfile blocks phage_therapy_cleared; other profiles allow the string ({'alife': |
| DX7_cornish_looks_fixed_claimgate_says_no | **SUCCESS** | obs_score=0.2 vs intervention_scores=[1.0, 1.0, 1.0] — looks fixed; ClaimGate intervention_supported |
| DX8_engine_boundary_hard_lock | **SUCCESS** | engine.py: zero infection tokens; host_parasite_env.py: inject APIs present |

## سقف ادعا

هیچ‌کدام از این کمپین‌ها `red_queen_proved`، `intelligence_proved`، `phage_therapy_cleared`،
`intervention_supported`، `oee_modes_passed`، یا هویت CRISPR/ژن را ثابت نمی‌کنند.
