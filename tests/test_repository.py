from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_validator(self) -> None:
        result = subprocess.run([sys.executable, "scripts/validate.py"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_archives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, "scripts/build_release.py", "--output-dir", temp], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = [Path(temp) / f"claude-bounded-orchestrator-v0.3.0-{kind}.zip" for kind in ("source", "macos-linux", "windows")]
            self.assertTrue(all(path.is_file() for path in paths))
            with zipfile.ZipFile(paths[0]) as archive:
                names = set(archive.namelist())
                self.assertIn("claude-bounded-orchestrator/.claude/agents/implementer.md", names)
                self.assertIn("claude-bounded-orchestrator/.claude/tools/openai_mcp.py", names)
                self.assertFalse(any("/.git/" in name or name.endswith(".pyc") for name in names))
            with zipfile.ZipFile(paths[2]) as archive:
                data = archive.read("claude-bounded-orchestrator/setup.ps1")
                self.assertIn(b"\r\n", data)


if __name__ == "__main__":
    unittest.main()
