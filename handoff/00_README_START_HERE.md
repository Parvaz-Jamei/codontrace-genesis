# شروع از اینجا — ایجنت بعدی CodonTrace Genesis

این پوشه **کپی نقش** ایجنت قبلی است (دانش چت + پرامپت‌ها + patch موج ۱c).

## ترتیب خواندن
1. همین فایل
2. `01_CHAT_KNOWLEDGE.md` (وضعیت، قوانین، اعداد، ریشهٔ باگ)
3. `04_AGENT_HANDOFF_NEXT_WAVES.md` بخش ۳ = پرامپت اجرایی Step 0–5
4. `02_AGENT_PROMPT_WAVES_0_3.md` = قوانین + موج ۰–۳ + Addendum 1 (assay) + Addendum 2 (E1–E7)

## کار اول (همین الان)
مخزن: `Parvaz-Jamei/codontrace-genesis`  
base باید `49b9f2c` باشد (اگر main جلو رفته rebase + تست مجدد).

```bash
git clone https://github.com/Parvaz-Jamei/codontrace-genesis.git
cd codontrace-genesis
git checkout -b cursor/wave-1c-e2-coupling-c909 49b9f2c
gunzip -c 03_0001-wave-1c-e2-coupling.patch.gz | git am --3way
```

SHA256 فایل خام patch (بعد از gunzip):  
`af6db978e31ec38198cf2679c96e95c47d7a0fdbab69ccb3aec0234fc2172a52`

سپس تست‌های فهرست‌شده در handoff، PR draft با عنوان  
`fix(he01): Wave 1c e2 coupling + valid manipulation check (v3)`  
و تصمیم در برابر **PR #25** (رقیب؛ assay نامعتبر). فقط یکی merge شود.

سقف ClaimGate: `runtime_observation`. هویت: `0.3.0b4.dev0`. pinهای A–E دست‌نخورده. بدون tag/PyPI.

## بعد
Wave 1d (sd=0 را با تصادفی‌سازی seedدار نقش/غذا درست کن) → E6 → HE02 → HE03 → موج ۳.

گزارش هر موج: حداکثر ۱۰ خط فارسی.
