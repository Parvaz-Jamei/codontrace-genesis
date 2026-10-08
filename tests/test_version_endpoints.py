"""Integration tests for Phase 4 version endpoints (R10, R11, R19)."""

import json
import threading
import urllib.error
import urllib.request

from codontrace.console.server import make_server


def test_version_endpoints_r10_r11_r19():
    """R10, R11, R19: Verify the /api/version and /api/v1/version endpoints."""
    server = make_server("127.0.0.1", 0)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        for path in ("/api/version", "/api/v1/version"):
            url = f"http://127.0.0.1:{port}{path}"
            req = urllib.request.Request(url, headers={"Origin": f"http://127.0.0.1:{port}"})
            
            with urllib.request.urlopen(req) as resp:
                assert resp.status == 200
                
                # Check custom headers (Deprecation, Link)
                assert resp.getheader("Deprecation") == "false"
                assert "api.genesis.local/v1/docs" in resp.getheader("Link")
                
                data = json.loads(resp.read().decode("utf-8"))
                
                assert "version" in data
                assert "metadata" in data
                assert "lifecycle" in data
                assert data["lifecycle"] == "active"
                
                metadata = data["metadata"]
                assert "dataset_version" in metadata
                assert "model_version" in metadata
                assert "adapter_engine_version" in metadata
                
                assert metadata["dataset_version"] == "1.0"
                assert metadata["model_version"] == "1.0"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1.0)
