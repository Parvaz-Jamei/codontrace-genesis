# Swarm/Atlas V5 — اصلاحات تأییدشده و حسگرهای قابل‌تنظیم

مبنا b29 / `694af75`، ورودی ZIP V4 ضمیمه‌شدهٔ کاربر، تاریخ ۲۰۲۶-۱۰-۱۱. core فرگشت، RNG علمی و expected digest دستکاری نشده‌اند. قابلیت UI قبلی حذف نشده؛ فایل‌های generated قدیمی با build واحد جایگزین شده‌اند.

## ارزیابی گزارش تیم

اصل ایرادهای build، journal بدون recovery/rotation، client ID ثابت، مسیر پیش‌فرض وابسته به CWD، exception پل و محدودیت scalar از کد V4 تأیید شد. آزمون paho در محیط بدون extra نیز ModuleNotFoundError داد. print و عدد catalog اصلاح شدند، بدون حذف خروجی CLI یا تست قابلیت. عدد ابزارها ۱۷ است و نام‌های لازم/یکتایی هم بررسی می‌شود.

«۱۶/۱۶» کنترل‌های ثابت گزارش V4، ۱۶ تکرار fixture قطعی است؛ ۱۶ آزمایش مستقل نیست. متن قبلیِ آن حذف نشده، اما باید با این توضیح خوانده شود. پوشش interval همچنان از traceهای مستقل محاسبه می‌شود؛ چنین محدودیتی به controls قطعی مربوط است.

سه شکست مشاهده‌شده در آغاز suite عمومی روی b29 بدون پچ نیز بازتولید شدند:

- test_idea2_engine_seed_variance_survival
- test_p2_survival_varies_across_seeds
- test_p3_four_quantities_match_and_stay_a_planted_mirror

تعداد collection عمومی هنگام بررسی ۳۰۰۷ بود. اجرای کامل عمومی پایان نیافت؛ این بسته ادعای all-repository green ندارد. تست‌های تغییرات و digest اختصاصی اجرا شده‌اند. نتیجهٔ digest وابسته به ترتیب در گزارش تیم، در اجرای اختصاصی ما بازتولید نشد؛ عدد مبنا عوض نشده و آن ادعا نباید «حل‌شده» تلقی شود.

## تغییرات اجرایی

### Build و graphics

یک Vite build چندentry هم console و هم simulation.html را تولید می‌کند؛ build:simulation نیز همین مسیر را استفاده می‌کند تا یکی خروجی دیگری را پاک نکند. emptyOutDir=true، public assets واقعی حفظ شده و swarm.html منبع خودش را در console/public دارد. server.browser chunk از build واقعی آمده؛ packaging تمام فایل‌های خروجی لازم را شامل می‌شود. ارتقا فقط generated assets مشخص با hash مبنا را حذف می‌کند.

جست‌وجوی ارجاعات فایل: ۱۲۶ مرجع local بررسی، فایل گم‌شده صفر. هر ۱۴۵ فایل static با HTTP واقعی پاسخ ۲۰۰ داد. ۳۳ آزمون UI، typecheck/build پاس. DOM صفحه حسگر با API واقعی، اطلاعات FDC، تنظیم normalization و stop/archive بررسی شد. این تست جایگزین بازبینی چیدمان در مرورگر بومی/موبایل یا آزمون برد نیست.

### Journal و recovery

active journal به صورت segment شماره‌دار می‌چرخد؛ default threshold چهار MiB، قابل تنظیم در constructor. archives حذف نمی‌شوند و زنجیره hash/sequence هنگام replay بررسی می‌شود. سقف رشد active مساوی سقف کل مصرف دیسک نیست؛ برای archive و نگهداری بلندمدت فضای دیسک لازم است. این نسخه checkpoint/retention خودکار ندارد و تاریخچه معتبر را برای کوچک‌شدن فایل دور نمی‌ریزد.

خطای نوشتن state حافظه را commit نمی‌کند و journal_health=recovery_required ظاهر می‌شود. `journal_recover` عمل مدیریتی صریح است؛ کامل‌بودن tail، chain و config را بررسی و سپس فایل را fsync می‌کند. tail ناقص یا خراب را بی‌صدا truncate نمی‌کند. اگر write تا قبل از خطای fsync روی دیسک کامل شده باشد، recovery ممکن است آن record معتبر را adopt کند؛ state_changed این موضوع را نشان می‌دهد. قبل تکرار command پس از recovery شناسه و state آن بررسی شود.

قفل نوشتن بین‌process روی POSIX nonblocking است؛ writer قدیمی بدون replay اجازه fork زنجیره ندارد. hash chain مدرک authenticity cryptographic در برابر مهاجم دارای write access نیست.

### پل موتور و MQTT

