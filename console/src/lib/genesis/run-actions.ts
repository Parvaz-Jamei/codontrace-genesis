import type { Job } from "./types";
export type RunAction = "pause" | "resume" | "stop" | "restart" | "delete";
export function runActionAvailable(job: Job, action: RunAction): boolean {
  if (job.pendingAction && !(action === "stop" && ["pause", "resume"].includes(job.pendingAction))) return false;
  if (action === "delete") return !["running","queued","paused"].includes(job.status);
  if (action === "restart") return job.id !== "engine-check-17001" && (job.isDemo === true || ["stopped","failed","archived"].includes(job.status));
  if (action === "stop") return ["running","paused","queued"].includes(job.status);
  if (action === "pause") return job.status === "running" && (job.isDemo === true || job.capabilities?.pause === true);
  if (!job.isDemo && ["stopped","failed"].includes(job.status)) return runActionAvailable(job, "restart");
  return ["paused","queued","stopped","failed"].includes(job.status) && (job.isDemo === true || (job.status === "paused" ? job.capabilities?.resume === true : job.capabilities?.checkpoint_continue === true));
}
