# حسابرسی شواهد مدل‌های in silico در مهندسی پزشکی با نردبان اعتبار کودون‌تریس جنسیس

# Auditing In-Silico Evidence with the CodonTrace Genesis Ladder

پرواز جمیعی۱

۱پژوهشگر مستقل، مشهد، ایران، parvaz.jamie@gmail.com، ORCID: 0009-0002-9980-270X

چکیده - این ابزار بعد از اجرا مشخص می‌کند ادعا تا چه سطحی، از صفر تا پنج، با شواهد همان بسته پشتیبانی می‌شود. کودون‌تریس جنسیس اجرا را قطعی می‌کند، مداخله روی یال را ثبت می‌کند و ادعا را روی نردبان اعتبار حسابرسی می‌کند. موتور، هستهٔ اجراست و حوزه را نمی‌شناسد. پورت `DomainProfile` درگاهی است که پرونده را به بستهٔ شواهد تبدیل می‌کند. درگاه پزشکی واژگان ASME V&V 40، راهنمای FDA ۲۰۲۳، IEC 62304 و IMDRF را روی همین نردبان می‌گذارد و برچسب را به‌جای تأیید نمی‌نشاند. ارزیابی یک جفت کنترل است. HE01 کمپینی اجراشده و بازپخش‌پذیر با سی بذر جفتی است: اختلاف انرژی نسبت به کنترل ۱۶٫۴۹ و بازهٔ BCa برابر [۱۴٫۲۵، ۱۹٫۱۴] بود و حسابرس سطح ۴ داد. جدول مدل تجهیز، کنترل منفی با برچسب IEC و FDA، در سطح صفر ماند. این فاصله را هیچ برچسبی پر نمی‌کند.

کلید واژه- اعتبارسنجی in silico، حسابرسی شواهد، مدل‌سازی محاسباتی، نردبان اعتبار


## مقدمه

این ابزار بعد از اجرای یک مدل محاسباتی مشخص می‌کند نتایج تا چه سطحی، از صفر تا پنج، با شواهد بسته پشتیبانی می‌شوند. این سطح‌ها نردبان اعتبارند: پلهٔ بالاتر شاهد بیشتری می‌خواهد و تأیید تجهیز نیست. در پروندهٔ مدل محاسباتی برای تجهیز پزشکی، سؤال این است که شواهد موجود تا کجا ادعا را نگه می‌دارند. راهنمای نوامبر ۲۰۲۳ سازمان غذا و داروی آمریکا اعتبار شبیه‌سازی فیزیک‌محور را به ریسک تصمیم وصل می‌کند و مدل یادگیری ماشین مستقل را بیرون از دامنه می‌گذارد [1]. ASME V&V 40 همین نکته را با پرسش مورد علاقه، زمینهٔ کاربرد و پیامد تصمیم می‌نویسد [2]. NASA-STD-7009B هم قابلیت مدل و هم جواز انتقال نتیجه را جدا می‌خواهد [3]. پیوست چهارم قانون هوش مصنوعی اتحادیهٔ اروپا مستندسازی اعتبارسنجی را لازم کرده است [4]. هیچ‌کدام به‌تنهایی درجهٔ ادعای یک فایل پژوهشی را معلوم نمی‌کنند.

Viceconti و همکاران آزمون in silico را بر زمینهٔ کاربرد، ریسک، و زنجیرهٔ راستی‌آزمایی، اعتبارسنجی و کمی‌سازی عدم‌قطعیت گذاشته‌اند [5]. Pathmanathan و همکاران همان زنجیره را تا زیرمدل‌های آزمون بالینی in silico برده‌اند [17] و سمپوزیوم FDA/MDIC در ۲۰۲۴ اعتبار مدل را در طول عمر تجهیز جمع کرده است [18]. در بررسی ۸۵ مقالهٔ ICSE و ASE ۲۰۲۴، از پنج مصنوع اجرایی هیچ‌کدام کامل بازتولید نشد [6]. کار این مقاله این است که بعد از انتشار هم سطح ادعا معلوم بماند.

