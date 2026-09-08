import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_adk_workflow_uses_mcp_and_a2a(monkeypatch):
    port = free_port()
    env = os.environ | {"A2A_HOST": "127.0.0.1", "A2A_PORT": str(port), "A2A_URL": f"http://127.0.0.1:{port}", "NO_PROXY": "127.0.0.1,localhost"}
    root = Path(__file__).resolve().parents[1]
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "sentinel.policy_agent:app", "--host", "127.0.0.1", "--port", str(port)], cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise AssertionError("A2A policy server did not start")
        monkeypatch.setenv("A2A_URL", env["A2A_URL"])
        monkeypatch.setenv("MODEL_MODE", "demo")
        from sentinel.workflow import investigate
        result = asyncio.run(investigate("integration-case", "fee_mismatch"))
    finally:
        server.terminate()
        server.wait(timeout=10)

    assert result["eligible"] is True
    assert result["adjustment_minor"] == 1500
    assert result["evidence"]["reference"] == "processor-batch-042"
    assert any(event["agent"] == "remote_policy" for event in result["timeline"])
