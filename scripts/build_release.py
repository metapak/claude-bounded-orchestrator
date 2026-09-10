#!/usr/bin/env python3
"""Build deterministic source, macOS/Linux, and Windows zip archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "claude-bounded-orchestrator"
EXCLUDED_PARTS = {".git", "__pycache__", "dist"}


def files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*") if path.is_file() and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts) and path.suffix not in {".pyc", ".pyo"})


def payload(path: Path, windows: bool) -> bytes:
    data = path.read_bytes()
    if windows and path.suffix in {".ps1", ".cmd"}:
        return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return data


def write_archive(path: Path, members: list[Path], *, windows: bool, start_file: tuple[str, str] | None = None) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in members:
            relative = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{NAME}/{relative}", (2026, 1, 1, 0, 0, 0))
            mode = 0o755 if relative in {"setup.command", "scripts/install.sh", "scripts/install.py", "scripts/build_release.py", "scripts/validate.py", ".claude/tools/task_ledger.py"} else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, payload(source, windows))
        if start_file:
            name, text = start_file
            info = zipfile.ZipInfo(f"{NAME}/{name}", (2026, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, text.replace("\n", "\r\n") if windows else text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    members = files()
    archives = [
        (output / f"{NAME}-v{version}-source.zip", False, None),
        (output / f"{NAME}-v{version}-macos-linux.zip", False, ("START-HERE-MACOS-LINUX.txt", "Read INSTALL-MACOS.md, then preview with:\npython3 scripts/install.py /path/to/project --dry-run\n")),
        (output / f"{NAME}-v{version}-windows.zip", True, ("START-HERE-WINDOWS.txt", "Read INSTALL-WINDOWS.md, then preview with:\n.\\scripts\\install.ps1 -Target C:\\path\\to\\project -DryRun\n")),
    ]
    checksums: dict[str, str] = {}
    for archive, windows, start in archives:
        write_archive(archive, members, windows=windows, start_file=start)
        checksums[archive.name] = hashlib.sha256(archive.read_bytes()).hexdigest()
        print(archive)
    (output / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
