# افزودنی‌های بین‌رشته‌ای V4 — 2026-10-11

سه ابزار سبک Python بدون وابستگی محاسباتی جدید افزوده شده‌اند؛ source در `src/codontrace/swarm/decision_support.py`، اتصال در service و runtime، مثال در `examples/swarm_decision_support.py`. core فرگشت، firmware و رابط گرافیکی قبلی تغییر نکرده‌اند. این ابزارها decision support هستند؛ فرمان خودکار یا safety theorem ندارند.

| ابزار | رشته‌های مرتبط | کاربرد عملی | اتصال |
|---|---|---|---|
| residual_interval | آمار، اندازه‌شناسی، پردازش سیگنال | همراه عدد حسگر، شعاع خطای کالیبره‌شده یا «داده ناکافی» بدهد | API action: uncertainty_interval |
| freshness_plan | شبکه، Age of Information، کنترل، منابع محدود | با بودجه محدود از حسگر دارای داده کهنه و هزینه مناسب، درخواست تازه را پیشنهاد کند | node/channel واقعی، sample_ms واقعی و قابلیت sample؛ API action: freshness_plan |
| capsule_shadow | انتقال یادگیری، baseline محافظه‌کار، پایش سامانه | پیش از ارسال سیاست جدید آن را روی همان داده با قبلی مقایسه کند؛ در پنجره پس از استقرار، افت را گزارش و rollback پیشنهاد کند | API action: capsule_shadow؛ ارسال/بازگشت از مسیر command موجود و با ACK واقعی |

همچنین `freshness_schedule` محاسبه خالص روی candidateهای صریح است و `swarm_decision_report` ابزار readonly LLM برای گزارش ثبت‌شده هر run/seed است. ابزار LLM اعداد خامی از خودش برای ارزیابی نمی‌سازد؛ فقط artifact موجود را می‌خواند و synthetic بودن و hash را نشان می‌دهد.

## ۱. بازه خطا، نه confidence ساختگی

برای predictor ثابت، score کالیبراسیون `abs(prediction-reference)` و رتبه `ceil((n+1)*(1-alpha))` است. اگر رتبه از n بیشتر باشد، بازه متناهی موجود نیست؛ radius/lower/upper برابر null می‌مانند. کمبود داده را با بزرگ‌ترین خطای موجود جایگزین نمی‌کنیم. training_id و calibration_id باید متفاوت باشند؛ این چک فقط reuse آشکار را می‌گیرد و استقلال واقعی را اثبات نمی‌کند. model_id باید همان predictor و configuration ثابت را مشخص کند.

بازه روی داده زمانی خودهم‌بسته یا drift به تنهایی تضمین پوشش ندارد. alpha فقط هدف است؛ coverage_verified=false یعنی دادهٔ ارزیابی پوشش به این تابع ارائه نشده، نه اینکه یک فرضیه رد شده باشد. calibration/test باید هم‌واحد، هم‌کمیت و با مرجع مناسب باشند. این نسخه split-residual پایه است، نه ACI/AgACI یا WATCH. انتخاب alpha، مدل، quantile یا threshold بعد از دیدن test نشت داده است.

پنج فاز: (۱) مرجع و واحد و pipeline digest قفل؛ (۲) تاریخچه‌های training/calibration/test جدا؛ (۳) پوشش و پهنای بازه روی noise، drift و correlation سنجیده؛ (۴) داده node/day ندیده با reference مستقل؛ (۵) مقایسه با baseline و انتشار تمام موارد undercoverage. واحد استقلال run/device/day است، نه تک‌نمونه‌های پیوسته. برای وابستگی زمانی روش block/ACI را به عنوان گسترش جدا و با آزمون فرض‌ها بررسی کنید.

## ۲. زمان‌بندیِ کهنگی و بودجه

مدل ساده scalar random walk: variance فعلیِ تخمینی `noise_variance + q * age_ms` و بعد از رسیدن نمونه تازه `noise_variance + q * latency_ms`. کاهش مورد انتظار `success_probability * max(0, q*(age-latency))` است. انتخاب greedy بر اساس کاهش افزایشی به ازای estimated payload bytes انجام می‌شود. برای nodeهای یک group، منفعت تجمعی max است تا نسخه‌های تکراری یک اطلاعات چندبار جمع نشوند. group باید با آزمون یا شناخت سیستم توجیه شود؛ این جایگزین covariance تخمین‌زده نیست.

