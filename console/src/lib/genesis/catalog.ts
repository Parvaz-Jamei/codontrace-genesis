import type { PresetId } from "./types";

export const ARMS = ["coevolve", "adaptation_cut", "constant_parasite"] as const;

export const PRESETS: Record<
  Exclude<PresetId, "custom">,
  { seeds: number[]; generations: number }
> = {
  smoke: { seeds: [17001, 17002], generations: 3 },
  standard: { seeds: range(17101, 17112), generations: 100 },
  overnight: { seeds: range(18001, 18024), generations: 1000 },
  expedition: { seeds: range(19001, 19048), generations: 3000 },
};

export const GATE_FILES = [
  { file: "test_rq_controlled_benchmark.py", count: 3 },
  { file: "test_rq_parallel_readiness.py", count: 4 },
  { file: "test_rq1_confirmatory_gate.py", count: 3 },
  { file: "test_rq_mechanism_v2_phase5.py", count: 9 },
  { file: "test_rq_bidirectional_timeshift_confirm.py", count: 6 },
  { file: "test_rq_birth_archive_witness.py", count: 4 },
] as const;

export const ENGINE_IDENTITY = "0.3.0b19";
// Engine tree this preview was checked against. The console does not run it.
export const ENGINE_COMMIT = "5209c87";

export const MODELS = [
  { id: "local-analyst", mounted: true },
  { id: "board-model", mounted: false },
] as const;

export function range(from: number, to: number) {
  const out: number[] = [];
  for (let n = from; n <= to; n += 1) out.push(n);
  return out;
}

export function previewGenerations(requested: number) {
  return Math.min(Math.max(2, requested), 2);
}

export function contactsFor(arm: string) {
  return arm === "adaptation_cut" ? 60 : 64;
}
