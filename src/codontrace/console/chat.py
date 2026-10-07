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
    global _RUNTIME_ENDPOINT, _STATUS_CACHE
    _STATUS_CACHE.clear()
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


_STATUS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 5.0


def _probe_single_endpoint(ep: str) -> dict[str, Any] | None:
    try:
        base_url = ep.split("/v1/")[0]
        models_url = f"{base_url}/v1/models"
        req = urllib.request.Request(models_url, headers={"User-Agent": "CodonTraceConsole/1.0"})
        with urllib.request.urlopen(req, timeout=0.35) as resp:
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
    except Exception:
        return None
    return None


def check_llm_status() -> dict[str, Any]:
    """Check if any local LLM server is mounted and responding with concurrency and caching."""
    global _STATUS_CACHE
    now = time.monotonic()
    
    endpoint = get_llm_endpoint()
    
    if endpoint in _STATUS_CACHE:
        cached_time, cached_val = _STATUS_CACHE[endpoint]
        if (now - cached_time) < _CACHE_TTL_SECONDS:
            return dict(cached_val)

    env_set = bool(_RUNTIME_ENDPOINT or os.environ.get("CODONTRACE_LLM_ENDPOINT"))
    endpoints_to_try = [endpoint] if env_set else list(DEFAULT_ENDPOINTS)

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(endpoints_to_try))) as executor:
        futures = [executor.submit(_probe_single_endpoint, ep) for ep in endpoints_to_try]
        done, _ = concurrent.futures.wait(futures, timeout=0.5)
        for fut in done:
            try:
                res = fut.result()
                if res and res.get("mounted"):
                    _STATUS_CACHE[endpoint] = (now, res)
                    return dict(res)
            except Exception:
                pass

    fallback_status = {
        "mounted": False,
        "endpoint": endpoint,
        "model": None,
        "provider": "none",
        "available_models": [],
    }
    _STATUS_CACHE[endpoint] = (now, fallback_status)
    return dict(fallback_status)


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
        with urllib.request.urlopen(req, timeout=5.0) as resp:
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

    if model in ("local-analyst", "deterministic-analyst"):
        llm_answer = None
    else:
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

    # Deterministic domain-aware fallback answer
    if model not in ("local-analyst", "deterministic-analyst"):
        err_msg = "ارتباط با مدل زبانی محلی برقرار نشد. لطفاً مطمئن شوید سرویس Llama-server در حال اجراست." if lang == "fa" else "Connection to the local LLM failed. Please ensure Llama-server is running."
        return {
            "source": "analyst",
            "reply": err_msg,
            "mounted": False,
            "model": model,
            "duration_ms": duration_ms,
            "fallback": True,
        }

    fallback_reply = _generate_analyst_reply(text, lang, job_context, effective_run_id)

    return {
        "source": "analyst",
        "reply": fallback_reply,
        "mounted": False,
        "model": "deterministic-analyst",
        "duration_ms": duration_ms,
        "fallback": False,
    }


