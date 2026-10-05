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
from urllib.parse import parse_qs, unquote, urlparse

from codontrace.console.release import (
    installed_version,
    refresh_release,
    release_state,
    start_release_monitor,
    update_checkout,
)

STATIC_ROOT = Path(__file__).resolve().parent / "static"
_CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}


def recommended_workers(cores: int) -> int:
    count = cores if cores > 0 else 1
    if count > 4:
        return 4
    return count


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
    cores = os.cpu_count() or 1
    if cores < 1:
        cores = 1
    total, free = memory_bytes()
    return {
        "platform": sys.platform,
        "arch": arch_name(),
        "cores": cores,
        "memoryMb": round(total / (1024 * 1024)),
        "freeMb": round(free / (1024 * 1024)),
        "load1": load_average(),
        "tempC": read_temp_c(),
        "recommendedWorkers": recommended_workers(cores),
        "hostname": socket.gethostname(),
        "source": "host",
        "packageVersion": installed_version(),
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

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length > 4096:
            self._send(400, "text/plain; charset=utf-8", b"body too large\n", include_body=True, cache="no-store")
            return
        if length > 0:
            self.rfile.read(length)
        if path != "/api/release/update":
            self._send(404, "text/plain; charset=utf-8", b"not found\n", include_body=True, cache="no-store")
            return
        if not _from_this_machine(self.client_address[0]):
            payload = json.dumps({"ok": False, "message": "Update is only accepted from this machine."}).encode("utf-8")
            self._send(403, "application/json; charset=utf-8", payload, include_body=True, cache="no-store")
            return
        ok, message = update_checkout()
        if ok:
            refresh_release(force=True)
        payload = json.dumps({"ok": ok, "message": message}).encode("utf-8")
        self._send(200, "application/json; charset=utf-8", payload, include_body=True, cache="no-store")

    def _respond(self, *, include_body: bool) -> None:
        path = urlparse(self.path).path
        if path == "/api/host":
            payload = json.dumps(host_profile(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload, include_body=include_body, cache="no-store")
            return
        if path == "/api/release":
            query = parse_qs(urlparse(self.path).query)
            refresh = query.get("refresh", ["0"])[0] == "1"
            state = refresh_release(force=True) if refresh else release_state()
            payload = json.dumps(state, allow_nan=False).encode("utf-8")
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

    def _send(self, status: int, content_type: str, body: bytes, *, include_body: bool, cache: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if include_body:
            self.wfile.write(body)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m codontrace.console",
        description=(
            "Serve the CodonTrace Genesis preview console. "
            "Does not run the evolution engine and does not set red_queen_proved."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="bind port (default: 8765)")
    parser.add_argument("--open", action="store_true", help="open the page in a browser")
    args = parser.parse_args(argv)
    if not STATIC_ROOT.joinpath("index.html").is_file():
        sys.stderr.write("console static page is missing\n")
        return 1
    try:
        server = make_server(args.host, args.port)
    except OSError as exc:
        sys.stderr.write(f"console-bind-error: {exc}\n")
        return 1
    start_release_monitor()
    address = server.server_address
    shown_host = address[0].decode("ascii") if isinstance(address[0], bytes) else str(address[0])
    url = f"http://{shown_host}:{address[1]}/"
    sys.stdout.write(url + "\n")
    sys.stdout.flush()
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("console stopped\n")
    finally:
        server.server_close()
    return 0
