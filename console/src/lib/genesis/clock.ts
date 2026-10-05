import { gateLine, nextLine, scriptLine, useBench } from "./store";

const clocks = new Map<string, number>();

export function startJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.status === "archived") return;
  stopClock(id);
  useBench.getState().patchJob(id, { status: "running" });
  const timer = window.setInterval(() => tick(id), 700);
  clocks.set(id, timer);
}

export function pauseJob(id: string) {
  stopClock(id);
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (job?.status === "running") useBench.getState().patchJob(id, { status: "paused" });
}

export function stopJob(id: string) {
  stopClock(id);
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.status === "archived") return;
  useBench.getState().appendLog(id, "STOP");
  useBench.getState().patchJob(id, { status: "stopped" });
}

export function restartJob(id: string) {
  stopClock(id);
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.id === "engine-check-17001") return;
  useBench.getState().patchJob(id, {
    status: "running",
    cursor: 0,
    logs: ["preview restart · exploratory · red_queen_proved=false"],
  });
  const timer = window.setInterval(() => tick(id), 700);
  clocks.set(id, timer);
}

export function removeJob(id: string) {
  stopClock(id);
  useBench.getState().removeJob(id);
}

function tick(id: string) {
  const { jobs, appendLog, patchJob } = useBench.getState();
  const job = jobs.find((item) => item.id === id);
  if (!job || job.status !== "running") {
    stopClock(id);
    return;
  }
  if (job.cursor >= job.totalSteps) {
    finish(id);
    return;
  }
  const line = job.kind === "engine" ? nextLine(job) : job.kind === "gates" ? gateLine(job) : scriptLine(job);
  appendLog(id, line);
  const cursor = job.cursor + 1;
  patchJob(id, { cursor, status: cursor >= job.totalSteps ? "archived" : "running" });
  if (cursor >= job.totalSteps) {
    appendLog(
      id,
      job.kind === "engine"
        ? "preview archive closed · diagnostics not run · red_queen_proved=false"
        : "preview closed · not a board result · red_queen_proved=false",
    );
    stopClock(id);
  }
}

function finish(id: string) {
  stopClock(id);
  useBench.getState().patchJob(id, { status: "archived" });
}

function stopClock(id: string) {
  const timer = clocks.get(id);
  if (timer) window.clearInterval(timer);
  clocks.delete(id);
}
