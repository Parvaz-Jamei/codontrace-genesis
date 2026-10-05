import type { Job, Lang } from "./types";

export function answer(lang: Lang, text: string, job: Job | null): string {
  const q = text.toLowerCase();
  const proved =
    /prov|proof|اثبات|ثابت|red queen|ملکه/.test(q) && /queen|سرخ|proved|اثبات|ثابت/.test(q);
  if (proved || /red_queen_proved/.test(q)) {
    return lang === "fa"
      ? "خیر. red_queen_proved روی این اجرا false است و این کنسول آن را true نمی‌کند. سه بازو فقط برای مقایسهٔ اکتشافی کنار هم می‌مانند."
      : "No. red_queen_proved is false on this run, and this console will not set it. The three arms stay side by side as an exploratory comparison.";
  }
  if (/arm|بازو|coevolve|adaptation|constant/.test(q)) {
    return lang === "fa"
      ? "سه بازو coevolve، adaptation_cut و constant_parasite هستند. در بررسی موتور، adaptation_cut شصت تماس داشت و دو بازوی دیگر شصت‌وچهار. این عددها اثبات نیستند."
      : "The three arms are coevolve, adaptation_cut, and constant_parasite. On the engine check, adaptation_cut logged 60 contacts and the other two logged 64. Those counts are not a proof.";
  }
  if (job) {
    const tail = job.logs.slice(-3).join("\n");
    const head =
      lang === "fa"
        ? `رشتهٔ «${job.title}» وضعیت ${job.status} دارد. ${job.cursor} از ${job.totalSteps} گام پیش‌نمایش. تشخیص‌ها اجرا نشده‌اند.`
        : `Thread “${job.title}” is ${job.status}. Preview step ${job.cursor} of ${job.totalSteps}. Diagnostics were not run.`;
    return tail ? `${head}\n${tail}` : head;
  }
  return lang === "fa"
    ? "یک اجرا را انتخاب کنید تا این رشته به همان کارت بچسبد. بدون اجرا، چیزی برای تفسیر نیست."
    : "Select a run so this thread stays on that card. There is nothing to interpret until a run exists.";
}
