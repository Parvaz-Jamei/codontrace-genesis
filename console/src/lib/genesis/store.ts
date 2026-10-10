import { create } from "zustand";
import { persist } from "zustand/middleware";
import { answer } from "./analyst";
import { ARMS, contactsFor, ENGINE_COMMIT, GATE_FILES, PRESETS } from "./catalog";
import {
  checkChatStatus,
  fetchRunDetails,
  fetchSimulationRuns,
  launchServerRun,
  sendChatMessage,
} from "./host";
import type {
  BenchSettings,
  ChatMessage,
  ChatStatus,
  HostProfile,
  Job,
  JobKind,
  PresetId,
  ScriptRec,
  Thread,
  View,
} from "./types";
import { zipStore } from "./zip";

const PREVIEW_HORIZON = 2;
let isSyncing = false;

export function mapServerStatus(st: string): Job["status"] {
  switch (st.toUpperCase()) {
    case "RUNNING":
    case "STARTING":
    case "RESUMING":
      return "running";
    case "PAUSED":
    case "PAUSING":
      return "paused";
    case "STOPPED":
    case "STOPPING":
    case "CANCELLED":
    case "STALE":
      return "stopped";
    case "COMPLETED":
      return "archived";
    case "FAILED":
      return "failed";
    default:
      return "queued";
  }
}

type BenchState = {
  settings: BenchSettings;
  host: HostProfile | null;
  jobs: Job[];
  threads: Thread[];
  scripts: ScriptRec[];
  view: View;
  selectedJobId: string | null;
  activeThreadId: string | null;
  chatStatus: ChatStatus | null;
  refreshChatStatus: () => Promise<void>;
  setHost: (host: HostProfile) => void;
  setView: (view: View) => void;
  setSettings: (patch: Partial<BenchSettings>) => void;
  selectJob: (id: string | null) => void;
  openThread: (id: string) => void;
  ensureThread: (id: string, title: string, jobId: string | null) => void;
  createRun: (input: RunInput) => string | null;
  launchJob: (input: RunInput) => Promise<string | null>;
  syncServerRuns: () => Promise<void>;
  loadEngineCheck: () => void;
  patchJob: (id: string, patch: Partial<Job>) => void;
  appendLog: (id: string, line: string) => void;
  removeJob: (id: string) => void;
  addScript: (name: string, note: string, body: string) => string | null;
  send: (threadId: string, text: string) => void;
  togglePin: (threadId: string) => void;
  clearThread: (threadId: string) => void;
  clearChats: () => void;
  abortChat: (threadId?: string) => void;
  retryLastAssistant: (threadId: string) => void;
  settle: () => void;
};

export type RunInput = {
  title: string;
  kind: JobKind;
  preset: PresetId;
  seedsText: string;
  generations: number;
  workers: number;
  cores: number[];
  gateFile?: string;
  scriptName?: string;
  track?: "engine" | "reference" | "contracts";
  isDemo?: boolean;
};

const baseSettings: BenchSettings = {
  lang: "en",
  followLog: true,
  density: "comfortable",
  model: "local-analyst",
};

let activeChatAbortController: AbortController | null = null;

