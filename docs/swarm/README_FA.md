# Genesis Wi-Fi Sensor Swarm — V1

این پچ روی `694af75a4047c98a24eb90e7f1c8bf10ff149d8c` ساخته شده است. هیچ firmware، push یا تغییر پیش‌فرض در اکولوژی موتور ندارد. میکروکنترلر یا کامپیوتر تک‌بردی فقط قرارداد شبکه را پیاده می‌کند؛ Genesis داده و قابلیت‌ها را می‌گیرد، تحلیل می‌کند و درخواست می‌فرستد.

## راه‌اندازی

```bash
python -m pip install -e '.[swarm]'
# API token را از secret manager یا محیط امن تنظیم کنید؛ داخل git ننویسید.
python -m codontrace.swarm serve --host 127.0.0.1 --port 8765 --swarm-id lab
```

پنل مستقل: `http://127.0.0.1:8765/swarm.html`. پنل اصلی دست‌نخورده است. شروع/ادامه، pause و stop مربوط به پذیرش داده و فرمان‌های میزبان هستند؛ توقف فیزیکی نمونه‌برداری برد تنها با قابلیت firmware و پاسخ تأییدشده ممکن است. اتصال به شبکه با `--host 0.0.0.0` به `CODONTRACE_API_TOKEN` نیاز دارد. خارج localhost، HTTP را پشت reverse proxy با TLS قرار دهید. سرور console خود TLS termination انجام نمی‌دهد.

برای MQTT و API در **یک پردازش**:

```bash
# CODONTRACE_MQTT_USERNAME و CODONTRACE_MQTT_PASSWORD را خارج کد تنظیم کنید.
python -m codontrace.swarm serve --swarm-id lab --mqtt-host broker.example --mqtt-port 8883 --ca-file ca.pem
```

Broker باید TLS، احراز هویت و ACL مستقل هر node داشته باشد: هر node فقط روی `genesis/swarm/lab/NODE/up` publish و روی `genesis/swarm/lab/NODE/down` subscribe کند. اعلان wifi=true به‌تنهایی اثبات اتصال Wi-Fi یا هویت نیست؛ این‌ها مسئولیت شبکه/احراز هویت هستند. QoS=1 ممکن است پیام را تکرار کند: ورودی با boot_id/seq حذف تکرار می‌شود و firmware باید command_id را idempotent اجرا کند. retain برای telemetry و فرمان ممنوع است. ACK حمل‌ونقل MQTT معادل اجرای فرمان نیست؛ پاسخ node لازم است.

## قرارداد پیام

`schema=genesis_swarm_v1`، `swarm_id`، `node_id`، `boot_id`، `seq` عدد صحیح صعودی، `kind` و `payload` اجباری‌اند. اولین پیام هر boot باید hello باشد. همه عددها finite، زمان‌ها UTC millisecond و ساعت نمونه‌برداری همگام باشند. دستگاهی با ساعت نسبی باید در adapter به زمان UTC نگاشت کند و عدم قطعیت آن را پیش از اجرای علمی اندازه بگیرد.

```json
{"schema":"genesis_swarm_v1","swarm_id":"lab","node_id":"esp01","boot_id":"boot1","seq":0,"kind":"hello","payload":{"wifi":true,"channels":{"temp":{"quantity":"temperature","unit":"degC"}},"operations":["sample","raw","features","result","set_rate","pipeline","capsule"]}}
```

Reading: `channel, sample_ms, value, processing_version`؛ اختیاری: `raw` تا ۲۵۶ مقدار، `features` تا ۳۲، `quality` در [۰،۱]، `reference` همراه `reference_id` و `energy_j`. مرجع صرفاً داده اعلام‌شده است؛ مستقل‌بودن و کالیبراسیون آن را پژوهشگر باید تأیید کند. heartbeat دارای payload خالی است. reply شامل `command_id, ok` و message اختیاری است. firmware فقط operations واقعاً پشتیبانی‌شده را advertise کند. pipeline/capsule تنظیمات عددی محدود می‌فرستند، نه کد اجرایی دلخواه.

