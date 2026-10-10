"""Official cloud providers. Server-only credentials and bounded explicit discovery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

PROVIDERS = {
    "openai": ("OpenAI / GPT", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    "deepseek": ("DeepSeek", "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
}
_LOCK = threading.RLock()
_CACHE: dict[str, dict[str, Any]] = {}
def _positive_limit(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return min(maximum, value) if value > 0 else default


_ACTIVE_REQUESTS = threading.BoundedSemaphore(
    _positive_limit("CODONTRACE_CLOUD_MAX_CONCURRENT", 4, 32)
)
_REQUEST_TIMES: deque[float] = deque()


class _LimitedResponse:
    """Keep the admission slot until the response body is closed."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.closed = False

    def __enter__(self) -> _LimitedResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self.response, name)

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                self.response.close()
            finally:
                _ACTIVE_REQUESTS.release()


class ProviderError(ValueError):
    """Safe public error code; never contains credentials or raw upstream bodies."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any, headers: Any, newurl: Any) -> None:
        raise ProviderError("provider_redirect_refused")


def open_request(request: urllib.request.Request, timeout: float) -> Any:
    # Admission is fail-fast: no unbounded thread/credit backlog on small boards.
    if not _ACTIVE_REQUESTS.acquire(blocking=False):
        raise ProviderError("provider_concurrency_limit")
    try:
        now = time.monotonic()
        with _LOCK:
            while _REQUEST_TIMES and _REQUEST_TIMES[0] <= now - 60:
                _REQUEST_TIMES.popleft()
            if len(_REQUEST_TIMES) >= _positive_limit("CODONTRACE_CLOUD_REQUESTS_PER_MINUTE", 30, 10000):
                raise ProviderError("provider_local_rate_limit")
            _REQUEST_TIMES.append(now)
        response = urllib.request.build_opener(_NoRedirect()).open(request, timeout=timeout)
        return _LimitedResponse(response)
    except BaseException:
        _ACTIVE_REQUESTS.release()
        raise


def _path() -> Path:
    directory = Path(os.environ.get("CODONTRACE_CONFIG_DIR", str(Path.home() / ".config" / "codontrace")))
    return directory / "cloud_providers.json"


def _load() -> dict[str, Any]:
    p = _path()
    if not p.is_file():
        return {}
    try:
        if p.stat().st_size > 16384:
            raise ProviderError("provider_config_too_large")
        value = json.loads(p.read_text())
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, ValueError) as exc:
        raise ProviderError("provider_config_invalid") from exc


def _write(value: dict[str, Any]) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".cloud-", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _credential(provider: str) -> tuple[str, bool, str]:
    if provider not in PROVIDERS:
        raise ProviderError("unknown_provider")
    config = _load().get(provider) or {}
    if not isinstance(config, dict):
        raise ProviderError("provider_config_invalid")
    enabled = config.get("enabled", True) is True
    env = os.environ.get(PROVIDERS[provider][2], "").strip()
    key = env or config.get("api_key", "")
    return str(key) if enabled else "", enabled, "environment" if env else "server_file"


def configure(provider: str, *, api_key: str | None = None, disconnect: bool = False) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise ProviderError("unknown_provider")
    if api_key is not None and (
        not isinstance(api_key, str)
        or not 8 <= len(api_key.strip()) <= 512
        or any(c.isspace() for c in api_key.strip())
    ):
        raise ProviderError("invalid_api_key")
    with _LOCK:
        data = _load()
        entry = data.get(provider) or {}
        entry = dict(entry)
        if disconnect:
            entry = {"enabled": False}
        else:
            entry["enabled"] = True
            if api_key is not None:
                entry["api_key"] = api_key.strip()
        data[provider] = entry
        _write(data)
        _CACHE.pop(provider, None)
    return provider_catalog()


def _fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def refresh(provider: str) -> dict[str, Any]:
    with _LOCK:
        key, enabled, _ = _credential(provider)
    if not enabled or not key:
        raise ProviderError("provider_not_configured")
    request = urllib.request.Request(
        PROVIDERS[provider][1] + "/models",
        headers={"Authorization": "Bearer " + key, "User-Agent": "CodonTraceConsole/1.0"},
    )
    result: dict[str, Any] = {"models": [], "updated_at": time.time(), "fingerprint": _fingerprint(key)}
    try:
        with open_request(request, 6) as response:
            raw = response.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024:
                raise ProviderError("provider_catalog_too_large")
            body = json.loads(raw)
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            raise ProviderError("provider_catalog_invalid")
        ids = sorted(
            {
                r["id"]
                for r in body["data"][:2000]
                if isinstance(r, dict)
                and isinstance(r.get("id"), str)
                and re.fullmatch(r"[A-Za-z0-9._:/-]{1,180}", r["id"])
            }
        )
        if not ids:
            raise ProviderError("provider_catalog_empty")
        result["models"] = [
            {"id": provider + "::" + m, "name": m, "provider": provider, "chat_candidate": _chat_candidate(provider, m)}
            for m in ids
        ]
        result["error"] = None
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        result["error"] = f"provider_http_{code}"
    except (urllib.error.URLError, TimeoutError, OSError):
        result["error"] = "provider_unreachable"
    except (ProviderError, ValueError, TypeError):
        result["error"] = "provider_catalog_invalid"
    with _LOCK:
        now, enabled, _ = _credential(provider)
        if enabled and now and _fingerprint(now) == result["fingerprint"]:
            _CACHE[provider] = result
    return provider_catalog()


def _chat_candidate(provider: str, name: str) -> bool:
    if provider == "deepseek":
        return True
    return name.startswith(("gpt-", "chatgpt-", "o1", "o3", "o4", "ft:gpt-")) and not any(
        s in name for s in ("audio", "realtime", "transcribe", "tts", "image", "search", "codex")
    )


def provider_catalog() -> dict[str, Any]:
    rows = []
    with _LOCK:
        for provider, (title, base, _) in PROVIDERS.items():
            key, enabled, source = _credential(provider)
            cached = _CACHE.get(provider, {})
            if not key or cached.get("fingerprint") != _fingerprint(key):
                cached = {}
            rows.append(
                {
                    "id": provider,
                    "title": title,
                    "base_url": base,
                    "configured": bool(key),
                    "enabled": enabled,
                    "credential_source": source,
                    "models": cached.get("models", []),
                    "error": cached.get("error"),
                    "updated_at": cached.get("updated_at"),
                }
            )
    return {
        "ok": True,
        "providers": rows,
        "notice": "Model IDs are fetched, not hardcoded. Listing access does not guarantee Chat Completions/tool compatibility.",
    }


def cloud_model(model: str | None) -> bool:
    return isinstance(model, str) and "::" in model


def resolve(model: str) -> tuple[str, str, dict[str, str], str]:
    provider, identifier = model.split("::", 1)
    if provider not in PROVIDERS or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,180}", identifier):
        raise ProviderError("invalid_provider_model")
    with _LOCK:
        key, enabled, _ = _credential(provider)
    if not enabled or not key:
        raise ProviderError("provider_not_configured")
    return provider, PROVIDERS[provider][1] + "/chat/completions", {"Authorization": "Bearer " + key}, identifier