export const useBench = create<BenchState>()(
  persist(
    (set, get) => ({
      settings: baseSettings,
      host: null,
      jobs: [],
      threads: [],
      scripts: [],
      view: "home",
      selectedJobId: null,
      activeThreadId: null,
      chatStatus: null,
      refreshChatStatus: async () => {
        try {
          const status = await checkChatStatus();
          set({ chatStatus: status });
        } catch {
          set({ chatStatus: { mounted: false, endpoint: "", model: null, provider: "none" } });
        }
      },
      setHost: (host) => set({ host }),
      setView: (view) => set({ view }),
      setSettings: (patch) => set({ settings: { ...get().settings, ...patch } }),
      selectJob: (id) => {
        const thread = id ? get().threads.find((item) => item.jobId === id) : undefined;
        set({
          selectedJobId: id,
          activeThreadId: thread?.id ?? get().activeThreadId,
        });
      },
      openThread: (id) => {
        const thread = get().threads.find((item) => item.id === id);
        set({
          view: "chat",
          activeThreadId: id,
          selectedJobId: thread?.jobId ?? get().selectedJobId,
        });
      },
      ensureThread: (id, title, jobId) => {
        const existing = get().threads.some((item) => item.id === id);
        if (!existing) {
          set({
            threads: [
              { id, title, jobId, pinned: false, messages: [], updatedAt: Date.now() },
              ...get().threads,
            ],
          });
        }
        set({
          view: "chat",
          activeThreadId: id,
          selectedJobId: jobId ?? get().selectedJobId,
        });
      },
      createRun: (input) => {
        const job = buildJob({ ...input, isDemo: input.isDemo ?? true });
        if (!job) return null;
        const thread = emptyThread(job.id, job.title);
        set({
          jobs: [job, ...get().jobs],
          threads: [thread, ...get().threads],
          selectedJobId: job.id,
          activeThreadId: thread.id,
          view: "jobs",
        });
        return job.id;
      },
      launchJob: async (input) => {
        if (input.isDemo) {
          return get().createRun(input);
        }
        const seedsText = input.seedsText.trim()
          ? input.seedsText
          : input.preset !== "custom" && PRESETS[input.preset]
            ? PRESETS[input.preset].seeds.join(", ")
            : "16001";
        const res = await launchServerRun({
          title: input.title,
          generations: input.generations,
          workers: input.workers,
          seeds: seedsText,
          budget: 1800,
          track: input.track || "engine",
          cores: input.cores.length ? input.cores : null,
          script: input.scriptName,
          scriptName: input.scriptName,
        });
        if (!res.ok || !res.runId) {
          throw new Error(res.error || "Failed to launch run");
        }
        const runId = res.runId;
        const parsedSeeds = parseSeeds(seedsText) || [16001];
        const initialJob: Job = {
          id: runId,
          title: input.title.trim() || runId,
          kind: input.kind,
          preset: input.preset,
          seeds: parsedSeeds,
          generations: input.generations,
          previewGenerations: PREVIEW_HORIZON,
          workers: input.workers,
          cores: input.cores,
          status: "running",
          cursor: 0,
          totalSteps: 6,
          logs: [`starting execution on board/host · ${input.track || "engine"} · red_queen_proved=false`],
          createdAt: Date.now(),
          note: input.track || "engine",


          diagnostics: "not_run",
          serverManaged: true,
          isDemo: false,
          pct: 0,
          gateFile: input.gateFile,
          scriptName: input.scriptName,
        };
        const thread = emptyThread(runId, initialJob.title);
        set({
          jobs: [initialJob, ...get().jobs],
          threads: [thread, ...get().threads],
          selectedJobId: runId,
          activeThreadId: thread.id,
          view: "jobs",
        });
        void get().syncServerRuns();
        return runId;
      },
      syncServerRuns: async () => {
        if (isSyncing) return;
        isSyncing = true;
        try {
          const serverRuns = await fetchSimulationRuns();
          if (!serverRuns || !serverRuns.length) return;

          const selectedId = get().selectedJobId;
          let details: Awaited<ReturnType<typeof fetchRunDetails>> | null = null;
          if (selectedId) {
            const currentSelected = get().jobs.find((j) => j.id === selectedId);
            if (currentSelected && !currentSelected.isDemo) {
              details = await fetchRunDetails(selectedId);
            }
          }

          set((state) => {
            let updatedJobs = [...state.jobs];
            const newThreads = [...state.threads];

            for (const sRun of serverRuns) {
              const existingIndex = updatedJobs.findIndex((j) => j.id === sRun.id);
              let mappedStatus = mapServerStatus(sRun.status);
              const sRunPct = typeof sRun.pct === "number" && Number.isFinite(sRun.pct) ? sRun.pct : undefined;
              const totalSteps = sRun.totalSeeds || 12;
              const completedSeeds = typeof sRun.completedSeeds === "number" && Number.isFinite(sRun.completedSeeds)
                ? sRun.completedSeeds
                : (sRun.status === "COMPLETED" ? totalSteps : 0);

              const incomingRev = sRun.snapshot?.revision ?? (sRun as any).revision ?? 0;
              const incomingSession = sRun.snapshot?.session_id ?? (sRun as any).session_id ?? null;

              if (existingIndex >= 0) {
                const existing = updatedJobs[existingIndex];
                const existingRev = existing.snapshot?.revision ?? existing.revision ?? 0;
                const existingSession = existing.snapshot?.session_id ?? (existing as any).session_id ?? null;
                const sameSession = !incomingSession || !existingSession || incomingSession === existingSession;

                // Monotonic revision guard: Drop stale responses from the same session
                if (sameSession && existingRev > 0 && incomingRev > 0 && incomingRev < existingRev) {
                  continue;
                }

                // Optimistic action grace period: Do not regress pending UI actions
                if (existing.pendingAction && existing.pendingActionTime) {
                  const elapsedPending = Date.now() - existing.pendingActionTime;
                  if (elapsedPending < 5000) {
                    if (existing.pendingAction === "pause" && mappedStatus !== "paused") {
                      mappedStatus = existing.status;
                    } else if (existing.pendingAction === "resume" && mappedStatus !== "running") {
                      mappedStatus = existing.status;
                    } else if (existing.pendingAction === "stop" && mappedStatus !== "stopped") {
                      mappedStatus = existing.status;
                    } else {
                      existing.pendingAction = null;
                    }
                  } else {
                    existing.pendingAction = null;
                  }
                }

                const logs = sRun.recentLogs?.length ? sRun.recentLogs : existing.logs;
                updatedJobs[existingIndex] = {
                  ...existing,
                  title: sRun.title || existing.title,
                  status: mappedStatus,
                  pct: sRunPct ?? existing.pct,
                  totalSteps: sRun.totalSeeds || existing.totalSteps,
                  cursor: sRun.status === "COMPLETED" ? (sRun.totalSeeds || existing.totalSteps) : completedSeeds,
                  logs,
                  snapshot: sRun.snapshot ?? existing.snapshot,
                  capabilities: sRun.capabilities ?? existing.capabilities,
                  revision: sameSession ? Math.max(incomingRev, existingRev) : incomingRev,
                  pendingAction: existing.pendingAction,
                  pendingActionTime: existing.pendingActionTime,
                };
              } else {
                const sRunParams = (sRun as any).manifest?.params || (sRun as any).params;
                const rawSeeds = sRunParams?.seeds;
                const initialSeeds = Array.isArray(rawSeeds) && rawSeeds.length > 0 && rawSeeds.every((s: any) => typeof s === "number")
                  ? (rawSeeds as number[])
                  : [16001];
                const initialGenerations = typeof sRunParams?.generations === "number" ? sRunParams.generations : 100;
                const initialWorkers = typeof sRunParams?.workers === "number" ? sRunParams.workers : (sRun.snapshot?.workers_expected || 2);
                const initialCores = Array.isArray(sRunParams?.cores) ? (sRunParams.cores as number[]) : [];
                const initialScriptName = typeof sRunParams?.scriptName === "string" ? sRunParams.scriptName : undefined;

                const newJob: Job = {
                  id: sRun.id,
                  title: sRun.title,
                  kind: "engine",
                  preset: "custom",
                  seeds: initialSeeds,
                  generations: initialGenerations,
                  previewGenerations: 2,
                  workers: initialWorkers,
                  cores: initialCores,
                  scriptName: initialScriptName,
                  status: mappedStatus,
                  cursor: sRun.status === "COMPLETED" ? totalSteps : completedSeeds,
                  totalSteps,
                  logs: sRun.recentLogs || [],
                  createdAt: Math.round((sRun.mtime || Date.now() / 1000) * 1000),
                  note: "server run",
                  diagnostics: "not_run",
                  serverManaged: true,
                  isDemo: false,
                  pct: sRunPct,
                  snapshot: sRun.snapshot,
                  capabilities: sRun.capabilities,
                  revision: incomingRev,
                };
                updatedJobs.push(newJob);
                if (!newThreads.some((t) => t.id === `thread-${sRun.id}`)) {
                  newThreads.push(emptyThread(sRun.id, sRun.title));
                }
              }
            }

            const serverRunIds = new Set(serverRuns.map((r) => r.id));
            updatedJobs = updatedJobs.filter((j) => !j.serverManaged || serverRunIds.has(j.id));

            if (selectedId && details) {
              const idx = updatedJobs.findIndex((j) => j.id === selectedId);
              if (idx >= 0) {
                const liveLogs = details.liveLogs?.length ? details.liveLogs : details.consoleLogs || [];
                const detailsPct =
                  typeof details.pct === "number" && Number.isFinite(details.pct)
                    ? details.pct
                    : typeof details.snapshot?.progress?.pct === "number" && Number.isFinite(details.snapshot.progress.pct)
                    ? details.snapshot.progress.pct
                    : undefined;

                let manifestSeeds = updatedJobs[idx].seeds;
                let manifestGenerations = updatedJobs[idx].generations;
                let manifestWorkers = updatedJobs[idx].workers;
                let manifestCores = updatedJobs[idx].cores;
                let manifestScriptName = updatedJobs[idx].scriptName;

                const rawParams = details.manifest?.params;
                if (rawParams && typeof rawParams === "object") {
                  const p = rawParams as Record<string, unknown>;
                  if (Array.isArray(p.seeds) && p.seeds.length > 0 && p.seeds.every((s) => typeof s === "number")) {
                    manifestSeeds = p.seeds as number[];
                  }
                  if (typeof p.generations === "number") {
                    manifestGenerations = p.generations;
                  }
                  if (typeof p.workers === "number") {
                    manifestWorkers = p.workers;
                  }
                  if (Array.isArray(p.cores)) {
                    manifestCores = p.cores as number[];
                  }
                  if (typeof p.scriptName === "string") {
                    manifestScriptName = p.scriptName;
                  }
                }
                if (typeof details.manifest?.scriptName === "string" && !manifestScriptName) {
                  manifestScriptName = details.manifest.scriptName as string;
                }

                const dRev = details.snapshot?.revision ?? (details as any).revision ?? 0;
                const curRev = updatedJobs[idx].snapshot?.revision ?? updatedJobs[idx].revision ?? 0;
                const dSession = details.snapshot?.session_id ?? (details as any).session_id ?? null;
                const curSession = updatedJobs[idx].snapshot?.session_id ?? (updatedJobs[idx] as any).session_id ?? null;
                const sameSession = !dSession || !curSession || dSession === curSession;

                const bnd = details.executionBoundary ?? (details.manifest?.executionBoundary as any);

                if (sameSession && curRev > 0 && dRev > 0 && dRev < curRev) {
                  // Stale details response: do not overwrite newer list state with stale details
                  updatedJobs[idx] = {
                    ...updatedJobs[idx],
                    seeds: manifestSeeds,
                    generations: manifestGenerations,
                    workers: manifestWorkers,
                    cores: manifestCores,
                    scriptName: manifestScriptName,
                    execution: details.execution ?? updatedJobs[idx].execution,
                    diagnosticsData: details.diagnostics ?? updatedJobs[idx].diagnosticsData,
                    engineBackend: bnd?.engineBackend ?? (details.statusData?.engineBackend as string) ?? updatedJobs[idx].engineBackend,
                    isFrontierReference: Boolean(bnd?.isFrontierReference ?? details.statusData?.isFrontierReference ?? updatedJobs[idx].isFrontierReference),
                    modelScope: bnd?.modelScope ?? updatedJobs[idx].modelScope,
                    modelBoundaryNotice: bnd?.modelBoundaryNotice ?? updatedJobs[idx].modelBoundaryNotice,
                    hypothesisAssessment: details.hypothesis_assessment ?? (details.execution?.hypothesis_assessment as any) ?? updatedJobs[idx].hypothesisAssessment,
                  };
                } else {
                  let detStatus = mapServerStatus(details.status);
                  if (updatedJobs[idx].pendingAction && updatedJobs[idx].pendingActionTime) {
                    const elapsedPending = Date.now() - (updatedJobs[idx].pendingActionTime || 0);
                    if (elapsedPending < 5000) {
                      if (updatedJobs[idx].pendingAction === "pause" && detStatus !== "paused") {
                        detStatus = updatedJobs[idx].status;
                      } else if (updatedJobs[idx].pendingAction === "resume" && detStatus !== "running") {
                        detStatus = updatedJobs[idx].status;
                      } else if (updatedJobs[idx].pendingAction === "stop" && detStatus !== "stopped") {
                        detStatus = updatedJobs[idx].status;
                      }
                    }
                  }

                  updatedJobs[idx] = {
                    ...updatedJobs[idx],
                    title: details.title || updatedJobs[idx].title,
                    status: detStatus,
                    pct: detailsPct ?? updatedJobs[idx].pct,
                    seeds: manifestSeeds,
                    generations: manifestGenerations,
                    workers: manifestWorkers,
                    cores: manifestCores,
                    scriptName: manifestScriptName,
                    logs: liveLogs.length ? liveLogs : updatedJobs[idx].logs,
                    execution: details.execution,
                    diagnosticsData: details.diagnostics,
                    cursor: details.status === "COMPLETED" ? updatedJobs[idx].totalSteps : updatedJobs[idx].cursor,
                    snapshot: details.snapshot ?? updatedJobs[idx].snapshot,
                    capabilities: details.capabilities ?? updatedJobs[idx].capabilities,
                    revision: sameSession ? Math.max(dRev, curRev) : dRev,
                    engineBackend: bnd?.engineBackend ?? (details.statusData?.engineBackend as string) ?? updatedJobs[idx].engineBackend,
                    isFrontierReference: Boolean(bnd?.isFrontierReference ?? details.statusData?.isFrontierReference ?? updatedJobs[idx].isFrontierReference),
                    modelScope: bnd?.modelScope ?? updatedJobs[idx].modelScope,
                    modelBoundaryNotice: bnd?.modelBoundaryNotice ?? updatedJobs[idx].modelBoundaryNotice,
                    hypothesisAssessment: details.hypothesis_assessment ?? (details.execution?.hypothesis_assessment as any) ?? updatedJobs[idx].hypothesisAssessment,
                  };
                }
              }
            }

            return { jobs: updatedJobs, threads: newThreads };
          });
        } catch {
          // Ignore transient network errors
        } finally {
          isSyncing = false;
        }
      },
      loadEngineCheck: () => {
        if (get().jobs.some((job) => job.id === "engine-check-17001")) {
          get().selectJob("engine-check-17001");
          set({ view: "jobs" });
          return;
        }
        const job = engineCheck();
        const thread = emptyThread(job.id, job.title);
        thread.messages.push({
          id: "m-check",
          role: "assistant",
          at: job.createdAt,
          text:
            get().settings.lang === "fa"
              ? "بررسی موتور، بذر ۱۷۰۰۱، دو نسل، سه بازو. بازپخش تماس‌ها جور بود. red_queen_proved برابر false است. تشخیص‌های افق بلند در این بسته نیستند."
              : "Engine check, seed 17001, two generations, three arms. Contact replay matched. red_queen_proved is false. Long-horizon diagnostics are not in this package.",
        });
        set({
          jobs: [job, ...get().jobs],
          threads: [thread, ...get().threads],
          selectedJobId: job.id,
          activeThreadId: thread.id,
          view: "jobs",
        });
      },
      patchJob: (id, patch) =>
        set({
          jobs: get().jobs.map((job) => (job.id === id ? { ...job, ...patch } : job)),
        }),
      appendLog: (id, line) =>
        set({
          jobs: get().jobs.map((job) =>
            job.id === id ? { ...job, logs: [...job.logs, line].slice(-400) } : job,
          ),
        }),
      removeJob: (id) =>
        set({
          jobs: get().jobs.filter((job) => job.id !== id),
          selectedJobId: get().selectedJobId === id ? null : get().selectedJobId,
        }),
      addScript: (name, note, body) => {
        const clean = name.trim();
        const source = body.slice(0, 200_000);
        if (!/^[\w.-]+\.py$/.test(clean)) return null;
        const rec: ScriptRec = {
          id: uid(),
          name: clean,
          note: note.trim(),
          body: source,
          createdAt: Date.now(),
        };
        set({ scripts: [rec, ...get().scripts] });
        return rec.id;
      },
      send: (threadId, text) => {
        const trimmed = text.trim();
        if (!trimmed) return;
        const state = get();
        const thread = state.threads.find((item) => item.id === threadId);
        if (!thread) return;
        const job = thread.jobId ? state.jobs.find((item) => item.id === thread.jobId) ?? null : null;
        const at = Date.now();
        const userMsg = { id: uid(), role: "user" as const, text: trimmed, at };

        // Post user message immediately
        set({
          threads: get().threads.map((item) =>
            item.id === threadId
              ? {
                  ...item,
                  title: item.messages.length === 0 ? trimmed.slice(0, 72) : item.title,
                  updatedAt: at,
                  messages: [...item.messages, userMsg],
                  isThinking: true,
                }
              : item,
          ),
        });

        if (activeChatAbortController) {
          activeChatAbortController.abort();
        }
        activeChatAbortController = new AbortController();
        const controller = activeChatAbortController;

        const activeModel =
          state.settings.model === "board-model" && state.chatStatus?.model
            ? state.chatStatus.model
            : state.settings.model;

        let timeoutId = setTimeout(() => {
          const threads = get().threads;
          const thread = threads.find((t) => t.id === threadId);
          if (thread && thread.isThinking) {
            const noticeMsg: ChatMessage = {
              id: uid(),
              role: "assistant",
              text: state.settings.lang === "fa" ? "مدل در حال پردازش است؛ به دلیل سنگین بودن مدل ممکن است زمان ببرد. در صورت تمایل می‌توانید مدل سبک‌تری انتخاب کنید" : "The model is processing; it may take time due to its size. You can select a lighter model if you prefer.",
              at: Date.now(),
              source: "analyst",
            };
            set({
              threads: get().threads.map((item) =>
                item.id === threadId ? { ...item, messages: [...item.messages, noticeMsg] } : item
              ),
            });
          }
        }, 300000);

        sendChatMessage(
          trimmed,
          state.settings.lang,
          job,
          job?.id,
          activeModel,
          controller.signal,
        )
          .then((res) => {
            clearTimeout(timeoutId);
            if (controller.signal.aborted) return;
            const assistantMsg: ChatMessage = {
              id: uid(),
              role: "assistant" as const,
              text: res.reply,
              at: Date.now(),
              source: res.source,
              model: res.model,
              durationMs: res.duration_ms,
              fallback: res.fallback,
            };
            set({
              threads: get().threads.map((item) =>
                item.id === threadId
                  ? {
                      ...item,
                      updatedAt: Date.now(),
                      messages: [...item.messages, assistantMsg],
                      isThinking: false,
                    }
                  : item,
              ),
            });
          })
          .catch((err: unknown) => {
            clearTimeout(timeoutId);
            if (
              controller.signal.aborted ||
              (err instanceof Error && err.name === "AbortError")
            ) {
              return;
            }
            const reply = answer(state.settings.lang, trimmed, job ?? null);
            const spoken =
              state.settings.lang === "fa"
                ? `پاسخ از تحلیلگر محلی (مدل زنده در دسترس نیست):\n${reply}`
                : `Local analyst fallback (live model offline):\n${reply}`;
            const assistantMsg: ChatMessage = {
              id: uid(),
              role: "assistant" as const,
              text: spoken,
              at: Date.now(),
              source: "analyst",
              fallback: true,
            };
            set({
              threads: get().threads.map((item) =>
                item.id === threadId
                  ? {
                      ...item,
                      updatedAt: Date.now(),
                      messages: [...item.messages, assistantMsg],
                      isThinking: false,
                    }
                  : item,
              ),
            });
          });
      },
      abortChat: (threadId) => {
        if (activeChatAbortController) {
          activeChatAbortController.abort();
          activeChatAbortController = null;
        }
        const targetId = threadId ?? get().activeThreadId;
        if (targetId) {
          set({
            threads: get().threads.map((item) =>
              item.id === targetId ? { ...item, isThinking: false } : item,
            ),
          });
        }
      },
      retryLastAssistant: (threadId) => {
        const state = get();
        const thread = state.threads.find((item) => item.id === threadId);
        if (!thread) return;

        // Remove the last assistant message (the failed one)
        const msgs = [...thread.messages];
        const lastAssistantIdx = msgs.map((m) => m.role).lastIndexOf("assistant");
        if (lastAssistantIdx === -1) return;
        msgs.splice(lastAssistantIdx, 1);

        // Find the last user message to re-send
        const lastUser = [...msgs].reverse().find((m) => m.role === "user");
        if (!lastUser) return;

        const trimmed = lastUser.text;
        const job = thread.jobId ? state.jobs.find((item) => item.id === thread.jobId) ?? null : null;
        const at = Date.now();

        // Update thread: remove failed assistant reply, set isThinking
        set({
          threads: get().threads.map((item) =>
            item.id === threadId
              ? { ...item, messages: msgs, updatedAt: at, isThinking: true }
              : item,
          ),
        });

        if (activeChatAbortController) {
          activeChatAbortController.abort();
        }
        activeChatAbortController = new AbortController();
        const controller = activeChatAbortController;

        const activeModel =
          state.settings.model === "board-model" && state.chatStatus?.model
            ? state.chatStatus.model
            : state.settings.model;

        let timeoutId = setTimeout(() => {
          const threads = get().threads;
          const thread = threads.find((t) => t.id === threadId);
          if (thread && thread.isThinking) {
            const noticeMsg: ChatMessage = {
              id: uid(),
              role: "assistant",
              text: state.settings.lang === "fa" ? "مدل در حال پردازش است؛ به دلیل سنگین بودن مدل ممکن است زمان ببرد. در صورت تمایل می‌توانید مدل سبک‌تری انتخاب کنید" : "The model is processing; it may take time due to its size. You can select a lighter model if you prefer.",
              at: Date.now(),
              source: "analyst",
            };
            set({
              threads: get().threads.map((item) =>
                item.id === threadId ? { ...item, messages: [...item.messages, noticeMsg] } : item
              ),
            });
          }
        }, 300000);

        sendChatMessage(
          trimmed,
          state.settings.lang,
          job,
          job?.id,
          activeModel,
          controller.signal,
        )
          .then((res) => {
            clearTimeout(timeoutId);
            if (controller.signal.aborted) return;
            const assistantMsg: ChatMessage = {
              id: uid(),
              role: "assistant" as const,
              text: res.reply,
              at: Date.now(),
              source: res.source,
              model: res.model,
              durationMs: res.duration_ms,
              fallback: res.fallback,
            };
            set({
              threads: get().threads.map((item) =>
                item.id === threadId
                  ? { ...item, updatedAt: Date.now(), messages: [...item.messages, assistantMsg], isThinking: false }
                  : item,
              ),
            });
          })
          .catch((err: unknown) => {
            clearTimeout(timeoutId);
            if (
              controller.signal.aborted ||
              (err instanceof Error && err.name === "AbortError")
            ) {
              return;
              return;
            }
            const reply = answer(state.settings.lang, trimmed, job ?? null);
            const spoken =
              state.settings.lang === "fa"
                ? `پاسخ از تحلیلگر محلی (مدل زنده در دسترس نیست):\n${reply}`
                : `Local analyst fallback (live model offline):\n${reply}`;
            const assistantMsg: ChatMessage = {
              id: uid(),
              role: "assistant" as const,
              text: spoken,
              at: Date.now(),
              source: "analyst",
              fallback: true,
            };
            set({
              threads: get().threads.map((item) =>
                item.id === threadId
                  ? { ...item, updatedAt: Date.now(), messages: [...item.messages, assistantMsg], isThinking: false }
                  : item,
              ),
            });
          });
      },
      togglePin: (threadId) =>
        set({
          threads: get().threads.map((item) =>
            item.id === threadId ? { ...item, pinned: !item.pinned } : item,
          ),
        }),
      clearThread: (threadId) =>
        set({
          threads: get().threads.map((item) =>
            item.id === threadId ? { ...item, messages: [], updatedAt: Date.now() } : item,
          ),
        }),
      clearChats: () => set({ threads: [], activeThreadId: null }),
      settle: () =>
        set({
          jobs: get().jobs.map((job) =>
            job.status === "running" || job.status === "paused"
              ? {
                  ...job,
                  status: "stopped",
                  logs: [...job.logs, "console: this session closed before the preview clock finished"],
                }
              : job,
          ),
        }),
    }),
    {
      name: `genesis-console-${typeof window !== "undefined" ? window.location.host.replace(/:/g, "_") : "default"}`,
      partialize: (state) => ({
        settings: state.settings,
        jobs: state.jobs,
        threads: state.threads,
        scripts: state.scripts,
        // view is intentionally not persisted: app always starts on HomeView
        selectedJobId: state.selectedJobId,
        activeThreadId: state.activeThreadId,
      }),
      onRehydrateStorage: () => (state) => {
        state?.settle();
        // Always reset to home on fresh page load
        state?.setView("home");
      },
      skipHydration: true,
    },
  ),
);