Link اختیاری خطای قابل‌انتظار IO/validation پل را در last_error/errors ثبت می‌کند و موتور دیجیتال مستقل ادامه می‌دهد. اگر required=True یا environment_mapper داده حسگر را به جهان می‌برد، نبود داده تازه قبل از گام خطا می‌دهد؛ خطای evidence در boundary نیز پنهان نمی‌شود. خطای programming/غیرمنتظره را کورکورانه swallow نمی‌کنیم. run_ticks wrapper باید برای mapping استفاده شود.

هر MqttSwarmBridge شناسهٔ زیرساختی یکتا دارد، ثابت در reconnect همان object؛ client_id صریح هم ممکن است. caller موظف است ID صریح را میان processهای هم‌زمان تکرار نکند. تولید UUID زیرساختی در RNG علمی دخالت ندارد. callback API نسخه ۲، TLS و reconnect backoff حفظ شده‌اند. تست MQTT با extra نصب‌شده اجرا شد؛ نبود dependency فقط در test اختیاری skip می‌شود، نه در job Swarm دارای extra.

پیش‌فرض storage از CWD مستقل و در ~/.local/share/codontrace/swarm_runs است. در deployment مسیر absolute `CODONTRACE_SWARM_DIR` را تنظیم کنید؛ مسیر نسبی رد می‌شود. این مسیر باید برای user سرویس writable باشد.

### Recorder

از snapshot committed همان generation که core قبلاً ساخته استفاده می‌شود؛ snapshot/digest دوباره صرفاً برای recorder تولید نمی‌شود. تنها lineage مربوط به interval بین دو فریم serialize می‌شود. هر فریم مستقل atomic publish دارد و history کامل بازنویسی نمی‌شود.

اسکن lineage هنوز O(total lineage) است و retention snapshotهای خود core تغییر نکرده؛ رشدهای باقی‌مانده را «حل کامل performance موتور» نمی‌نامیم. benchmark سخت‌افزاری بلندمدت Orange Pi باقی است. schema/رویداد واقعی/عدم استنتاج مرگ از ناپدیدشدن حفظ شده‌اند.

## حسگرهای جنریک: مسیر واقعی، نه صرفاً نام در فهرست

نسخه ۱ بدون تغییر قرارداد قبلی کار می‌کند. نسخه ۲ با schema=`genesis_swarm_v2` در همان endpoint `/api/swarm` و MQTT route دریافت می‌شود. پنج نوع مقدار فعلی: scalar، vector با axes، waveform کوتاه با length و sample_period_us اختیاری، boolean و category. همه archive/inspection/export دارند؛ fusion و pipeline فعلی فقط scalar معتبر را می‌پذیرند.

استقلال از vendor/driver یعنی برد Wi-Fi دلخواه JSON مطابق قرارداد می‌فرستد؛ موتور درایور I2C/SPI یا firmware آن را اجرا نمی‌کند. دوربین/تصویر بزرگ، quaternion averaging، angular filtering و covariance fusion در این نسخه پیاده نشده‌اند. برای حسگر جدیدی با یکی از پنج نوع، descriptor/config کافی است؛ برای نوع پردازش تازه adapter/schema باید گسترش یابد.

descriptor اجباری v2: value_type، measurement_model (direct/derived/proxy/raw)، feature_id، source_unit و config_id. derived/proxy نیازمند model_id است. axes، coordinate_frame، waveform length/period، range و rate_hz محدود قابل تنظیم‌اند. unit/quantity channel صریح‌اند؛ تفاوت source/output unit بدون normalization رد می‌شود.

normalization: affine با scale/offset یا table با ۲..۶۴ knot و بدون extrapolation. evidence_id شواهد producer را مشخص می‌کند؛ موتور وجود/کیفیت کالیبراسیون را از یک رشته تضمین نمی‌کند. uncertainty استاندارد scalar فقط برای تبدیل affine/identity با واحد source وارد و با قدرمطلق scale تبدیل می‌شود. propagated uncertainty مدل nonlinear/table خودکار ساخته نمی‌شود.

reading v2 علاوه بر فیلدهای v1، valid/status/config_id دارد. invalid فقط null؛ صفر، NaN و last value به اسم تازه جای آن نمی‌نشیند. source_value/source_unit و sensor_descriptor/digest حفظ می‌شوند. مرجع scalar باید reference_unit برابر واحد normalized داشته باشد. metadata flat محدود برای registers/status/clock ممکن است. measurement shape/type و config قبل commit بررسی می‌شوند.

fusion همسانی feature_id، measurement_model و model_id را کنترل می‌کند؛ direct/derived یا مکان‌های نامتناسب ادغام نمی‌شوند. rate خارج قابلیت اعلام‌شده رد می‌شود. capsule/pipeline اسکالر روی vector یا category رد می‌شود.