موتور مدل را گام‌به‌گام پیش می‌برد و برای پزشکی از نو نوشته نشده است. یال یک گام از مسیر علت است، مثلاً از کنش تا پیامد. ارزیابی یک جفت کنترل است. HE01 کنترل مثبت و اجراشده است و تا سطح ۴ بالا می‌رود. جدول مدل تجهیز کنترل منفی است: برچسب تنظیم‌گری دارد و شاهد اجرایی ندارد، پس در سطح صفر می‌ماند.


## پیشینه و کارهای مرتبط

درجه‌بندی اعتبار اغلب در حد راهنما مانده است. ASME VVUQ 40.1-2026 بدترین اندازهٔ سینی تیبیال را برای آزمون خستگی ISO 14879-1 مشخص می‌کند [7]. IEC 62304 ردهٔ ایمنی نرم‌افزار را A، B یا C می‌گذارد [8]. اسناد IMDRF زبان SiMD و SaMD را تثبیت کرده‌اند [9]، [10]. اینجا همان واژه‌ها روی بستهٔ شواهد اجرا می‌شوند. بستهٔ شواهد همان چیزی است که حسابرس می‌بیند: نتیجه، مداخله و بازپخش، نه نام استاندارد.

آویدا بستر برنامه‌های خودتکثیرشونده است [11] و پروندهٔ `.dat` آن از همین در خوانده می‌شود. پایداری عملکرد در محیط نامطمئن [12] با بازپخش بیت‌به‌بیت یکی نیست. توصیف مدل از پروتکل ODD است [13]. رشتهٔ `asme_vv40_passed` در پیکربندی پذیرفته نمی‌شود، چون این ابزار گواهی استاندارد صادر نمی‌کند.


## معماری سامانه


### موتور و جداسازی پورت

هسته از ژنوم، عامل، جهان و زمان‌بند ساخته شده است. تنظیم تازه با پیش‌فرض خاموش می‌آید. برای هر یال شناسه و اثرانگشت قبل و بعد ذخیره می‌شود. نسخه از پیکربندی پروژه خوانده می‌شود و داخل بسته ثابت نوشته نمی‌شود.

پورت درگاهی بیرون از موتور است. موتور نمی‌داند آزمایش پزشکی است یا زندگی مصنوعی یا سخت‌افزار. آداپتور بسته را می‌سازد و `DomainProfile` فقط نام حوزه را دارد. حوزهٔ تازه پروفایل تازه است، نه موتور دوم. پروفایل `hardware` و پورت ESP32 هم از همین درگاه می‌آیند و موتور دوم نمی‌سازند. شکل ۱ همین جدایی را نشان می‌دهد [14].

شکل ۱: معماری پورت‌ها. موتور حوزه نمی‌شناسد؛ حسابرس روی بستهٔ شواهد کار می‌کند.

حسابرسی پنج مرحله دارد: ساخت بسته، نگاشت نقش بازو، سنجش اثرانگشت، خواندن بازپخش و بازه، و برگرداندن بالاترین سطح کامل.


### حسابرس و نردبان شواهد

حسابرس شش سطح دارد و از موتور جداست. سطح ۳ مداخله یا حذف یال، کنترل منفی و بازپخش می‌خواهد. سطح ۴ بازه و حداقل شانزده بذر را هم می‌خواهد. سطح ۵ آرشیو و محدودیت نوشته‌شده را می‌افزاید. این آستانه‌ها مربوط به همین پیاده‌سازی است. آزمون وقتی بی‌اعتبار است که خود مداخله اعمال نشده باشد.


### آداپتورها

آداپتور HE01 فایل JSON را می‌خواند و بایت پرونده را عوض نمی‌کند. Avida و CSV مربوط به MABE2 از همین مسیر می‌آیند. آداپتور زیست‌پزشکی جدول امتیاز را با زمینه و ریسک مدل پر می‌کند. اتصال سخت‌افزاری **اختیاری** است. هش متن بعد از یکسان‌سازی سطر ساخته می‌شود و هش دودویی با `Path.read_bytes()` است. آزمون پیش‌فرض جایگشت علامت با Holm و بازهٔ BCa است. بوت‌استرپ studentized برای n≤۴۰ اختیاری است.


## پروفایل زیست‌پزشکی

حوزه از `DomainProfile` می‌آید: `alife`، `biomedical` و `hardware` [15]. `simd_declared` عبارت IMDRF را یادداشت می‌کند و محصول را رده‌بندی نمی‌کند. اگر مدل فیزیک‌محور اعلام نشده باشد، نسبت به راهنمای ۲۰۲۳ خارج از دامنه است. `asme_vv40_passed`، `fda_cleared`، `clinical_validated` و `iec_62304_certified` در پیکربندی قبول نمی‌شوند.

