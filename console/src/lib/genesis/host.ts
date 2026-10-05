import type { HostProfile } from "./types";

export async function getHostProfile(): Promise<HostProfile> {
  const response = await fetch("/api/host", { headers: { accept: "application/json" } });
  if (!response.ok) throw new Error(String(response.status));
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") throw new Error("host");
  return body as HostProfile;
}
