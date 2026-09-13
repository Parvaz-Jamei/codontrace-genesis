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
