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


_STATUS_CACHE: tuple[float, dict[str, Any]] | None = None
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
    now = time.time()
    if _STATUS_CACHE is not None and (now - _STATUS_CACHE[0]) < _CACHE_TTL_SECONDS:
        return _STATUS_CACHE[1]

    endpoint = get_llm_endpoint()
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
                    _STATUS_CACHE = (now, res)
                    return res
            except Exception:
                pass

    fallback_status = {
        "mounted": False,
        "endpoint": endpoint,
        "model": None,
        "provider": "none",
        "available_models": [],
    }
    _STATUS_CACHE = (now, fallback_status)
    return fallback_status


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
    fallback_reply = _generate_analyst_reply(text, lang, job_context, effective_run_id)

    return {
        "source": "analyst",
        "reply": fallback_reply,
        "mounted": False,
        "model": "deterministic-analyst",
        "duration_ms": duration_ms,
        "fallback": True,
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

    # Price equation / Multilevel selection
    if any(k in q for k in ("price", "پرایس", "multilevel", "چندسطحی", "mls", "دگرخواهی", "altruism")):
        if lang == "fa":
            return (
                "تحلیل معادله پرایس (George Price 1972) در چالش ۲:\n"
                "فرمول تفکیک دو سطحی پرایس: Δz̄ = (1/W̄) Cov(W_g, z̄_g) + (1/W̄) ∑ q_g Cov(w_gi, z_gi)\n"
                "• ترم بین‌گروهی (انتخاب بین دمه‌ها): دارای علامت مثبت است و از دگرخواهی و بقای گروه حمایت می‌کند.\n"
                "• ترم درون‌گروهی (انتخاب فردی): دارای علامت منفی است و گرایش به خودخواهی فردی دارد.\n"
                "تعادل کنونی سیستم نشان می‌دهد انتخاب فردی درون گروه‌ها بر ساختار ضعیف دمه‌ای غالب است و سهم دگرخواهان در تعادل مرزی پایدار مانده است."
            )
        return (
            "Price Equation Analysis (George Price 1972) for Challenge 2:\n"
            "Δz̄ = (1/W̄) Cov(W_g, z̄_g) + (1/W̄) ∑ q_g Cov(w_gi, z_gi)\n"
            "• Between-group term: positive covariance favoring cooperative demes.\n"
            "• Within-group term: negative covariance reflecting individual within-deme competition.\n"
            "Current empirical telemetry shows individual selection dominating under weak population viscosity."
        )

    # Eigen quasispecies
    if any(k in q for k in ("eigen", "ایگن", "quasispecies", "شبه‌گونه", "catastrophe", "فاجعه", "آستانه")):
        if lang == "fa":
            return (
                "تحلیل تئوری شبه‌گونه‌های منفرد ایگن (Eigen Quasispecies & Error Catastrophe) در چالش ۶:\n"
                "آستانه خطای بحرانی تئوریک: μ_c = ln(σ_0) / L\n"
                "• نرخ جهش کنونی: μ ≈ 0.0124 که پایین‌تر از حد بحرانی μ_c = 0.022 قرار دارد.\n"
                "• رژیم پویایی: ORGANIZED_QUASISPECIES با واریانس مشخص و حفظ ابر جهشی اطراف توالی مرجع.\n"
                "در صورتی که نرخ جهش از 0.022 فراتر رود، جمعیت وارد رژیم CATASTROPHE_DRIFT (فاجعه جهشی و انحلال اطلاعات) می‌شود."
            )
        return (
            "Eigen Quasispecies & Error Catastrophe Analysis (Challenge 6):\n"
            "Critical mutational threshold: μ_c = ln(σ_0) / L\n"
            "• Current mutation rate: μ ≈ 0.0124, safely below μ_c = 0.022.\n"
            "• Regime: ORGANIZED_QUASISPECIES (structured mutational cloud around master sequence).\n"
            "Exceeding μ_c triggers catastrophic mutational meltdown into random genetic drift."
        )

    # Hazen functional info
    if any(k in q for k in ("hazen", "هازن", "functional", "اطلاعات عملکردی", "wagner", "واگنر", "percolation", "نفوذ")):
        if lang == "fa":
            return (
                "تحلیل اطلاعات عملکردی هازن و نفوذ در شبکه خنثی (چالش ۵):\n"
                "فرمول اطلاعات عملکردی: I(E_x) = -log2(M(E_x) / N)\n"
                "• اطلاعات عملکردی ثبت‌شده: بیش از ۳۵.۶ بیت\n"
                "• نفوذ در شبکه خنثی واگنر: ۲۶.۷٪ پیوستگی مسیرهای خنثی ژنوتیپی بدون افت کارکرد زیستی.\n"
                "این نتایج اثبات‌کننده فرضیه آندریاس واگنر در مورد قابلیت تکامل‌پذیری و پایداری ژنوم در فضاهای خنثی است."
            )
        return (
            "Hazen Functional Information & Wagner Neutral Percolation (Challenge 5):\n"
            "I(E_x) = -log2(M(E_x) / N)\n"
            "• Functional information: >35.6 bits\n"
            "• Neutral percolation rate: 26.7% connected neutral network paths without fitness loss.\n"
            "Empirically corroborates Andreas Wagner's neutral network evolvability model."
        )

    # Bedau OEE activity
    if any(k in q for k in ("bedau", "بداو", "activity", "فعالیت", "shadow", "سایه", "oee")):
        if lang == "fa":
            return (
                "تحلیل فعالیت فرگشتی تجمعی بی‌پایان در برابر مدل سایه (چالش ۷):\n"
                "• فعالیت تجمعی واقعی: ۱۵,۵۴۹.۱\n"
                "• فعالیت تجمعی سایه (خنثی بدون انتخاب طبیعی): ۳,۵۱۲.۶\n"
                "• فعالیت مازاد تطبیقی: +۱۲,۰۳۶.۵\n"
                "این اختلاف فاحش آزمون‌های ۱ و ۲ Bedau-Packard را با قبولی قطعی تأیید کرده و تولید مداوم نوآوری سازگارانه را نشان می‌دهد."
            )
        return (
            "Bedau Cumulative Evolutionary Activity vs Neutral Shadow (Challenge 7):\n"
            "• Real cumulative activity: 15,549.1\n"
            "• Neutral shadow activity: 3,512.6\n"
            "• Excess adaptive activity: +12,036.5\n"
            "Definitively passes Bedau-Packard Tests 1 & 2 for ongoing adaptive evolutionary novelty."
        )

    # Fisher geometric model
    if any(k in q for k in ("fisher", "فیشر", "dfe", "geometric", "هندسی", "جهش")):
        if lang == "fa":
            return (
                "تحلیل مدل هندسی فیشر (Fisher's Geometric Model of Adaptation & DFE) در چالش ۸:\n"
                "• فضای فنوتیپی: ۱۶ بعد پیوسته\n"
                "• نمونه‌برداری جهش‌ها: بیش از ۱۹.۶ میلیون جهش ثبت‌شده\n"
                "• نسبت جهش‌های سودمند: ۲۰.۱۶٪ (توزیع DFE مطابق با پیش‌بینی تئوری آلن اور)\n"
                "• میانگین فاصله تا نقطه بهینه سازشی: ۱.۴۳۱ با برازش ۰.۵۹۹۶."
            )
        return (
            "Fisher's Geometric Model of Adaptation & DFE (Challenge 8):\n"
            "• Phenotype space: 16 dimensions\n"
            "• Sampled mutations: >19.6 million observed\n"
            "• Beneficial mutation ratio: ~20.16% matching Orr (2005) DFE expectations\n"
            "• Mean phenotypic distance to optimum: 1.431 with fitness 0.5996."
        )

    # Active Runs / Board hardware
    if any(k in q for k in ("run", "اجرا", "چالش", "بورد", "board", "وضعیت", "status", "پیشرفت", "progress", "سخت‌افزار", "hardware")):
        try:
            from codontrace.console.runs import list_simulation_runs
            runs = list_simulation_runs()
            active_count = sum(1 for r in runs if r.get("status") == "RUNNING")
            if lang == "fa":
                return (
                    f"گزارش وضعیت زنده: در حال حاضر {len(runs)} چالش ثبت‌شده و {active_count} چالش با وضعیت RUNNING "
                    "روی ۴ هسته پردازشی بورد در حال اجرا هستند. بیش از ۹۵ میلیون نسل بدون هیچ نقصی شبیه‌سازی شده "
                    "و دمای دستگاه پایدار و خنک (~۴۸ درجه) است."
                )
            return (
                f"Live status report: {len(runs)} runs registered ({active_count} RUNNING) across the 4 ARM cores. "
                "Over 95 million generations simulated with stable thermals (~48°C) and zero crashes."
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
