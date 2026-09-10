from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".claude/tools/task_ledger.py"


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(TOOL), "--repo", str(self.repo), *args], text=True, capture_output=True, check=False)

    def test_dependencies_transitions_gate_and_private_atomic_state(self) -> None:
        self.assertEqual(self.tool("init").returncode, 0)
        self.assertEqual(self.tool("add", "MAP", "--summary", "Map files", "--role", "explorer").returncode, 0)
        self.assertEqual(self.tool("add", "BUILD", "--summary", "Build fix", "--role", "implementer", "--depends-on", "MAP").returncode, 0)
        self.assertEqual(self.tool("start", "BUILD").returncode, 2)
        self.assertEqual(self.tool("check").returncode, 2)
        self.assertEqual(self.tool("start", "MAP").returncode, 0)
        self.assertEqual(self.tool("complete", "MAP", "--evidence", "Paths identified").returncode, 0)
        self.assertEqual(self.tool("start", "BUILD").returncode, 0)
        self.assertEqual(self.tool("complete", "BUILD", "--evidence", "Focused tests passed").returncode, 0)
        self.assertEqual(self.tool("check").returncode, 0)
        path = self.repo / ".claude/.bounded-orchestrator/tasks.json"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        data = json.loads(path.read_text())
        self.assertEqual([item["status"] for item in data["tasks"]], ["complete", "complete"])
        self.assertFalse(path.with_name(path.name + ".lock").exists())

    def test_block_and_restart(self) -> None:
        self.tool("init")
        self.tool("add", "QA", "--summary", "Check flow", "--role", "qa-operator")
        self.tool("start", "QA")
        self.assertEqual(self.tool("block", "QA", "--evidence", "Environment unavailable").returncode, 0)
        self.assertEqual(self.tool("start", "QA").returncode, 0)

    def test_rejects_unknown_dependency_and_long_evidence(self) -> None:
        self.tool("init")
        self.assertEqual(self.tool("add", "X", "--summary", "x", "--role", "owner", "--depends-on", "NOPE").returncode, 2)
        self.tool("add", "X", "--summary", "x", "--role", "owner")
        self.tool("start", "X")
        self.assertEqual(self.tool("complete", "X", "--evidence", "x" * 241).returncode, 2)


if __name__ == "__main__":
    unittest.main()
