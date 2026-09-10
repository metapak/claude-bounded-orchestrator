from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install.py"
EXPECTED_ROUTING = {
    "explorer": ("sonnet", "medium"),
    "researcher": ("sonnet", "medium"),
    "implementer": ("sonnet", "high"),
    "verifier": ("sonnet", "high"),
    "qa-operator": ("sonnet", "high"),
    "failure-analyst": ("opus", "high"),
    "reviewer": ("opus", "high"),
    "advisor": ("opus", "xhigh"),
}


def agent_frontmatter(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8").split("\n---\n", 1)[0][4:]
    return {
        key.strip(): value.strip()
        for line in raw.splitlines()
        if ":" in line
        for key, value in [line.split(":", 1)]
    }


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
        self.assertEqual(settings["model"], "opus")
        self.assertEqual(settings["effortLevel"], "xhigh")
        self.assertEqual(settings["env"]["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"], "1")
        for name, (model, effort) in EXPECTED_ROUTING.items():
            agent = agent_frontmatter(self.target / f".claude/agents/{name}.md")
            self.assertEqual(agent["model"], model)
            self.assertEqual(agent["effort"], effort)
        instructions = (self.target / "CLAUDE.md").read_text()
        self.assertEqual(instructions.count("<!-- claude-bounded-orchestrator:start -->"), 1)
        for phrase in (
            "objective, exact scope, write ownership or read-only status",
            "freeze the candidate",
            "reject its review if the candidate changes",
            "one focused repair for a proven verification failure",
            "one focused repair for accepted material review findings",
            "all required agents have stopped",
            "final candidate still matches the reviewed identity",
        ):
            self.assertIn(phrase, instructions)
        self.assertEqual(self.installer("--uninstall").returncode, 0)
        self.assertFalse((self.target / ".claude/agents/implementer.md").exists())
        self.assertFalse((self.target / "CLAUDE.md").exists())
        self.assertTrue((self.target / ".claude/.bounded-orchestrator/.gitignore").exists())

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
        example = json.loads(
            (self.target / ".claude/bounded-orchestrator.settings.example.json").read_text()
        )
        self.assertEqual(example["model"], "opus")
        self.assertEqual(example["effortLevel"], "xhigh")

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

    def test_uninstall_rejects_absolute_and_traversal_manifest_entries(self) -> None:
        self.assertEqual(self.installer().returncode, 0)
        manifest_path = self.target / ".claude/.bounded-orchestrator/install.json"
        manifest = json.loads(manifest_path.read_text())
        external = Path(self.temp.name) / "external.txt"
        external.write_text("keep\n")

        for malicious in (str(external.resolve()), "../../external.txt"):
            with self.subTest(malicious=malicious):
                current = json.loads(json.dumps(manifest))
                current["files"][malicious] = {
                    "owned": True,
                    "sha256": hashlib.sha256(external.read_bytes()).hexdigest(),
                }
                manifest_path.write_text(json.dumps(current))
                result = self.installer("--uninstall")
                self.assertEqual(result.returncode, 2)
                self.assertIn("unmanaged uninstall path", result.stderr)
                self.assertEqual(external.read_text(), "keep\n")

    @unittest.skipIf(os.name == "nt", "directory symlinks require extra Windows privileges")
    def test_uninstall_rejects_symlinked_parent_without_deleting_external(self) -> None:
        self.assertEqual(self.installer().returncode, 0)
        agents = self.target / ".claude/agents"
        shutil.rmtree(agents)
        external = Path(self.temp.name) / "external-agents"
        external.mkdir()
        external_file = external / "explorer.md"
        external_file.write_text("keep external\n")
        agents.symlink_to(external, target_is_directory=True)

        result = self.installer("--uninstall")
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlinked directory", result.stderr)
        self.assertEqual(external_file.read_text(), "keep external\n")

    def test_uninstall_keeps_runtime_ignore_for_ledger_and_backups(self) -> None:
        settings = self.target / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_text('{"custom": true}\n')
        self.assertEqual(self.installer("--force-settings").returncode, 0)
        ledger = self.target / ".claude/tools/task_ledger.py"
        initialized = subprocess.run(
            [sys.executable, str(ledger), "--repo", str(self.target), "init"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        backup = next((self.target / ".claude/.bounded-orchestrator/backups").rglob("settings.json"))
        self.assertEqual(self.installer("--uninstall").returncode, 0)
        runtime_ignore = self.target / ".claude/.bounded-orchestrator/.gitignore"
        self.assertTrue(runtime_ignore.is_file())
        subprocess.run(["git", "init", "-b", "main"], cwd=self.target, check=True, capture_output=True)
        for path in (
            self.target / ".claude/.bounded-orchestrator/tasks.json",
            backup,
        ):
            result = subprocess.run(
                ["git", "check-ignore", "-q", str(path.relative_to(self.target))],
                cwd=self.target,
                check=False,
            )
            self.assertEqual(result.returncode, 0, f"not ignored: {path}")


if __name__ == "__main__":
    unittest.main()