export function getRunProgress(job: Job | null): number | null {
  if (!job) return null;

  if (job.serverManaged) {
    if (job.snapshot?.progress?.pct !== undefined && job.snapshot.progress.pct !== null) {
      const snapPct = Number(job.snapshot.progress.pct);
      if (Number.isFinite(snapPct)) {
        return Math.min(100, Math.max(0, Math.round(snapPct * 10) / 10));
      }
    }
    if (typeof job.pct === "number" && Number.isFinite(job.pct)) {
      return Math.min(100, Math.max(0, Math.round(job.pct * 10) / 10));
    }
    if (job.status === "archived") {
      return 100;
    }
    return null;
  }

  if (job.totalSteps > 0 && Number.isFinite(job.cursor)) {
    const raw = (job.cursor / job.totalSteps) * 100;
    if (Number.isFinite(raw)) {
      return Math.min(100, Math.max(0, Math.round(raw * 10) / 10));
    }
  }

  return null;
}

export function jobProgress(job: Job | null): number {
  const p = getRunProgress(job);
  if (p === null) return 0;
  return p / 100;
}

export function nextLine(job: Job) {
  const span = job.previewGenerations * ARMS.length;
  const seed = job.seeds[Math.floor(job.cursor / span)] ?? job.seeds[0] ?? 0;
  const rest = job.cursor % span;
  const generation = Math.floor(rest / ARMS.length) + 1;
  const arm = ARMS[rest % ARMS.length];
  return `preview phase=5 seed=${seed} arm=${arm} generation=${generation} contacts=${contactsFor(arm)} invariant=ok red_queen_proved=false`;
}