جدول ۱: نگاشت واژگان تنظیم‌گری به برچسب‌های ثبت‌شده

جدول ۲ کنترل منفی طرح است. برچسب تنظیم‌گری در بسته هست و اجرای ثبت‌شده نیست. سطح خروجی آن صفر است.

جدول ۲: کنترل منفی؛ بدون شاهد اجرایی، خروجی حسابرس سطح ۰


## ارزیابی


### کنترل مثبت: کمپین HE01

HE01 کنترل مثبت است: کمپینی اجراشده و بازپخش‌پذیر برای سوگیری منشأ، با مداخله و سی بذر جفتی. درمان با کنترل‌های محتوای تهی، کانال بسته، کانال روشن بدون سوگیری، و محتوای برخورده مقایسه می‌شود. سنجه، میانگین انرژی پایانی گیرنده در شبیه‌سازی است. برچسب داخل `results_v7.json` برابر `intervention_supported` است و درجهٔ حسابرس ۴ است.

فایل `results_v7.json` با پیشوند `28f812c5` سه مقایسه دارد [16]. نسبت به کانال روشن بدون سوگیری، اختلاف ۱۶٫۴۹، p خام ۴٫۹۹۹۷۵×۱۰⁻⁵، p هولم ۱٫۵۰×۱۰⁻⁴ و بازهٔ BCa برابر [۱۴٫۲۵، ۱۹٫۱۴] است. نسبت به کانال بسته و محتوای تهی، اختلاف ۳۰٫۶۷ و بازهٔ [۲۶٫۰۳، ۳۵٫۳۲] است. بوت‌استرپ studentized اختیاری همان سی اختلاف را حدود ۱۴٫۰۵ تا ۱۹٫۳۰ می‌گذارد و فایل v7 دست نمی‌خورد. شکل ۲ همین دو بازه را نشان می‌دهد.

شکل ۲: تفاضل میانگین انرژی و بازهٔ ۹۵٪ در ۳۰ بذر جفتی.


### کنترل منفی: جدول بدون شاهد اجرایی

جدول ۲ با زمینهٔ یک مدل تجهیز به حسابرس داده شد و شاهد اجرایی ندارد. سؤال، مجاز بودن انتخاب اندازهٔ بدترین حالت بود. آزمون ISO 14879-1 و ایمپلنت در کار نیست. تأثیر مدل ۲ و پیامد تصمیم ۳ است، پس ریسک مدل ۳ ثبت می‌شود. امتیاز درمان ۰٫۱۲، ۰٫۱۱ و ۰٫۱۳ و کنترل ۰٫۲۰، ۰٫۱۹ و ۰٫۲۱ است. برچسب‌ها `simd_declared`، ردهٔ B از IEC 62304، دستهٔ II از IMDRF و شواهد ۱، ۳ و ۸ هستند. خروجی سطح صفر بود. HE01، کنترل مثبت، به سطح ۴ می‌رسد. فاصلهٔ این دو خروجی را هیچ برچسبی پر نمی‌کند.


### نسبت این کار با V&V 40

ASME V&V 40 اعتبار مدل در یک زمینهٔ مشخص است. اینجا پرسش، زمینه، تأثیر و پیامد ثبت می‌شود و ادعای بسته درجه می‌گیرد. آزمون نیمکت بیرون از نرم‌افزار می‌ماند. کودون‌تریس جای آن آزمون را نمی‌گیرد. نسخه از پیکربندی پروژه خوانده می‌شود.


## نتیجه‌گیری

فاصلهٔ کنترل مثبت و کنترل منفی را هیچ برچسبی پر نمی‌کند. HE01، کمپین اجراشده با سی بذر و بازه، به سطح ۴ رسید. جدول مدل تجهیز، با برچسب تنظیم‌گری و بدون شاهد اجرایی، در سطح صفر ماند. موتور حوزه را نمی‌شناسد و واژگان ASME V&V 40، راهنمای FDA ۲۰۲۳، IEC 62304 و IMDRF از پورت پزشکی روی همین نردبان می‌نشیند. راهنمای ۲۰۲۳ مدل یادگیری ماشین مستقل را در بر نمی‌گیرد. گام بعدی، ارزیابی همین حسابرس روی پروفایل سخت‌افزار و نشاندن مدل فیزیک‌محور با مانیفست روی همین پورت است.

