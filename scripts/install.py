#!/usr/bin/env python3
"""Safely install Claude Bounded Orchestrator into an existing repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
START_MARKER = "<!-- claude-bounded-orchestrator:start -->"
END_MARKER = "<!-- claude-bounded-orchestrator:end -->"
MANIFEST_RELATIVE = Path(".claude/.bounded-orchestrator/install.json")
BACKUP_RELATIVE = Path(".claude/.bounded-orchestrator/backups")
SETTINGS_RELATIVE = Path(".claude/settings.json")
SETTINGS_EXAMPLE_RELATIVE = Path(".claude/bounded-orchestrator.settings.example.json")
MANAGED_FILES = (
    Path(".claude/agents/explorer.md"),
    Path(".claude/agents/researcher.md"),
    Path(".claude/agents/implementer.md"),
    Path(".claude/agents/verifier.md"),
    Path(".claude/agents/failure-analyst.md"),
    Path(".claude/agents/qa-operator.md"),
    Path(".claude/agents/reviewer.md"),
    Path(".claude/agents/advisor.md"),
    Path(".claude/skills/ui-design/SKILL.md"),
    Path(".claude/skills/secure-change/SKILL.md"),
    Path(".claude/tools/task_ledger.py"),
    Path(".claude/.bounded-orchestrator/.gitignore"),
)
RUNTIME_IGNORE_RELATIVE = Path(".claude/.bounded-orchestrator/.gitignore")
ALLOWED_UNINSTALL_FILES = frozenset(
    path.as_posix()
    for path in (*MANAGED_FILES, SETTINGS_RELATIVE, SETTINGS_EXAMPLE_RELATIVE)
)


class InstallError(RuntimeError):
    """Expected installer failure."""


def source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def version(root: Path) -> str:
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise InstallError("VERSION is missing") from exc


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def same_file(left: Path, right: Path) -> bool:
    return left.is_file() and right.is_file() and digest(left) == digest(right)


def atomic_copy(source: Path, destination: Path, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_text(destination: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_manifest(target: Path) -> dict[str, Any]:
    path = target / MANIFEST_RELATIVE
    if not path.exists():
        return {"schema": SCHEMA_VERSION, "files": {}, "claude_block": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError(f"cannot read install manifest: {path}") from exc
    if data.get("schema") != SCHEMA_VERSION or not isinstance(data.get("files"), dict):
        raise InstallError(f"unsupported install manifest: {path}")
    return data


def remember(manifest: dict[str, Any], relative: Path, destination: Path, owned: bool) -> None:
    manifest.setdefault("files", {})[relative.as_posix()] = {"sha256": digest(destination), "owned": owned}


def backup(target: Path, destination: Path, dry_run: bool) -> Path:
    relative = destination.relative_to(target)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = target / BACKUP_RELATIVE / stamp / relative
    index = 1
    while candidate.exists():
        candidate = candidate.with_name(f"{destination.name}.{index}")
        index += 1
    if not dry_run:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, candidate)
    return candidate


def ensure_sources(root: Path) -> None:
    required = [root / item for item in MANAGED_FILES]
    required += [root / SETTINGS_RELATIVE, root / "templates/CLAUDE.block.md", root / "VERSION"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InstallError("installer source is incomplete:\n  - " + "\n  - ".join(missing))


def install_one(root: Path, target: Path, relative: Path, manifest: dict[str, Any], force: bool, dry_run: bool, output: list[str]) -> None:
    source = root / relative
    destination = target / relative
    previous = manifest.get("files", {}).get(relative.as_posix(), {})
    if destination.exists() and destination.is_dir():
        output.append(f"SKIP {relative}: destination is a directory")
    elif not destination.exists():
        output.append(f"INSTALL {relative}")
        atomic_copy(source, destination, dry_run)
        if not dry_run:
            remember(manifest, relative, destination, True)
    elif same_file(source, destination):
        output.append(f"UNCHANGED {relative}")
        if not dry_run:
            remember(manifest, relative, destination, bool(previous.get("owned")))
    elif not force:
        output.append(f"SKIP {relative}: existing file differs; use --force to replace")
    else:
        saved = backup(target, destination, dry_run)
        output.append(f"BACKUP {relative} -> {saved.relative_to(target)}")
        output.append(f"REPLACE {relative}")
        atomic_copy(source, destination, dry_run)
        if not dry_run:
            remember(manifest, relative, destination, True)


def install_settings(root: Path, target: Path, manifest: dict[str, Any], force_settings: bool, dry_run: bool, output: list[str]) -> None:
    source = root / SETTINGS_RELATIVE
    destination = target / SETTINGS_RELATIVE
    if not destination.exists():
        output.append(f"INSTALL {SETTINGS_RELATIVE}")
        atomic_copy(source, destination, dry_run)
        if not dry_run:
            remember(manifest, SETTINGS_RELATIVE, destination, True)
        return
    if same_file(source, destination):
        previous = manifest.get("files", {}).get(SETTINGS_RELATIVE.as_posix(), {})
        output.append(f"UNCHANGED {SETTINGS_RELATIVE}")
        if not dry_run:
            remember(manifest, SETTINGS_RELATIVE, destination, bool(previous.get("owned")))
        return
    if force_settings:
        saved = backup(target, destination, dry_run)
        output.append(f"BACKUP {SETTINGS_RELATIVE} -> {saved.relative_to(target)}")
        output.append(f"REPLACE {SETTINGS_RELATIVE}")
        atomic_copy(source, destination, dry_run)
        if not dry_run:
            remember(manifest, SETTINGS_RELATIVE, destination, True)
        return
    output.append(f"PRESERVE {SETTINGS_RELATIVE}")
    output.append(f"INSTALL {SETTINGS_EXAMPLE_RELATIVE} (merge manually)")
    example = target / SETTINGS_EXAMPLE_RELATIVE
    if example.exists() and not same_file(source, example) and not dry_run:
        output.append(f"SKIP {SETTINGS_EXAMPLE_RELATIVE}: existing example differs")
        return
    atomic_copy(source, example, dry_run)
    if not dry_run:
        remember(manifest, SETTINGS_EXAMPLE_RELATIVE, example, True)


def remove_managed_block(text: str) -> tuple[str, bool]:
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        return text, False
    end += len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip("\n")
    if before and after:
        result = before + "\n\n" + after
    elif before:
        result = before + "\n"
    else:
        result = after
    return result, True


def install_claude_block(root: Path, target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> None:
    destination = target / "CLAUDE.md"
    block = (root / "templates/CLAUDE.block.md").read_text(encoding="utf-8").strip()
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    cleaned, had_block = remove_managed_block(existing)
    content = (cleaned.rstrip() + "\n\n" + block + "\n").lstrip("\n")
    if existing == content:
        output.append("UNCHANGED CLAUDE.md block")
    else:
        output.append("UPDATE CLAUDE.md block" if had_block else "INSTALL CLAUDE.md block")
        atomic_text(destination, content, dry_run)
    if not dry_run:
        manifest["claude_block"] = True


def save_manifest(target: Path, manifest: dict[str, Any], root: Path, dry_run: bool) -> None:
    if dry_run:
        return
    manifest.update({"schema": SCHEMA_VERSION, "tool_version": version(root), "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
    atomic_text(target / MANIFEST_RELATIVE, json.dumps(manifest, indent=2, sort_keys=True) + "\n", False)


def safe_uninstall_path(target: Path, relative: Path) -> Path:
    """Return a contained non-symlink path or reject the uninstall."""
    if relative.is_absolute() or ".." in relative.parts:
        raise InstallError(f"unsafe uninstall path: {relative}")
    current = target
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise InstallError(f"refusing uninstall through symlinked directory: {current}")
    candidate = target / relative
    if candidate.is_symlink():
        raise InstallError(f"refusing to uninstall symlink: {candidate}")
    try:
        candidate.resolve(strict=False).relative_to(target)
    except ValueError as exc:
        raise InstallError(f"uninstall path escapes target: {relative}") from exc
    return candidate


def uninstall(target: Path, manifest: dict[str, Any], dry_run: bool, output: list[str]) -> None:
    entries = manifest.get("files", {})
    safe_paths: dict[str, Path] = {}
    for name, entry in entries.items():
        if not isinstance(name, str) or name not in ALLOWED_UNINSTALL_FILES:
            raise InstallError(f"manifest contains unmanaged uninstall path: {name!r}")
        if not isinstance(entry, dict):
            raise InstallError(f"manifest contains invalid entry for: {name}")
        safe_paths[name] = safe_uninstall_path(target, Path(name))
    manifest_path = safe_uninstall_path(target, MANIFEST_RELATIVE)
    claude = safe_uninstall_path(target, Path("CLAUDE.md"))

    for name, entry in sorted(entries.items(), reverse=True):
        path = safe_paths[name]
        if not entry.get("owned") or not path.exists():
            continue
        if Path(name) == RUNTIME_IGNORE_RELATIVE:
            output.append(f"KEEP {name}: protects retained private runtime data")
            continue
        if not path.is_file() or digest(path) != entry.get("sha256"):
            output.append(f"KEEP {name}: modified after installation")
            continue
        output.append(f"REMOVE {name}")
        if not dry_run:
            path.unlink()
    if manifest.get("claude_block") and claude.is_file():
        current = claude.read_text(encoding="utf-8")
        cleaned, removed = remove_managed_block(current)
        if removed:
            output.append("REMOVE CLAUDE.md block")
            if not dry_run:
                if cleaned:
                    atomic_text(claude, cleaned, False)
                else:
                    claude.unlink()
    output.append(f"REMOVE {MANIFEST_RELATIVE}")
    if not dry_run and manifest_path.exists():
        manifest_path.unlink()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="existing project directory")
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
    parser.add_argument("--force", action="store_true", help="replace conflicting managed files after backup")
    parser.add_argument("--force-settings", action="store_true", help="replace .claude/settings.json after backup")
    parser.add_argument("--uninstall", action="store_true", help="remove unchanged files installed by this tool")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = source_root()
    try:
        target = args.target.expanduser().resolve()
        if not target.is_dir():
            raise InstallError(f"target must be an existing directory: {target}")
        if target == root:
            raise InstallError("target must differ from the installer repository")
        ensure_sources(root)
        manifest = load_manifest(target)
        output: list[str] = []
        if args.uninstall:
            if not (target / MANIFEST_RELATIVE).exists():
                raise InstallError("no installation manifest found")
            uninstall(target, manifest, args.dry_run, output)
        else:
            for relative in MANAGED_FILES:
                install_one(root, target, relative, manifest, args.force, args.dry_run, output)
            install_settings(root, target, manifest, args.force_settings, args.dry_run, output)
            install_claude_block(root, target, manifest, args.dry_run, output)
            save_manifest(target, manifest, root, args.dry_run)
        print("\n".join(output))
        return 0
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