export function seedSlots(job: Job) {
  const span = Math.max(1, job.previewGenerations * ARMS.length);
  return job.seeds.map((seed, index) => {
    const start = index * span;
    const done = Math.min(span, Math.max(0, job.cursor - start));
    const state = done >= span ? "done" : done > 0 ? "active" : "idle";
    const arm = ARMS[done === 0 ? 0 : (done - 1) % ARMS.length] ?? ARMS[0];
    return { seed, done, total: span, state, arm };
  });
}

export function artifactZip(job: Job) {
  const execution = {
    complete: job.status === "archived",

    red_queen_proved: false,
    diagnostics_complete: false,
    diagnostics: job.diagnostics,
    preview_generations: job.previewGenerations,
    requested_generations: job.generations,
    seeds: job.seeds,
    commit: ENGINE_COMMIT,
  };
  return zipStore([
    { name: "live.log", text: `${job.logs.join("\n")}\n` },
    { name: "status.json", text: JSON.stringify({ status: job.status, cursor: job.cursor, total: job.totalSteps }, null, 2) },
    { name: "execution.json", text: JSON.stringify(execution, null, 2) },
  ]);
}

export function suiteZip(jobs: Job[]) {
  const newest = (file: string) => {
    let best: Job | null = null;
    for (const job of jobs) {
      if (job.kind !== "gates" || job.gateFile !== file) continue;
      if (!best || job.createdAt > best.createdAt) best = job;
    }
    return best;
  };
  const result = (file: string, count: number) => {
    const job = newest(file);
    return {
      name: `results/${file.replace(/\.py$/, "")}.json`,
      text: `${JSON.stringify(
        {
          file,
          registered: count,
          status: job?.status ?? "not_run",
          cursor: job?.cursor ?? 0,
          total: job?.totalSteps ?? count,
          red_queen_proved: false,

          pytest: false,
          log: job?.logs ?? [],
        },
        null,
        2,
      )}\n`,
    };
  };
  return zipStore([
    {
      name: "README.txt",
      text: "Genesis console preview.\nThese files are not pytest results and not a pass.\nred_queen_proved=false\n",
    },
    ...GATE_FILES.map((gate) => result(gate.file, gate.count)),
    result("all", GATE_FILES.reduce((sum, gate) => sum + gate.count, 0)),
  ]);
}

