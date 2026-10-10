import type { Job, Lang } from "./types";
export function answer(lang: Lang, _text: string, job: Job | null): string {
  if (!job)
    return lang === "fa"
      ? "یک پروژه را انتخاب کنید؛ ابزارها روی دادهٔ ذخیره‌شدهٔ همان پروژه کار می‌کنند."
      : "Select a project; tools use its recorded data.";
  const summary = job.execution?.summary as Record<string, unknown> | undefined;
  const assessment =
    job.hypothesisAssessment?.verdict ??
    summary?.scientific_assessment ??
    "UNASSESSED";
  const rationale = job.hypothesisAssessment?.rationale ?? "";
  const head =
    lang === "fa"
      ? `پروژهٔ «${job.title}» — وضعیت اجرا: ${job.status}. ارزیابی ثبت‌شده: ${String(assessment)}. ${rationale} تحلیل دادهٔ ذخیره‌شده در حالت توقف و مکث هم ممکن است؛ وضعیت اجرا نتیجهٔ علمی را تعیین نمی‌کند.`
      : `Project “${job.title}” — execution state: ${job.status}. Recorded assessment: ${String(assessment)}. ${rationale} Saved data remains analyzable while paused or stopped; execution state does not determine the scientific verdict.`;
  return [head, ...job.logs.slice(-3)].join("\n");
}