محدودیت‌ها: ۲۵۶ node برای هر swarm، ۳۲ session در سرویس، ۲۵۶ فرمان pending، آرشیو ۱۰۲۴ فرمان، نمایش ۵۱۲ خوانش و ۱۲۸ مرز موتور. آرشیو کامل در events.jsonl باقی می‌ماند؛ پنل آرشیو کامل را در RAM بارگذاری نمی‌کند. TTL پیش‌فرض ۱۰ ثانیه، skew مجاز ۲ ثانیه، alignment در fusion یک ثانیه. دستگاه rebootشده وزن اعتماد پیشین را به ارث نمی‌برد؛ تغییر processing_version نیز وزن را reset می‌کند. در نبود داده معتبر خروجی None است، نه صفر ساختگی.

## API و ابزار LLM

POST `/api/swarm` با `Authorization: Bearer TOKEN` و بدنه `{"action":"snapshot","args":{"swarm_id":"lab"}}`. GET snapshot هم محافظت شده است. برای nodeهای HTTP می‌توان `CODONTRACE_SWARM_NODE_TOKENS` را یک JSON object مانند `{"lab/esp01":"secret"}` تنظیم کرد. این توکن فقط ingest همان node را مجاز می‌کند؛ توکن اپراتور را به node ندهید. secrets در snapshot و log ثبت نمی‌شوند.

| action | پارامترها علاوه بر swarm_id | کار واقعی |
|---|---|---|
| snapshot | — | داده و وضعیت واقعی، حتی paused/stopped |
| ingest | message | ورود hello/reading/heartbeat/reply |
| command | node_id, operation, params؛ timeout_ms اختیاری | pending با پاسخ هم‌هویت و انقضا |
| status | status: running/paused/stopped | کنترل intake میزبان |
| fusion | quantity, unit؛ mode اختیاری | median/mean/calibrated با کنترل واحد و تازگی |
| diagnosis | quantity, unit؛ reference,tolerance اختیاری | نامزد خطا؛ بدون ادعای تشخیص علّی |
| plan | quantity, unit؛ budget اختیاری | ارسال درخواست oldest-first بر اساس قابلیت و دسترس‌پذیری |
| calibrate | key, reference, reference_id؛ scale اختیاری | یادگیری وزن روی مرجع اعلام‌شده |
| pipeline_fit | values,references,seed؛ rounds اختیاری | جست‌وجوی تکاملی پردازش روی میزبان |
| capsule_validate | candidate,baseline,values,references؛ minimum_gain اختیاری | قبول/رد انتقال بر اساس validation محلی |
| processing_contrast | frame,reference؛ tolerance اختیاری | مقایسه raw/processed با مرجع |
| information_level | options,byte_budget,maximum_mse | انتخاب raw/features/result با بودجه JSON و خطای validation اعلام‌شده |
| twin_fit | references,observations | twin کالیبراسیون خطی، نه twin کامل فیزیکی |
| coevolve | references,seed؛ rounds,disturbance_budget اختیاری | هم‌سازگاری محدود policy/اختلال روی میزبان |

هر action فیلدهای ناشناخته را رد می‌کند. اطلاعات سطح‌های مختلف باید validation_id داشته باشند. خروجی information_level فقط اندازه payload کاربردی را می‌سنجد، نه انرژی رادیو یا سربار Wi-Fi.

ابزار `swarm_inspect` در catalog ابزارهای علمی LLM اضافه شده است: فقط خواندنی، با swarm_id و محدود به selected_run_id اگر انتخاب شده باشد. تحلیل و نمودار از تاریخچه ثبت‌شده، حتی در pause/stop؛ نمودارها بر اساس quantity/unit جدا می‌شوند. این پچ به LLM اختیار ارسال فرمان سخت‌افزاری نمی‌دهد؛ اپراتور از API استفاده می‌کند. تعمیم کنترل خودکار نیازمند policy اجازه مستقل است.

## اتصال واقعی به موتور