function buildJob(input: RunInput): Job | null {
  const kind = input.track === "contracts" ? "gates" : input.kind;
  const gateFile = input.track === "contracts" ? "all" : input.gateFile;
  const seeds =
    kind === "engine"
      ? input.seedsText.trim()
        ? parseSeeds(input.seedsText)
        : input.preset !== "custom"
          ? PRESETS[input.preset].seeds
          : null
      : [0];
  if (!seeds) return null;
  if (kind === "engine" && (!Number.isInteger(input.generations) || input.generations < 2)) return null;
  if (kind === "gates" && gateFile !== "all" && !GATE_FILES.some((gate) => gate.file === gateFile)) return null;
  if (kind === "script" && !input.scriptName) return null;
  const previewGenerations = kind === "engine" ? PREVIEW_HORIZON : 1;
  const steps =
    kind === "engine"
      ? seeds.length * previewGenerations * ARMS.length
      : kind === "gates"
        ? gateFile === "all"
          ? GATE_FILES.reduce((sum, gate) => sum + gate.count, 0)
          : GATE_FILES.find((gate) => gate.file === gateFile)?.count ?? 1
        : 3;
  const id = uid();
  const title =
    input.title.trim() ||
    (kind === "gates" ? (gateFile === "all" ? "All 29 gates" : gateFile || "gates") : kind === "script" ? input.scriptName || "script" : input.preset);
  return {
    id,
    title,
    kind,
    preset: input.preset,
    seeds: kind === "engine" ? seeds : [],
    generations: kind === "engine" ? input.generations : previewGenerations,
    previewGenerations,
    workers: input.workers,
    cores: input.cores,
    status: "queued",
    cursor: 0,
    totalSteps: steps,
    logs: [
      kind === "engine"
        ? `preview horizon ${previewGenerations} of ${input.generations} requested · ${input.track ?? "engine"} · exploratory · red_queen_proved=false`
        : "preview only · not a result from the board",
    ],
    createdAt: Date.now(),
    note: input.track ?? "",


    diagnostics: "not_run",
    gateFile,
    scriptName: input.scriptName,
    isDemo: Boolean(input.isDemo ?? false),
    serverManaged: Boolean(!input.isDemo),
  };
}

