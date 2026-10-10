import { authorizedFetch } from "../../lib/genesis/api-access";
import React, { useEffect, useState } from "react";
import type {
  ScientificArtifact,
  ScientificChartSpec,
  ScientificTool,
} from "@/lib/genesis/types";
import { useBench } from "@/lib/genesis/store";
import {
  SCIENCE_API,
  scientificToolRequest,
} from "@/lib/genesis/scientific-tools";

function MathOutput({ latex }: { latex: string }) {
  const [rendered, setRendered] = useState<{ html: string } | null>(null);
  useEffect(() => {
    let active = true;
    setRendered(null);
    import("katex")
      .then(({ default: katex }) => {
        const html = katex.renderToString(latex.slice(0, 12000), {
          displayMode: true,
          throwOnError: false,
          trust: false,
          strict: "warn",
          maxExpand: 200,
          maxSize: 20,
        });
        if (active) setRendered({ html });
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [latex]);
  return rendered ? (
    <div
      dir="ltr"
      className="overflow-x-auto py-2"
      dangerouslySetInnerHTML={{ __html: rendered.html }}
    />
  ) : (
    <code dir="ltr" className="block overflow-auto text-xs">
      {latex}
    </code>
  );
}

export { ScientificChart as Chart } from "./scientific-chart";
import { ScientificChart as Chart } from "./scientific-chart";
function downloadArtifact(artifact: ScientificArtifact) {
  const blob = new Blob([JSON.stringify(artifact, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob),
    link = document.createElement("a");
  link.href = url;
  link.download = `scientific-${artifact.kind}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function ScientificOutput({
  artifacts,
}: {
  artifacts?: ScientificArtifact[] | null;
}) {
  return (
    <div className="space-y-3">
      {(Array.isArray(artifacts) ? artifacts : [])
        .filter(
          (a) =>
            a &&
            typeof a === "object" &&
            ["chart", "math", "code", "table"].includes(a.kind),
        )
        .slice(0, 20)
        .map((a, i) => (
          <section
            key={i}
            className="min-w-0 overflow-hidden rounded-xl border border-white/10 bg-white/[0.02] p-3"
          >
            <button
              type="button"
              onClick={() => downloadArtifact(a)}
              className="float-end min-h-8 rounded px-2 text-xs text-muted hover:bg-white/10"
              aria-label="Download artifact with provenance"
            >
              JSON ↓
            </button>
            <h4 className="mb-2 text-sm font-medium">
              {a.spec?.title ?? a.kind}
            </h4>
            {a.kind === "chart" && a.provenance?.mode ? <p className="mb-2 text-xs text-muted">{a.provenance.mode === "raw" ? "As recorded / بدون تغییر — bounded display snapshot" : "Configured / قابل تنظیم — options recorded in provenance"}</p> : null}
            {a.kind === "chart" && a.spec ? (
              <Chart spec={a.spec} />
            ) : a.kind === "math" ? (
              <MathOutput latex={a.latex ?? ""} />
            ) : a.kind === "code" ? (
              <>
                <span className="text-xs text-muted">
                  {a.language ?? "text"} · display only
                </span>
                <pre
                  dir="ltr"
                  className="mt-2 max-h-96 overflow-auto whitespace-pre text-xs"
                >
                  <code>{a.text}</code>
                </pre>
              </>
            ) : a.kind === "table" ? (
              <div className="max-h-96 overflow-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr>
                      {(Array.isArray(a.columns) ? a.columns : []).map(
                        (c, j) => (
                          <th key={j} className="p-2 text-start">
                            {c}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {(Array.isArray(a.rows) ? a.rows : [])
                      .filter(Array.isArray)
                      .slice(0, 500)
                      .map((r, j) => (
                        <tr key={j}>
                          {r.map((v, k) => (
                            <td key={k} className="border-t border-white/5 p-2">
                              {typeof v === "object"
                                ? JSON.stringify(v)
                                : String(v ?? "—")}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            {a.provenance ? (
              <details className="mt-2 text-xs text-muted">
                <summary className="cursor-pointer">
                  Provenance / منشأ داده
                </summary>
                <pre dir="ltr" className="overflow-auto whitespace-pre-wrap">
                  {JSON.stringify(a.provenance, null, 2)}
                </pre>
              </details>
            ) : null}
          </section>
        ))}
    </div>
  );
}

export function ScientificToolPicker({
  threadId,
  runId,
}: {
  threadId: string;
  runId: string | null;
}) {
  const lang = useBench((s) => s.settings.lang),
    append = useBench((s) => s.appendToolResult);
  const [accessRevision, setAccessRevision] = useState(0);
  useEffect(() => {
    const changed = () => setAccessRevision(v => v + 1);
    window.addEventListener("genesis-api-access-changed", changed);
    return () => window.removeEventListener("genesis-api-access-changed", changed);
  }, []);
  const [tools, setTools] = useState<ScientificTool[]>([]),
    [name, setName] = useState(""),
    [args, setArgs] = useState<Record<string, string>>({}),
    [mode, setMode] = useState<"raw" | "tool">("raw"),
    [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    authorizedFetch(SCIENCE_API.catalog)
      .then((r) => {
        if (!r.ok) throw Error(`Tool registry: ${r.status}`);
        return r.json();
      })
      .then((b) => {
        if (alive) { setTools(b.tools ?? []); setError(""); }
      })
      .catch((e) => {
        if (alive) setError(String(e));
      });
    return () => {
      alive = false;
    };
  }, [accessRevision]);
  const selected = tools.find((t) => t.name === name);
  const cross = selected?.requires_project_opt_in === true;
  const run = async () => {
    if (!selected || (!runId && !cross)) return;
    setBusy(true);
    setError("");
    try {
      const payload = scientificToolRequest(selected, runId, selected.name === "scientific_plot" ? { ...args, mode } : args);
      const response = await authorizedFetch(SCIENCE_API.execute, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok || !body.ok)
        throw Error(
          body.error ?? body.errors?.join("; ") ?? `HTTP ${response.status}`,
        );
      append(threadId, body.summary ?? selected.title, body.artifacts ?? []);
      setOpen(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="min-h-11 rounded-lg bg-white/5 px-3 text-sm hover:bg-white/10"
      >
        {lang === "fa" ? "ابزارهای علمی" : "Scientific tools"}
      </button>
      {open ? (
        <div className="absolute bottom-full start-0 z-40 mb-2 w-[min(90vw,360px)] max-h-[70vh] overflow-auto rounded-xl border border-white/10 bg-[#181a20] p-3 shadow-xl">
          <p className="mb-2 text-xs text-muted">
            {lang === "fa"
              ? "تحلیل دادهٔ ذخیره‌شده در همهٔ وضعیت‌ها؛ تمرکز روی پروژهٔ انتخاب‌شده."
              : "Analyze saved data in every run state. Scope: selected project."}
          </p>
          <div className="mb-3 flex gap-2" role="group" aria-label="Chart mode">
            <button className="min-h-10 rounded bg-white/10 px-2" aria-pressed={mode === "raw"} onClick={() => { setMode("raw"); setName("scientific_plot"); setArgs({}); }}> {lang === "fa" ? "نمایش بدون تغییر" : "As recorded"} </button>
            <button className="min-h-10 rounded bg-white/10 px-2" aria-pressed={mode === "tool"} onClick={() => { setMode("tool"); setName("scientific_plot"); setArgs({}); }}> {lang === "fa" ? "ابزار قابل تنظیم / LLM" : "Configurable / LLM"} </button>
          </div>
          <label className="text-xs">
            {lang === "fa" ? "ابزار" : "Tool"}
            <select
              className="mt-1 min-h-11 w-full rounded-lg bg-bg p-2 text-sm"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setMode("tool");
                setArgs({});
              }}
            >
              <option value="">
                {lang === "fa" ? "انتخاب ابزار" : "Choose tool"}
              </option>
              {tools.map((t) => (
                <option key={t.name} value={t.name}>
                  {t.title}
                </option>
              ))}
            </select>
          </label>
          {selected ? (
            <>
              <p className="my-2 text-xs text-muted">{selected.description}</p>
              {cross ? (
                <p className="mb-2 text-xs text-amber-400">
                  {lang === "fa"
                    ? "اجرای این ابزار درخواست صریح نمایش پروژه‌ها یا فرایندهای محلی دیگر است."
                    : "Running this tool explicitly requests other local projects or processes."}
                </p>
              ) : null}
              {Object.entries(selected.parameters.properties ?? {})
                .filter(([k]) => k !== "run_id" && k !== "allow_cross_project" && k !== "mode" && !(selected.name === "scientific_plot" && mode === "raw"))
                .map(([key, p]) => (
                  <label key={key} className="mb-2 block text-xs">
                    {key}
                    {p.description ? (
                      <span className="mt-1 block text-[11px] text-muted">
                        {p.description}
                      </span>
                    ) : null}
                    {p.enum ? (
                      <select
                        className="mt-1 min-h-10 w-full rounded bg-bg p-2"
                        value={args[key] ?? ""}
                        onChange={(e) =>
                          setArgs((v) => ({ ...v, [key]: e.target.value }))
                        }
                      >
                        <option value="">Default</option>
                        {p.enum.map((v) => (
                          <option key={String(v)}>{String(v)}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={
                          p.type === "integer" || p.type === "number"
                            ? "number"
                            : "text"
                        }
                        className="mt-1 min-h-10 w-full rounded bg-bg p-2"
                        value={args[key] ?? ""}
                        placeholder={String(p.default ?? p.description ?? "")}
                        onChange={(e) =>
                          setArgs((v) => ({ ...v, [key]: e.target.value }))
                        }
                      />
                    )}
                  </label>
                ))}
              <button
                type="button"
                disabled={busy || (!runId && !cross)}
                onClick={() => void run()}
                className="min-h-11 w-full rounded-lg bg-teal-500/20 text-teal-300 disabled:opacity-40"
              >
                {busy ? "…" : lang === "fa" ? "اجرای ابزار" : "Run tool"}
              </button>
            </>
          ) : null}
          {error ? (
            <p role="alert" className="mt-2 text-xs text-red-400">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