`SwarmEngineLink.attach(engine)` به generation_boundary_observers موتور واقعی وصل می‌شود و run_id، spec_digest، fusion و فرمان‌ها را ثبت می‌کند. حالت پیش‌فرض **مشاهده‌گر** است. برای اثرگذاری داده بر محیط، mapper دامنه‌محور ارائه کنید و از `link.run_ticks()` استفاده کنید؛ نگاشت قبل از گام موتور انجام می‌شود. `engine.run_ticks()` مستقیم نگاشت ورودی را اجرا نمی‌کند. داده حسگر الزاماً ATP دیجیتال نیست؛ تبدیل انرژی یا کمیت فیزیکی باید واحددار و آزموده باشد. تکامل pipeline این پچ روی میزبان است و نباید به‌عنوان fitness زایشی همه ارگانیسم‌های ALife معرفی شود.

یک coordinator مشترک در یک پردازش برای engine/API/MQTT استفاده کنید. journal روی filesystem محلی، تک‌نویسنده است؛ lock سیستم‌عامل نوشتن‌ها را serialize می‌کند و writer با snapshot قدیمی به‌جای fork کردن hash-chain متوقف می‌شود. این distributed database یا ضمانت فایل‌سیستم شبکه نیست. در خطای fsync ادامه نوشتن مسدود می‌شود؛ پس از بررسی لاگ coordinator تازه بسازید. رکورد ناقص fail-closed است، خودکار حذف نمی‌شود.

## آزمایش و بازپخش

```bash
python -m codontrace.swarm probe --output swarm_probe --seeds 16 --samples 64
python -m codontrace.swarm replay --swarm-id lab --journal swarm_runs/lab/events.jsonl
python -m pytest -o addopts='' tests/test_swarm_protocol_runtime.py tests/test_swarm_engine_api.py
```

probe ده مسیر را واقعاً اجرا و metrics.jsonl را زنده flush می‌کند؛ داده‌ها **synthetic** هستند. replay hash-chain، پیکربندی و state_digest را می‌سنجد؛ بازپخش تصمیم میزبان است نه بازسازی جهان واقعی. یافته علمی نهایی از پاس‌کردن unit test به‌دست نمی‌آید. برنامه تحقیق و کنترل‌ها در RESEARCH_PLAN_FA.md است.

نمونه اتصال موتور: `examples/swarm_engine_link.py`؛ این مثال صریحاً synthetic است. گزارش آزمون و محدودیت‌ها: [VALIDATION.md](VALIDATION.md).

## افزوده V2

تب React «اطلس لایه‌ها» و صفحه `/simulation.html` افزوده شد. بخش‌های قبلی حفظ شده‌اند؛ فایل build پنل اصلی به‌دلیل تب جدید به‌روز شده است. راهنما: [Simulation Atlas](../simulation/README_FA.md).

## V4 — عدم‌قطعیت، تازگی و انتقال محافظه‌کار

سه ابزار جدید و actionهای API آن‌ها در [راهنمای V4](DECISION_SUPPORT_V4_FA.md) توضیح داده شده‌اند. freshness_plan به زمان و قابلیت nodeهای واقعی وصل است؛ uncertainty_interval و capsule_shadow داده/reference مستقل می‌خواهند. گزارش مثال ۱۶ seed از ابزار readonly `swarm_decision_report` برای LLM قابل خواندن است. توصیه scheduler یا rollback فرمان فیزیکی نیست و اجرای برد باید با ACK مستقل اثبات شود.

## V5: حسگرهای typed و پایداری

پروتکل v1 حفظ و v2 برای scalar/vector/waveform/boolean/category اضافه شده است. پشتیبانی از داده با پشتیبانی همهٔ الگوریتم‌ها برابر نیست. اتصال واقعی FDCxCapSense، normalization قابل تنظیم میزبان، replay journal چرخیده و جزئیات آزمون/محدودیت: [AUDIT_V5_FA.md](AUDIT_V5_FA.md). نمونه: `examples/swarm_generic_sensors.py`.