function engineCheck(): Job {
  const lines = [
    "phase=5 seed=17001 arm=coevolve generation=1 contacts=64 invariant=ok red_queen_proved=false",
    "phase=5 seed=17001 arm=coevolve generation=2 contacts=64 invariant=ok red_queen_proved=false",
    "phase=5 seed=17001 arm=adaptation_cut generation=1 contacts=60 invariant=ok red_queen_proved=false",
    "phase=5 seed=17001 arm=adaptation_cut generation=2 contacts=60 invariant=ok red_queen_proved=false",
    "phase=5 seed=17001 arm=constant_parasite generation=1 contacts=64 invariant=ok red_queen_proved=false",
    "phase=5 seed=17001 arm=constant_parasite generation=2 contacts=64 invariant=ok red_queen_proved=false",
    "replay matched · diagnostics not in 0.3.0b15 · red_queen_proved=false",
  ];
  return {
    id: "engine-check-17001",
    title: "Engine check 17001",
    kind: "engine",
    preset: "custom",
    seeds: [17001],
    generations: 2,
    previewGenerations: 2,
    workers: 1,
    cores: [0],
    status: "archived",
    cursor: 6,
    totalSteps: 6,
    logs: lines,
    createdAt: Date.now(),
    note: "Measured on the 0.3.0b15 engine tree. Not a campaign.",


    diagnostics: "not_run",
    isDemo: true,
    serverManaged: false,
  };
}

