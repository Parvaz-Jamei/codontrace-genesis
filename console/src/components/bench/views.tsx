import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import { t } from "@/lib/genesis/copy";
import { ENGINE_COMMIT, ENGINE_IDENTITY, GATE_FILES, MODELS, PRESETS } from "@/lib/genesis/catalog";
import { pauseJob, removeJob, restartJob, startJob, stopJob } from "@/lib/genesis/clock";
import { artifactZip, seedSlots, suiteZip, useBench, type RunInput } from "@/lib/genesis/store";
import { fetchRelease, pullRelease } from "@/lib/genesis/host";
import type { Job, JobStatus, PresetId, ReleaseReport } from "@/lib/genesis/types";
import { cn } from "@/lib/cn";

export function JobsView() {
  const lang = useBench((state) => state.settings.lang);
  const jobs = useBench((state) => state.jobs);
  const selected = useBench((state) => state.selectedJobId);
  const selectJob = useBench((state) => state.selectJob);
  const openThread = useBench((state) => state.openThread);
  const loadEngineCheck = useBench((state) => state.loadEngineCheck);
  const createRun = useBench((state) => state.createRun);
  const text = t(lang);
  const [openIds, setOpenIds] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "run" | "done" | "pause" | "stop">("all");
  const [sort, setSort] = useState<"new" | "old" | "status" | "name">("new");
  const counts = {
    all: jobs.length,
    run: jobs.filter((job) => job.status === "running" || job.status === "queued").length,
    done: jobs.filter((job) => job.status === "archived").length,
    pause: jobs.filter((job) => job.status === "paused").length,
    stop: jobs.filter((job) => job.status === "stopped" || job.status === "failed").length,
  };
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = jobs.filter((job) => {
      const blob = `${job.title} ${job.id} ${job.seeds.join(" ")}`.toLowerCase();
      if (q && !blob.includes(q)) return false;
      if (filter === "run") return job.status === "running" || job.status === "queued";
      if (filter === "done") return job.status === "archived";
      if (filter === "pause") return job.status === "paused";
      if (filter === "stop") return job.status === "stopped" || job.status === "failed";
      return true;
    });
    const rank = (job: Job) => (job.status === "running" ? 0 : job.status === "paused" ? 1 : 2);
    return filtered.sort((a, b) => {
      if (sort === "old") return a.createdAt - b.createdAt;
      if (sort === "name") return a.title.localeCompare(b.title);
      if (sort === "status") return rank(a) - rank(b) || b.createdAt - a.createdAt;
      return b.createdAt - a.createdAt;
    });
  }, [jobs, query, filter, sort]);

  if (jobs.length === 0) {
    return (
      <section className="grid h-full place-items-center bg-bg/80 px-6">
        <div className="w-full max-w-xl text-center">
          <h2 className="text-3xl font-medium tracking-tight sm:text-4xl">{text.emptyTitle}</h2>
          <p className="mx-auto mt-3 max-w-md text-muted">{text.emptyBody}</p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <button
              className="min-h-11 rounded-full border border-line px-4 text-sm hover:bg-surface"
              onClick={() => {
                const id = createRun(smokeInput());
                if (id) startJob(id);
              }}
            >
              {text.startSmoke}
            </button>
            <button className="min-h-11 rounded-full border border-line px-4 text-sm hover:bg-surface" onClick={loadEngineCheck}>
              {text.showCheck}
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="h-full overflow-auto bg-bg px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto flex w-full max-w-3xl min-w-0 flex-col gap-2">
        <div className="flex min-w-0 flex-col gap-2 rounded-2xl bg-white/5 p-2 sm:p-3">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={text.searchRuns}
            className="min-h-11 w-full min-w-0 rounded-lg bg-white/5 px-3 text-sm outline-none placeholder:text-subtle focus:bg-white/10"
          />
          <div className="flex flex-wrap gap-1">
            {(
              [
                ["all", text.filterAll, counts.all],
                ["run", text.filterRun, counts.run],
                ["done", text.filterDone, counts.done],
                ["pause", text.filterPause, counts.pause],
                ["stop", text.filterStop, counts.stop],
              ] as const
            ).map(([id, label, count]) => (
              <button
                key={id}
                className={cn(
                  "min-h-11 rounded-full px-3 text-sm",
                  filter === id ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10",
                )}
                aria-pressed={filter === id}
                onClick={() => setFilter(id)}
              >
                {label} {count}
              </button>
            ))}
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-1">
            <label className="inline-flex min-h-11 max-w-full min-w-0 items-center gap-2 text-sm text-muted">
              <span className="shrink-0">{text.sort}</span>
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as typeof sort)}
                className="min-h-11 min-w-0 max-w-full rounded-lg bg-transparent px-2 text-fg outline-none hover:bg-white/10"
              >
                <option value="new">{text.sortNew}</option>
                <option value="old">{text.sortOld}</option>
                <option value="status">{text.sortStatus}</option>
                <option value="name">{text.sortName}</option>
              </select>
            </label>
            <button
              className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
              onClick={() => {
                const visible = shown.map((job) => job.id);
                const allOpen = visible.length > 0 && visible.every((id) => openIds.includes(id));
                setOpenIds(allOpen ? openIds.filter((id) => !visible.includes(id)) : [...new Set([...openIds, ...visible])]);
              }}
            >
              {shown.length > 0 && shown.every((job) => openIds.includes(job.id)) ? text.collapseAll : text.expandAll}
            </button>
          </div>
        </div>
        {shown.length === 0 ? (
          <p className="text-sm text-muted">{text.noMatch}</p>
        ) : (
          shown.map((job) => {
            const open = openIds.includes(job.id);
            const pct = Math.round((job.cursor / Math.max(1, job.totalSteps)) * 100);
            return (
            <article key={job.id} className={cn("rise min-w-0 overflow-hidden rounded-2xl", selected === job.id ? "bg-white/10" : "hover:bg-white/5")}>
              <button
                className="flex w-full min-w-0 items-center gap-3 px-3 py-3 text-start sm:px-4"
                aria-expanded={open}
                onClick={() => {
                  selectJob(job.id);
                  setOpenIds(open ? openIds.filter((id) => id !== job.id) : [...openIds, job.id]);
                }}
              >
                <span className={cn("h-2 w-2 shrink-0 rounded-full", dotClass(job.status))} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="truncate font-medium">{job.title}</span>
                    <span className="shrink-0 text-xs text-subtle">{pct}%</span>
                  </span>
                  <span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-white/10">
                    <span className="meter block h-full bg-fg" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="mt-1.5 block truncate text-xs text-muted">
                    {kindLabel(text, job)} · {job.preset} · {job.seeds.length} · {job.cursor}/{job.totalSteps}
                  </span>
                </span>
                <Status job={job} />
                <ChevronDown className={cn("h-4 w-4 shrink-0 text-subtle transition-transform duration-200", open && "rotate-180")} />
              </button>
              {open ? (
                <div className="rise flex min-w-0 flex-col gap-3 px-3 pb-3 sm:px-4">
                  <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-white/10 sm:grid-cols-4">
                    <Stat k={text.requested} v={String(job.generations)} />
                    <Stat k={text.preview} v={String(job.previewGenerations)} />
                    <Stat k={text.workers} v={String(job.workers)} />
                    <Stat k={text.cores} v={job.cores.length ? job.cores.map((index) => `#${index}`).join(", ") : "—"} />
                  </dl>
                  {job.execution ? (
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl bg-white/5 px-3 py-2 text-xs text-muted">
                      <span>Status: <strong className="text-fg">{job.execution.complete ? "Complete" : "In Progress"}</strong></span>
                      {job.execution.elapsed_seconds != null ? (
                        <span>Elapsed: <strong className="text-fg">{Number(job.execution.elapsed_seconds).toFixed(1)}s</strong></span>
                      ) : null}
                      {Array.isArray(job.execution.replays) ? (
                        <span>Replays: <strong className="text-fg">{job.execution.replays.length} verified</strong></span>
                      ) : null}
                      <span className="ms-auto font-mono text-[11px] text-subtle">red_queen_proved=false</span>
                    </div>
                  ) : null}
                  {job.kind === "engine" && job.seeds.length > 0 ? <SeedMatrix job={job} /> : null}
                  {job.logs.length > 0 ? (
                    <pre className="max-h-40 min-w-0 max-w-full overflow-auto whitespace-pre-wrap break-all rounded-xl bg-bg px-3 py-2 font-mono text-xs leading-relaxed text-muted">
                      {job.logs.slice(-8).join("\n")}
                    </pre>
                  ) : null}
                  <p className="text-xs text-subtle">
                    {text.sliceNote} {text.diag} · {text.exploratory}
                  </p>
                  <div className="flex flex-wrap items-center gap-1">
                    {job.status !== "archived" && job.status !== "running" ? (
                      <button className="min-h-11 rounded-lg bg-fg px-3 text-sm text-bg" onClick={() => startJob(job.id)}>
                        {job.status === "paused" ? text.resume : job.cursor > 0 ? text.resumeRemaining : text.start}
                      </button>
                    ) : null}
                    {job.status === "running" ? (
                      <button className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => pauseJob(job.id)}>
                        {text.pause}
                      </button>
                    ) : null}
                    {job.status === "running" || job.status === "paused" ? (
                      <button className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => stopJob(job.id)}>
                        {text.stop}
                      </button>
                    ) : null}
                    <button className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => restartJob(job.id)}>
                      {text.restart}
                    </button>
                    <button className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => openThread(`thread-${job.id}`)}>
                      {text.openChat}
                    </button>
                    <button className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => downloadJob(job)}>
                      {text.download}
                    </button>
                    <button
                      className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
                      onClick={() => downloadText(`log_${job.id}.txt`, `${job.logs.join("\n")}\n`, "text/plain")}
                    >
                      {text.downloadLog}
                    </button>
                    <button className="ms-auto min-h-11 rounded-lg px-3 text-sm text-bad hover:bg-white/10" onClick={() => removeJob(job.id)}>
                      {text.remove}
                    </button>
                  </div>
                </div>
              ) : null}
            </article>
            );
          })
        )}
      </div>
    </section>
  );
}

