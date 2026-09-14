from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USAGE = ROOT / ".claude/tools/usage_report.py"
LOCAL_EVAL = ROOT / ".claude/tools/local_eval.py"


class UsageAndEvalTests(unittest.TestCase):
    def test_usage_is_unavailable_without_explicit_telemetry_input(self) -> None:
        result = subprocess.run([sys.executable, str(USAGE), "--json"], text=True, capture_output=True, check=False)
        self.assertEqual(json.loads(result.stdout)["status"], "unavailable")

    def test_usage_reads_synthetic_otlp_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.json"
            path.write_text(json.dumps({"resourceMetrics": [{"scopeMetrics": [{"metrics": [{"name": "claude_code.token.usage", "sum": {"aggregationTemporality": 1, "dataPoints": [{"asInt": "7", "attributes": [{"key": "model", "value": {"stringValue": "claude-test"}}, {"key": "type", "value": {"stringValue": "input"}}]}]}}]}]}]}))
            result = subprocess.run([sys.executable, str(USAGE), "--input", str(path), "--json"], text=True, capture_output=True, check=False)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "available")
            self.assertEqual(payload["groups"][0]["value"], 7)

    def test_delta_cumulative_streams_and_resets_are_accounted_separately(self) -> None:
        attrs = [{"key": "model", "value": {"stringValue": "claude-test"}}, {"key": "type", "value": {"stringValue": "input"}}]
        def metric(mode, values):
            return {"name": "claude_code.token.usage", "sum": {"aggregationTemporality": mode, "dataPoints": [{"asInt": str(value), "attributes": attrs} for value in values]}}
        document = {"resourceMetrics": [
            {"resource": {"attributes": [{"key": "session.id", "value": {"stringValue": "cumulative-one"}}]}, "scopeMetrics": [{"metrics": [metric(2, [100, 150])]}]},
            {"resource": {"attributes": [{"key": "session.id", "value": {"stringValue": "delta-one"}}]}, "scopeMetrics": [{"metrics": [metric(1, [100, 150])]}]},
            {"resource": {"attributes": [{"key": "session.id", "value": {"stringValue": "reset-stream"}}]}, "scopeMetrics": [{"metrics": [metric(2, [40, 10])]}]},
        ]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.json"
            path.write_text(json.dumps(document))
            payload = json.loads(subprocess.run([sys.executable, str(USAGE), "--input", str(path), "--json"], text=True, capture_output=True, check=True).stdout)
            self.assertEqual(payload["totals"]["input"], 450)
            self.assertEqual(payload["delta_points"], 2)
            self.assertEqual(payload["cumulative_points"], 4)
            self.assertEqual(payload["counter_resets_observed"], 1)

    def test_cumulative_start_time_change_opens_a_new_epoch(self) -> None:
        attrs = [{"key": "model", "value": {"stringValue": "claude-test"}}, {"key": "type", "value": {"stringValue": "input"}}]
        points = [
            {"asInt": "100", "startTimeUnixNano": "1000", "attributes": attrs},
            {"asInt": "150", "startTimeUnixNano": "2000", "attributes": attrs},
        ]
        document = {"resourceMetrics": [{"scopeMetrics": [{"metrics": [{
            "name": "claude_code.token.usage",
            "sum": {"aggregationTemporality": 2, "dataPoints": points},
        }]}]}]}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "metrics.json"
            path.write_text(json.dumps(document))
            payload = json.loads(subprocess.run(
                [sys.executable, str(USAGE), "--input", str(path), "--json"],
                text=True, capture_output=True, check=True,
            ).stdout)
            self.assertEqual(payload["totals"]["input"], 250)
            self.assertEqual(payload["counter_resets_observed"], 1)

    def test_local_eval_writes_digest_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            manifest = repo / "eval.json"
            manifest.write_text(json.dumps({"label": "unit", "argv": [sys.executable, "-c", "print('ok')"], "timeout_seconds": 10}))
            result = subprocess.run([sys.executable, str(LOCAL_EVAL), "--repo", str(repo), "--json", str(manifest)], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((repo / ".claude/.bounded-orchestrator/evals/unit.json").read_text())
            self.assertEqual(summary["outcome"], "pass")
            self.assertNotIn("sanitized_tail", summary)


if __name__ == "__main__":
    unittest.main()