عمل operator `configure_channel` normalization/range میزبان را transactionally تغییر می‌دهد؛ frame قدیمی و trust قبلی پاک و تا نمونه بعدی داده نامعتبر برای تحلیل باقی نمی‌ماند. این عمل firmware را reprogram نمی‌کند و ACK سخت‌افزاری ادعا ندارد. با reboot، override میزبان قدیمی پاک می‌شود تا config جدید دستگاه به اشتباه تفسیر نشود.

پنل /swarm.html metadata، نوع داده، source/normalized و رنگ محورهای vector را نشان می‌دهد؛ waveform در نمودار پنجره و boolean/category در جدول متنی وضعیت دیده می‌شوند. ویرایشگر normalization/range JSON validator دارد و پس از apply منتظر نمونه تازه است. channel حتی بدون frame جدید قابل انتخاب می‌ماند.

## اتصال FDCxCapSense خود شما

کد نسخه 0.6.13 / commit `215031db9a6bc37ac26cd1d2b6dca96bbe3b4da7` خوانده شد و host unit + smoke/contract native پاس شدند. آداپتر Python `fdc_sample` reading اصلی را می‌گیرد؛ فقط toSample کافی نیست چون raw/CAPDAC یا clock از دست می‌روند.

FDC1004/Q1: raw24 signed، capacitancePf، capdacCode/enabled، diagnosticFlags، channel/status حفظ می‌شود. مقدار نهایی pF فقط به F scale می‌شود؛ CAPDAC دوباره اعمال نمی‌شود. خطای خواندن—even اگر کتابخانه صفر placeholder بدهد—به null/invalid تبدیل می‌شود.

FDC2212/2214: rawCode، reference frequency، divider، multiplier و dataReady حفظ؛ خروجی frequency Hz با منشأ reference-clock مدل است. تبدیل capacitance از LC در این آداپتر انجام نمی‌شود، چون L/parasitic/model uncertainty لازم است. variant/channel/clock/status نامعتبر رد می‌شود.

FDC2112/2114: مسیر frequency conversion نسخه کتابخانه فعلی NotSupported است. آداپتر خروجی موفق ساختگی را رد می‌کند و وضعیت NotSupported را می‌تواند با raw metadata archive کند. درایور raw-only را اگر استفاده می‌کنید به عنوان quantity raw_code/measurement_model raw در descriptor جدا اعلام کنید؛ پشتیبانی دقیق Hz/PF را ادعا نکنید.

`fdc_decode` روی API یک preview آداپتر operator-only است؛ خودش ingest نمی‌کند. hello با channel برگشتی و reading با payload برگشتی باید ارسال شوند؛ نمونه کامل در examples/swarm_generic_sensors.py است. firmware هیچ وابستگی به کد Python ندارد و می‌تواند مستقیماً همین schema را از هر کتابخانه‌ای منتشر کند.

## اجرای نمونه

```bash
python examples/swarm_generic_sensors.py --output simulation_runs/generic_probe
```

نمونه synthetic است؛ خروجی موجود overwrite نمی‌شود. شامل FDC، vector، boolean، category، waveform، journal چرخیده و snapshot در stop است. scope این مثال integration contract است، نه اندازه‌گیری دستگاه واقعی یا کشف علمی.

## ادامه علمی در پنج فاز

۱. quantity/unit/model/type و clock/reference را برای هر خانواده قفل و validator/fault fixture اجرا کنید.
۲. trace واقعی چند device/day با raw، source/normalized، config و calibration ثبت؛ confidence heuristic را از uncertainty جدا کنید.
۳. بودجه sensing، interval و shadow guard در baseline هم‌سنگ و factorial هشت‌بازویی سنجیده شوند؛ true reference جدا و تمام نتایج منفی حفظ شوند.
۴. انتقال policy واقعاً command→ACK→processing_version جدید داشته باشد؛ کیفیت، latency، bytes واقعی و انرژی اندازه‌گیری‌شده مستقل از fitness دیجیتال گزارش شوند.
۵. آزمایش قفل‌شده روی device/day ندیده، drift/packet loss/corruption و معیارهای latency/event preservation/coverage/false rollback؛ نتیجه معتبر مثبت پذیرفته شود، threshold پس از دیدن test تغییر نکند.

منابع اولیهٔ خوانده‌شده: TI FDC1004 Rev C، TI FDC2214، IETF RFC8428 SenML، W3C SSN/SOSA، BIPM VIM calibration/uncertainty، Paho Client API و Vite emptyOutDir؛ لینک‌ها در SOURCES.md و گزارش تکمیلی همراه بسته‌اند. قرارداد الهام‌گرفته از استانداردهاست؛ بدون validator رسمی ادعای SenML conformance نداریم. اجزای روش سابقه دارند؛ نوآوری ترکیب به نتیجه آزمایش مقایسه‌ای نیاز دارد.
