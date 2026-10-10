"""Stdlib host for the preview console.

This file does not import the evolution engine. The page is a preview:
uploaded script text is not executed, and ``red_queen_proved`` is not set.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from codontrace.campaigns.readiness import inventory as campaign_inventory
from codontrace.console.chat import (
    abort_chat_request,
    chat_turn,
    check_llm_status,
    list_discovered_models,
    set_llm_endpoint,
)
from codontrace.console.release import (
    installed_version,
    refresh_release,
    release_state,
    start_release_monitor,
    update_checkout,
)
from codontrace.console.runs import (
    get_allowed_cpu_ids as _runs_get_allowed_cpu_ids,
)
from codontrace.console.runs import (
    get_run_details,
    get_run_zip,
    launch_simulation_run,
    list_simulation_runs,
    manage_run_action,
    validate_run_id,
)
from codontrace.console.scripts_service import (
    list_gates,
    list_scripts,
    read_script,
    run_gate_tests,
    run_script,
    save_script,
    validate_script_name,
)

STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _parse_json_dict(raw: bytes) -> tuple[dict[str, Any] | None, str | None]:
    """Safely parse JSON request body ensuring it is a dictionary/object."""
    if not raw or not raw.strip():
        return {}, None
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return None, f"Invalid JSON syntax: {exc}"
    if not isinstance(obj, dict):
        return None, f"Expected JSON object, got {type(obj).__name__}"
    return obj, None
_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".webmanifest": "application/manifest+json",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


def get_allowed_cpu_ids() -> list[int]:
    """Return sorted list of CPU core IDs allowed for this process."""
    get_affinity = getattr(os, "sched_getaffinity", None)
    if callable(get_affinity):
        try:
            aff = get_affinity(0)
            if aff:
                return sorted(int(x) for x in aff)
        except OSError:
            pass
    return _runs_get_allowed_cpu_ids()


def recommended_workers(cores: int) -> int:
    return cores if cores > 0 else 1



def parse_temp_c(raw: str) -> float | None:
    try:
        value = float(raw.strip())
    except ValueError:
        return None
    if value != value:
        return None
    if value > 200:
        return round(value / 100) / 10
    return value


def cpu_temp_c(thermal_root: Path) -> float | None:
    """Prefer a zone whose type names the CPU. Zone 0 is the GPU on some ARM boards."""
    chosen: float | None = None
    fallback: float | None = None
    try:
        zones = sorted(path for path in thermal_root.glob("thermal_zone*") if path.is_dir())
    except OSError:
        zones = []
    for zone in zones:
        try:
            kind = (zone / "type").read_text(encoding="utf-8").strip().lower()
            raw = (zone / "temp").read_text(encoding="utf-8")
        except OSError:
            continue
        temp = parse_temp_c(raw)
        if temp is None:
            continue
        if zone.name == "thermal_zone0":
            fallback = temp
        if chosen is None and "cpu" in kind and "gpu" not in kind:
            chosen = temp
    if chosen is not None:
        return chosen
    if fallback is not None:
        return fallback
    try:
        return parse_temp_c((thermal_root / "thermal_zone0" / "temp").read_text(encoding="utf-8"))
    except OSError:
        return None


def read_temp_c() -> float | None:
    if sys.platform != "linux":
        return None
    return cpu_temp_c(Path("/sys/class/thermal"))


def load_average() -> float:
    """One-minute load. Windows has no load average; the page treats win32 as unmeasured."""
    if sys.platform == "win32":
        return 0.0
    getter = getattr(os, "getloadavg", None)
    if getter is None:
        return 0.0
    try:
        load = float(getter()[0])
    except (OSError, ValueError, IndexError):
        return 0.0
    return round(load * 100) / 100


def _linux_memory() -> tuple[int, int] | None:
    path = Path("/proc/meminfo")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    total = 0
    available = 0
    free = 0
    for line in lines:
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            kib = int(parts[1])
        except ValueError:
            continue
        if parts[0] == "MemTotal:":
            total = kib * 1024
        elif parts[0] == "MemAvailable:":
            available = kib * 1024
        elif parts[0] == "MemFree:":
            free = kib * 1024
    if total <= 0:
        return None
    return total, available or free


def _windows_memory() -> tuple[int, int]:
    import ctypes

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = (
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        )

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    loader = getattr(ctypes, "WinDLL", None)
    if loader is None:
        return 0, 0
    kernel = loader("kernel32")
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 0, 0
    return int(status.ullTotalPhys), int(status.ullAvailPhys)


def _posix_memory() -> tuple[int, int]:
    try:
        page = int(os.sysconf("SC_PAGE_SIZE"))
        total_pages = int(os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        return 0, 0
    total = page * total_pages if page > 0 and total_pages > 0 else 0
    free = 0
    try:
        avail_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
    except (AttributeError, OSError, ValueError):
        avail_pages = 0
    if page > 0 and avail_pages > 0:
        free = page * avail_pages
    return total, free


def memory_bytes() -> tuple[int, int]:
    if sys.platform == "win32":
        return _windows_memory()
    if sys.platform == "linux":
        found = _linux_memory()
        if found is not None:
            return found
    return _posix_memory()


def arch_name() -> str:
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        return "x64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    if machine in {"i386", "i686", "x86"}:
        return "ia32"
    return machine or "unknown"


def host_profile() -> dict[str, object]:
    logical_cores = os.cpu_count() or 1
    if logical_cores < 1:
        logical_cores = 1
    allowed_cpus = get_allowed_cpu_ids()
    usable_cores = len(allowed_cpus) if allowed_cpus else logical_cores
    affinity_supported = sys.platform in ("linux", "win32") or hasattr(os, "sched_getaffinity")
    total, free = memory_bytes()
    rec_workers = recommended_workers(usable_cores)
    return {
        "platform": sys.platform,
        "arch": arch_name(),
        "cores": logical_cores,
        "logical_cpu_count": logical_cores,
        "logicalCpuCount": logical_cores,
        "allowed_cpu_ids": allowed_cpus,
        "allowedCpuIds": allowed_cpus,
        "usable_cpu_count": usable_cores,
        "usableCpuCount": usable_cores,
        "affinity_supported": affinity_supported,
        "affinitySupported": affinity_supported,
        "memoryMb": round(total / (1024 * 1024)),
        "freeMb": round(free / (1024 * 1024)),
        "load1": load_average(),
        "tempC": read_temp_c(),
        "recommendedWorkers": rec_workers,
        "recommended_workers": rec_workers,
        "hostname": socket.gethostname(),
        "source": "host",
        "packageVersion": installed_version(),
        "llm": check_llm_status(),
    }


def static_file(url_path: str) -> Path | None:
    parsed = urlparse(url_path)
    raw = unquote(parsed.path)
    if raw in {"", "/"}:
        rel = "index.html"
    else:
        rel = raw.lstrip("/")
    root = STATIC_ROOT.resolve()
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


def _can_serve_app_shell(url_path: str) -> bool:
    path = unquote(urlparse(url_path).path)
    if path.startswith("/api/") or ".." in path:
        return False
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return "." not in name


RUN_MUTATING_PATHS = frozenset({
    "/api/runs/launch",
    "/api/runs/action",  # pause / resume / stop / restart / delete
    "/api/scripts/upload",
    "/api/scripts/run",
    "/api/gates/run",
})


def _is_run_mutating_path(path: str) -> bool:
    """POST routes that start, change, delete runs or execute code on this host."""
    if path in RUN_MUTATING_PATHS:
        return True
    return path.startswith("/api/runs/") and (path.endswith("/pause") or path.endswith("/resume"))


def _from_this_machine(address: str) -> bool:
    host = address.split("%", 1)[0].lower()
    if host.startswith("::ffff:"):
        host = host.removeprefix("::ffff:")
    return host in {"127.0.0.1", "::1", "localhost"}


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "CodonTraceConsole"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    def do_HEAD(self) -> None:
        self._respond(include_body=False)

    def do_GET(self) -> None:
        self._respond(include_body=True)

    def _authorize_inference(self, *, include_body: bool = True) -> bool:
        """Usage credentials are distinct from credentials granting key administration."""
        import hmac
        token = os.environ.get("CODONTRACE_API_TOKEN", "").strip()
        local = (_from_this_machine(self.client_address[0])
                 and not self.headers.get("X-Forwarded-For")
                 and not self.headers.get("X-Real-IP"))
        supplied = self.headers.get("Authorization", "")
        allowed = hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + token).encode("utf-8")) if token else local
        if not allowed:
            self._send(403, "application/json", b'{"ok":false,"error":"API access requires CODONTRACE_API_TOKEN or a direct local connection"}',
                       include_body=include_body, cache="no-store")
        return allowed

    def _is_origin_allowed(self) -> bool:
        """Validate request Origin to prevent cross-origin mutation attacks."""
        origin = self.headers.get("Origin")
        if not origin:
            fetch_site = (self.headers.get("Sec-Fetch-Site") or "").lower()
            if fetch_site == "cross-site":
                return False
            return True

        from urllib.parse import urlparse
        parsed = urlparse(origin)
        origin_host = (parsed.hostname or "").lower()
        if origin_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return True

        host_header = self.headers.get("Host", "")
        if host_header:
            req_host = host_header.split(":", 1)[0].lower()
            if origin_host == req_host:
                return True

        server_host = str(getattr(self.server, "server_address", ("", 0))[0]).lower()
        if server_host and origin_host == server_host:
            return True

        return False

    def _check_update_authorization(self, body_json: dict[str, Any] | None) -> tuple[bool, int, str]:
        """Verify independent authorization token and origin security for release update (R18)."""
        client_ip = self.client_address[0] if self.client_address else ""
        is_local = _from_this_machine(client_ip)
        
        # If proxy headers are present, treat as remote to prevent reverse proxy bypass or spoofing
        if self.headers.get("X-Forwarded-For") or self.headers.get("X-Real-IP"):
            is_local = False

        configured_token = os.environ.get("CODONTRACE_UPDATE_TOKEN", "").strip()

        # Extract provided token from Authorization header, X-Update-Token, or JSON body
        auth_header = self.headers.get("Authorization", "").strip()
        provided_token = ""
        if auth_header.lower().startswith("bearer "):
            provided_token = auth_header[7:].strip()
        elif self.headers.get("X-Update-Token"):
            provided_token = self.headers.get("X-Update-Token", "").strip()
        elif body_json and isinstance(body_json, dict) and body_json.get("token"):
            provided_token = str(body_json.get("token", "")).strip()

        if configured_token:
            import hmac
            if provided_token and hmac.compare_digest(provided_token, configured_token):
                return True, 200, "Authorized via token"
            return False, 401, "Unauthorized: Invalid or missing update authorization token"

        # If no update token is configured, remote clients are strictly forbidden
        if not is_local:
            return False, 403, "Forbidden: Remote update requires CODONTRACE_UPDATE_TOKEN authorization"

        return True, 200, "Authorized (local caller)"

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if origin and not self._is_origin_allowed():
            self.close_connection = True
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Connection", "close")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(204)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        if not self._is_origin_allowed():
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length > 0:
                try:
                    self.rfile.read(min(length, 262144))
                except OSError:
                    pass
            self.close_connection = True
            self._send(
                403,
                "application/json; charset=utf-8",
                b'{"ok": false, "error": "Forbidden: untrusted origin"}\n',
                include_body=True,
                cache="no-store",
                extra_headers={"Connection": "close"},
            )
            return

        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 262144:  # 256 KB max payload
            self.close_connection = True
            self._send(
                413,
                "application/json; charset=utf-8",
                b'{"ok": false, "error": "Payload too large"}\n',
                include_body=True,
                cache="no-store",
                extra_headers={"Connection": "close"},
            )
            return
        raw_body = self.rfile.read(length) if length > 0 else b""

        body_json, json_err = _parse_json_dict(raw_body)
        if json_err is not None:
            self._send(
                400,
                "application/json; charset=utf-8",
                json.dumps({"ok": False, "error": json_err}).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return
        assert body_json is not None

        if path == "/api/providers":
            import hmac

            from codontrace.console import providers
            token = os.environ.get("CODONTRACE_SETTINGS_TOKEN", "").strip()
            supplied = self.headers.get("Authorization", "")
            local = _from_this_machine(self.client_address[0]) and not self.headers.get("X-Forwarded-For") and not self.headers.get("X-Real-IP")
            authorized = hmac.compare_digest(supplied.encode("utf-8"), ("Bearer " + token).encode("utf-8")) if token else local
            if not authorized:
                self._send(403, "application/json", b'{"ok":false,"error":"Provider settings require a local caller or CODONTRACE_SETTINGS_TOKEN"}', include_body=True, cache="no-store")
                return
            try:
                provider = body_json.get("provider")
                action = body_json.get("action", "refresh")
                if action == "save":
                    providers.configure(provider, api_key=body_json.get("api_key"))
                    payload = providers.refresh(provider)
                elif action == "disconnect":
                    payload = providers.configure(provider, disconnect=True)
                elif action == "refresh":
                    payload = providers.refresh(provider)
                else:
                    raise providers.ProviderError("unknown_provider_action")
                code = 200
            except providers.ProviderError as exc:
                payload = {"ok":False,"error":str(exc)}
                code = 400
            except (OSError, TypeError, ValueError):
                payload = {"ok":False,"error":"provider_settings_unavailable"}
                code = 400
            self._send(code, "application/json", json.dumps(payload, allow_nan=False).encode(), include_body=True, cache="no-store")
            return

        if path in ("/api/chat", "/api/chat/abort", "/api/chat/cancel", "/api/chat/endpoint", "/api/science/tools"):
            if not self._authorize_inference():
                return

        # Run-mutating and code-executing endpoints use the same usage credential:
        # CODONTRACE_API_TOKEN when configured, otherwise a direct loopback caller.
        if _is_run_mutating_path(path):
            if not self._authorize_inference():
                return

        if path in ("/api/chat/abort", "/api/chat/cancel"):
            req_id = str(body_json.get("request_id") or body_json.get("requestId") or "").strip()
            if not req_id:
                self._send(
                    400,
                    "application/json; charset=utf-8",
                    json.dumps({"ok": False, "error": "Missing request_id"}, allow_nan=False).encode("utf-8"),
                    include_body=True,
                    cache="no-store",
                )
                return
            aborted = abort_chat_request(req_id)
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps({"ok": True, "aborted": aborted, "request_id": req_id}, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/science/tools":
            from codontrace.console.science_tools import invoke_tool
            result = invoke_tool(str(body_json.get("tool") or ""), body_json.get("args"),
                                 allow_cross_project=body_json.get("allow_cross_project") is True)
            self._send(200 if result["ok"] else 400, "application/json; charset=utf-8",
                       json.dumps(result, allow_nan=False).encode("utf-8"), include_body=True, cache="no-store")
            return

        if path == "/api/chat":
            text = str(body_json.get("text") or body_json.get("message") or "").strip()
            lang = str(body_json.get("lang", "en")).strip()
            ctx = body_json.get("jobContext")
            job_id = body_json.get("jobId") or body_json.get("runId")
            model = body_json.get("model")
            chat_req_id = str(body_json.get("request_id") or body_json.get("requestId") or "").strip() or None
            result = chat_turn(
                text,
                lang,
                ctx if isinstance(ctx, dict) else None,
                job_id=str(job_id).strip() if job_id else None,
                model=str(model).strip() if model else None,
                request_id=chat_req_id,
            )
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(result, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/chat/endpoint":
            ep = body_json.get("endpoint")
            try:
                set_llm_endpoint(ep)
            except ValueError as exc:
                self._send(
                    400,
                    "application/json; charset=utf-8",
                    json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"),
                    include_body=True,
                    cache="no-store",
                )
                return
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(check_llm_status(), allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/runs/launch":
            res = launch_simulation_run(body_json)
            code = int(res.get("status_code", 200 if res.get("ok") else 400))
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(res, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/runs/action":
            run_id = str(body_json.get("runId") or body_json.get("run_id") or "")
            action = str(body_json.get("action", ""))
            res = manage_run_action(run_id, action, request_id=body_json.get("requestId") or body_json.get("request_id"))
            code = int(res.get("status_code", 200 if res.get("ok") else 400))
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(res, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/scripts/upload":
            name = str(body_json.get("name", ""))
            content = str(body_json.get("content", ""))
            res = save_script(name, content)
            code = int(res.get("status_code", 200 if res.get("ok") else 400))
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(res, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/scripts/run":
            name = str(body_json.get("name", ""))
            res = run_script(name)
            code = int(res.get("status_code", 200 if res.get("ok") else 400))
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(res, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path == "/api/gates/run":
            res = run_gate_tests(body_json.get("filter"))
            self._send(
                200,
                "application/json; charset=utf-8",
                json.dumps(res, allow_nan=False).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path.startswith("/api/runs/") and path.endswith("/pause"):
            run_id = path.removeprefix("/api/runs/").removesuffix("/pause")
            if not validate_run_id(run_id):
                self._send(400, "application/json; charset=utf-8", b'{"ok": false, "error": "Invalid run ID"}\n', include_body=True, cache="no-store")
                return
            res = manage_run_action(run_id, "pause")
            code = int(res.get("status_code", 200 if res.get("ok") else 400))
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(res).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path.startswith("/api/runs/") and path.endswith("/resume"):
            run_id = path.removeprefix("/api/runs/").removesuffix("/resume")
            if not validate_run_id(run_id):
                self._send(400, "application/json; charset=utf-8", b'{"ok": false, "error": "Invalid run ID"}\n', include_body=True, cache="no-store")
                return
            res = manage_run_action(run_id, "resume")
            code = int(res.get("status_code", 200 if res.get("ok") else 400))
            self._send(
                code,
                "application/json; charset=utf-8",
                json.dumps(res).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        if path != "/api/release/update":
            self._send(404, "text/plain; charset=utf-8", b"not found\n", include_body=True, cache="no-store")
            return

        authorized, status_code, msg = self._check_update_authorization(body_json)
        if not authorized:
            self._send(
                status_code,
                "application/json; charset=utf-8",
                json.dumps({"ok": False, "error": msg}).encode("utf-8"),
                include_body=True,
                cache="no-store",
            )
            return

        ok, message = update_checkout()
        if ok:
            refresh_release(force=True)
        payload = json.dumps({"ok": ok, "message": message}).encode("utf-8")
        self._send(200, "application/json; charset=utf-8", payload, include_body=True, cache="no-store")

    def _respond(self, *, include_body: bool) -> None:
        path = urlparse(self.path).path
        # @audit-control R10
        # @audit-control R11
        # @audit-control R19
        if path in ("/api/version", "/api/v1/version"):
            metadata = {
                "dataset_version": "1.0",
                "model_version": "1.0",
                "adapter_engine_version": installed_version()
            }
            payload = json.dumps({"version": installed_version(), "metadata": metadata, "lifecycle": "active"}, allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store",
                       extra_headers={"Deprecation": "false", "Link": "<https://api.genesis.local/v1/docs>; rel=\"help\""})
            return
        if path == "/api/host":
            payload = json.dumps(host_profile(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path == "/api/campaign/readiness":
            payload = json.dumps(campaign_inventory(), allow_nan=False, ensure_ascii=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path == "/api/release":
            query = parse_qs(urlparse(self.path).query)
            refresh = query.get("refresh", ["0"])[0] == "1"
            state = refresh_release(force=True) if refresh else release_state()
            payload = json.dumps(state, allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path == "/api/science/tools":
            if not self._authorize_inference(include_body=include_body):
                return
            from codontrace.console.science_tools import tool_catalog
            self._send(200, "application/json; charset=utf-8", json.dumps({"tools": tool_catalog()}, allow_nan=False).encode("utf-8"),
                       include_body=include_body, cache="no-store")
            return

        if path == "/api/chat/status":
            payload = json.dumps(check_llm_status(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path == "/api/providers":
            from codontrace.console import providers
            try:
                payload = providers.provider_catalog()
            except providers.ProviderError as exc:
                payload = {"ok":False,"error":str(exc),"providers":[]}
            self._send(200, "application/json", json.dumps(payload, allow_nan=False).encode(), include_body=include_body, cache="no-store")
            return

        if path == "/api/models":
            payload = json.dumps(list_discovered_models(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path == "/api/runs":
            payload = json.dumps(list_simulation_runs(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path.startswith("/api/runs/") and path.endswith("/zip"):
            run_id = path.removeprefix("/api/runs/").removesuffix("/zip").strip("/")
            if not validate_run_id(run_id):
                self._send(400, "application/json; charset=utf-8", b'{"ok": false, "error": "Invalid run ID or path traversal attempt"}\n', include_body=include_body, cache="no-store")
                return
            zip_bytes = get_run_zip(run_id)
            if zip_bytes is None:
                self._send(404, "application/json; charset=utf-8", b'{"error": "run not found"}', include_body=include_body, cache="no-store")
                return
            self._send(
                200,
                "application/zip",
                zip_bytes,
                include_body=include_body,
                cache="no-store",
                extra_headers={"Content-Disposition": f'attachment; filename="{run_id}.zip"'},
            )
            return
        if path.startswith("/api/runs/"):
            run_id = path.removeprefix("/api/runs/").strip("/")
            if not validate_run_id(run_id):
                self._send(400, "application/json; charset=utf-8", b'{"ok": false, "error": "Invalid run ID or path traversal attempt"}\n', include_body=include_body, cache="no-store")
                return
            details = get_run_details(run_id)
            if details is None:
                self._send(404, "application/json; charset=utf-8", b'{"error": "run not found"}', include_body=include_body, cache="no-store")
                return
            self._send(200, "application/json; charset=utf-8", json.dumps(details, allow_nan=False).encode("utf-8"), include_body=include_body, cache="no-store")
            return
        if path == "/api/scripts":
            payload = json.dumps(list_scripts(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path.startswith("/api/scripts/"):
            script_name = path.removeprefix("/api/scripts/").strip("/")
            if not validate_script_name(script_name):
                self._send(400, "text/plain; charset=utf-8", b"invalid script name\n", include_body=include_body, cache="no-store")
                return
            body_text = read_script(script_name)
            if body_text is None:
                self._send(404, "text/plain; charset=utf-8", b"script not found\n", include_body=include_body, cache="no-store")
                return
            self._send(200, "text/plain; charset=utf-8", body_text.encode("utf-8"), include_body=include_body, cache="no-store")
            return
        if path == "/api/gates":
            payload = json.dumps(list_gates(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        found = static_file(self.path)
        if found is None and _can_serve_app_shell(self.path):
            found = static_file("/")
        if found is None:
            message = b"not found\n"
            self._send(404, "text/plain; charset=utf-8", message, include_body=include_body, cache="no-store")
            return
        content_type = _CONTENT_TYPES.get(found.suffix.lower(), "application/octet-stream")
        cache = "no-store" if found.name == "index.html" else "public, max-age=3600"
        self._send(200, content_type, found.read_bytes(), include_body=include_body, cache=cache)

    def _send(
        self,
        status: int,
        content_type: str,
        body: bytes,
        *,
        include_body: bool,
        cache: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        origin = self.headers.get("Origin")
        if origin:
            if self._is_origin_allowed():
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        if include_body:
            self.wfile.write(body)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    server.daemon_threads = True
    return server


def get_all_ips() -> list[str]:
    ips = []
    try:
        host_name = socket.gethostname()
        ips.extend(socket.gethostbyname_ex(host_name)[2])
    except Exception:
        pass
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip not in ips:
            ips.append(ip)
    except Exception:
        pass
    finally:
        s.close()
        
    if "127.0.0.1" not in ips:
        ips.insert(0, "127.0.0.1")
    return list(dict.fromkeys(ips))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m codontrace.console",
        description=(
            "Serve the CodonTrace Genesis console. "
            "This process does not import the evolution engine and does not set red_queen_proved. "
            "A launch can start a child script."
        ),
    )
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="bind port (default: 8765)")
    parser.add_argument("--open", action="store_true", help="open the page in a browser")
    args = parser.parse_args(argv)
    if not STATIC_ROOT.joinpath("index.html").is_file():
        sys.stderr.write("console static page is missing\n")
        return 1
    
    server = None
    port = args.port
    max_retries = 10 if args.port == 8765 else 1
    for p in range(port, port + max_retries):
        try:
            server = make_server(args.host, p)
            break
        except OSError as exc:
            if p == port + max_retries - 1:
                sys.stderr.write(f"console-bind-error: Unable to bind to any port from {port} to {port + max_retries - 1}. ({exc})\n")
                return 1
    if not server:
        return 1
        
    start_release_monitor()
    address = server.server_address
    bind_host = address[0].decode("ascii") if isinstance(address[0], bytes) else str(address[0])
    actual_port = address[1]
    
    sys.stdout.write("CodonTrace Console running on:\n")
    if bind_host in ("0.0.0.0", "::"):
        for ip in get_all_ips():
            url = f"http://{ip}:{actual_port}/"
            sys.stdout.write(f"  {url}\n")
    else:
        url = f"http://{bind_host}:{actual_port}/"
        sys.stdout.write(f"  {url}\n")
    sys.stdout.flush()
    
    if args.open:
        primary_ip = "127.0.0.1" if bind_host in ("0.0.0.0", "::") else bind_host
        webbrowser.open(f"http://{primary_ip}:{actual_port}/")
        
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("console stopped\n")
    finally:
        server.server_close()
    return 0