داده و کد: https://github.com/Parvaz-Jamei/codontrace-genesis — DOI: 10.5281/zenodo.20337435


## مراجع

[1] U.S. Food and Drug Administration, “Assessing the Credibility of Computational Modeling and Simulation in Medical Device Submissions,” Guidance for Industry and FDA Staff, Nov. 2023.

[2] ASME, V&V 40-2018: Assessing Credibility of Computational Modeling through Verification and Validation: Application to Medical Devices. New York, NY, USA: ASME, 2018.

[3] NASA, NASA-STD-7009B: Standard for Models and Simulations. Washington, DC, USA: NASA, 5 Mar. 2024.

[4] Regulation (EU) 2024/1689 of the European Parliament and of the Council (Artificial Intelligence Act), Annex IV.

[5] M. Viceconti, F. Pappalardo, B. Rodriguez, M. Horner, J. Bischoff, and F. Musuamba Tshinanu, “In silico trials: Verification, validation and uncertainty quantification of predictive models used in the regulatory evaluation of biomedical products,” Methods, vol. 185, pp. 120–127, 2021, doi: 10.1016/j.ymeth.2020.01.011.

[6] F. Angermeir, M. Amougou, M. Kreitz, et al., “Reflections on the reproducibility of commercial LLM performance in empirical software engineering studies,” Proc. IEEE/ACM 48th Int. Conf. Software Engineering (ICSE), 2026, doi: 10.1145/3744916.3773207.

[7] ASME, VVUQ 40.1-2026: An Example of Assessing Computational Model Credibility Using the ASME V&V 40 Risk-Based Framework: Tibial Tray Component Worst-Case Size Identification for Fatigue Testing. New York, NY, USA: ASME, 2026.

[8] IEC 62304:2006+AMD1:2015, Medical device software — Software life cycle processes. Geneva, Switzerland: IEC.

[9] IMDRF, Software as a Medical Device: Possible Framework for Risk Categorization and Corresponding Considerations, IMDRF/SaMD WG/N12 FINAL:2014.

[10] IMDRF, Characterization Considerations for Medical Device Software and Software-Specific Risk, IMDRF/SaMD WG/N81 FINAL:2025, Jan. 2025.

[11] C. Ofria and C. O. Wilke, “Avida: A software platform for research in computational evolutionary biology,” Artif. Life, vol. 10, no. 2, pp. 191–229, 2004, doi: 10.1162/106454604773563612.

[12] M. Flageat, H. Janmohamed, B. Lim, and A. Cully, “Exploring the performance-reproducibility trade-off in quality-diversity,” IEEE Trans. Evol. Comput., vol. 30, no. 1, pp. 286–295, Feb. 2026, doi: 10.1109/TEVC.2025.3548438.

[13] V. Grimm et al., “The ODD protocol for describing agent-based and other simulation models: A second update to improve clarity, replication, and structural realism,” J. Artif. Soc. Soc. Simul., vol. 23, no. 2, art. 7, 2020, doi: 10.18564/jasss.4259.

[14] CodonTrace Genesis, “Ports, not a domain-specific engine,” docs/ARCHITECTURE_PORTS.md, 2026.

[15] CodonTrace Genesis, “Biomedical engineering interface,” docs/BIOMEDICAL_ENGINEERING.md, 2026.

[16] Hard Experiment 01 confirmatory artifact, docs/hard_experiment_01/results_v7.json, digest prefix 28f812c5.

[17] P. Pathmanathan, K. Aycock, A. Badal, et al., “Credibility assessment of in silico clinical trials for medical devices,” PLoS Comput. Biol., vol. 20, no. 8, e1012289, 2024, doi: 10.1371/journal.pcbi.1012289.

[18] B. A. Craven, C. A. Basciano, P. Afshari, et al., “Computational modeling and simulation for medical devices: a summary of the 2024 FDA/MDIC Symposium,” Prog. Biomed. Eng., vol. 8, no. 1, 013001, 2026, doi: 10.1088/2516-1091/ae1c05.
