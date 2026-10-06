import { useEffect, useState, ViewTransition, type ReactNode } from "react";
import * as Collapsible from "@radix-ui/react-collapsible";
import { Check, CircleHelp, Cpu, FileCode, List, Menu, MessageSquare, PanelLeft, Plus, Settings } from "lucide-react";
import { fetchRelease, getHostProfile } from "@/lib/genesis/host";
import { t } from "@/lib/genesis/copy";
import { useBench } from "@/lib/genesis/store";
import type { HostProfile, ReleaseReport, View } from "@/lib/genesis/types";
import { cn } from "@/lib/cn";
import { Stage } from "./stage";
import { ChatView, GatesView, HelpDialog, HostView, JobsView, LogRail, NewRunDialog, ScriptsView, SettingsView } from "./views";

export function BenchApp() {
  const settings = useBench((state) => state.settings);
  const view = useBench((state) => state.view);
  const setView = useBench((state) => state.setView);
  const setHost = useBench((state) => state.setHost);
  const setSettings = useBench((state) => state.setSettings);
  const host = useBench((state) => state.host);
  const jobs = useBench((state) => state.jobs);
  const selectJob = useBench((state) => state.selectJob);
  const live = jobs.some((job) => job.status === "running");
  const text = t(settings.lang);
  const [menu, setMenu] = useState(false);
  const [log, setLog] = useState(false);
  const [composer, setComposer] = useState(false);
  const [help, setHelp] = useState(false);
  const [release, setRelease] = useState<ReleaseReport | null>(null);
  const [hideRelease, setHideRelease] = useState(false);

  useEffect(() => {
    void useBench.persist.rehydrate();
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setMenu(false);
      setLog(false);
      setComposer(false);
      setHelp(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    document.documentElement.lang = settings.lang;
    document.documentElement.dir = settings.lang === "fa" ? "rtl" : "ltr";
    document.documentElement.dataset.density = settings.density;
  }, [settings.lang, settings.density]);

  useEffect(() => {
    const syncFromLocation = () => {
      const rawHash = window.location.hash.replace(/^#\/?/, "").toLowerCase();
      const validViews: View[] = ["jobs", "chat", "gates", "scripts", "host", "settings"];
      if (validViews.includes(rawHash as View)) {
        setView(rawHash as View);
      }
      const params = new URLSearchParams(window.location.search);
      const urlLang = params.get("lang");
      if (urlLang === "fa" || urlLang === "en") {
        setSettings({ lang: urlLang });
      }
      if (params.get("new") === "1") {
        setComposer(true);
      }
      if (params.get("log") === "1") {
        setLog(true);
      }
      if (params.get("help") === "1") {
        setHelp(true);
      }
    };
    syncFromLocation();
    window.addEventListener("hashchange", syncFromLocation);
    return () => window.removeEventListener("hashchange", syncFromLocation);
  }, [setView, setSettings, setComposer, setLog, setHelp]);

  const handlePick = (next: View) => {
    setView(next);
    if (window.location.hash.replace(/^#\/?/, "") !== next) {
      window.location.hash = `#/${next}`;
    }
  };

  useEffect(() => {
    let gone = false;
    getHostProfile()
      .then((profile) => {
        if (!gone) setHost(profile);
      })
      .catch(() => {
        if (!gone) setHost(browserHost());
      });
    const timer = window.setInterval(() => {
      getHostProfile()
        .then((profile) => {
          if (!gone) setHost(profile);
        })
        .catch(() => undefined);
    }, 4000);
    return () => {
      gone = true;
      window.clearInterval(timer);
    };
  }, [setHost]);

  const syncServerRuns = useBench((state) => state.syncServerRuns);

  useEffect(() => {
    let gone = false;
    const sync = () => {
      if (gone) return;
      void syncServerRuns();
    };
    sync();
    const intervalMs = live ? 1500 : 3000;
    const timer = window.setInterval(sync, intervalMs);
    return () => {
      gone = true;
      window.clearInterval(timer);
    };
  }, [syncServerRuns, live]);

  useEffect(() => {
    let gone = false;
    const load = () => {
      fetchRelease()
        .then((next) => {
          if (!gone) setRelease(next);
        })
        .catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, 60_000);
    return () => {
      gone = true;
      window.clearInterval(timer);
    };
  }, []);

  const titles: Record<View, string> = {
    jobs: settings.lang === "fa" ? "کارزارهای تکامل" : "Evolution Campaigns",
    chat: settings.lang === "fa" ? "دستیار پژوهش" : "Research Assistant",
    gates: settings.lang === "fa" ? "مجموعه ۲۹ گیت" : "Test Suite · 29 gates",
    scripts: settings.lang === "fa" ? "آزمون‌های سفارشی" : "Custom Tests",
    host: settings.lang === "fa" ? "سخت‌افزار و نسخه" : "Hardware & Releases",
    settings: settings.lang === "fa" ? "تنظیمات" : "Settings",
  };

  return (
    <div className="flex h-dvh min-h-0 bg-bg pt-[env(safe-area-inset-top)] pe-[env(safe-area-inset-right)] pb-[env(safe-area-inset-bottom)] ps-[env(safe-area-inset-left)] text-fg rtl:pe-[env(safe-area-inset-left)] rtl:ps-[env(safe-area-inset-right)]">
      <Sidebar
        className="hidden lg:flex"
        view={view}
        host={host}
        jobs={jobs}
        live={live}
        collapsible
        onPick={handlePick}
        onNew={() => setComposer(true)}
        onOpenJob={(id) => {
          selectJob(id);
          handlePick("jobs");
        }}
        onLang={() => setSettings({ lang: settings.lang === "en" ? "fa" : "en" })}
        onHelp={() => setHelp(true)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center gap-2 px-3">
          <button className="grid h-11 w-11 place-items-center rounded-lg text-muted hover:bg-surface lg:hidden" onClick={() => setMenu(true)} aria-label={text.menu}>
            <Menu className="h-4 w-4" />
          </button>
          <p className="truncate text-sm text-muted">{titles[view]}</p>
          <button className="ms-auto grid h-11 min-w-11 place-items-center rounded-lg px-3 text-sm text-muted hover:bg-surface" onClick={() => setLog((open) => !open)}>
            {text.log}
          </button>
        </header>
        <Telemetry />
        {release?.updateAvailable && !hideRelease ? (
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2 text-sm">
            <p className="min-w-0 flex-1">
              {release.releaseAhead ? text.releaseAvailable : text.releaseBehind} {release.latestVersion ?? release.latestCommit}
            </p>
            <button type="button" className="min-h-10 rounded-lg px-2 text-muted hover:bg-white/10" onClick={() => handlePick("host")}>
              {text.release}
            </button>
            <button type="button" className="min-h-10 rounded-lg px-2 text-muted hover:bg-white/10" onClick={() => setHideRelease(true)}>
              {text.releaseDismiss}
            </button>
          </div>
        ) : null}
        <div className={cn("grid min-h-0 flex-1 transition-[grid-template-columns] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]", log ? "lg:grid-cols-[minmax(0,1fr)_320px]" : "lg:grid-cols-[minmax(0,1fr)_0px]")}>
          <main className="relative min-h-0 min-w-0">
            <Stage />
            <ViewTransition enter="vt-enter" exit="vt-exit">
              <div key={view} className="relative z-10 h-full min-h-0">
                {view === "jobs" ? <JobsView /> : null}
                {view === "chat" ? <ChatView /> : null}
                {view === "gates" ? <GatesView /> : null}
                {view === "scripts" ? <ScriptsView /> : null}
                {view === "host" ? <HostView /> : null}
                {view === "settings" ? <SettingsView /> : null}
              </div>
            </ViewTransition>
          </main>
          <div inert={!log} aria-hidden={!log} className={cn("hidden min-h-0 overflow-hidden border-line bg-[#101218] lg:block", log && "border-s")}>
            <div className="flex h-full w-80 flex-col">
              <div className="flex h-12 items-center justify-between px-3 text-sm text-muted">
                <span>{text.log}</span>
                <button className="min-h-10 rounded-lg px-2 hover:bg-white/10" onClick={() => setLog(false)}>
                  {text.close}
                </button>
              </div>
              <div className="min-h-0 flex-1">
                <LogRail filterId="log-filter-side" />
              </div>
            </div>
          </div>
        </div>
      </div>
      {menu ? (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMenu(false)}>
          <div className="fixed inset-y-0 start-0 z-40 h-full w-[260px] pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <Sidebar
              className="flex"
              view={view}
              host={host}
              jobs={jobs}
              live={live}
              collapsible={false}
              onPick={(next) => {
                handlePick(next);
                setMenu(false);
              }}
              onNew={() => {
                setComposer(true);
                setMenu(false);
              }}
              onOpenJob={(id) => {
                selectJob(id);
                handlePick("jobs");
                setMenu(false);
              }}
              onLang={() => setSettings({ lang: settings.lang === "en" ? "fa" : "en" })}
              onHelp={() => {
                setHelp(true);
                setMenu(false);
              }}
            />
          </div>
        </div>
      ) : null}
      {log ? (
        <div className="fixed inset-0 z-40 flex flex-col bg-bg pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)] lg:hidden">
          <div className="flex h-14 items-center justify-end px-3">
            <button className="min-h-11 px-3 text-sm" onClick={() => setLog(false)}>
              {text.close}
            </button>
          </div>
          <div className="min-h-0 flex-1">
            <LogRail filterId="log-filter-sheet" />
          </div>
        </div>
      ) : null}
      {composer ? <NewRunDialog onClose={() => setComposer(false)} /> : null}
      {help ? <HelpDialog onClose={() => setHelp(false)} /> : null}
    </div>
  );
}

function Sidebar({
  className,
  view,
  host,
  jobs,
  live,
  collapsible = true,
  onPick,
  onNew,
  onOpenJob,
  onLang,
  onHelp,
}: {
  className?: string;
  view: View;
  host: HostProfile | null;
  jobs: { id: string; title: string; status: string }[];
  live: boolean;
  collapsible?: boolean;
  onPick: (view: View) => void;
  onNew: () => void;
  onOpenJob: (id: string) => void;
  onLang: () => void;
  onHelp: () => void;
}) {
  const lang = useBench((state) => state.settings.lang);
  const text = t(lang);
  const [recentsOpen, setRecentsOpen] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [query, setQuery] = useState("");
  const selectedId = useBench((state) => state.selectedJobId);
  const items: { id: View; label: string; icon: typeof List }[] = [
    { id: "jobs", label: lang === "fa" ? "شبیه‌سازی‌ها" : "Simulations", icon: List },
    { id: "chat", label: lang === "fa" ? "تحلیلگر" : "Analyst", icon: MessageSquare },
    { id: "gates", label: lang === "fa" ? "گیت‌ها" : "Gates", icon: Check },
    { id: "scripts", label: lang === "fa" ? "اسکریپت" : "Scripts", icon: FileCode },
    { id: "host", label: lang === "fa" ? "سخت‌افزار" : "Hardware", icon: Cpu },
    { id: "settings", label: text.settings, icon: Settings },
  ];
  const ram = host && host.memoryMb > 0 ? Math.round(((host.memoryMb - host.freeMb) / host.memoryMb) * 100) : null;
  const recent = jobs.filter((job) => job.title.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 12);
  return (
    <aside className={cn("h-full shrink-0 flex-col overflow-hidden bg-[#101218] transition-[width] duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]", collapsed && collapsible ? "w-[72px]" : "w-[260px]", className)}>
      <div className="flex items-center gap-2 px-3 pt-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-fg text-xs font-semibold text-bg">G</span>
        {collapsed ? null : <span className="text-sm font-medium">Genesis</span>}
        <button
          className={cn("ms-auto grid h-8 w-8 place-items-center rounded-lg text-muted hover:bg-white/10", !collapsible && "hidden")}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={() => setCollapsed((open) => !open)}
        >
          <PanelLeft className="h-4 w-4" />
        </button>
      </div>
      <div className="px-2 pt-3">
        <button className="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-sm hover:bg-white/10" onClick={onNew}>
          <Plus className="h-4 w-4 shrink-0" />
          {collapsed ? null : text.newRun}
        </button>
      </div>
      <nav className="flex flex-col gap-0.5 px-2 pt-2">
        {items.map((item) => (
          <button
            key={item.id}
            aria-current={view === item.id ? "page" : undefined}
            className={cn(
              "flex min-h-10 items-center gap-3 rounded-lg px-3 text-start text-sm",
              view === item.id ? "bg-white/10 text-fg" : "text-muted hover:bg-white/10",
            )}
            onClick={() => onPick(item.id)}
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {collapsed ? null : item.label}
          </button>
        ))}
      </nav>
      {collapsed ? <div className="min-h-0 flex-1" /> : (
      <Collapsible.Root open={recentsOpen} onOpenChange={setRecentsOpen} className="mt-3 min-h-0 flex-1 overflow-auto px-2">
        <Collapsible.Trigger className="flex min-h-10 w-full items-center justify-between px-3 text-xs text-subtle">
          {lang === "fa" ? "اخیر" : "Recents"}
          <span>{recentsOpen ? "–" : "+"}</span>
        </Collapsible.Trigger>
        <Collapsible.Content>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={lang === "fa" ? "جستجوی اجرا" : "Search runs"}
              className="mb-1 h-10 w-full rounded-lg bg-white/5 px-3 text-sm outline-none placeholder:text-subtle focus:bg-white/10"
            />
            {recent.map((job) => (
              <button
                key={job.id}
                className={cn(
                  "flex min-h-10 w-full items-center gap-2 rounded-lg px-3 text-start text-sm hover:bg-white/10",
                  selectedId === job.id ? "bg-white/10 text-fg" : "text-muted",
                )}
                onClick={() => onOpenJob(job.id)}
              >
                <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", job.status === "running" ? "bg-ok" : "bg-subtle")} />
                <span className="truncate">{job.title}</span>
              </button>
            ))}
            {recent.length === 0 ? <p className="px-3 text-xs text-subtle">{lang === "fa" ? "چیزی پیدا نشد" : jobs.length === 0 ? "No runs yet" : "No match"}</p> : null}
        </Collapsible.Content>
      </Collapsible.Root>
      )}
      <div className="mt-auto flex flex-col gap-1 border-t border-white/8 p-2">
        <p className="px-3 py-1 text-xs text-subtle">
          {live ? "● " : ""}
          {collapsed ? host?.cores ?? "—" : host ? `${host.cores} cores` : "—"}
          {!collapsed && ram !== null ? ` · ${ram}%` : ""}
          {!collapsed && host ? ` · ${host.platform}` : ""}
        </p>
        {collapsed ? null : <p className="px-3 text-[11px] text-subtle">{text.claim}</p>}
        <button className="flex min-h-10 items-center gap-2 rounded-lg px-3 text-start text-sm text-muted hover:bg-white/10" onClick={onHelp}>
          <CircleHelp className="h-4 w-4 shrink-0" />
          {collapsed ? null : text.help}
        </button>
        <button className="min-h-10 rounded-lg px-3 text-start text-sm text-muted hover:bg-white/10" onClick={onLang}>
          {collapsed ? (lang === "en" ? "فا" : "EN") : lang === "en" ? "فارسی" : "English"}
        </button>
      </div>
    </aside>
  );
}

function Pill({ children }: { children: ReactNode }) {
  return <span className="inline-flex min-h-8 items-center gap-1.5 rounded-full border border-line bg-surface px-3 text-xs text-muted">{children}</span>;
}

function Telemetry() {
  const host = useBench((state) => state.host);
  const lang = useBench((state) => state.settings.lang);
  const text = t(lang);
  const ram = host && host.memoryMb > 0 ? Math.round(((host.memoryMb - host.freeMb) / host.memoryMb) * 100) : null;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-3 py-2 font-mono text-xs text-muted">
      <span>
        {host ? host.cores : "—"} {text.coresOnline}
      </span>
      <span>
        {text.temp} {host?.tempC === null || host?.tempC === undefined ? "—" : `${host.tempC}°C`}
      </span>
      <span className="inline-flex min-w-28 items-center gap-2">
        {text.ram} {ram === null ? "—" : `${ram}%`}
        <span className="h-1 w-16 overflow-hidden rounded-sm bg-surface-2">
          <span className="meter block h-full bg-fg" style={{ width: `${ram ?? 0}%` }} />
        </span>
      </span>
      <span>
        {text.load} {host && host.platform !== "win32" ? host.load1 : "—"}
      </span>
    </div>
  );
}

function browserHost(): HostProfile {
  const cores = Math.max(1, navigator.hardwareConcurrency || 1);
  const ua = navigator.userAgent;
  const platform = /windows/i.test(ua) ? "win32" : /mac/i.test(ua) ? "darwin" : "linux";
  return {
    platform,
    arch: "browser",
    cores,
    memoryMb: 0,
    freeMb: 0,
    load1: 0,
    tempC: null,
    recommendedWorkers: Math.max(1, Math.min(4, cores)),
    hostname: "browser",
    source: "browser",
  };
}
