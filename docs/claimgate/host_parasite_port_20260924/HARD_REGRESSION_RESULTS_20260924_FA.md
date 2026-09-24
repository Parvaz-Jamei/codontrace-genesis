# خلاصه نتایج رگرسیون سخت — میزبان–انگل ClaimGate (۲۰۲۶-۰۹-۲۴)

**پروژه:** CodonTrace Genesis

چند حفرهٔ مهم و سخت (نه دود Wave ۶) پیدا و تست شد:

1. **ادعای ماتریس بدون fail-closed** — `modes_passed_proved` / `oee_type1_proved` / ظهور پیچیدگی / هویت ژن روی `claimed=` قبول می‌شد → به `blocked_claims` اضافه و تست سخت شد.
2. **نام‌های مستعار** — مثل `intelligence_proved` و `modes_passed` دیگر دور نمی‌زنند.
3. **Cornish ترتیبی** — حتی اگر همهٔ مداخله‌ها موفق باشند، `intervention_supported` نمی‌آید.
4. **content-null** — برای `candidate_evidence` فقط structure/abiotic کافی نیست (صداقت Floreano/Knoester).
5. **بستهٔ HE_HP** — schema و `engine_infection_physics` هم fail-closed شدند.
6. **بذرهای contingency پشتیبان قانون** — هنوز `complexity_emergence_proved=False`.
7. **ثبت digest ری‌پلی (#50)** — همهٔ dataclassهای digest میزبان–انگل ثبت‌مانده‌اند.

سنجاق‌های BAIC و خالی‌بودن infection در `engine.py` سالم‌اند. جزئیات و DOIها در
`HARD_REGRESSION_RESULTS_20260924.md`.
