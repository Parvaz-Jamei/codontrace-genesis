import { sendServerRunAction } from "./host";
import { gateLine, nextLine, scriptLine, useBench } from "./store";

const clocks = new Map<string, number>();

export async function startJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.status === "archived") return;
  if (job.isDemo) {
    stopClock(id);
    useBench.getState().patchJob(id, { status: "running" });
    const timer = window.setInterval(() => tick(id), 700);
    clocks.set(id, timer);
    return;
  }
  try {
    await sendServerRunAction(id, "resume");
    useBench.getState().patchJob(id, { status: "running" });
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to start/resume job:", err);
  }
}

export async function pauseJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job) return;
  if (job.isDemo) {
    stopClock(id);
    if (job.status === "running") useBench.getState().patchJob(id, { status: "paused" });
    return;
  }
  try {
    await sendServerRunAction(id, "pause");
    useBench.getState().patchJob(id, { status: "paused" });
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to pause job:", err);
  }
}

export async function stopJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.status === "archived") return;
  if (job.isDemo) {
    stopClock(id);
    useBench.getState().appendLog(id, "STOP");
    useBench.getState().patchJob(id, { status: "stopped" });
    return;
  }
  try {
    await sendServerRunAction(id, "stop");
    useBench.getState().patchJob(id, { status: "stopped" });
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to stop job:", err);
  }
}

export async function restartJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.id === "engine-check-17001") return;
  if (job.isDemo) {
    stopClock(id);
    useBench.getState().patchJob(id, {
      status: "running",
      cursor: 0,
      logs: ["preview restart · exploratory · red_queen_proved=false"],
    });
    const timer = window.setInterval(() => tick(id), 700);
    clocks.set(id, timer);
    return;
  }
  try {
    await sendServerRunAction(id, "resume");
    useBench.getState().patchJob(id, { status: "running" });
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to restart job:", err);
  }
}

export async function removeJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  stopClock(id);
  if (job?.isDemo) {
    useBench.getState().removeJob(id);
    return;
  }
  try {
    await sendServerRunAction(id, "delete");
  } catch (err) {
    console.error("Failed to delete job on server:", err);
  }
  useBench.getState().removeJob(id);
  void useBench.getState().syncServerRuns();
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
