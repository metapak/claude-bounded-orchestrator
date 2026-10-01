from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("launch_dashboard", ROOT / "launchers/launch_dashboard.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class MacLauncherTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX shell launcher")
    def test_extracted_folder_picker_only_exits_quietly_on_cancel(self) -> None:
        original = (ROOT / "launchers/Bounded Orchestrator.app/Contents/MacOS/launch").read_text()
        for error, expected_code, expected_calls in (
            ("User canceled. (-128)", 0, 1),
            ("Automation permission denied. (-1743)", 1, 2),
        ):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shell = root / "launchers/Bounded Orchestrator.app/Contents/MacOS/launch"
                shell.parent.mkdir(parents=True)
                stub = root / "osascript"
                stub.write_text(
                    "#!/bin/sh\n"
                    "printf '%s\\n' \"$*\" >> \"$TRACE\"\n"
                    f"if [ \"$#\" -eq 2 ]; then printf '%s\\n' '{error}' >&2; exit 1; fi\n",
                    encoding="utf-8",
                )
                stub.chmod(0o755)
                shell.write_text(original.replace("/usr/bin/osascript", str(stub)), encoding="utf-8")
                trace = root / "calls"
                result = subprocess.run(
                    ["/bin/sh", str(shell)],
                    env={**os.environ, "TRACE": str(trace)},
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected_code)
                self.assertEqual(len(trace.read_text().splitlines()), expected_calls)

    def test_app_is_visible_and_picker_does_not_activate_background_script(self) -> None:
        plist = ROOT / "launchers/Bounded Orchestrator.app/Contents/Info.plist"
        self.assertFalse(plistlib.loads(plist.read_bytes())["LSUIElement"])
        chosen = subprocess.CompletedProcess([], 0, stdout="/tmp/project folder/\n", stderr="")
        with patch.object(launcher.sys, "platform", "darwin"), patch.object(
            launcher.subprocess, "run", return_value=chosen
        ) as run:
            self.assertEqual(launcher.choose_project(), Path("/tmp/project folder/"))
        self.assertIn("choose folder", run.call_args.args[0][2])
        self.assertNotIn("activate", run.call_args.args[0][2])

    def test_opens_full_tokenized_url_after_server_reports_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entry = Path(directory) / "server.py"
            entry.write_text(
                "import time\nprint('Local console: http://127.0.0.1:43210/#private-token', flush=True)\ntime.sleep(0.2)\n",
                encoding="utf-8",
            )
            with patch.object(launcher.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as opened:
                self.assertEqual(launcher.run_mac_console(entry, Path(directory)), 0)
            self.assertEqual(opened.call_args.args[0], ["/usr/bin/open", "http://127.0.0.1:43210/#private-token"])

    def test_reports_server_start_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entry = Path(directory) / "server.py"
            entry.write_text("raise RuntimeError('startup failed')\n", encoding="utf-8")
            with patch.object(launcher, "alert") as alert:
                self.assertEqual(launcher.run_mac_console(entry, Path(directory)), 1)
            self.assertIn("startup failed", alert.call_args.args[1])

    def test_browser_failure_keeps_server_live_and_reports_full_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            entry = Path(directory) / "server.py"
            failure = subprocess.CompletedProcess([], 1, stderr="Launch Services error")
            server = Mock()
            server.poll.return_value = None
            server.wait.return_value = 0

            def start_server(*_args, **kwargs):
                kwargs["stdout"].write("Local console: http://127.0.0.1:43210/#private-token\n")
                kwargs["stdout"].flush()
                return server

            def inspect_alert(_title: str, message: str) -> None:
                self.assertIn("Open http://127.0.0.1:43210/#private-token", message)
                self.assertIn("Launch Services error", message)
                server.terminate.assert_not_called()
                server.wait.assert_not_called()

            with patch.object(launcher.subprocess, "Popen", side_effect=start_server), patch.object(
                launcher.subprocess, "run", return_value=failure
            ), patch.object(launcher, "alert", side_effect=inspect_alert):
                self.assertEqual(launcher.run_mac_console(entry, Path(directory)), 1)
            server.wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
