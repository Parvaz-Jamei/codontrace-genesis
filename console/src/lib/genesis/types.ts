export type Lang = "en" | "fa";
export type View = "home" | "jobs" | "chat" | "gates" | "scripts" | "host" | "settings";
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

export type ReleaseReport = {
  currentVersion: string;
  currentCommit: string | null;
  latestVersion: string | null;
  latestCommit: string | null;
  updateAvailable: boolean;
  behindMain: boolean;
  releaseAhead: boolean;
  lastChecked: number;
  checking: boolean;
  error: string | null;
  checkout: boolean;
  htmlUrl: string | null;
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
  assessments?: HypothesisAssessment[];
  diagnostics?: string;
  gateFile?: string;
  scriptName?: string;
  isDemo?: boolean;
  serverManaged?: boolean;
  pct?: number;
  mtime?: number;
  execution?: Record<string, unknown>;
  diagnosticsData?: Record<string, unknown>;
  snapshot?: RunSnapshotV2;
  capabilities?: CapabilitiesV2;
};

export type CapabilitiesV2 = {
  pause: boolean;
  resume: boolean;
  checkpoint_continue: boolean;
};

export type ProgressV2 = {
  kind: string;
  stage: string;
  done: number;
  total: number;
  pct: number | null;
};

export type RunSnapshotV2 = {
  schema_version: "run_snapshot_v2";
  run_id: string;
  session_id: string;
  revision: number;
  state: string;
  requested_state?: string | null;
  capabilities: CapabilitiesV2;
  workers_expected: number;
  workers_paused: number;
  progress: ProgressV2;
  active_elapsed_seconds: number;
  paused_seconds: number;
  wall_elapsed_seconds: number;
  heartbeat_at: string;
  pending_command_id?: string | null;
};

export type HypothesisAssessment = {
  hypothesis_id: string;
  conclusion: string;
  confidence: number;
  evidence_digests: string[];
};

export type ChatStatus = {
  mounted: boolean;
  endpoint: string;
  model: string | null;
  provider: string;
  available_models?: string[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  at: number;
  source?: "llm" | "analyst";
  model?: string;
  durationMs?: number;
  fallback?: boolean;
};

export type Thread = {
  id: string;
  title: string;
  jobId: string | null;
  pinned: boolean;
  messages: ChatMessage[];
  updatedAt: number;
  isThinking?: boolean;
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
  model: string;
};
