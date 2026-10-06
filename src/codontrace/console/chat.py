"""LLM chat and analyst backend for the preview console.

Standard library only. Does not import the evolution engine.
Supports local OpenAI-compatible endpoints (e.g. llama-server on :8088, Ollama on :11434)
with fallback to deterministic analysis.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_ENDPOINTS = (
    "http://127.0.0.1:8088/v1/chat/completions",
    "http://127.0.0.1:11434/v1/chat/completions",
    "http://127.0.0.1:1234/v1/chat/completions",
)

_RUNTIME_ENDPOINT: str | None = None


def set_llm_endpoint(endpoint: str | None) -> None:
    """Dynamically set the active LLM endpoint with scheme validation."""
    global _RUNTIME_ENDPOINT
    if not endpoint:
        _RUNTIME_ENDPOINT = None
        return
    clean = endpoint.strip()
    from urllib.parse import urlparse
    parsed = urlparse(clean)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Invalid LLM endpoint: must be a valid http or https URL")
    _RUNTIME_ENDPOINT = clean


def get_llm_endpoint() -> str:
    if _RUNTIME_ENDPOINT:
        return _RUNTIME_ENDPOINT
    return os.environ.get("CODONTRACE_LLM_ENDPOINT", "").strip() or DEFAULT_ENDPOINTS[0]


def list_discovered_models() -> list[dict[str, Any]]:
    """Scan local storage directories for GGUF model files."""
    from pathlib import Path

    candidates = []
    custom = os.environ.get("CODONTRACE_MODELS_DIR", "").strip()
    if custom:
        candidates.append(Path(custom))

    candidates.extend([
        Path("models"),
        Path.home() / "models",
        Path("E:/Zero3/models"),
        Path("/home/parvaz/models"),
    ])

    seen = set()
    models = []
    for d in candidates:
        if not d.is_dir():
            continue
        try:
            for item in sorted(d.glob("*.gguf")):
                if item.name not in seen:
                    seen.add(item.name)
                    stat = item.stat()
                    models.append({
                        "name": item.name,
                        "path": str(item),
                        "sizeMb": round(stat.st_size / (1024 * 1024)),
                        "mtime": stat.st_mtime,
                        "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                    })
        except OSError:
            continue

    return models


def check_llm_status() -> dict[str, Any]:
    """Check if any local LLM server is mounted and responding."""
    endpoint = get_llm_endpoint()
    env_set = bool(_RUNTIME_ENDPOINT or os.environ.get("CODONTRACE_LLM_ENDPOINT"))

    endpoints_to_try = [endpoint] if env_set else list(DEFAULT_ENDPOINTS)

    for ep in endpoints_to_try:
        try:
            # Quick OPTIONS or models check
            base_url = ep.split("/v1/")[0]
            models_url = f"{base_url}/v1/models"
            req = urllib.request.Request(models_url, headers={"User-Agent": "CodonTraceConsole/1.0"})
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("id", "model") for m in data.get("data", [])] if isinstance(data, dict) else []
                    active_model = models[0] if models else "active-model"
                    provider = "llama-server" if ":8088" in ep else ("ollama" if ":11434" in ep else "local-llm")
                    return {
                        "mounted": True,
                        "endpoint": ep,
                        "model": active_model,
                        "provider": provider,
                        "available_models": models,
                    }
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue

    return {
        "mounted": False,
        "endpoint": endpoint,
        "model": None,
        "provider": "none",
        "available_models": [],
    }


def query_llm(
    messages: list[dict[str, str]],
    system_prompt: str | None = None,
    model: str | None = None,
) -> str | None:
    """Send query to local LLM server with explicit model and safe timeout handling."""
    status = check_llm_status()
    if not status["mounted"]:
        return None

    endpoint = status["endpoint"]
    all_messages = []
    if system_prompt:
        all_messages.append({"role": "system", "content": system_prompt})
    all_messages.extend(messages)

    chosen_model = model or status.get("model") or "local-model"
    payload_dict: dict[str, Any] = {
        "model": chosen_model,
        "messages": all_messages,
        "temperature": 0.3,
        "max_tokens": 300,
    }
    payload = json.dumps(payload_dict).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "CodonTraceConsole/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                choices = body.get("choices", [])
                if choices and isinstance(choices, list):
                    content = choices[0].get("message", {}).get("content", "")
                    return content.strip() if content else None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    return None


def chat_turn(
    text: str,
    lang: str = "en",
    job_context: dict[str, Any] | None = None,
    job_id: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Execute an authoritative chat turn with LLM or deterministic fallback."""
    t0 = time.time()
    sys_prompt = (
        "You are the CodonTrace Genesis Research Assistant. "
        "CodonTrace is a deterministic digital evolution and host-parasite coevolution engine. "
        "Provide insightful, scientifically grounded evolutionary analysis. "
        "Keep responses structured and focused. "
        "EPISTEMOLOGICAL INVARIANT: The Red Queen hypothesis is NEVER proven by computational runs. "
        "red_queen_proved is strictly locked to false. Never claim or imply that Red Queen is proven. "
        f"Respond in {'Persian (Farsi)' if lang == 'fa' else 'English'}."
    )

    effective_run_id = job_id or (
        str(job_context.get("id") or job_context.get("runId"))
        if isinstance(job_context, dict) and (job_context.get("id") or job_context.get("runId"))
        else None
    )

    if effective_run_id:
        from codontrace.console.runs import get_run_details

        run_data = get_run_details(effective_run_id)
        if run_data is not None:
            manifest = run_data.get("manifest") or {}
            params = manifest.get("params") or {}
            execution = run_data.get("execution")
            diagnostics = run_data.get("diagnostics")
            live_logs = run_data.get("liveLogs") or []
            tail_lines = live_logs[-5:] if isinstance(live_logs, list) else []

            ctx_summary = (
                f"\n[Authoritative Server Run Context for {effective_run_id}]:\n"
                f"- Title: {run_data.get('title')}\n"
                f"- Status: {run_data.get('status')}\n"
                f"- Generations: {params.get('generations', 'unspecified')}, Workers: {params.get('workers', 'unspecified')}\n"
                f"- Seeds: {params.get('seeds', [])}\n"
                f"- Invariant status: invariant=ok, red_queen_proved=false (LOCKED)\n"
            )
            if execution is not None and isinstance(execution, dict):
                ctx_summary += (
                    f"- Execution outcome: complete={execution.get('complete')}, "
                    f"elapsed_seconds={execution.get('elapsed_seconds')}, "
                    f"diagnostics_complete={execution.get('diagnostics_complete')}\n"
                )
            else:
                ctx_summary += "- Execution outcome: no execution summary available yet (in progress or pending)\n"

            if diagnostics is not None and isinstance(diagnostics, dict):
                ctx_summary += f"- Diagnostics summary: lag={diagnostics.get('lag')}, permutations={diagnostics.get('permutations')}\n"
            else:
                ctx_summary += "- Diagnostics: no time-shift diagnostics data recorded for this run\n"

            if tail_lines:
                ctx_summary += "- Recent live logs:\n  " + "\n  ".join(tail_lines) + "\n"

            sys_prompt += ctx_summary
        else:
            sys_prompt += (
                f"\n[Run Context]: Run '{effective_run_id}' was queried but no server run details exist "
                "(unmanaged client demo or archived).\n"
            )
    elif job_context:
        ctx_summary = (
            f"Active Job Context: title='{job_context.get('title')}', "
            f"kind='{job_context.get('kind')}', status='{job_context.get('status')}', "
            f"seeds={job_context.get('seeds')}, generations={job_context.get('generations')}."
        )
        sys_prompt += f" {ctx_summary}"

    llm_answer = query_llm([{"role": "user", "content": text}], system_prompt=sys_prompt, model=model)
    duration_ms = round((time.time() - t0) * 1000)

    if llm_answer is not None:
        # Enforce locked invariant guardrail on response
        if "red_queen_proved=true" in llm_answer.lower() or "red queen is proved" in llm_answer.lower():
            llm_answer += (
                "\n\n[Invariant Note: In accordance with scientific epistemic safeguards, "
                "red_queen_proved remains strictly false.]"
            )
        status = check_llm_status()
        return {
            "source": "llm",
            "reply": llm_answer,
            "mounted": True,
            "model": model or status.get("model") or "local-model",
            "duration_ms": duration_ms,
            "fallback": False,
        }

    # Deterministic fallback answer
    if lang == "fa":
        fallback_reply = (
            "مدل هوش مصنوعی محلی در پورت ۸۰۸۸ یا ۱۱۴۳۴ متصل نیست. "
            "تحلیلگر محلی جنسیس: این محیط جهت رصد و پایش تجربی دینامیک‌های مسابقه تسلیحاتی فرگشتی "
            "(Red Queen Dynamics) و ماتریس‌های انتقال زمانی دوطرفه طراحی شده است. "
            "قفل معرفت‌شناختی: red_queen_proved=false به صورت قطعی در سیستم برقرار است."
        )
    else:
        fallback_reply = (
            "No local LLM detected on port 8088 or 11434. "
            "CodonTrace local analyst: This console observes reciprocal antagonistic coevolutionary "
            "dynamics and bidirectional time-shift assays. "
            "Epistemic invariant: red_queen_proved=false is strictly preserved."
        )

    return {
        "source": "analyst",
        "reply": fallback_reply,
        "mounted": False,
        "model": "deterministic-analyst",
        "duration_ms": duration_ms,
        "fallback": True,
    }
