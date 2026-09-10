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
BRIDGE = ROOT / ".claude/tools/openai_mcp.py"
SPEC = importlib.util.spec_from_file_location("openai_mcp", BRIDGE)
assert SPEC and SPEC.loader
OPENAI_MCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPENAI_MCP)


class MockResponsesHandler(http.server.BaseHTTPRequestHandler):
    request_body: dict[str, object] | None = None
    authorization = ""

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        size = int(self.headers["Content-Length"])
        type(self).request_body = json.loads(self.rfile.read(size))
        type(self).authorization = self.headers.get("Authorization", "")
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "--- a/app.py\n+++ b/app.py\n"}],
                }
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


class OpenAIMcpTests(unittest.TestCase):
    def test_mcp_handshake_tool_list_and_mocked_provider_call(self) -> None:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockResponsesHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = f"http://127.0.0.1:{server.server_port}/v1/responses"
        previous = {name: os.environ.get(name) for name in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_REASONING_EFFORT")}
        os.environ.update(
            {"OPENAI_API_KEY": "mock-key", "OPENAI_MODEL": "gpt-5.6-sol", "OPENAI_REASONING_EFFORT": "high"}
        )
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "openai_bounded_implementation",
                    "arguments": {
                        "task": "Change the greeting",
                        "allowed_paths": ["app.py"],
                        "context": "app.py currently prints hello",
                        "constraints": "Return a unified diff only",
                    },
                },
            },
        ]
        previous_call = OPENAI_MCP.call_openai
        OPENAI_MCP.call_openai = lambda prompt: previous_call(prompt, endpoint=endpoint)
        try:
            responses = [OPENAI_MCP.dispatch(message) for message in messages]
            assert all(response is not None for response in responses)
        finally:
            OPENAI_MCP.call_openai = previous_call
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
            server.shutdown()
            server.server_close()
        assert responses[0] and responses[1] and responses[2]
        self.assertEqual(responses[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(responses[1]["result"]["tools"][0]["name"], "openai_bounded_implementation")
        self.assertIn("--- a/app.py", responses[2]["result"]["content"][0]["text"])
        body = MockResponsesHandler.request_body
        self.assertIsNotNone(body)
        assert body is not None
        self.assertEqual(body["model"], "gpt-5.6-sol")
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertEqual(MockResponsesHandler.authorization, "Bearer mock-key")
        serialized = json.dumps(body)
        self.assertIn("app.py", serialized)
        self.assertNotIn("mock-key", serialized)

    def test_missing_key_is_reported_without_crashing_or_writing(self) -> None:
        environment = dict(os.environ)
        environment.pop("OPENAI_API_KEY", None)
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "openai_bounded_implementation",
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
        response = json.loads(result.stdout)
        self.assertIn("OPENAI_API_KEY is not set", response["error"]["message"])

    def test_traversal_path_is_rejected_before_provider_call(self) -> None:
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "openai_bounded_implementation",
                "arguments": {"task": "x", "allowed_paths": ["../secret"], "context": "x"},
            },
        }
        result = subprocess.run(
            [sys.executable, str(BRIDGE)],
            input=json.dumps(message) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        response = json.loads(result.stdout)
        self.assertIn("unsafe allowed path", response["error"]["message"])


if __name__ == "__main__":
    unittest.main()