function emptyThread(jobId: string, title: string): Thread {
  return {
    id: `thread-${jobId}`,
    title,
    jobId,
    pinned: false,
    messages: [],
    updatedAt: Date.now(),
  };
}

function parseSeeds(text: string) {
  const parts = text.split(/[\s,]+/).filter(Boolean);
  if (parts.length === 0) return null;
  const seeds = parts.map((part) => Number(part));
  if (seeds.some((seed) => !Number.isInteger(seed) || seed < 0)) return null;
  if (new Set(seeds).size !== seeds.length) return null;
  return seeds;
}

function uid() {
  const webCrypto = globalThis.crypto;
  if (webCrypto && typeof webCrypto.randomUUID === "function") {
    return webCrypto.randomUUID();
  }
  if (webCrypto && typeof webCrypto.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    webCrypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `u-${Math.random().toString(36).slice(2, 11)}-${Date.now().toString(36)}`;
}

export function gateLine(job: Job) {
  if (job.gateFile === "all") {
    const names = GATE_FILES.flatMap((gate) => Array.from({ length: gate.count }, () => gate.file));
    return `preview ${names[job.cursor] ?? "gate"} · not a board pytest result · red_queen_proved=false`;
  }
  return `preview ${job.gateFile} item ${job.cursor + 1} · not a board pytest result · red_queen_proved=false`;
}

export function scriptLine(job: Job) {
  return `preview script ${job.scriptName} step ${job.cursor + 1} · record only · not executed`;
}
