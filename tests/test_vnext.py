from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VNextTests(unittest.TestCase):
    def test_quota_saver_and_managed_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), str(target), "--preset", "quota-saver"], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            settings = json.loads((target / ".claude/settings.json").read_text())
            self.assertEqual((settings["model"], settings["effortLevel"]), ("sonnet", "low"))
            reviewer = (target / ".claude/agents/reviewer.md").read_text()
            self.assertIn("model: sonnet", reviewer)
            self.assertTrue((target / ".claude/tools/usage_report.py").is_file())

    def test_retry_history_and_eval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            repo.mkdir(exist_ok=True)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            runtime = repo / ".claude/.bounded-orchestrator"
            runtime.mkdir(parents=True)
            (runtime / ".gitignore").write_text("*\n!.gitignore\n")
            (repo / "tracked.txt").write_text("before\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], cwd=repo, check=True)
            tool = ROOT / ".claude/tools/task_ledger.py"
            def run(*args):
                return subprocess.run([sys.executable, str(tool), "--repo", str(repo), *args], text=True, capture_output=True, check=False)
            self.assertEqual(run("init").returncode, 0)
            self.assertEqual(run("add", "A", "--summary", "Repair", "--role", "implementer").returncode, 0)
            for command in (("start", "A"), ("interrupt", "A", "--evidence", "Stopped"), ("retry", "A", "--evidence", "Checked"), ("start", "A"), ("complete", "A", "--evidence", "Passed")):
                self.assertEqual(run(*command).returncode, 0)
            manifest = repo / "eval.json"
            manifest.write_text(json.dumps({"label": "focused", "argv": [sys.executable, "-c", "pass"], "timeout_seconds": 10}))
            local_eval = ROOT / ".claude/tools/local_eval.py"
            self.assertEqual(subprocess.run([sys.executable, str(local_eval), "--repo", str(repo), str(manifest)], capture_output=True).returncode, 0)
            self.assertEqual(run("require-eval", "--label", "focused").returncode, 0)
            self.assertEqual(run("check").returncode, 0)
            self.assertEqual(json.loads(run("show", "--json").stdout)["tasks"][0]["attempt_count"], 2)
            (repo / "tracked.txt").write_text("after\n")
            stale = run("check")
            self.assertEqual(stale.returncode, 2)
            self.assertIn("stale candidate", stale.stderr)

    def test_waiting_user_resume_and_mutating_eval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            runtime = repo / ".claude/.bounded-orchestrator"
            runtime.mkdir(parents=True)
            (runtime / ".gitignore").write_text("*\n!.gitignore\n")
            (repo / "tracked.txt").write_text("before\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], cwd=repo, check=True)
            tool = ROOT / ".claude/tools/task_ledger.py"
            def run(*args): return subprocess.run([sys.executable, str(tool), "--repo", str(repo), *args], text=True, capture_output=True, check=False)
            self.assertEqual(run("init").returncode, 0)
            self.assertEqual(run("add", "P", "--summary", "Pending", "--role", "implementer").returncode, 0)
            self.assertEqual(run("wait-user", "P", "--evidence", "Need answer").returncode, 0)
            self.assertEqual(run("resume", "P", "--evidence", "Answered").returncode, 0)
            self.assertEqual(run("start", "P").returncode, 0)
            self.assertEqual(run("complete", "P", "--evidence", "Done").returncode, 0)
            self.assertEqual(run("add", "A", "--summary", "Active", "--role", "implementer").returncode, 0)
            self.assertEqual(run("start", "A").returncode, 0)
            self.assertEqual(run("wait-user", "A", "--evidence", "Need choice").returncode, 0)
            self.assertEqual(run("resume", "A", "--evidence", "Chosen").returncode, 0)
            self.assertEqual(run("complete", "A", "--evidence", "Done").returncode, 0)
            tasks = {item["id"]: item for item in json.loads(run("show", "--json").stdout)["tasks"]}
            self.assertEqual(tasks["P"]["attempt_count"], 1)
            self.assertEqual(tasks["A"]["attempt_count"], 1)
            manifest = repo / "eval.json"
            manifest.write_text(json.dumps({"label": "mutates", "argv": [sys.executable, "-c", "from pathlib import Path; Path('tracked.txt').write_text('after\\n')"], "timeout_seconds": 10}))
            result = subprocess.run([sys.executable, str(ROOT / ".claude/tools/local_eval.py"), "--repo", str(repo), "--json", str(manifest)], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["outcome"], "candidate_changed")


if __name__ == "__main__":
    unittest.main()