freshness_plan زمان‌ها را از snapshot واقعی می‌گیرد. node ناشناخته، channel معرفی‌نشده، واحد نامنطبق، node offline، نبود قابلیت sample، نمونه آینده و فرمان pending کنار گذاشته/رد می‌شوند. تابع state و journal را تغییر نمی‌دهد. در pause/stop هم تحلیل ممکن است؛ dispatch فقط از command معمول و با شرایط running انجام می‌شود. costs، q، latency و success probability مدل‌های caller هستند؛ evidence_id باید به اندازه‌گیری calibration واقعی متصل باشد.

این الگوریتم scheduler بهینه، mutual-information optimizer یا اجرای convex relaxation مقاله Boyd نیست. byte_budget بودجهٔ هزینه تخمینی payload است؛ هزینه واقعی TCP/TLS/MQTT، retransmission یا joule را تضمین نمی‌کند. اگر هزینه‌ها برابر و q=0 باشد، مدل ممکن است هیچ درخواست جدیدی پیشنهاد نکند؛ bootstrap یا health poll همچنان از oldest-first موجود انجام شود. noise variance در این مدل گزارش می‌شود؛ چون نویز همان حسگر قبل/بعد یکسان است، در gain refresh حذف می‌شود. برای انتخاب «حسگر دقیق‌تر» نیاز به مدل inference جدا است.

پنج فاز: (۱) latency/cost/q روی trace مستقل تخمین؛ (۲) oldest-first، random با بودجه هم‌سنگ و این greedy مقایسه؛ (۳) duplicate group، group اشتباه، latency و loss تغییر؛ (۴) ۳ node واقعی با ثبت دریافت و هزینه واقعی؛ (۵) مقایسه خطا–تأخیر–bytes و تحلیل مرز شکست مدل. hypothesis پیشنهادی: در drift متوسط و هزینه نامتجانس سود دارد، ولی با مدل q یا group غلط می‌تواند بدتر شود؛ هر دو جهت باید آزموده شوند.

## ۳. انتقال سیاست با shadow و پیشنهاد بازگشت

candidate و baseline روی همان values/reference پردازش می‌شوند؛ gain برابر MSE_baseline − MSE_candidate است. qualification فقط اگر gain از minimum_gain قفل‌شده بیشتر باشد، سیاست جدید پیشنهاد می‌شود. monitoring روی پنجره تازه، اگر gain کمتر از منفی maximum_regression باشد، baseline پیشنهاد و rollback_advised=true گزارش می‌شود. افت واقعی به نتیجه منفی می‌رسد؛ policy همیشه پذیرفته نمی‌شود.

این نتیجه فقط پنجرهٔ کامل همین داده است. Pipeline EMA در شروع هر window مقدار اولیه جدید می‌گیرد؛ این نسخه state پیوسته firmware یا stream ناقص را بازسازی نمی‌کند. برای مانیتور پیوسته، پنجره با warm-up/حالت واقعی تطبیق داده شود. شاخص event از raw input می‌آید، نه اثبات true-event recall؛ برای true event به برچسب مرجع مستقل نیاز است. حد آستانه و مدت پنجره باید پیش از monitoring مشخص باشد؛ تکرار تست در هر لحظه بدون تصحیح، تضمین آماری ایجاد نمی‌کند.

توصیهٔ انتقال یا rollback مساوی اجرای firmware نیست. پارامتر recommended_pipeline را از command موجود بفرستید؛ boot_id، command_id، expiry و ACK را بررسی کنید و داده با processing_version جدید را ثبت کنید. اگر ACK نرسید، «rollback انجام شد» ننویسید. این لایه از ایده baseline و پایش استقرار الهام گرفته، اما SPIBB، MDP و قضیه safe policy improvement آن را پیاده نمی‌کند.

پنج فاز: (۱) baseline/pipeline و training مستقل قفل؛ (۲) qualification بر داده validation جدا؛ (۳) آزمون تازه پس از پذیرش، بدون حذف نتایج رد؛ (۴) positive control سیاست مخرب و drift واقعی روی node/day جدید؛ (۵) ablation انتقال بدون guard، بدون rollback، با هر دو. شاخص‌ها: total error شامل دوره خرابی، زمان تشخیص، نرخ rollback بی‌مورد، منفعت انتقال، هزینه پیام و ACK واقعی.

## اجرا و API

```bash
python examples/swarm_decision_support.py --output simulation_runs/run_decision_probe --seeds 16
```

خروجی `swarm_decision_support.json` شامل مقادیر واقعی محاسبه‌شده روی ورودی مصنوعی، seed، hash و snapshot RNG است. فایل موجود overwrite نمی‌شود. LLM با swarm_decision_report و seed انتخابی جدول آن را می‌خواند؛ run scope محدود است و در stop هم آرشیو قابل خواندن است.