export function ChatView() {
  const lang = useBench((state) => state.settings.lang);
  const threads = useBench((state) => state.threads);
  const activeId = useBench((state) => state.activeThreadId);
  const openThread = useBench((state) => state.openThread);
  const send = useBench((state) => state.send);
  const togglePin = useBench((state) => state.togglePin);
  const clearThread = useBench((state) => state.clearThread);
  const model = useBench((state) => state.settings.model ?? "local-analyst");
  const setSettings = useBench((state) => state.setSettings);
  const text = t(lang);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);
  const threadBody = useRef<HTMLDivElement>(null);
  const draftBox = useRef<HTMLTextAreaElement>(null);
  const nearBottom = useRef(true);
  const seenThread = useRef<string | null>(null);
  const active = threads.find((item) => item.id === activeId) ?? null;
  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...threads]
      .filter((item) => !q || item.title.toLowerCase().includes(q) || item.messages.some((message) => message.text.toLowerCase().includes(q)))
      .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt - a.updatedAt);
  }, [threads, query]);
  const lastAssistantId = active?.messages.reduce<string | null>(
    (found, message) => (message.role === "assistant" ? message.id : found),
    null,
  );
  const lastId = active?.messages.at(-1)?.id;
  const canSend = draft.trim().length > 0;

  const submit = () => {
    if (!active || !draft.trim()) return;
    nearBottom.current = true;
    send(active.id, draft);
    setDraft("");
  };

  useLayoutEffect(() => {
    const node = scroller.current;
    const threadChanged = seenThread.current !== activeId;
    seenThread.current = activeId;
    if (!node) return;
    const fresh = Date.now() - (active?.messages.at(-1)?.at ?? 0) < 2000;
    if (threadChanged || nearBottom.current || fresh) {
      node.scrollTop = node.scrollHeight;
      nearBottom.current = true;
    }
  }, [activeId, active?.messages.length, lastId]);

  useEffect(() => {
    const node = scroller.current;
    const inner = threadBody.current;
    if (!node || !inner) return;
    const observer = new ResizeObserver(() => {
      if (nearBottom.current) node.scrollTop = node.scrollHeight;
    });
    observer.observe(node);
    observer.observe(inner);
    return () => observer.disconnect();
  }, [activeId]);

  useLayoutEffect(() => {
    const node = draftBox.current;
    if (!node) return;
    node.style.height = "0px";
    const cap = Number.parseFloat(getComputedStyle(node).maxHeight);
    const next = Number.isFinite(cap) ? Math.min(node.scrollHeight, cap) : node.scrollHeight;
    node.style.height = `${next}px`;
  }, [draft, activeId]);

  return (
    <section className="flex h-full min-h-0 flex-col bg-bg/95 sm:flex-row">
      <aside className="flex w-full shrink-0 flex-col gap-2 border-b border-white/10 p-3 sm:min-h-0 sm:w-[220px] sm:max-w-[220px] sm:self-stretch sm:overflow-hidden sm:border-b-0 sm:border-e">
        <label className="block text-xs text-subtle">
          {text.searchThreads}
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="mt-1 min-h-11 w-full rounded-xl bg-white/5 px-3 text-sm text-fg outline-none placeholder:text-subtle focus:bg-white/10"
          />
        </label>
        <div className="flex gap-1 overflow-x-auto sm:min-h-0 sm:flex-1 sm:flex-col sm:overflow-x-hidden sm:overflow-y-auto">
          {shown.length === 0 ? <p className="px-2 py-2 text-sm text-muted">{text.noThreads}</p> : null}
          {shown.map((thread) => (
            <button
              key={thread.id}
              type="button"
              className={cn(
                "flex min-h-11 max-w-48 shrink-0 items-center gap-2 rounded-xl px-3 text-start text-sm sm:w-full sm:max-w-full",
                thread.id === activeId ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10",
              )}
              aria-current={thread.id === activeId ? "true" : undefined}
              onClick={() => openThread(thread.id)}
            >
              <span className="min-w-0 flex-1 truncate">{thread.title}</span>
              <span className="shrink-0 text-xs text-subtle">{thread.messages.length}</span>
            </button>
          ))}
        </div>
      </aside>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div
          ref={scroller}
          role="log"
          aria-relevant="additions"
          aria-label={text.chat}
          onScroll={(event) => {
            const node = event.currentTarget;
            nearBottom.current = node.scrollHeight - node.scrollTop - node.clientHeight <= 80;
          }}
          className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto"
        >
          <div
            ref={threadBody}
            className={cn(
              "mx-auto flex w-full max-w-2xl flex-col px-4 py-6",
              !active || active.messages.length === 0 ? "min-h-full items-center justify-center gap-4 text-center" : "gap-6",
            )}
          >
            {!active ? <p className="max-w-md text-muted">{text.chatEmpty}</p> : null}
            {active && active.messages.length === 0 ? (
              <>
                <p className="max-w-md text-muted">{text.chatEmpty}</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {[text.suggestions1, text.suggestions2, text.suggestions3].map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      className="min-h-11 rounded-full bg-white/10 px-4 text-sm hover:bg-white/15"
                      onClick={() => {
                        nearBottom.current = true;
                        send(active.id, prompt);
                      }}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </>
            ) : null}
            {active?.messages.map((message) =>
              message.role === "user" ? (
                <div key={message.id} className="flex w-full justify-end">
                  <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl bg-white/10 px-4 py-3 text-start">
                    {message.text}
                  </p>
                </div>
              ) : (
                <p key={message.id} className="w-full whitespace-pre-wrap break-words text-start leading-relaxed">
                  <Reveal text={message.text} active={message.id === lastAssistantId && Date.now() - message.at < 8000} />
                </p>
              ),
            )}
          </div>
        </div>
        {active ? (
          <form
            className="shrink-0 px-3 pb-3"
            onSubmit={(event) => {
              event.preventDefault();
              submit();
            }}
          >
            <div className="mx-auto w-full max-w-2xl rounded-2xl bg-white/5 p-2">
              <textarea
                ref={draftBox}
                value={draft}
                rows={1}
                placeholder={text.placeholder}
                aria-label={text.placeholder}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing || event.keyCode === 229) return;
                  event.preventDefault();
                  submit();
                }}
                className="max-h-40 min-h-11 w-full resize-none overflow-y-auto bg-transparent px-3 py-2 text-fg outline-none placeholder:text-subtle"
              />
              <div className="flex items-center gap-2 ps-1">
                <ChatModelSelect
                  model={model}
                  text={text}
                  className="min-w-0 flex-1"
                  onModel={(next) => setSettings({ model: next })}
                />
                <button
                  type="submit"
                  disabled={!canSend}
                  className="min-h-11 shrink-0 rounded-xl bg-fg px-4 text-sm font-medium text-bg disabled:opacity-40"
                >
                  {text.send}
                </button>
              </div>
            </div>
            <div className="mx-auto mt-1 flex w-full max-w-2xl flex-wrap gap-1">
              <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => togglePin(active.id)}>
                {active.pinned ? text.unpin : text.pin}
              </button>
              <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => clearThread(active.id)}>
                {text.clearThread}
              </button>
              <button
                type="button"
                className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
                onClick={() => downloadText(`${active.title}.json`, JSON.stringify(active, null, 2), "application/json")}
              >
                {text.exportThread}
              </button>
            </div>
          </form>
        ) : (
          <div className="shrink-0 px-3 pb-3">
            <div className="mx-auto w-full max-w-2xl">
              <ChatModelSelect model={model} text={text} onModel={(next) => setSettings({ model: next })} />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function ChatModelSelect({
  model,
  text,
  onModel,
  className,
}: {
  model: "local-analyst" | "board-model";
  text: ReturnType<typeof t>;
  onModel: (model: "local-analyst" | "board-model") => void;
  className?: string;
}) {
  return (
    <label className={cn("inline-flex min-h-11 min-w-0 items-center gap-2 text-sm text-muted", className)}>
      <span className="shrink-0">{text.model}</span>
      <select
        value={model}
        onChange={(event) => {
          const next = event.target.value;
          if (next === "local-analyst" || next === "board-model") onModel(next);
        }}
        className="min-h-11 w-full min-w-0 truncate rounded-lg bg-transparent px-2 text-fg outline-none hover:bg-white/10"
      >
        {MODELS.map((item) => (
          <option key={item.id} value={item.id}>
            {item.id === "local-analyst" ? text.modelLocal : text.modelBoard}
            {item.mounted ? "" : ` · ${text.modelMissing}`}
          </option>
        ))}
      </select>
    </label>
  );
}

export function GatesView() {
  const lang = useBench((state) => state.settings.lang);
  const jobs = useBench((state) => state.jobs);
  const createRun = useBench((state) => state.createRun);
  const ensureThread = useBench((state) => state.ensureThread);
  const text = t(lang);
  const [query, setQuery] = useState("");
  const registered = GATE_FILES.reduce((sum, gate) => sum + gate.count, 0);
  const q = query.trim().toLowerCase();
  const shown = GATE_FILES.filter((gate) => !q || gate.file.toLowerCase().includes(q));
  const newest = (file: string) => {
    let best: Job | null = null;
    for (const job of jobs) {
      if (job.gateFile !== file) continue;
      if (!best || job.createdAt > best.createdAt) best = job;
    }
    return best;
  };
  const busyJob = (file: string) => {
    let best: Job | null = null;
    for (const job of jobs) {
      if (job.gateFile !== file) continue;
      if (job.status !== "running" && job.status !== "queued") continue;
      if (!best || job.createdAt > best.createdAt) best = job;
    }
    return best;
  };
  const tone = (status: Job["status"]) =>
    status === "failed" || status === "stopped" ? "text-bad" : status === "running" ? "text-ok" : status === "paused" ? "text-warn" : "text-muted";
  const allBusy = busyJob("all");
  const launch = (gateFile: string, title: string) => {
    const id = createRun({
      title,
      kind: "gates",
      preset: "custom",
      seedsText: "",
      generations: 2,
      workers: 1,
      cores: [0],
      gateFile,
    });
    if (id) startJob(id);
  };

  return (
    <section className="h-full overflow-auto bg-bg px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto flex w-full max-w-3xl min-w-0 flex-col gap-2">
        <div className="flex min-w-0 flex-col gap-2 rounded-2xl bg-white/5 p-2 sm:p-3">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm text-muted">{text.gatesLead}</p>
              <p className="mt-1 font-mono text-xs text-subtle">
                {registered} · {GATE_FILES.length}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => saveBlob(suiteZip(jobs), "genesis-gate-results.zip")}>
                {text.downloadSuite}
              </button>
              {allBusy?.status === "running" ? (
                <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => pauseJob(allBusy.id)}>
                  {text.pause}
                </button>
              ) : null}
              {allBusy && (allBusy.status === "running" || allBusy.status === "paused") ? (
                <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => stopJob(allBusy.id)}>
                  {text.stop}
                </button>
              ) : null}
              {allBusy?.status === "paused" ? (
                <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => startJob(allBusy.id)}>
                  {text.resume}
                </button>
              ) : null}
              <button
                type="button"
                disabled={Boolean(allBusy)}
                className="min-h-11 rounded-lg bg-fg px-3 text-sm text-bg disabled:opacity-40"
                onClick={() => {
                  if (allBusy) return;
                  launch("all", text.runAll);
                }}
              >
                {text.runAll}
              </button>
            </div>
          </div>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={text.gateKind}
            aria-label={text.gates}
            className="min-h-11 w-full min-w-0 rounded-lg bg-white/5 px-3 text-sm outline-none placeholder:text-subtle focus:bg-white/10"
          />
        </div>
        {shown.length === 0 ? (
          <p className="text-sm text-muted">{text.noMatch}</p>
        ) : (
          shown.map((gate) => {
            const job = newest(gate.file);
            const busy = busyJob(gate.file);
            return (
              <article
                key={gate.file}
                className={cn("rise min-w-0 overflow-hidden rounded-2xl", busy ? "bg-white/10" : "hover:bg-white/5")}
              >
                <div className="flex min-w-0 flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center sm:px-4">
                  <div className="min-w-0 flex-1">
                    <h3 className="break-all font-mono text-sm">{gate.file}</h3>
                    {job ? (
                      <>
                        <p className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                          {job.status === "running" ? <span className="live-dot shrink-0" aria-hidden /> : null}
                          <span className="text-muted">
                            {gate.count} · {job.cursor}/{job.totalSteps}
                          </span>
                          <span className={cn("font-medium", tone(job.status))}>{labelStatus(text, job.status)}</span>
                        </p>
                        <p className="mt-1 text-xs text-subtle">{text.sliceNote}</p>
                      </>
                    ) : (
                      <p className="mt-1 text-sm text-muted">
                        {gate.count} · {text.notRun}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {job && job.status !== "archived" && job.status !== "running" ? (
                      <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => startJob(job.id)}>
                        {job.status === "paused" ? text.resume : text.start}
                      </button>
                    ) : null}
                    {job?.status === "running" ? (
                      <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => pauseJob(job.id)}>
                        {text.pause}
                      </button>
                    ) : null}
                    {job && (job.status === "running" || job.status === "paused") ? (
                      <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => stopJob(job.id)}>
                        {text.stop}
                      </button>
                    ) : null}
                    {job && (job.status === "archived" || job.status === "stopped") ? (
                      <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => restartJob(job.id)}>
                        {text.restart}
                      </button>
                    ) : null}
                    {job ? (
                      <button type="button" className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10" onClick={() => downloadJob(job)}>
                        {text.download}
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
                      onClick={() => ensureThread(`gate-${gate.file}`, gate.file, null)}
                    >
                      {text.openGateChat}
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(busy)}
                      className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10 disabled:opacity-40"
                      onClick={() => {
                        if (busy) return;
                        launch(gate.file, gate.file);
                      }}
                    >
                      {text.previewFile}
                    </button>
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}

export function ScriptsView() {
  const lang = useBench((state) => state.settings.lang);
  const scripts = useBench((state) => state.scripts);
  const addScript = useBench((state) => state.addScript);
  const createRun = useBench((state) => state.createRun);
  const text = t(lang);
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState("");
  return (
    <section className="h-full overflow-auto bg-bg px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto flex w-full max-w-3xl min-w-0 flex-col gap-4">
        <p className="text-muted">{text.scriptsLead}</p>
        <form
          className="flex flex-col gap-2 rounded-2xl bg-white/5 p-4"
          onSubmit={(event) => {
            event.preventDefault();
            const id = addScript(name, note, body);
            if (!id) {
              setError(text.errorScript);
              return;
            }
            setError("");
            setName("");
            setNote("");
            setBody("");
          }}
        >
          <label className="text-sm text-muted">
            {text.scriptName}
            <input value={name} onChange={(event) => setName(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3" />
          </label>
          <label className="text-sm text-muted">
            {text.upload}
            <input
              type="file"
              accept=".py,text/x-python"
              className="mt-1 block min-h-11 w-full rounded-lg bg-white/5 px-3 text-sm"
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (!file) return;
                if (file.size > 200_000) {
                  setError(text.tooBig);
                  return;
                }
                const base = file.name.split(/[/\\]/).pop() ?? "";
                void file.text().then((source) => {
                  setName(base);
                  setBody(source.slice(0, 200_000));
                  setError("");
                });
              }}
            />
          </label>
          <label className="text-sm text-muted">
            {text.scriptNote}
            <input value={note} onChange={(event) => setNote(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3" />
          </label>
          {body ? <p className="text-xs text-subtle">{body.length} · {text.stored}</p> : null}
          {error ? <p className="text-sm text-bad">{error}</p> : null}
          <button className="min-h-11 self-start rounded-lg bg-fg px-4 text-sm text-bg" type="submit">
            {text.addScript}
          </button>
        </form>
        {scripts.map((script) => (
          <article key={script.id} className="rounded-2xl bg-white/5 px-4 py-3">
            <h3 className="font-mono text-sm">{script.name}</h3>
            <p className="text-sm text-muted">{script.note}</p>
            <p className="mt-1 text-xs text-subtle">{(script.body ?? "").length} · {text.stored}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              <button
                type="button"
                className="min-h-11 rounded-lg bg-fg px-3 text-sm text-bg"
                onClick={() => {
                  const id = createRun({
                    title: script.name,
                    kind: "script",
                    preset: "custom",
                    seedsText: "",
                    generations: 2,
                    workers: 1,
                    cores: [0],
                    scriptName: script.name,
                  });
                  if (id) startJob(id);
                }}
              >
                {text.previewScript}
              </button>
              <button
                type="button"
                className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
                onClick={() => downloadText(script.name, script.body ?? "", "text/x-python")}
              >
                {text.download}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function HostView() {
  const lang = useBench((state) => state.settings.lang);
  const host = useBench((state) => state.host);
  const text = t(lang);
  if (!host) {
    return (
      <section className="h-full overflow-auto bg-bg px-4 py-6 sm:px-6 sm:py-8">
        <p className="mx-auto w-full max-w-3xl text-muted">{text.hostWait}</p>
      </section>
    );
  }
  const memoryKnown = host.memoryMb > 0;
  const used = memoryKnown ? Math.max(0, host.memoryMb - host.freeMb) : 0;
  const pct = memoryKnown ? Math.min(100, Math.round((used / host.memoryMb) * 100)) : 0;
  const loadKnown = host.platform !== "win32";
  const loadPct = loadKnown && host.cores > 0 ? Math.min(100, (host.load1 / host.cores) * 100) : 0;
  const aboveCores = loadKnown && host.load1 > host.cores;
  return (
    <section className="h-full overflow-auto bg-bg px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto grid w-full max-w-3xl min-w-0 grid-cols-1 gap-2 sm:grid-cols-2">
        <article className="min-w-0 rounded-2xl bg-white/5 p-4 sm:col-span-2 sm:p-5">
          <h3 className="text-sm text-muted">{text.platform}</h3>
          <p className="mt-1 break-words font-medium">
            {host.platform} · {host.arch} · {host.hostname}
          </p>
          <p className="mt-2 text-sm text-muted">{host.source === "host" ? text.hostSource : text.browserSource}</p>
        </article>
        <article className="min-w-0 rounded-2xl bg-white/5 p-4 sm:col-span-2 sm:p-5">
          <div className="flex min-w-0 items-center gap-4">
            {memoryKnown ? <MemoryRing pct={pct} /> : null}
            <div className="min-w-0 flex-1">
              <h3 className="text-sm text-muted">{text.memory}</h3>
              <p className="mt-1 font-mono text-sm">{memoryKnown ? `${used} / ${host.memoryMb} MB · ${pct}%` : "—"}</p>
              {memoryKnown ? (
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10" aria-hidden>
                  <div className="meter h-full bg-fg" style={{ width: `${pct}%` }} />
                </div>
              ) : null}
            </div>
          </div>
        </article>
        <article className="min-w-0 rounded-2xl bg-white/5 p-4">
          <h3 className="text-sm text-muted">{text.load}</h3>
          {loadKnown ? (
            <>
              <p className="mt-1 font-mono text-sm">
                {host.load1} / {host.cores}
              </p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10" aria-hidden>
                <div className="meter h-full bg-fg" style={{ width: `${loadPct}%` }} />
              </div>
              {aboveCores ? (
                <p className="mt-2 text-sm text-muted">
                  {text.load} {host.load1} {">"} {host.cores}
                </p>
              ) : null}
            </>
          ) : (
            <>
              <p className="mt-1 font-mono text-sm">—</p>
              <p className="mt-2 text-sm text-subtle">{text.notReported}</p>
            </>
          )}
        </article>
        <article className="min-w-0 rounded-2xl bg-white/5 p-4">
          <h3 className="text-sm text-muted">{text.temp}</h3>
          <p className="mt-1 font-mono text-sm">{host.tempC === null ? "—" : `${host.tempC}°C`}</p>
          {host.tempC === null && host.platform !== "linux" ? <p className="mt-2 text-sm text-subtle">{text.notReported}</p> : null}
        </article>
        <article className="min-w-0 rounded-2xl bg-white/5 p-4 sm:col-span-2 sm:p-5">
          <h3 className="text-sm text-muted">{text.recommend}</h3>
          <p className="mt-1 font-mono text-sm">{host.recommendedWorkers}</p>
          <p className="mt-2 text-sm text-muted">{text.runnerCap}</p>
        </article>
        <article className="min-w-0 rounded-2xl bg-white/5 p-4 sm:col-span-2 sm:p-5">
          <h3 className="text-sm text-muted">{text.cores}</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {Array.from({ length: host.cores }, (_, index) => (
              <span
                key={index}
                className={cn(
                  "grid h-11 w-11 max-w-full place-items-center rounded-lg font-mono text-sm",
                  index < host.recommendedWorkers ? "bg-white/10 text-fg" : "bg-bg text-muted",
                )}
              >
                {index}
              </span>
            ))}
          </div>
        </article>
        <ReleaseCard identity={`${host.packageVersion ?? ENGINE_IDENTITY} · ${ENGINE_COMMIT}`} />
      </div>
    </section>
  );
}

function ReleaseCard({ identity }: { identity: string }) {
  const text = t(useBench((state) => state.settings.lang));
  const [report, setReport] = useState<ReleaseReport | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let gone = false;
    const load = (refresh = false) => {
      fetchRelease(refresh)
        .then((next) => {
          if (!gone) setReport(next);
        })
        .catch(() => {
          if (!gone) setReport(null);
        });
    };
    load(false);
    const timer = window.setInterval(() => load(false), 60_000);
    return () => {
      gone = true;
      window.clearInterval(timer);
    };
  }, []);
  const current = report?.currentVersion ? `${report.currentVersion}${report.currentCommit ? ` · ${report.currentCommit}` : ""}` : identity;
  return (
    <article className="min-w-0 rounded-2xl bg-white/5 p-4 sm:col-span-2 sm:p-5">
      <h3 className="text-sm font-medium">{text.release}</h3>
      <p className="mt-2 text-sm text-muted">{text.releaseNote}</p>
      <p className="mt-2 break-all font-mono text-sm">{current}</p>
      <p className="mt-3 text-sm text-muted">{text.releaseLatest}</p>
      <p className="mt-1 break-all font-mono text-sm">
        {report?.checking && !report.latestVersion
          ? text.releaseChecking
          : report?.latestVersion
            ? `${report.latestVersion}${report.latestCommit ? ` · ${report.latestCommit}` : ""}`
            : report?.error
              ? text.releaseFailed
              : "—"}
      </p>
      {report?.updateAvailable ? (
        <p className="mt-2 text-sm text-fg">{report.releaseAhead ? text.releaseAvailable : text.releaseBehind}</p>
      ) : report?.latestVersion ? (
        <p className="mt-2 text-sm text-muted">{text.releaseUpToDate}</p>
      ) : null}
      {report?.error && !report.latestVersion ? <p className="mt-2 text-sm text-subtle">{text.releaseFailed}</p> : null}
      <p className="mt-2 text-sm text-subtle">{text.releaseReadOnly}</p>
      {note ? <p className="mt-2 text-sm text-muted">{note}</p> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            fetchRelease(true)
              .then((next) => {
                setReport(next);
                setNote("");
              })
              .catch(() => setNote(text.releaseFailed))
              .finally(() => setBusy(false));
          }}
        >
          {text.releaseCheck}
        </button>
        {report?.checkout && report.updateAvailable ? (
          <button
            type="button"
            className="min-h-11 rounded-lg bg-white/10 px-3 text-sm"
            disabled={busy}
            onClick={() => {
              if (!window.confirm(text.releaseConfirm)) return;
              setBusy(true);
              pullRelease()
                .then((result) => setNote(result.message))
                .catch(() => setNote(text.releaseFailed))
                .finally(() => setBusy(false));
          }}
          >
            {text.releaseUpdate}
          </button>
        ) : null}
        {report?.htmlUrl ? (
          <a className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm text-muted hover:bg-white/10" href={report.htmlUrl} target="_blank" rel="noreferrer">
            {text.releaseOpen}
          </a>
        ) : null}
      </div>
    </article>
  );
}

function MemoryRing({ pct }: { pct: number }) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.min(100, Math.max(0, pct)) / 100);
  return (
    <svg viewBox="0 0 44 44" className="h-12 w-12 shrink-0" aria-hidden>
      <circle cx="22" cy="22" r={radius} fill="none" stroke="currentColor" strokeWidth="4" className="text-white/10" />
      <circle
        cx="22"
        cy="22"
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        className="meter-ring text-fg"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform="rotate(-90 22 22)"
      />
    </svg>
  );
}

export function SettingsView() {
  const settings = useBench((state) => state.settings);
  const setSettings = useBench((state) => state.setSettings);
  const threads = useBench((state) => state.threads);
  const clearChats = useBench((state) => state.clearChats);
  const installed = useBench((state) => state.host?.packageVersion);
  const text = t(settings.lang);
  useEffect(() => {
    document.documentElement.dataset.density = settings.density;
  }, [settings.density]);
  return (
    <section className="h-full overflow-auto bg-bg px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto w-full max-w-3xl min-w-0">
        <Accordion.Root
          type="multiple"
          defaultValue={["lang", "log"]}
          dir={settings.lang === "fa" ? "rtl" : "ltr"}
          className="flex min-w-0 flex-col gap-2"
        >
          <SettingSection value="lang" title={text.settingsLang}>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                aria-pressed={settings.lang === "en"}
                className={cn("min-h-11 rounded-lg px-3 text-sm", settings.lang === "en" ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10")}
                onClick={() => setSettings({ lang: "en" })}
              >
                {text.english}
              </button>
              <button
                type="button"
                aria-pressed={settings.lang === "fa"}
                className={cn("min-h-11 rounded-lg px-3 text-sm", settings.lang === "fa" ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10")}
                onClick={() => setSettings({ lang: "fa" })}
              >
                {text.persian}
              </button>
            </div>
          </SettingSection>
          <SettingSection value="log" title={text.settingsLog}>
            <label className="flex min-h-11 items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="size-4 shrink-0"
                checked={settings.followLog}
                onChange={(event) => setSettings({ followLog: event.target.checked })}
              />
              {text.followToggle}
            </label>
            <p className="mt-3 text-sm text-muted">{text.density}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                aria-pressed={settings.density === "comfortable"}
                className={cn(
                  "min-h-11 rounded-lg px-3 text-sm",
                  settings.density === "comfortable" ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10",
                )}
                onClick={() => setSettings({ density: "comfortable" })}
              >
                {text.comfortable}
              </button>
              <button
                type="button"
                aria-pressed={settings.density === "compact"}
                className={cn(
                  "min-h-11 rounded-lg px-3 text-sm",
                  settings.density === "compact" ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10",
                )}
                onClick={() => setSettings({ density: "compact" })}
              >
                {text.compact}
              </button>
            </div>
          </SettingSection>
          <SettingSection value="engine" title={text.settingsEngine}>
            <p className="break-all font-mono text-sm">
              {installed ?? ENGINE_IDENTITY} · {ENGINE_COMMIT}
            </p>
            <p className="mt-2 text-sm text-muted">{text.ceilingBody}</p>
          </SettingSection>
          <SettingSection value="data" title={text.settingsData}>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="min-h-11 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
                onClick={() => downloadText("genesis-chats.json", JSON.stringify(threads, null, 2), "application/json")}
              >
                {text.exportAll}
              </button>
              <button
                type="button"
                className="min-h-11 rounded-lg px-3 text-sm text-bad hover:bg-white/10"
                onClick={() => {
                  if (window.confirm(text.clearChats)) clearChats();
                }}
              >
                {text.clearChats}
              </button>
            </div>
          </SettingSection>
        </Accordion.Root>
      </div>
    </section>
  );
}

export function NewRunDialog({ onClose }: { onClose: () => void }) {
  const lang = useBench((state) => state.settings.lang);
  const host = useBench((state) => state.host);
  const launchJob = useBench((state) => state.launchJob);
  const text = t(lang);
  const cores = Math.max(1, host?.cores ?? 4);
  const opened = pinPreset("smoke", cores);
  const [kind, setKind] = useState<RunInput["kind"]>("engine");
  const [preset, setPreset] = useState<RunInput["preset"]>("smoke");
  const [seedsText, setSeedsText] = useState(opened.seedsText);
  const [generations, setGenerations] = useState(opened.generations);
  const [workers, setWorkers] = useState(opened.workers);
  const [picked, setPicked] = useState<number[]>(opened.cores);
  const [gateFile, setGateFile] = useState<string>(GATE_FILES[0].file);
  const [scriptName, setScriptName] = useState("check.py");
  const [title, setTitle] = useState("");
  const [track, setTrack] = useState<NonNullable<RunInput["track"]>>("engine");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  return (
    <dialog
      ref={ref}
      aria-labelledby="new-run-dialog-title"
      className="m-auto w-[min(100%,36rem)] max-w-full overflow-hidden rounded-2xl bg-[#101218] text-fg backdrop:bg-black/70 outline-none focus:outline-none"
      onClose={onClose}
    >
      <form
        className="grid max-h-[min(100dvh,40rem)] grid-rows-[minmax(0,1fr)_auto] outline-none focus:outline-none"
        onSubmit={async (event) => {
          event.preventDefault();
          const effectiveKind = track === "contracts" ? "gates" : kind;
          const effectiveGate = track === "contracts" ? "all" : gateFile;
          const message = validate(
            { title, kind: effectiveKind, preset, seedsText, generations, workers, cores: picked, gateFile: effectiveGate, scriptName, track },
            text,
          );
          if (message) {
            setError(message);
            return;
          }
          setBusy(true);
          try {
            const id = await launchJob({
              title,
              kind: effectiveKind,
              preset,
              seedsText,
              generations,
              workers,
              cores: picked,
              gateFile: effectiveGate,
              scriptName,
              track,
            });
            if (!id) {
              setError(text.errorSeeds);
              setBusy(false);
              return;
            }
            ref.current?.close();
          } catch (err: unknown) {
            setError(err instanceof Error ? err.message : String(err));
            setBusy(false);
          }
        }}
      >
        <div className="flex min-h-0 flex-col gap-3 overflow-y-auto px-5 pt-5 outline-none focus:outline-none">
        <h2 id="new-run-dialog-title" className="text-lg font-medium">{text.newRun}</h2>
        <p className="text-sm text-muted">{text.formHint}</p>
        <label className="text-sm text-muted">
          {text.title}
          <input value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3 text-fg" />
        </label>
        <label className="text-sm text-muted">
          {text.kind}
          <select value={kind} onChange={(event) => setKind(event.target.value as RunInput["kind"])} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3">
            <option value="engine">{text.engine}</option>
            <option value="gates">{text.gateKind}</option>
            <option value="script">{text.scriptKind}</option>
          </select>
        </label>
        <div>
          <p className="text-sm text-muted">{text.track}</p>
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {(
              [
                ["engine", text.trackEngine],
                ["reference", text.trackReference],
                ["contracts", text.trackContracts],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={cn("min-h-11 rounded-lg px-3 text-start text-sm", track === id ? "bg-white/10 text-fg" : "bg-white/5 text-muted")}
                onClick={() => {
                  setTrack(id);
                  if (id === "contracts") setKind("gates");
                  else setKind("engine");
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        {track !== "contracts" && kind === "engine" ? (
          <>
            <div>
              <p className="text-sm text-muted">{text.preset}</p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {(["smoke", "standard", "overnight", "expedition", "custom"] as const).map((id) => (
                  <button
                    key={id}
                    type="button"
                    className={cn("min-h-11 rounded-lg px-3 text-start text-sm", preset === id ? "bg-white/10 text-fg" : "bg-white/5 text-muted")}
                    onClick={() => {
                      setPreset(id);
                      if (id === "custom") return;
                      const next = pinPreset(id, cores);
                      setSeedsText(next.seedsText);
                      setGenerations(next.generations);
                      setWorkers(next.workers);
                      setPicked(next.cores);
                    }}
                  >
                    {id}
                  </button>
                ))}
              </div>
            </div>
            <label className="text-sm text-muted">
              {text.seeds}
              <input
                value={seedsText}
                onChange={(event) => {
                  setPreset("custom");
                  setSeedsText(event.target.value);
                }}
                className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3"
              />
            </label>
            <label className="text-sm text-muted">
              {text.generations}
              <input
                type="number"
                min={2}
                value={generations}
                onChange={(event) => {
                  setPreset("custom");
                  setGenerations(Number(event.target.value));
                }}
                className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3"
              />
            </label>
          </>
        ) : null}
        {kind === "gates" ? (
          <label className="text-sm text-muted">
            {text.gateKind}
            <select value={gateFile} onChange={(event) => setGateFile(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3">
              {GATE_FILES.map((gate) => (
                <option key={gate.file} value={gate.file}>
                  {gate.file}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        {kind === "script" ? (
          <label className="text-sm text-muted">
            {text.scriptName}
            <input value={scriptName} onChange={(event) => setScriptName(event.target.value)} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3" />
          </label>
        ) : null}
        <label className="text-sm text-muted">
          {text.workers}
          <input
            type="number"
            min={1}
            max={4}
            value={workers}
            onChange={(event) => setWorkers(Number(event.target.value))}
            className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3"
          />
        </label>
        <div>
          <p className="text-sm text-muted">{text.cores}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {Array.from({ length: cores }, (_, index) => {
              const on = picked.includes(index);
              return (
                <button
                  key={index}
                  type="button"
                  aria-pressed={on}
                  className={cn("h-11 w-11 rounded-lg text-sm", on ? "bg-white/10 text-fg" : "bg-white/5 text-muted")}
                  onClick={() => {
                    if (on && picked.length === 1) return;
                    const next = on ? picked.filter((core) => core !== index) : [...picked, index].sort((a, b) => a - b);
                    setPicked(next);
                    setWorkers((count) => Math.max(1, Math.min(count, next.length, 4)));
                  }}
                >
                  {index}
                </button>
              );
            })}
          </div>
        </div>
        </div>
        <div className="flex shrink-0 flex-col gap-2 border-t border-white/10 px-5 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          {error ? (
            <p className="text-sm text-bad" role="alert">
              {error}
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <button type="button" className="min-h-11 rounded-lg px-3 text-sm" onClick={() => ref.current?.close()}>
              {text.cancel}
            </button>
            <button
              type="submit"
              disabled={busy}
              className="min-h-11 rounded-lg bg-fg px-4 text-sm font-medium text-bg disabled:opacity-50"
            >
              {busy ? "..." : text.create}
            </button>
          </div>
        </div>
      </form>
    </dialog>
  );
}

export function LogRail({ filterId = "log-filter" }: { filterId?: string }) {
  const lang = useBench((state) => state.settings.lang);
  const follow = useBench((state) => state.settings.followLog);
  const job = useBench((state) => state.jobs.find((item) => item.id === state.selectedJobId) ?? null);
  const text = t(lang);
  const [filter, setFilter] = useState("");
  const [pinned, setPinned] = useState(true);
  const pinnedRef = useRef(true);
  const seenJob = useRef<string | null | undefined>(undefined);
  const scroller = useRef<HTMLDivElement>(null);
  const logs = job?.logs;
  const needle = filter.trim().toLowerCase();
  const shown: { line: string; index: number }[] = [];
  const source = logs ?? [];
  for (let index = 0; index < source.length; index += 1) {
    const line = source[index] ?? "";
    if (line.toLowerCase().includes(needle)) shown.push({ line, index });
  }

  useLayoutEffect(() => {
    const node = scroller.current;
    if (!node) return;
    const id = job?.id ?? null;
    if (seenJob.current !== id) {
      seenJob.current = id;
      if (follow) pinnedRef.current = true;
    }
    if (follow && pinnedRef.current) {
      node.scrollTop = node.scrollHeight;
      setPinned(true);
      return;
    }
    const near = node.scrollHeight - node.scrollTop - node.clientHeight <= 48;
    pinnedRef.current = near;
    setPinned(near);
  }, [follow, job?.id, logs, needle]);

  return (
    <aside className="flex h-full min-h-0 flex-col bg-transparent">
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-medium">{text.log}</h2>
          <p className="truncate text-xs text-subtle">{job ? job.title : "—"}</p>
        </div>
        <button
          type="button"
          className="min-h-11 shrink-0 rounded-lg px-3 text-sm text-muted hover:bg-white/10"
          onClick={() => {
            const node = scroller.current;
            if (!node) return;
            node.scrollTop = node.scrollHeight;
            pinnedRef.current = true;
            setPinned(true);
          }}
        >
          {pinned && follow ? text.follow : text.jump}
        </button>
      </div>
      <div className="px-3 pb-2">
        <div className="flex items-baseline justify-between gap-2">
          <label htmlFor={filterId} className="text-xs text-subtle">
            {text.filter}
          </label>
          <span className="text-xs text-subtle">
            {shown.length}/{source.length}
          </span>
        </div>
        <input
          id={filterId}
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3 text-sm text-fg outline-none"
        />
      </div>
      <div
        ref={scroller}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label={text.log}
        onScroll={(event) => {
          const node = event.currentTarget;
          const near = node.scrollHeight - node.scrollTop - node.clientHeight <= 48;
          if (near === pinnedRef.current) return;
          pinnedRef.current = near;
          setPinned(near);
        }}
        className="min-h-0 flex-1 overflow-auto px-3 pb-4 font-mono text-xs leading-relaxed [overflow-anchor:none]"
      >
        {job && shown.length === 0 && needle ? (
          <p className="py-1 text-muted">{lang === "fa" ? "خطی نیست" : "No lines"}</p>
        ) : null}
        {shown.map((item) => (
          <p key={item.index} className="py-1 text-muted">
            {item.line}
          </p>
        ))}
      </div>
    </aside>
  );
}

function Reveal({ text, active }: { text: string; active: boolean }) {
  const [count, setCount] = useState(active ? 0 : text.length);
  useEffect(() => {
    if (!active) {
      setCount(text.length);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setCount(text.length);
      return;
    }
    let index = 0;
    let frame = 0;
    const step = () => {
      index = Math.min(text.length, index + 3);
      setCount(index);
      if (index < text.length) frame = window.requestAnimationFrame(step);
    };
    frame = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(frame);
  }, [text, active]);
  return <>{text.slice(0, count)}</>;
}

function Status({ job }: { job: Job }) {
  const lang = useBench((state) => state.settings.lang);
  const text = t(lang);
  const tone =
    job.status === "failed" || job.status === "stopped"
      ? "text-bad"
      : job.status === "running"
        ? "text-ok"
        : job.status === "paused"
          ? "text-warn"
          : "text-muted";
  return <span className={cn("shrink-0 text-xs font-medium", tone)}>{labelStatus(text, job.status)}</span>;
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="min-w-0 bg-bg px-3 py-2">
      <dt className="text-xs text-subtle">{k}</dt>
      <dd className="mt-0.5 min-w-0 break-words font-mono text-sm">{v}</dd>
    </div>
  );
}

function SeedMatrix({ job }: { job: Job }) {
  const text = t(useBench((state) => state.settings.lang));
  const slots = seedSlots(job);
  return (
    <div>
      <p className="mb-2 text-xs text-subtle">{text.seedMatrix}</p>
      <div className="grid max-h-56 grid-cols-2 gap-2 overflow-auto sm:grid-cols-3">
        {slots.map((slot) => (
          <div key={slot.seed} className="rounded-xl bg-bg px-3 py-2">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-sm">{slot.seed}</span>
              <span className="text-xs text-muted">
                {slot.state === "done" ? text.seedDone : slot.state === "active" ? text.seedActive : text.seedIdle}
              </span>
            </div>
            <p className="mt-1 truncate font-mono text-xs text-subtle">
              {slot.arm} · {slot.done}/{slot.total}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SettingSection({ value, title, children }: { value: string; title: string; children: ReactNode }) {
  return (
    <Accordion.Item value={value} className="min-w-0 overflow-hidden rounded-2xl bg-white/5">
      <Accordion.Header>
        <Accordion.Trigger className="group flex min-h-11 w-full items-center justify-between gap-3 px-4 py-2 text-start text-sm font-medium hover:bg-white/10">
          <span className="min-w-0">{title}</span>
          <ChevronDown className="h-4 w-4 shrink-0 text-subtle transition-transform duration-200 group-data-[state=open]:rotate-180" aria-hidden />
        </Accordion.Trigger>
      </Accordion.Header>
      <Accordion.Content className="px-4 pb-4">{children}</Accordion.Content>
    </Accordion.Item>
  );
}

function kindLabel(text: ReturnType<typeof t>, job: Job) {
  if (job.kind === "gates") return job.gateFile ?? text.trackContracts;
  if (job.kind === "script") return job.scriptName || text.scripts;
  return text.trackEngine;
}

function dotClass(status: JobStatus) {
  if (status === "running") return "bg-ok live-dot";
  if (status === "paused") return "bg-warn";
  if (status === "failed" || status === "stopped") return "bg-bad";
  return "bg-subtle";
}

function labelStatus(text: ReturnType<typeof t>, status: JobStatus) {
  if (status === "queued") return text.statusQueued;
  if (status === "running") return text.statusRunning;
  if (status === "paused") return text.statusPaused;
  if (status === "stopped") return text.statusStopped;
  if (status === "archived") return text.statusArchived;
  return text.statusFailed;
}

function smokeInput(): RunInput {
  const smoke = pinPreset("smoke", 4);
  return {
    title: "Smoke",
    kind: "engine",
    preset: "smoke",
    seedsText: smoke.seedsText,
    generations: smoke.generations,
    workers: smoke.workers,
    cores: smoke.cores,
  };
}

function pinPreset(id: Exclude<PresetId, "custom">, hostCores: number) {
  const spec = PRESETS[id];
  const limit = Math.max(1, hostCores);
  const available = Array.from({ length: limit }, (_, index) => index);
  const pinned = spec.cores.filter((core) => available.includes(core));
  const nextCores = pinned.length > 0 ? pinned : [available[0] ?? 0];
  return {
    seedsText: spec.seeds.join(", "),
    generations: spec.generations,
    workers: Math.max(1, Math.min(4, spec.workers, nextCores.length)),
    cores: nextCores,
  };
}

function validate(input: RunInput, text: ReturnType<typeof t>) {
  if (input.cores.length < 1) return text.errorCores;
  if (!Number.isInteger(input.workers) || input.workers < 1 || input.workers > 4 || input.workers > input.cores.length) {
    return text.errorWorkers;
  }
  if (input.kind === "script" && !/^[\w.-]+\.py$/.test(input.scriptName ?? "")) return text.errorScript;
  if (input.kind === "engine" && input.track !== "contracts") {
    if (!Number.isInteger(input.generations) || input.generations < 2) return text.errorGen;
    const parts = input.seedsText.split(/[\s,]+/).filter(Boolean).map(Number);
    if (parts.length === 0 || parts.some((seed) => !Number.isInteger(seed) || seed < 0) || new Set(parts).size !== parts.length) {
      return text.errorSeeds;
    }
  }
  return "";
}

function downloadJob(job: Job) {
  if (job.isDemo) {
    saveBlob(artifactZip(job), `${job.id}.zip`);
    return;
  }
  const link = document.createElement("a");
  link.href = `/api/runs/${encodeURIComponent(job.id)}/zip`;
  link.download = `${job.id}.zip`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

export function HelpDialog({ onClose }: { onClose: () => void }) {
  const lang = useBench((state) => state.settings.lang);
  const text = t(lang);
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  const sections = [text.helpRuns, text.helpGates, text.helpScripts, text.helpZip, text.helpHost, text.claim];
  return (
    <dialog
      ref={ref}
      className="m-auto w-[min(100%,36rem)] max-h-[min(100dvh,40rem)] max-w-full overflow-auto rounded-2xl bg-[#101218] px-5 py-5 text-fg backdrop:bg-black/70"
      onClose={onClose}
    >
      <h2 className="text-lg font-medium">{text.helpTitle}</h2>
      <div className="mt-4 flex flex-col gap-3">
        {sections.map((section) => (
          <p key={section} className="text-sm text-muted">
            {section}
          </p>
        ))}
      </div>
      <div className="mt-4 flex justify-end">
        <button type="button" className="min-h-11 rounded-lg bg-fg px-4 text-sm text-bg" onClick={() => ref.current?.close()}>
          {text.close}
        </button>
      </div>
    </dialog>
  );
}

function downloadText(name: string, body: string, type: string) {
  const blob = new Blob([body], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