def _generate_analyst_reply(
    text: str,
    lang: str,
    job_context: dict[str, Any] | None,
    job_id: str | None,
) -> str:
    q = text.lower()

    # Invariant guardrail
    if any(k in q for k in ("proof", "prove", "proved", "اثبات", "ثابت", "red queen", "ملکه سرخ")) and any(k in q for k in ("queen", "سرخ", "proved", "اثبات", "ثابت")):
        if lang == "fa":
            return (
                "خیر. قید معرفت‌شناختی: red_queen_proved روی تمام اجراها و کل موتور به طور قطعی False است "
                "و با شبیه‌سازی‌های محاسباتی اثبات نمی‌شود. رصد دینامیک‌های هم‌فرگشتی فقط برای مقایسه اکتشافی است."
            )
        return (
            "No. Epistemic invariant: red_queen_proved remains strictly False across all runs and the engine. "
            "Computational simulations never prove the Red Queen hypothesis; dynamics serve as empirical observations only."
        )

    def _metric(k: str) -> str:
        if not job_context: return "no active run data"
        if "metrics" not in job_context: return "stale data"
        metrics = job_context["metrics"]
        if not isinstance(metrics, dict): return "read error"
        if k not in metrics: return "no data"
        val = metrics[k]
        if val is None: return "read error"
        if val == 0 or val == 0.0: return "measured zero"
        return str(val)

    # Price equation / Multilevel selection
    if any(k in q for k in ("price", "پرایس", "multilevel", "چندسطحی", "mls", "دگرخواهی", "altruism")):
        if lang == "fa":
            return (
                "تحلیل معادله پرایس (George Price 1972):\n"
                "فرمول تفکیک دو سطحی پرایس: Δz̄ = (1/W̄) Cov(W_g, z̄_g) + (1/W̄) ∑ q_g Cov(w_gi, z_gi)\n"
                "• ترم بین‌گروهی (انتخاب بین دمه‌ها): کوواریانس بین برازش گروه و میانگین فنوتیپ.\n"
                "• ترم درون‌گروهی (انتخاب فردی): رقابت فردی درون گروهی.\n"
                "علامت و مقادیر این ترم‌ها به صورت پویا به ساختار جمعیت وابسته است."
            )
        return (
            "Price Equation Analysis (George Price 1972):\n"
            "Δz̄ = (1/W̄) Cov(W_g, z̄_g) + (1/W̄) ∑ q_g Cov(w_gi, z_gi)\n"
            "• Between-group term: covariance between group fitness and mean trait.\n"
            "• Within-group term: within-group individual competition.\n"
            "The signs and magnitudes depend dynamically on the population structure."
        )

    # Eigen quasispecies
    if any(k in q for k in ("eigen", "ایگن", "quasispecies", "شبه‌گونه", "catastrophe", "فاجعه", "آستانه")):
        mu = _metric("observed_mutation_rate")
        if lang == "fa":
            return (
                "تحلیل تئوری شبه‌گونه‌های منفرد ایگن (Eigen Quasispecies & Error Catastrophe):\n"
                "آستانه خطای بحرانی تئوریک: μ_c = ln(σ_0) / L\n"
                f"• نرخ جهش رصد شده: {mu}\n"
                "عبور از آستانه خطای بحرانی موجب فروپاشی ساختار ژنتیکی می‌شود."
            )
        return (
            "Eigen Quasispecies & Error Catastrophe Analysis:\n"
            "Critical mutational threshold formulation: μ_c = ln(σ_0) / L\n"
            f"• Observed mutation rate: {mu}\n"
            "Exceeding μ_c triggers catastrophic mutational meltdown into random genetic drift."
        )

    # Hazen functional info
    if any(k in q for k in ("hazen", "هازن", "functional", "اطلاعات عملکردی", "wagner", "واگنر", "percolation", "نفوذ")):
        fi = _metric("functional_information")
        pr = _metric("neutral_percolation_rate")
        if lang == "fa":
            return (
                "تحلیل اطلاعات عملکردی هازن و نفوذ در شبکه خنثی:\n"
                "فرمول اطلاعات عملکردی: I(E_x) = -log2(M(E_x) / N)\n"
                f"• اطلاعات عملکردی ثبت‌شده: {fi}\n"
                f"• نفوذ در شبکه خنثی واگنر: {pr}\n"
            )
        return (
            "Hazen Functional Information & Wagner Neutral Percolation:\n"
            "I(E_x) = -log2(M(E_x) / N)\n"
            f"• Functional information: {fi}\n"
            f"• Neutral percolation rate: {pr}\n"
        )

    # Bedau OEE activity
    if any(k in q for k in ("bedau", "بداو", "activity", "فعالیت", "shadow", "سایه", "oee")):
        act = _metric("cumulative_activity")
        shad = _metric("shadow_activity")
        excess = _metric("excess_activity")
        if lang == "fa":
            return (
                "تحلیل فعالیت فرگشتی تجمعی بی‌پایان در برابر مدل سایه (آزمون‌های Bedau-Packard):\n"
                f"• فعالیت تجمعی واقعی: {act}\n"
                f"• فعالیت تجمعی سایه: {shad}\n"
                f"• فعالیت مازاد تطبیقی: {excess}\n"
            )
        return (
            "Bedau Cumulative Evolutionary Activity vs Neutral Shadow (Bedau-Packard tests):\n"
            f"• Real cumulative activity: {act}\n"
            f"• Neutral shadow activity: {shad}\n"
            f"• Excess adaptive activity: {excess}\n"
        )

    # Fisher geometric model
    if any(k in q for k in ("fisher", "فیشر", "dfe", "geometric", "هندسی", "جهش")):
        dfe = _metric("dfe_ratio")
        if lang == "fa":
            return (
                "تحلیل مدل هندسی فیشر (Fisher's Geometric Model of Adaptation & DFE):\n"
                "مدل هندسی فیشر توزیع اثرات جهش‌ها را در فضای فنوتیپی ارزیابی می‌کند.\n"
                f"• نسبت جهش‌های سودمند (DFE): {dfe}\n"
            )
        return (
            "Fisher's Geometric Model of Adaptation & DFE:\n"
            "Fisher's geometric model explains the distribution of fitness effects (DFE) in phenotypic space.\n"
            f"• Beneficial mutation ratio (DFE): {dfe}\n"
        )

    # Active Runs / Board hardware
    if any(k in q for k in ("run", "اجرا", "چالش", "challenge", "بورد", "board", "وضعیت", "status", "پیشرفت", "progress", "سخت‌افزار", "hardware")):
        try:
            from codontrace.console.runs import list_simulation_runs, get_run_details, runs_directory
            import sys
            import os
            import shutil
            
            runs = list_simulation_runs()
            active_count = sum(1 for r in runs if r.get("status") == "RUNNING")
            
            total_generations = 0
            has_generations = False
            for r in runs:
                details = get_run_details(r["id"])
                if details:
                    manifest = details.get("manifest", {})
                    params = manifest.get("params", {})
                    exec_data = details.get("execution", {})
                    if "generations" in params:
                        total_generations += params["generations"]
                        has_generations = True
                    elif "generations" in exec_data:
                        total_generations += exec_data["generations"]
                        has_generations = True
            
            gen_str = str(total_generations) if has_generations else "none"
            if not runs:
                gen_str = "unknown"
                
            cpu_load = "unknown"
            if hasattr(os, "getloadavg"):
                try:
                    cpu_load = str(os.getloadavg()[0])
                except Exception:
                    pass
                    
            mem_load = "unknown"
            if sys.platform == "win32":
                try:
                    import ctypes
                    class MEMORYSTATUSEX(ctypes.Structure):
                        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
                    stat = MEMORYSTATUSEX()
                    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                    mem_load = f"{stat.dwMemoryLoad}%"
                except Exception:
                    pass
            else:
                try:
                    with open("/proc/meminfo") as f:
                        mi = f.read()
                    total = int([x for x in mi.splitlines() if x.startswith("MemTotal:")][0].split()[1])
                    free = int([x for x in mi.splitlines() if x.startswith("MemAvailable:")][0].split()[1])
                    mem_load = f"{int(100 * (total - free) / total)}%"
                except Exception:
                    pass
                    
            disk_str = "unknown"
            try:
                du = shutil.disk_usage(runs_directory())
                disk_str = f"{du.used // (1024**3)}GB/{du.total // (1024**3)}GB"
            except Exception:
                pass
            
            if lang == "fa":
                return (
                    f"گزارش وضعیت زنده: {len(runs)} چالش ثبت‌شده ({active_count} RUNNING). "
                    f"نسل‌های شبیه‌سازی‌شده: {gen_str}. "
                    f"بار پردازنده: {cpu_load}، حافظه: {mem_load}، دیسک: {disk_str}."
                )
            return (
                f"Live status report: {len(runs)} runs registered ({active_count} RUNNING). "
                f"Generations simulated: {gen_str}. "
                f"CPU load: {cpu_load}, Memory: {mem_load}, Disk: {disk_str}."
            )
        except Exception:
            pass

    # General Greeting / Default
    if lang == "fa":
        return (
            "درود! من دستیار هوشمند پژوهش CodonTrace Genesis هستم. "
            "می‌توانید وضعیت زنده هر ۸ چالش فرانتیر روی بورد، سنجه‌های ریاضی فرگشت "
            "(معادله پرایس، فاجعه خطای ایگن، اطلاعات عملکردی هازن، مدل هندسی فیشر و نوآوری بداو) "
            "و سلامت سخت‌افزاری دستگاه را از من بپرسید.\n"
            "قید معرفتی سیستم: red_queen_proved=false به صورت قطعی در سیستم برقرار است."
        )
    return (
        "Hello! I am the CodonTrace Genesis Research Assistant. "
        "You can ask me about the 8 live frontier challenges running on the board, evolutionary metrics "
        "(Price equation, Eigen quasispecies threshold, Hazen functional information, Fisher geometric model, Bedau OEE), "
        "and hardware telemetry.\n"
        "Epistemic invariant: red_queen_proved=false is strictly preserved."
    )
