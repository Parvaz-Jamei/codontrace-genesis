"""Read-only scientific tool and native tool-calling contracts; no model weights required."""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from codontrace.console import chat, science_tools, server


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setenv("CODONTRACE_RUNS_DIR", str(root))

    def create(name="run_alpha", seed=7, state="STOPPED", campaign="local", synthetic=False):
        folder = root / name
        folder.mkdir()
        manifest = {
            "runId": name,
            "title": name,
            "source_sha": "test-source",
            "campaign_id": campaign,
            "params": {"seed": seed, "seeds": [seed], "experiment": "T05", "arm": "A"},
            "engineBackend": "reference_experiment",
        }
        (folder / "run_manifest.json").write_text(json.dumps(manifest))
        (folder / "status.json").write_text(json.dumps({"status": state, "work_done": 3, "work_total": 9}))
        rows = [
            {
                "generation": i,
                "tick": 0,
                "primary_metric_name": "fitness",
                "primary_metric_value": i / 10,
                "secondary_metrics": {"energy_used": i * 2, "shannon_diversity": i / 3},
                "synthetic": synthetic,
            }
            for i in range(1, 4)
        ]
        (folder / "metrics.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        return folder

    return root, create


@pytest.mark.parametrize("state", ["RUNNING", "PAUSED", "STOPPED", "COMPLETED", "FAILED"])
def test_analysis_is_independent_of_lifecycle(recorded, state):
    _, create = recorded
    create(state=state)
    result = science_tools.invoke_tool("metric_series", {}, selected_run_id="run_alpha")
    assert result["ok"] is True
    chart = result["artifacts"][0]
    assert chart["spec"]["series"][0]["points"] == [[1.0, 0.1], [2.0, 0.2], [3.0, 0.3]]
    assert chart["provenance"]["sources"][0]["snapshot_sha256"]


def test_scope_and_parameters_are_enforced(recorded):
    _, create = recorded
    create()
    create("run_beta", seed=8)
    for name, args in [
        ("metric_series", {"run_id": "run_beta"}),
        ("metric_series", {"max_points": True}),
        ("metric_series", {"seed_from": 9, "seed_to": 2}),
        ("unknown", {}),
        ("list_projects", {}),
        ("board_processes", {}),
    ]:
        assert science_tools.invoke_tool(name, args, selected_run_id="run_alpha")["ok"] is False
    assert science_tools.invoke_tool("list_projects", {}, allow_cross_project=True)["ok"] is True


def test_no_fabricated_matrix_or_synthetic_data(recorded):
    _, create = recorded
    create(synthetic=True)
    for tool in ("metric_series", "effect_summary", "time_shift_heatmap", "confusion_matrix"):
        assert science_tools.invoke_tool(tool, {}, selected_run_id="run_alpha")["ok"] is False


def test_real_matrix_and_math_code_are_read_only(recorded):
    _, create = recorded
    folder = create()
    (folder / "execution.json").write_text(
        json.dumps(
            {
                "summary": {
                    "summary_metrics": {
                        "time_shift": {
                            "matrix": [[0.1, 0.2], [0.3, 0.4]],
                            "host_generations": [0, 3],
                            "parasite_generations": [0, 3],
                        }
                    }
                }
            }
        )
    )
    result = science_tools.invoke_tool("time_shift_heatmap", {}, selected_run_id="run_alpha")
    assert result["ok"] is True
    assert result["artifacts"][0]["spec"]["row_labels"] == [0, 3]
    math = science_tools.invoke_tool("mathematical_summary", {}, selected_run_id="run_alpha")
    assert "Delta z" in math["artifacts"][0]["latex"]
    code = science_tools.invoke_tool("reproducibility_code", {}, selected_run_id="run_alpha")
    assert code["artifacts"][0]["kind"] == "code"
    assert list(folder.glob("*.py")) == []


def test_seed_uncertainty_uses_seeds_not_generations(recorded):
    _, create = recorded
    create()
    one = science_tools.invoke_tool("effect_summary", {}, selected_run_id="run_alpha")
    assert one["artifacts"][0]["rows"] == [["A", 1, 0.3, None, None]]
    create("run_beta", seed=8)
    two = science_tools.invoke_tool("effect_summary", {}, selected_run_id="run_alpha")
    assert two["artifacts"][0]["rows"][0][1] == 2
    create("run_duplicate", seed=7)
    assert science_tools.invoke_tool("effect_summary", {}, selected_run_id="run_alpha")["ok"] is False
    assert (
        len(
            science_tools.invoke_tool("metric_series", {"seed_from": 0}, selected_run_id="run_alpha")["artifacts"][0]["spec"][
                "series"
            ]
        )
        == 3
    )


def test_metric_symlink_cannot_escape_selected_run(recorded, tmp_path):
    _, create = recorded
    folder = create()
    external = tmp_path / "private.jsonl"
    external.write_text('{"fitness": 999}\n')
    (folder / "metrics.jsonl").unlink()
    (folder / "metrics.jsonl").symlink_to(external)
    assert science_tools.invoke_tool("metric_series", {}, selected_run_id="run_alpha")["ok"] is False


def test_downsampling_retains_spike_and_endpoints():
    points = [[float(i), 99.0 if i == 507 else 0.0] for i in range(1000)]
    result = science_tools._downsample(points, 40)
    assert len(result) <= 40
    assert points[0] == result[0] and points[-1] == result[-1]
    assert points[507] in result


def test_native_llm_calls_get_actual_numeric_evidence(recorded, monkeypatch):
    _, create = recorded
    create()
    received = []

    class FakeModel(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(payload)
            message = {"role": "assistant", "content": "Observed endpoint is 0.3; descriptive only."}
            if len(received) == 1:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "c1", "type": "function", "function": {"name": "metric_series", "arguments": "{}"}}
                    ],
                }
            raw = json.dumps({"choices": [{"message": message}]}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeModel)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(chat, "check_llm_status", lambda: {"mounted": True, "model": "synthetic-test"})
    context = {"run_id": "run_alpha", "allow_cross_project": False}
    try:
        text = chat.query_llm(
            [{"role": "user", "content": "Analyze selected run"}],
            endpoint_override=f"http://127.0.0.1:{httpd.server_port}/v1/chat/completions",
            tool_context=context,
        )
        assert text.startswith("Observed endpoint")
        assert len(context["artifacts"]) == 1
        evidence = json.loads(received[1]["messages"][-1]["content"])
        assert evidence["measurements"][0]["series"][0]["last"] == [3.0, 0.3]
        assert not any(t["function"]["name"] == "board_processes" for t in received[0]["tools"])
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_http_catalog_and_manual_tool_integration(recorded):
    _, create = recorded
    create()
    httpd = server.make_server("127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    try:
        catalog = json.load(urllib.request.urlopen(base + "/api/science/tools"))
        assert len(catalog["tools"]) == 14
        body = json.dumps({"tool": "metric_series", "args": {"run_id": "run_alpha"}}).encode()
        response = json.load(
            urllib.request.urlopen(
                urllib.request.Request(
                    base + "/api/science/tools", data=body, headers={"Content-Type": "application/json"}
                )
            )
        )
        assert response["ok"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_campaign_plot_has_one_aggregate_memory_budget(recorded, monkeypatch):
    _, create = recorded
    for i in range(8):
        create("run_alpha" if i == 0 else f"run_{i}", seed=i)
    monkeypatch.setattr(science_tools, "MAX_RECORDS", 16)
    result = science_tools.invoke_tool("metric_series", {"seed_from": 0}, selected_run_id="run_alpha")
    assert result["ok"] is True
    sources = result["artifacts"][0]["provenance"]["sources"]
    assert sum(s["record_budget"] for s in sources) <= 16
    assert sum(s["byte_budget"] for s in sources) <= science_tools.MAX_BYTES
    assert sum(s["records_read"] for s in sources) <= 16
    assert all(s["truncated"] for s in sources)


def test_lightweight_model_rejecting_tools_gets_bounded_text_fallback(recorded, monkeypatch):
    _, create = recorded
    create()
    requests = []

    class TextOnlyModel(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            raw = json.dumps({"error": "tools are unsupported"} if "tools" in payload else
                             {"choices": [{"message": {"content": "Use the recorded chart; no new inference."}}]}).encode()
            self.send_response(400 if "tools" in payload else 200)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), TextOnlyModel)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(chat, "check_llm_status", lambda: {"mounted": True, "model": "text-only-test"})
    context = {"run_id": "run_alpha", "artifacts": []}
    try:
        reply = chat.query_llm([{"role": "user", "content": "Analyze selected run"}],
                              endpoint_override=f"http://127.0.0.1:{httpd.server_port}/v1/chat/completions", tool_context=context)
        assert reply == "Use the recorded chart; no new inference."
        assert len(requests) == 2
        assert "tools" not in requests[1]
        assert context["native_tools_unavailable"] is True
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_default_chart_and_http_chat_stay_on_own_run(recorded, monkeypatch):
    _, create = recorded
    first = create()
    second = create("run_beta", seed=8)
    (second / "metrics.jsonl").write_text(json.dumps({"generation": 99, "primary_metric_name": "fitness", "primary_metric_value": 9000}) + "\n")
    selected = science_tools.invoke_tool("metric_series", {}, selected_run_id="run_alpha")
    assert len(selected["artifacts"][0]["spec"]["series"]) == 1
    assert selected["artifacts"][0]["provenance"]["sources"][0]["run_id"] == first.name
    monkeypatch.setattr(chat, "check_llm_status", lambda: {"mounted": False, "model": "none"})
    httpd = server.make_server("127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{httpd.server_port}"
        for run_id, last in (("run_alpha", .3), ("run_beta", 9000)):
            body = json.dumps({"text": "plot fitness", "jobId": run_id, "model": "local-analyst",
                               "jobContext": {"id": "forged_client_id", "status": "COMPLETED"}}).encode()
            result = json.load(urllib.request.urlopen(urllib.request.Request(base + "/api/chat", data=body,
                                          headers={"Content-Type": "application/json"})))
            chart = result["artifacts"][0]
            assert chart["provenance"]["run_id"] == run_id
            assert chart["spec"]["series"][0]["points"][-1][1] == last
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_chart_modes_filters_and_raw_immutability(recorded):
    _, create = recorded
    folder = create()
    before = (folder / 'metrics.jsonl').read_bytes()
    raw = science_tools.invoke_tool('scientific_plot', {}, selected_run_id='run_alpha')
    assert raw['ok']
    assert raw['artifacts'][0]['spec']['series'][0]['points'] == [[1., .1], [2., .2], [3., .3]]
    assert raw['artifacts'][0]['provenance']['mode'] == 'raw'
    assert not science_tools.invoke_tool('scientific_plot', {'metric':'fitness'}, selected_run_id='run_alpha')['ok']
    custom = science_tools.invoke_tool('scientific_plot', {'mode':'tool','generation_from':2,'generation_to':3,'palette':'warm','chart':'step'}, selected_run_id='run_alpha')
    assert custom['ok']
    spec = custom['artifacts'][0]['spec']
    assert spec['series'][0]['points'] == [[2.,.2],[3.,.3]]
    assert spec['palette'] == 'warm'
    assert (folder / 'metrics.jsonl').read_bytes() == before
    for args in [{'mode':'tool','chart':'garbage'},{'mode':'tool','palette':'<script>'},{'mode':'tool','generation_from':4,'generation_to':2},{'mode':'tool','arm':'unknown'}]:
        assert not science_tools.invoke_tool('scientific_plot', args, selected_run_id='run_alpha')['ok']


@pytest.mark.parametrize('kind', ['line','step','area','scatter','bar','histogram','ecdf','box','violin','density','bubble','errorbar','correlation'])
def test_chart_geometry_and_observation_statistics(recorded, kind):
    _, create = recorded
    folder = create()
    rows = [json.loads(s) for s in (folder/'metrics.jsonl').read_text().splitlines()]
    for r in rows:
        r['metrics'] = {'low':r['primary_metric_value']-.02,'high':r['primary_metric_value']+.02}
    (folder/'metrics.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    args={'mode':'tool','chart':kind,'metric':'fitness'}
    if kind=='bubble':args['size_metric']='energy_used'
    if kind=='errorbar':args.update(lower_metric='low',upper_metric='high')
    if kind=='correlation':args['metrics']='fitness,energy_used'
    result = science_tools.invoke_tool('scientific_plot',args,selected_run_id='run_alpha')
    assert result['ok'], result
    spec=result['artifacts'][0]['spec']
    if kind=='histogram':assert sum(p[1] for p in spec['series'][0]['points'])==3
    if kind=='ecdf':assert spec['series'][0]['points'][-1]==[.3,1.]
    if kind=='box':
        assert spec['boxes'][0]['median']==.2
        assert spec['boxes'][0]['q1']==pytest.approx(.15)
    if kind=='correlation':assert spec['matrix'][0][1]==pytest.approx(1.)
    if kind=='errorbar':assert spec['series'][0]['points'][0][2:]==pytest.approx([.08,.12])
    if kind in {'violin','density'}:assert result['artifacts'][0]['provenance']['kde'][0]['bandwidth']>0


def test_no_invented_intervals_or_invalid_log_coordinates(recorded):
    _,create=recorded;create()
    for args in [{'chart':'errorbar'},{'chart':'bubble'},{'chart':'line','metric':'unknown'},{'chart':'histogram','y_scale':'log'}]:
        assert not science_tools.invoke_tool('scientific_plot',{'mode':'tool',**args},selected_run_id='run_alpha')['ok']
    assert science_tools.invoke_tool('scientific_plot',{'mode':'tool','x_scale':'log','y_scale':'log'},selected_run_id='run_alpha')['ok']


def test_deepseek_tool_round_preserves_protocol_reasoning_without_exposing_it(recorded, tmp_path, monkeypatch):
    from codontrace.console import providers
    import io
    _,create=recorded;create()
    monkeypatch.setenv('CODONTRACE_CONFIG_DIR',str(tmp_path/'config'))
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    providers.configure('deepseek',api_key='fake-deepseek-key')
    monkeypatch.setattr(chat,'check_llm_status',lambda:{'mounted':False,'model':None})
    requests=[]
    def fake(req,timeout):
        requests.append(json.loads(req.data))
        if len(requests)==1:
            response={'choices':[{'message':{'content':None,'reasoning_content':'synthetic-protocol-field','tool_calls':[{'id':'call_plot','type':'function','function':{'name':'scientific_plot','arguments':'{"mode":"raw"}'}}]}}]}
        else:
            assert requests[-1]['messages'][-2]['reasoning_content']=='synthetic-protocol-field'
            response={'choices':[{'message':{'content':'Recorded fitness rises in this partial snapshot.'}}]}
        return io.BytesIO(json.dumps(response).encode())
    monkeypatch.setattr(providers,'open_request',fake)
    context={'run_id':'run_alpha'}
    text=chat.query_llm([{'role':'user','content':'plot'}],model='deepseek::new-model',tool_context=context)
    assert text.startswith('Recorded fitness')
    assert len(context['artifacts'])==1
    assert context['artifacts'][0]['provenance']['mode']=='raw'
    assert 'synthetic-protocol-field' not in json.dumps(context)
    assert requests[0]['model']=='new-model'