API همان POST `/api/swarm` با Authorization اپراتور است؛ قالب `{"action": "...", "args": {"swarm_id":"lab", ...}}`. توکن node فقط ingest است. مثال‌های کامل در `examples/swarm_decision_support_api.json` هستند. freshness_plan models را برای channelهای واقعی نظیر a/s می‌خواهد، نه نمونهٔ fabricated؛ مثال باید با nodeهای شما تطبیق داده شود.

حدود محاسبه: حداکثر ۴۰۹۶ زوج کالیبراسیون/shadow، ۲۵۶ candidate، ۳۲ درخواست، ۶۵۵۳۶ bytes تخمینی برای هر payload، یک ساعت horizon کهنگی و ۲۵۶ seed در گزارش. گروه‌بندی و costها explicit هستند. وابستگی جدیدی مانند PyTorch لازم نیست؛ bench روی Orange Pi هنوز باید اندازه‌گیری شود.

## نتیجه فعلی ابزارها

۱۶ seed مصنوعی: متوسط پوشش heldout با predictor ثابت و هدف ۹۰٪ برابر ۰٫۹۱۶۹۹۲۱۸۷۵؛ این متوسطِ نمونه است، نه guarantee یا coverage روی سنسور. نویزگیری ثابت پیشنهادی در ۱۶ window qualification بهبود داشت. positive control ramp، smoothing مخرب را در ۱۶/۱۶ تشخیص داد و پیشنهاد rollback داد. scheduler در همه نمونه‌ها سقف ۲۰۰ estimated bytes را رعایت کرد. این‌ها آزمون صحت و حساسیت ابزارند؛ نه کشف نو یا مقایسه جامع الگوریتمی.

## نوآوری پژوهشی احتمالی جنسیس

روش‌های اجزا سابقه دارند. پرسش قابل دفاع برای جنسیس: آیا تعامل «uncertainty + freshness budget + selective capsule guard» در ecology دیجیتال/شبکه حسگر، مرز قابل تکراری میان سازگاری مفید و انتقال مخرب ایجاد می‌کند؟ آزمایش factorial با سه کلید روشن/خاموش (۸ بازو) و trace/seed/budget جفت‌شده لازم است. true reference و post-adoption test مستقل باشند؛ fitness فرگشتی را با joule یا دقت حسگر هم‌معنا نگیرید. برای کشف اثر تعاملی، اثر منفرد هر جزء و interaction گزارش شود؛ انتخاب فقط بهترین بازو پس از دیدن test نوآوری محسوب نمی‌شود.

این نقطه را «اولین در جهان» نمی‌نامیم تا literature comparison اختصاصی و نتیجهٔ قفل‌شده داشته باشیم. موتور می‌تواند هم با گزارش موفق، هم با مرز شکست، دانش قابل استفاده تولید کند.

## منابع اولیه بررسی‌شده

- [Barber & Pananjady, ALT 2026](https://proceedings.mlr.press/v313/barber26a.html): وابستگی زمانی، memory predictor و کاهش اعتبار پوشش split conformal؛ در کد switch coefficient یا bound مقاله محاسبه نمی‌شود.
- [Zaffran et al., ICML 2022](https://proceedings.mlr.press/v162/zaffran22a.html): ACI/AgACI، extension آینده؛ الگوریتم فعلی آن نیست.
- [Prinster et al., WATCH, ICML 2025](https://proceedings.mlr.press/v267/prinster25a.html): پایش sequential و آزمون‌های anytime؛ threshold پنجره‌ای ما چنین theoremی ندارد.
- [Yates et al., AoI survey](https://arxiv.org/abs/2007.08564): ارتباط تازگی اطلاعات، منابع و estimation؛ age به تنهایی کیفیت یا انرژی نیست.
- [Joshi & Boyd, Sensor Selection](https://web.stanford.edu/~boyd/papers/sensor_selection.html): انتخاب حسگر مدل‌محور سابقه دارد؛ greedy proxy فعلی جایگزین پیاده‌سازی convex optimization نیست.
- [Laroche et al., SPIBB, ICML 2019](https://proceedings.mlr.press/v97/laroche19a.html): baseline-constrained safe RL؛ source الهام، نه ادعای اجرای قضیه.

قاعده تیم: قبل از تغییر، commit/candidate/config و منابع مقاله دقیق خوانده شود؛ برای هر فاز پنج دور طرح، تقسیم کار مدیر بین چهار کدر و دو تستر، دو دور نقد کد، آزمون و دو دور نقد نتیجه. نقص نرم‌افزار رفع شود؛ hypothesis منفی با تغییر آستانه مثبت نشود. شاهد خام و hash همیشه کنار گزارش باشد.
