import { sendServerRunAction } from "./host";
import { gateLine, nextLine, scriptLine, useBench } from "./store";

const clocks = new Map<string, number>();

export async function startJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.status === "archived") return;
  if (job.isDemo) {
    stopClock(id);
    useBench.getState().patchJob(id, { status: "running", actionError: null });
    const timer = window.setInterval(() => tick(id), 700);
    clocks.set(id, timer);
    return;
  }
  const previousStatus = job.status;
  useBench.getState().patchJob(id, {
    status: "running",
    pendingAction: "resume",
    pendingActionTime: Date.now(),
    actionError: null,
  });
  try {
    await sendServerRunAction(id, "resume");
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to start/resume job:", err);
    useBench.getState().patchJob(id, {
      status: previousStatus,
      pendingAction: null,
      pendingActionTime: undefined,
      actionError: err instanceof Error ? err.message : String(err),
    });
  }
}

export async function pauseJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job) return;
  if (job.isDemo) {
    stopClock(id);
    if (job.status === "running") useBench.getState().patchJob(id, { status: "paused", actionError: null });
    return;
  }
  const previousStatus = job.status;
  useBench.getState().patchJob(id, {
    status: "paused",
    pendingAction: "pause",
    pendingActionTime: Date.now(),
    actionError: null,
  });
  try {
    await sendServerRunAction(id, "pause");
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to pause job:", err);
    useBench.getState().patchJob(id, {
      status: previousStatus,
      pendingAction: null,
      pendingActionTime: undefined,
      actionError: err instanceof Error ? err.message : String(err),
    });
  }
}

export async function stopJob(id: string) {
  const job = useBench.getState().jobs.find((item) => item.id === id);
  if (!job || job.status === "archived") return;
  if (job.isDemo) {
    stopClock(id);
    useBench.getState().appendLog(id, "STOP");
    useBench.getState().patchJob(id, { status: "stopped", actionError: null });
    return;
  }
  const previousStatus = job.status;
  useBench.getState().patchJob(id, {
    status: "stopped",
    pendingAction: "stop",
    pendingActionTime: Date.now(),
    actionError: null,
  });
  try {
    await sendServerRunAction(id, "stop");
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to stop job:", err);
    useBench.getState().patchJob(id, {
      status: previousStatus,
      pendingAction: null,
      pendingActionTime: undefined,
      actionError: err instanceof Error ? err.message : String(err),
    });
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
  if (job.status === "paused") {
    await startJob(id);
    return;
  }
  try {
    await useBench.getState().launchJob({
      kind: job.kind,
      preset: job.preset,
      seedsText: job.seeds.join(", "),
      generations: job.generations,
      workers: job.workers,
      cores: job.cores,
      title: `${job.title} (restart)`,
      gateFile: job.gateFile,
      scriptName: job.scriptName,
    });
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
    useBench.getState().removeJob(id);
    void useBench.getState().syncServerRuns();
  } catch (err) {
    console.error("Failed to delete job on server:", err);
  }
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
