export type Lang = "en" | "fa";
export type View = "jobs" | "chat" | "gates" | "scripts" | "host" | "settings";
export type JobKind = "engine" | "gates" | "script";
export type JobStatus = "queued" | "running" | "paused" | "stopped" | "archived" | "failed";
export type PresetId = "smoke" | "standard" | "overnight" | "expedition" | "custom";

export type HostProfile = {
  platform: string;
  arch: string;
  cores: number;
  memoryMb: number;
  freeMb: number;
  load1: number;
  tempC: number | null;
  recommendedWorkers: number;
  hostname: string;
  source: "host" | "browser";
  packageVersion?: string;
};

export type Job = {
  id: string;
  title: string;
  kind: JobKind;
  preset: PresetId;
  seeds: number[];
  generations: number;
  previewGenerations: number;
  workers: number;
  cores: number[];
  status: JobStatus;
  cursor: number;
  totalSteps: number;
  logs: string[];
  createdAt: number;
  note: string;
  redQueenProved: false;
  exploratory: true;
  diagnostics: "not_run";
  gateFile?: string;
  scriptName?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  at: number;
};

export type Thread = {
  id: string;
  title: string;
  jobId: string | null;
  pinned: boolean;
  messages: ChatMessage[];
  updatedAt: number;
};

export type ScriptRec = {
  id: string;
  name: string;
  note: string;
  body: string;
  createdAt: number;
};

export type BenchSettings = {
  lang: Lang;
  followLog: boolean;
  density: "comfortable" | "compact";
  model: "local-analyst" | "board-model";
};
