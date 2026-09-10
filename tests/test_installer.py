from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install.py"


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.target = Path(self.temp.name) / "target"
        self.target.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def installer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(INSTALLER), str(self.target), *args], text=True, capture_output=True, check=False)

    def test_fresh_idempotent_install_and_uninstall(self) -> None:
        self.assertEqual(self.installer().returncode, 0)
        self.assertEqual(self.installer().returncode, 0)
        settings = json.loads((self.target / ".claude/settings.json").read_text())
        self.assertEqual(settings["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"], "1")
        self.assertEqual((self.target / "CLAUDE.md").read_text().count("<!-- claude-bounded-orchestrator:start -->"), 1)
        self.assertEqual(self.installer("--uninstall").returncode, 0)
        self.assertFalse((self.target / ".claude/agents/implementer.md").exists())
        self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_preserves_existing_settings_and_conflict(self) -> None:
        settings = self.target / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_text('{"custom": true}\n')
        agent = self.target / ".claude/agents/explorer.md"
        agent.parent.mkdir()
        agent.write_text("custom\n")
        self.assertEqual(self.installer().returncode, 0)
        self.assertEqual(settings.read_text(), '{"custom": true}\n')
        self.assertEqual(agent.read_text(), "custom\n")
        self.assertTrue((self.target / ".claude/bounded-orchestrator.settings.example.json").exists())

    def test_force_backs_up_and_uninstall_keeps_modified(self) -> None:
        agent = self.target / ".claude/agents/explorer.md"
        agent.parent.mkdir(parents=True)
        agent.write_text("custom\n")
        self.assertEqual(self.installer("--force").returncode, 0)
        self.assertEqual(len(list((self.target / ".claude/.bounded-orchestrator/backups").rglob("explorer.md"))), 1)
        agent.write_text(agent.read_text() + "local\n")
        result = self.installer("--uninstall")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(agent.exists())
        self.assertIn("modified after installation", result.stdout)

    def test_dry_run_writes_nothing(self) -> None:
        self.assertEqual(self.installer("--dry-run").returncode, 0)
        self.assertEqual(list(self.target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
