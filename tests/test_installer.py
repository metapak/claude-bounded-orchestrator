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

    def installer(self, *args: str, input_text: str | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), str(self.target), *args],
            text=True,
            input=input_text,
            env=env,
            capture_output=True,
            check=False,
        )

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
        self.assertEqual(self.installer("--dry-run", "--preset", "quality", "--external-openai").returncode, 0)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_prepared_profiles_and_noninteractive_overrides(self) -> None:
        self.assertEqual(self.installer("--preset", "quality").returncode, 0)
        settings = json.loads((self.target / ".claude/settings.json").read_text())
        self.assertEqual((settings["model"], settings["effortLevel"]), ("opus", "xhigh"))
        explorer = agent_frontmatter(self.target / ".claude/agents/explorer.md")
        self.assertEqual((explorer["model"], explorer["effort"]), ("opus", "high"))

        other = Path(self.temp.name) / "economy"
        other.mkdir()
        result = subprocess.run(
            [
                sys.executable,
                str(INSTALLER),
                str(other),
                "--preset",
                "economy",
                "--role-model",
                "implementer=claude-sonnet-4-6",
                "--role-effort",
                "implementer=xhigh",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        economy = json.loads((other / ".claude/settings.json").read_text())
        self.assertEqual((economy["model"], economy["effortLevel"]), ("sonnet", "medium"))
        implementer = agent_frontmatter(other / ".claude/agents/implementer.md")
        self.assertEqual((implementer["model"], implementer["effort"]), ("claude-sonnet-4-6", "xhigh"))

    def test_interactive_custom_profile_prompts_for_every_role(self) -> None:
        answers = ["4", "sonnet", "low"] + [""] * 16 + ["1"]
        result = self.installer("--interactive", input_text="\n".join(answers) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads((self.target / ".claude/settings.json").read_text())
        self.assertEqual((settings["model"], settings["effortLevel"]), ("sonnet", "low"))
        manifest = json.loads((self.target / ".claude/.bounded-orchestrator/install.json").read_text())
        self.assertEqual(manifest["preset"], "custom")
        self.assertFalse(manifest["external_openai"])

    def test_rejects_frontmatter_injection_and_invalid_native_effort_before_writing(self) -> None:
        cases = (
            ("model-newline", ["--role-model", "implementer=sonnet\nname: injected"]),
            ("model-colon", ["--role-model", "implementer=sonnet:injected"]),
            ("effort", ["--role-effort", "implementer=ultra"]),
        )
        for name, arguments in cases:
            with self.subTest(name=name):
                target = Path(self.temp.name) / name
                target.mkdir()
                result = subprocess.run(
                    [sys.executable, str(INSTALLER), str(target), *arguments],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(list(target.iterdir()), [])

    def test_interactive_invalid_model_is_rejected_before_rendering(self) -> None:
        answers = ["4", "sonnet:name", "low"] + [""] * 16 + ["1"]
        result = self.installer("--interactive", input_text="\n".join(answers) + "\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid model", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_rejects_invalid_external_model_and_effort_before_writing(self) -> None:
        cases = (
            ("model", ["--external-openai", "--external-model", "gpt:injected"]),
            ("effort", ["--external-openai", "--external-effort", "ultra"]),
        )
        for name, arguments in cases:
            with self.subTest(name=name):
                target = Path(self.temp.name) / f"external-{name}"
                target.mkdir()
                result = subprocess.run(
                    [sys.executable, str(INSTALLER), str(target), *arguments],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(list(target.iterdir()), [])

    def test_external_openai_configuration_never_persists_api_key(self) -> None:
        secret = "test-secret-that-must-not-be-written"
        environment = dict(os.environ)
        environment["OPENAI_API_KEY"] = secret
        result = self.installer(
            "--external-openai",
            "--external-model",
            "gpt-5.6-sol",
            "--external-effort",
            "high",
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.target / ".mcp.json").read_text())
        server = config["mcpServers"]["openai-bounded-implementer"]
        self.assertEqual(server["env"]["OPENAI_MODEL"], "gpt-5.6-sol")
        self.assertEqual(server["env"]["OPENAI_REASONING_EFFORT"], "high")
        self.assertNotIn("OPENAI_API_KEY", json.dumps(config))
        for path in self.target.rglob("*"):
            if path.is_file():
                self.assertNotIn(secret, path.read_text(encoding="utf-8", errors="ignore"))
        self.assertEqual(self.installer("--uninstall").returncode, 0)
        self.assertFalse((self.target / ".mcp.json").exists())

    def test_external_openai_merges_and_surgically_uninstalls_mcp_entry(self) -> None:
        mcp = self.target / ".mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {"existing": {"command": "keep"}}}) + "\n")
        self.assertEqual(self.installer("--external-openai").returncode, 0)
        installed = json.loads(mcp.read_text())
        self.assertIn("existing", installed["mcpServers"])
        self.assertIn("openai-bounded-implementer", installed["mcpServers"])
        self.assertEqual(self.installer("--uninstall").returncode, 0)
        remaining = json.loads(mcp.read_text())
        self.assertEqual(remaining, {"mcpServers": {"existing": {"command": "keep"}}})

    def test_external_openai_preserves_conflicting_mcp_entry(self) -> None:
        original = {"mcpServers": {"openai-bounded-implementer": {"command": "custom"}}}
        mcp = self.target / ".mcp.json"
        mcp.write_text(json.dumps(original) + "\n")
        result = self.installer("--external-openai")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(mcp.read_text()), original)
        example = json.loads((self.target / ".claude/bounded-orchestrator.mcp.example.json").read_text())
        self.assertIn("openai-bounded-implementer", example["mcpServers"])

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
