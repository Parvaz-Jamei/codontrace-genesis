import type { ScientificTool } from "./types";
export const SCIENCE_API = {
  catalog: "/api/science/tools",
  execute: "/api/science/tools",
  launch: "/api/runs/launch",
} as const;
export function scientificToolRequest(
  tool: ScientificTool,
  runId: string | null,
  values: Record<string, string>,
) {
  const cross = tool.requires_project_opt_in === true;
  if (!runId && !cross)
    throw new Error("Select a project before using this tool.");
  const args: Record<string, unknown> = runId && !cross ? { run_id: runId } : {};
  for (const [key, value] of Object.entries(values)) {
    if (!value.trim()) continue;
    const property = tool.parameters.properties?.[key];
    if (!property || key === "run_id" || key === "allow_cross_project")
      continue;
    if (property.type === "number" || property.type === "integer") {
      const number = Number(value);
      if (
        !Number.isFinite(number) ||
        (property.type === "integer" && !Number.isInteger(number))
      )
        throw new Error(`Invalid numeric value: ${key}`);
      args[key] = number;
    } else args[key] = property.type === "boolean" ? value === "true" : value;
  }
  for (const key of tool.parameters.required ?? [])
    if (args[key] === undefined)
      throw new Error(`Missing required parameter: ${key}`);
  return { tool: tool.name, args, allow_cross_project: cross };
}
