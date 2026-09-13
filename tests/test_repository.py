from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_validator(self) -> None:
        result = subprocess.run([sys.executable, "scripts/validate.py"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_release_archives(self) -> None:
        runtime = ROOT / ".claude/.bounded-orchestrator"
        sentinel = runtime / "release-private-sentinel.json"
        private_marker = f"release-private-{uuid.uuid4().hex}"
        sentinel.write_text(f'{{"secret": "{private_marker}"}}\n', encoding="utf-8")
        try:
            with tempfile.TemporaryDirectory() as temp:
                result = subprocess.run([sys.executable, "scripts/build_release.py", "--output-dir", temp], cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                paths = [Path(temp) / f"claude-bounded-orchestrator-v0.4.0-{kind}.zip" for kind in ("source", "macos-linux", "windows")]
                self.assertTrue(all(path.is_file() for path in paths))
                runtime_prefix = "claude-bounded-orchestrator/.claude/.bounded-orchestrator/"
                for path in paths:
                    with self.subTest(archive=path.name), zipfile.ZipFile(path) as archive:
                        names = set(archive.namelist())
                        runtime_names = {name for name in names if name.startswith(runtime_prefix)}
                        self.assertEqual(runtime_names, {runtime_prefix + ".gitignore"})
                        self.assertNotIn(runtime_prefix + sentinel.name, names)
                        marker = private_marker.encode("utf-8")
                        self.assertFalse(any(marker in archive.read(name) for name in names))
                        self.assertFalse(any("/.git/" in name or name.endswith(".pyc") for name in names))
                with zipfile.ZipFile(paths[0]) as archive:
                    names = set(archive.namelist())
                    self.assertIn("claude-bounded-orchestrator/.claude/agents/implementer.md", names)
                    self.assertIn("claude-bounded-orchestrator/.claude/tools/openai_mcp.py", names)
                    self.assertIn("claude-bounded-orchestrator/.claude/tools/deepseek_mcp.py", names)
                with zipfile.ZipFile(paths[2]) as archive:
                    data = archive.read("claude-bounded-orchestrator/setup.ps1")
                    self.assertIn(b"\r\n", data)
        finally:
            sentinel.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
