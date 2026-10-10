import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ScientificOutput } from "../src/components/bench/scientific-output";
import { answer } from "../src/lib/genesis/analyst";
import type { Job } from "../src/lib/genesis/types";

test("scientific line shows observed data and discards nonfinite observations", () => {
  const html = renderToStaticMarkup(
    <ScientificOutput
      artifacts={[
        {
          kind: "chart",
          spec: {
            chart_type: "line",
            title: "Recorded survival",
            series: [
              {
                name: "seed 7",
                points: [
                  [0, 1],
                  [1, 2],
                  [2, NaN],
                ],
              },
            ],
          },
        },
      ]}
    />,
  );
  assert.match(html, /Recorded survival/);
  assert.match(html, /stroke-dasharray/);
  assert.match(html, /seed 7/);
  assert.doesNotMatch(html, /NaN/);
});
test("heatmap uses recorded matrix with missing values distinguishable", () => {
  const html = renderToStaticMarkup(
    <ScientificOutput
      artifacts={[
        {
          kind: "chart",
          spec: {
            chart_type: "heatmap",
            title: "Time shift",
            matrix: [
              [0.1, 0.2],
              [0.4, 0.9],
            ],
            row_labels: ["past", "current"],
          },
        },
      ]}
    />,
  );
  assert.equal((html.match(/<rect /g) ?? []).length, 5);
  assert.match(html, /past/);
  assert.match(html, /0.9/);
});
test("code and provenance are text, never executable markup", () => {
  const html = renderToStaticMarkup(
    <ScientificOutput
      artifacts={[
        {
          kind: "code",
          text: "<script>alert(1)</script>",
          language: "python",
          provenance: { run_id: "paused-7" },
        },
      ]}
    />,
  );
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /paused-7/);
});
test("table values escape HTML", () => {
  const html = renderToStaticMarkup(
    <ScientificOutput
      artifacts={[
        {
          kind: "table",
          columns: ["Evidence"],
          rows: [["<img src=x onerror=alert(1)>"]],
        },
      ]}
    />,
  );
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img/);
});
test("saved scientific support is reported consistently in every execution state", () => {
  for (const status of [
    "running",
    "paused",
    "stopped",
    "failed",
    "archived",
  ] as const) {
    const job = {
      title: "saved result",
      status,
      logs: [],
      execution: {
        summary: { scientific_assessment: "SUPPORTED_IN_THIS_MODEL" },
      },
    } as unknown as Job;
    assert.match(
      answer("en", "Red Queen proved?", job),
      /SUPPORTED_IN_THIS_MODEL/,
    );
    assert.doesNotMatch(
      answer("en", "Red Queen proved?", job),
      /false on this run/,
    );
  }
});

import {
  scientificToolRequest,
  SCIENCE_API,
} from "../src/lib/genesis/scientific-tools";
import { spawnSync } from "node:child_process";
const catalogResult = spawnSync(
  "python3",
  [
    "-c",
    "import json; from codontrace.console.science_tools import tool_catalog; print(json.dumps(tool_catalog()))",
  ],
  { cwd: "..", env: { ...process.env, PYTHONPATH: "src" }, encoding: "utf8" },
);
test("UI request matches actual backend catalog for opt-in processes and Pareto filters", () => {
  assert.equal(catalogResult.status, 0, catalogResult.stderr);
  const tools = JSON.parse(catalogResult.stdout);
  const board = tools.find((t: any) => t.name === "board_processes");
  assert.equal(
    scientificToolRequest(board, null, {}).allow_cross_project,
    true,
  );
  for (const name of ["list_projects", "board_processes"]) {
    const tool = tools.find((t: any) => t.name === name);
    assert.deepEqual(scientificToolRequest(tool, "selected-run-7", {}), {tool:name,args:{},allow_cross_project:true});
  }
  const pareto = tools.find((t: any) => t.name === "pareto_front");
  const body = scientificToolRequest(pareto, "stopped-7", {
    x_metric: "energy_used",
    y_metric: "fitness",
    max_points: "300",
  });
  assert.deepEqual(body.args, {
    run_id: "stopped-7",
    x_metric: "energy_used",
    y_metric: "fitness",
    max_points: 300,
  });
  assert.equal(body.allow_cross_project, false);
  assert.throws(
    () => scientificToolRequest(pareto, null, {}),
    /Select a project/,
  );
  assert.throws(
    () => scientificToolRequest(pareto, "run", { max_points: "not-a-number" }),
    /Invalid numeric/,
  );
  assert.equal(SCIENCE_API.launch, "/api/runs/launch");
});
test("null artifact payloads and malformed saved rows do not crash rendering", () => {
  assert.doesNotThrow(() =>
    renderToStaticMarkup(<ScientificOutput artifacts={null} />),
  );
  assert.doesNotThrow(() =>
    renderToStaticMarkup(
      <ScientificOutput
        artifacts={
          [
            null,
            {
              kind: "chart",
              spec: {
                chart_type: "line",
                title: "partial",
                series: [{ name: "bad", points: null }],
              },
            },
          ] as any
        }
      />,
    ),
  );
});

test("chart studio exposes all supported geometries with labels and export controls", () => {
  for (const kind of ["step","area","scatter","bubble","bar","histogram","ecdf","box","violin","density","errorbar"] as const) {
    const html=renderToStaticMarkup(<ScientificOutput artifacts={[{kind:"chart",spec:{chart_type:kind,title:kind,palette:"warm",series:[{name:"observed A",points:[[1,2,1,3],[2,3,2,4]]}],boxes:kind === "box"?[{name:"observed A",index:0,q1:2,median:2.5,q3:3,low:1,high:4,n:4,outliers:[]}]:undefined}}]}/>);
    assert.match(html,/SVG/);assert.match(html,/PNG/);assert.match(html,/observed A/);assert.match(html,/warm/);assert.doesNotMatch(html,/NaN|Infinity/);
  }
});
test("raw and configurable requests match the actual shared LLM tool schema", () => {
  const tool=JSON.parse(catalogResult.stdout).find((t:any)=>t.name === "scientific_plot");
  assert.deepEqual(scientificToolRequest(tool,"run-7",{mode:"raw"}).args,{run_id:"run-7",mode:"raw"});
  const request=scientificToolRequest(tool,"run-7",{mode:"tool",chart:"histogram",bins:"12",generation_from:"50",generation_to:"200",palette:"accessible"});
  assert.equal(request.args.bins,12);assert.equal(request.args.generation_from,50);assert.equal(request.args.mode,"tool");
});
