import assert from "node:assert/strict";
import { test } from "node:test";
import { authorizedFetch, setApiAccessToken } from "../src/lib/genesis/api-access";

test("usage token reaches requests without persisting provider secrets", async () => {
  const original = globalThis.fetch;
  const requests: RequestInit[] = [];
  globalThis.fetch = async (_input, init) => { requests.push(init ?? {}); return new Response("{}", {status: 200}); };
  try {
    setApiAccessToken("  session-usage-token  ");
    await authorizedFetch("/api/chat", {method: "POST", headers: {"Content-Type": "application/json"}});
    assert.equal(new Headers(requests[0].headers).get("Authorization"), "Bearer session-usage-token");
    assert.equal(new Headers(requests[0].headers).get("Content-Type"), "application/json");
    setApiAccessToken("");
    await authorizedFetch("/api/science/tools");
    assert.equal(new Headers(requests[1].headers).get("Authorization"), null);
  } finally { setApiAccessToken(""); globalThis.fetch = original; }
});
