import { ENGINE_IDENTITY } from "./catalog";
import type { HostProfile, ReleaseReport } from "./types";

export async function getHostProfile(): Promise<HostProfile> {
  const response = await fetch("/api/host", { headers: { accept: "application/json" } });
  if (!response.ok) throw new Error(String(response.status));
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") throw new Error("host");
  return body as HostProfile;
}

export async function fetchRelease(refresh = false): Promise<ReleaseReport> {
  try {
    const response = await fetch(refresh ? "/api/release?refresh=1" : "/api/release", {
      headers: { accept: "application/json" },
    });
    if (response.ok) {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "currentVersion" in body) return body as ReleaseReport;
    }
  } catch {
    // The page can still ask GitHub itself when the console server is absent.
  }
  return releaseFromGitHub();
}

async function releaseFromGitHub(): Promise<ReleaseReport> {
  const response = await fetch("https://api.github.com/repos/Parvaz-Jamei/codontrace-genesis/releases/latest", {
    headers: { accept: "application/vnd.github+json" },
  });
  if (!response.ok) throw new Error(String(response.status));
  const body: unknown = await response.json();
  const tag = body && typeof body === "object" && "tag_name" in body && typeof body.tag_name === "string" ? body.tag_name : null;
  const page = body && typeof body === "object" && "html_url" in body && typeof body.html_url === "string" ? body.html_url : null;
  const ahead = tag ? newerRelease(tag, ENGINE_IDENTITY) : false;
  return {
    currentVersion: ENGINE_IDENTITY,
    currentCommit: null,
    latestVersion: tag,
    latestCommit: null,
    updateAvailable: ahead,
    behindMain: false,
    releaseAhead: ahead,
    lastChecked: Date.now() / 1000,
    checking: false,
    error: tag ? null : "release had no tag",
    checkout: false,
    htmlUrl: page,
  };
}

function newerRelease(latest: string, current: string) {
  const left = versionKey(latest);
  const right = versionKey(current);
  if (!left || !right) return false;
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return (left[index] ?? 0) > (right[index] ?? 0);
  }
  return false;
}

function versionKey(value: string) {
  const match = /^v?(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$/.exec(value.trim());
  if (!match) return null;
  const rank = match[4] === "a" ? 0 : match[4] === "b" ? 1 : match[4] === "rc" ? 2 : 3;
  return [Number(match[1]), Number(match[2]), Number(match[3]), rank, Number(match[5] ?? 0)];
}

export async function pullRelease(): Promise<{ ok: boolean; message: string }> {
  const response = await fetch("/api/release/update", { method: "POST" });
  const body: unknown = await response.json().catch(() => null);
  if (!body || typeof body !== "object") throw new Error(String(response.status));
  const record = body as { ok?: boolean; message?: string };
  return { ok: Boolean(record.ok), message: record.message ?? "" };
}

export async function checkChatStatus(): Promise<{ mounted: boolean; endpoint?: string; model?: string }> {
  try {
    const res = await fetch("/api/chat/status");
    if (res.ok) return (await res.json()) as { mounted: boolean; endpoint?: string; model?: string };
  } catch {
    // fallback
  }
  return { mounted: false };
}

export async function sendChatMessage(
  text: string,
  lang: string,
  jobContext?: unknown,
): Promise<{ reply: string; source: string; mounted: boolean }> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang, jobContext }),
  });
  if (!res.ok) throw new Error(String(res.status));
  return (await res.json()) as { reply: string; source: string; mounted: boolean };
}

export async function fetchSimulationRuns(): Promise<unknown[]> {
  try {
    const res = await fetch("/api/runs");
    if (res.ok) return (await res.json()) as unknown[];
  } catch {
    // fallback
  }
  return [];
}

export async function fetchScripts(): Promise<unknown[]> {
  try {
    const res = await fetch("/api/scripts");
    if (res.ok) return (await res.json()) as unknown[];
  } catch {
    // fallback
  }
  return [];
}

