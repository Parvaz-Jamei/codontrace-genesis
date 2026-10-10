"""Negative controls and API boundaries for the independent V3 review."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from codontrace.console import server
from codontrace.console.chat import inference_timeout
from codontrace.experiments.t03_mutualism import SymbioticPair, T03MutualismRunner


@pytest.mark.parametrize("cost,benefit", [(0.2, True), (0.9, False), (2.0, False)])
def test_t03_net_benefit_can_be_negative(cost, benefit):
    runner = T03MutualismRunner(1, cooperation_cost=cost, population_size=2, generations=1)
    runner.population = [SymbioticPair(i, i, 0.1, 0.1) for i in range(2)]
    assay = runner.run_4_assays(1)
    assert assay.payoff_partner_removed == (1.0, 0.8)
    assert assay.mutual_benefit_achieved is benefit
    assert assay.payoff_with_partner == pytest.approx((1 - cost * 0.1 + 0.06 + 0.012, 0.8 - cost * 0.1 + 0.06 + 0.012))


@pytest.mark.parametrize("value,expected", [("2400", 2400), ("nan", 1800), ("-1", 1800), ("bad", 1800)])
def test_local_timeout_not_capped(monkeypatch, value, expected):
    monkeypatch.setenv("CODONTRACE_LLM_TIMEOUT", value)
    assert inference_timeout(cloud=False) == expected
    monkeypatch.setenv("CODONTRACE_CLOUD_TIMEOUT", "90")
    assert inference_timeout(cloud=True) == 90


def test_api_token_rejects_before_cloud_spend_and_tools(monkeypatch):
    monkeypatch.setenv("CODONTRACE_API_TOKEN", "review-secret")
    calls = []
    monkeypatch.setattr(server, "chat_turn", lambda *a, **k: calls.append(k) or {"ok": True})
    httpd = server.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_port}"

    def request(path, token=None, post=True):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            base + path, data=b'{"text":"hi","model":"openai::gpt-test"}' if post else None, headers=headers
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            resp = exc
        with resp:
            return resp.status, json.load(resp)

    try:
        for path in ["/api/chat", "/api/chat/abort", "/api/chat/endpoint", "/api/science/tools"]:
            assert request(path)[0] == 403
            assert request(path, "wrong")[0] == 403
        assert request("/api/science/tools", post=False)[0] == 403
        assert request("/api/chat", "caf\xe9")[0] == 403
        assert calls == []
        assert request("/api/chat", "review-secret")[0] == 200
        assert len(calls) == 1
        assert request("/api/science/tools", "review-secret", post=False)[0] == 200
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(5)


def test_cloud_admission_is_bounded_and_releases_on_close(monkeypatch):
    import io

    from codontrace.console import providers

    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(providers, "_ACTIVE_REQUESTS", slots)
    monkeypatch.setattr(providers, "_REQUEST_TIMES", providers.deque())

    class Opener:
        def open(self, *a, **k):
            return io.BytesIO(b"{}")

    monkeypatch.setattr(providers.urllib.request, "build_opener", lambda *a: Opener())
    req = urllib.request.Request("https://api.openai.com/v1/models")
    first = providers.open_request(req, 5)
    with pytest.raises(providers.ProviderError, match="concurrency_limit"):
        providers.open_request(req, 5)
    first.close()
    first.close()
    with providers.open_request(req, 5) as response:
        assert response.read() == b"{}"
    for _ in range(28):
        with providers.open_request(req, 5):
            pass
    with pytest.raises(providers.ProviderError, match="local_rate_limit"):
        providers.open_request(req, 5)
    assert slots.acquire(blocking=False)
    slots.release()


def test_t11_exited_child_awaits_watcher_seal(tmp_path, monkeypatch):
    from codontrace.console import runs

    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(tmp_path))
    run_id = "t11_pending_seal"
    folder = tmp_path / run_id
    folder.mkdir()
    params = {"scriptName": "board_long_campaign.py", "ticks": 2, "workers": 1, "seeds": [7]}
    (folder / "run_manifest.json").write_text(json.dumps({"params": params, "engineBackend": "genesis_engine"}))
    initial = {"status": "RUNNING", "params": params, "pid": 12345, "work_done": 1, "work_total": 2}
    (folder / "status.json").write_text(json.dumps(initial))

    class Exited:
        def poll(self):
            return 0

    monkeypatch.setitem(runs._RUN_PROCESSES, run_id, Exited())
    detail = runs.get_run_details(run_id)
    assert detail["status"] == "RUNNING"
    assert json.loads((folder / "status.json").read_text())["status"] == "RUNNING"
