import { useEffect, useRef } from "react";
import { mountGraphics, type StageFrame } from "@/lib/genesis/graphics";
import { jobProgress, useBench } from "@/lib/genesis/store";
import { t } from "@/lib/genesis/copy";

export function Stage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<StageFrame>({ cores: 1, progress: 0, running: false, arms: 3 });
  const host = useBench((state) => state.host);
  const job = useBench((state) => state.jobs.find((item) => item.id === state.selectedJobId) ?? null);
  frameRef.current = {
    cores: host?.cores ?? 1,
    progress: jobProgress(job),
    running: job?.status === "running",
    arms: 3,
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    return mountGraphics(canvas, () => frameRef.current);
  }, []);

  return (
    <div className="pointer-events-none absolute inset-0">
      <canvas ref={canvasRef} className="h-full w-full opacity-40" aria-hidden="true" />
    </div>
  );
}

export function StageReadout() {
  const lang = useBench((state) => state.settings.lang);
  const host = useBench((state) => state.host);
  const job = useBench((state) => state.jobs.find((item) => item.id === state.selectedJobId) ?? null);
  const text = t(lang);
  const progress = Math.min(100, Math.max(0, Math.round(jobProgress(job) * 1000) / 10));
  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex items-start justify-between gap-4 p-4 sm:p-6">
      <div>
        <p className="text-xs tracking-wide text-subtle">{text.field}</p>
        <p className="mt-1 max-w-[16rem] text-3xl font-medium tracking-tight sm:text-4xl">{job?.title ?? text.idle}</p>
        <p className="mt-2 font-mono text-sm text-muted">
          {host ? `${host.cores} cores · ${host.platform}` : text.hostWait}
        </p>
      </div>
      <div className="relative grid h-16 w-16 place-items-center text-fg" aria-hidden="true">
        <svg viewBox="0 0 36 36" className="col-start-1 row-start-1 h-16 w-16">
          <circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2" />
          <circle
            cx="18"
            cy="18"
            r="14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeDasharray={`${(progress / 100) * 88} 88`}
            strokeLinecap="round"
            transform="rotate(-90 18 18)"
          />
        </svg>
        <span className="col-start-1 row-start-1 font-mono text-xs">{progress}</span>
      </div>
    </div>
  );
}
