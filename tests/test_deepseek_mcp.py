from __future__ import annotations

import http.server
import importlib.util
import json
import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / ".claude/tools/deepseek_mcp.py"
SPEC = importlib.util.spec_from_file_location("deepseek_mcp", BRIDGE)
assert SPEC and SPEC.loader
DEEPSEEK_MCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEEPSEEK_MCP)


class MockDeepSeekHandler(http.server.BaseHTTPRequestHandler):
    request_body: dict[str, object] | None = None
    authorization = ""

    def do_POST(self) -> None:  # noqa: N802
        size = int(self.headers["Content-Length"])
        type(self).request_body = json.loads(self.rfile.read(size))
        type(self).authorization = self.headers.get("Authorization", "")
        payload = {
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "--- a/app.py\n+++ b/app.py\n"}]}
            ]
        }
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class DeepSeekMcpTests(unittest.TestCase):
    def test_mcp_handshake_and_mocked_proposal_call(self) -> None:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockDeepSeekHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}/responses"
        names = ("DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_REASONING_EFFORT")
        previous_env = {name: os.environ.get(name) for name in names}
        os.environ.update(
            {"DEEPSEEK_API_KEY": "mock-key", "DEEPSEEK_MODEL": "deepseek-flash", "DEEPSEEK_REASONING_EFFORT": "max"}
        )
        previous_call = DEEPSEEK_MCP.call_deepseek
        DEEPSEEK_MCP.call_deepseek = lambda prompt: previous_call(prompt, endpoint=endpoint)
        try:
            listed = DEEPSEEK_MCP.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
            called = DEEPSEEK_MCP.dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "deepseek_bounded_proposal",
                        "arguments": {
                            "task": "Change greeting",
                            "allowed_paths": ["app.py"],
                            "context": "app.py prints hello",
                            "constraints": "unified diff only",
                        },
                    },
                }
            )
        finally:
            DEEPSEEK_MCP.call_deepseek = previous_call
            for name, value in previous_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            server.shutdown()
            server.server_close()
        assert listed and called
        self.assertEqual(listed["result"]["tools"][0]["name"], "deepseek_bounded_proposal")
        self.assertIn("--- a/app.py", called["result"]["content"][0]["text"])
        body = MockDeepSeekHandler.request_body
        assert body is not None
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["reasoning"], {"effort": "max"})
        self.assertEqual(MockDeepSeekHandler.authorization, "Bearer mock-key")
        self.assertNotIn("mock-key", json.dumps(body))

    def test_missing_key_invalid_effort_and_oversized_payload_are_rejected(self) -> None:
        environment = dict(os.environ)
        environment.pop("DEEPSEEK_API_KEY", None)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "deepseek_bounded_proposal",
                "arguments": {"task": "x", "allowed_paths": ["x.py"], "context": "x"},
            },
        }
        result = subprocess.run(
            [sys.executable, str(BRIDGE)],
            input=json.dumps(message) + "\n",
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )
        self.assertIn("DEEPSEEK_API_KEY is not set", json.loads(result.stdout)["error"]["message"])
        previous_key = os.environ.get("DEEPSEEK_API_KEY")
        previous_effort = os.environ.get("DEEPSEEK_REASONING_EFFORT")
        os.environ["DEEPSEEK_API_KEY"] = "mock-key"
        os.environ["DEEPSEEK_REASONING_EFFORT"] = "medium"
        try:
            with self.assertRaises(DEEPSEEK_MCP.BridgeError):
                DEEPSEEK_MCP.validate_runtime()
        finally:
            if previous_key is None:
                os.environ.pop("DEEPSEEK_API_KEY", None)
            else:
                os.environ["DEEPSEEK_API_KEY"] = previous_key
            if previous_effort is None:
                os.environ.pop("DEEPSEEK_REASONING_EFFORT", None)
            else:
                os.environ["DEEPSEEK_REASONING_EFFORT"] = previous_effort
        with self.assertRaises(DEEPSEEK_MCP.BridgeError):
            DEEPSEEK_MCP.build_prompt(
                {"task": "x" * 150_000, "allowed_paths": ["x.py"], "context": "y" * 150_000, "constraints": "z"}
            )


if __name__ == "__main__":
    unittest.main()
